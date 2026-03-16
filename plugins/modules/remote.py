#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: remote
short_description: Manage LINSTOR remotes for backup shipping
version_added: "0.10.0"
description:
  - Creates, modifies, or deletes LINSTOR remotes used as backup shipping targets.
  - Supports S3-compatible, LINSTOR-to-LINSTOR, and EBS remote types.
  - Idempotent. If the remote already exists, only changed parameters are modified.
  - The remote type cannot be changed after creation. The module warns if a
    type mismatch is detected.
  - Use C(state=query) to check whether a remote exists and retrieve its properties.
  - S3 and EBS credentials (O(access_key), O(secret_key)) are write-only.
    The API does not return them, so the module cannot detect credential changes
    and always sends them on modify operations.
options:
  name:
    description: Name of the remote.
    type: str
    required: true
  state:
    description: Desired state of the remote.
    type: str
    default: present
    choices: [present, absent, query]
  type:
    description:
      - Remote type.
      - Required when C(state=present).
    type: str
    choices: [s3, linstor, ebs]
  endpoint:
    description:
      - S3 or EBS endpoint URL.
      - Required for C(type=s3). Optional for C(type=ebs).
    type: str
  bucket:
    description:
      - S3 bucket name.
      - Required for C(type=s3).
    type: str
  region:
    description:
      - S3 or EBS region.
      - Required for C(type=s3). Optional for C(type=ebs).
    type: str
  access_key:
    description:
      - S3 or EBS access key.
      - Required for C(type=s3) and C(type=ebs) on creation.
      - Write-only. The API does not return this value, so the module
        cannot detect changes.
    type: str
  secret_key:
    description:
      - S3 or EBS secret key.
      - Required for C(type=s3) and C(type=ebs) on creation.
      - Write-only. The API does not return this value, so the module
        cannot detect changes.
    type: str
  use_path_style:
    description:
      - Use path-style S3 addressing instead of virtual-hosted-style.
      - Only applicable for C(type=s3).
    type: bool
    default: false
  url:
    description:
      - LINSTOR controller URL for LINSTOR-to-LINSTOR remotes.
      - Required for C(type=linstor).
      - The LINSTOR controller normalizes URLs internally, so the stored
        value may differ from the value provided (for example
        C(linstor://10.0.0.1) may become C(http://linstor:3370)). URL
        changes are not detected by the module. To change the URL, delete
        and recreate the remote.
    type: str
  passphrase:
    description:
      - Encryption passphrase for LINSTOR-to-LINSTOR remote connections.
      - Only applicable for C(type=linstor).
    type: str
  cluster_id:
    description:
      - Cluster ID of the remote LINSTOR cluster.
      - Only applicable for C(type=linstor).
      - Required for LINSTOR-to-LINSTOR backup shipping. Each cluster must
        have a remote configured with the peer cluster's ID. Retrieve the
        local cluster ID from the C(Cluster/LocalID) controller property.
      - Write-only. The API does not return this value.
    type: str
  availability_zone:
    description:
      - AWS availability zone.
      - Required for C(type=ebs).
    type: str
  controllers:
    description:
      - Comma-separated list of LINSTOR controller URIs.
      - If omitted, reads from C(LS_CONTROLLERS) env, then
        C(/etc/linstor/linstor-client.conf), then falls back to
        C(linstor://localhost).
    type: str
requirements:
  - python-linstor
notes:
  - This module issues cluster-wide API calls via C(python-linstor) to the LINSTOR controller.
  - Requires the L(linstor-api-py,https://github.com/LINBIT/linstor-api-py) package
    (C(python-linstor)) on the play host.
  - "Use C(run_once=true) or a single-host play such as C(hosts: linstor_controllers[0])."
  - Credentials (O(access_key), O(secret_key), O(passphrase)) and O(cluster_id)
    are write-only. The LINSTOR API does not return them, so the module cannot
    detect changes to these values.
  - "LINSTOR-to-LINSTOR backup shipping requires bidirectional remotes: each
    cluster must have a remote pointing at the other with the peer's
    O(cluster_id) set. Without this, shipping fails with 'Unknown Cluster'."
seealso:
  - name: LINSTOR User's Guide - Backups
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-backups
    description: Backup and remote concepts in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Create an S3-compatible remote
  linbit.linstor.remote:
    name: remote-s3-backup
    type: s3
    endpoint: https://s3.us-east-1.amazonaws.com
    bucket: linstor-backups
    region: us-east-1
    access_key: "{{ vault_s3_access_key }}"
    secret_key: "{{ vault_s3_secret_key }}"
  run_once: true  # noqa: run-once[task]

- name: Create an S3 remote with path-style addressing (MinIO)
  linbit.linstor.remote:
    name: remote-minio
    type: s3
    endpoint: https://minio.example.com:9000
    bucket: drbd-backups
    region: us-east-1
    access_key: "{{ vault_minio_access }}"
    secret_key: "{{ vault_minio_secret }}"
    use_path_style: true
  run_once: true  # noqa: run-once[task]

- name: Create a LINSTOR-to-LINSTOR remote with cluster ID
  linbit.linstor.remote:
    name: remote-dr-site
    type: linstor
    url: linstor://dr-controller.example.com
    cluster_id: "{{ dr_cluster_id }}"
  run_once: true  # noqa: run-once[task]

- name: Create the reverse remote on the DR cluster for bidirectional shipping
  linbit.linstor.remote:
    name: remote-primary-site
    type: linstor
    url: linstor://primary-controller.example.com
    cluster_id: "{{ primary_cluster_id }}"
    controllers: linstor://dr-controller.example.com
  run_once: true  # noqa: run-once[task]

- name: Create an EBS remote
  linbit.linstor.remote:
    name: remote-ebs
    type: ebs
    availability_zone: us-east-1a
    access_key: "{{ vault_aws_access_key }}"
    secret_key: "{{ vault_aws_secret_key }}"
  run_once: true  # noqa: run-once[task]

- name: Query a remote
  linbit.linstor.remote:
    name: remote-s3-backup
    state: query
  register: remote_result
  run_once: true  # noqa: run-once[task]

- name: Remove a remote
  linbit.linstor.remote:
    name: remote-s3-backup
    state: absent
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
name:
  description: Name of the remote.
  type: str
  returned: always
exists:
  description: Whether the remote exists. Only returned with C(state=query).
  type: bool
  returned: query
type:
  description: Remote type (s3, linstor, or ebs).
  type: str
  returned: success
url:
  description: LINSTOR controller URL for LINSTOR-to-LINSTOR remotes.
  type: str
  returned: query, when type=linstor
endpoint:
  description: S3 or EBS endpoint URL.
  type: str
  returned: query, when type=s3 or type=ebs
bucket:
  description: S3 bucket name.
  type: str
  returned: query, when type=s3
region:
  description: S3 or EBS region.
  type: str
  returned: query, when type=s3 or type=ebs
availability_zone:
  description: AWS availability zone.
  type: str
  returned: query, when type=ebs
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
    check_api_response,
)


def find_remote(lin, name):
    """Find a remote by name across all remote types.

    Returns (type_str, remote_obj) or (None, None).
    """
    result = lin.remote_list()
    if not result:
        return None, None

    remote_list = result[0] if isinstance(result, list) else result

    for remote in getattr(remote_list, 's3_remotes', []):
        if remote.remote_name == name:
            return 's3', remote
    for remote in getattr(remote_list, 'linstor_remotes', []):
        if remote.remote_name == name:
            return 'linstor', remote
    for remote in getattr(remote_list, 'ebs_remotes', []):
        if remote.remote_name == name:
            return 'ebs', remote

    return None, None


def s3_needs_modify(existing, module):
    """Check if S3 remote parameters differ from existing state."""
    if module.params.get('endpoint') and existing.endpoint != module.params['endpoint']:
        return True
    if module.params.get('bucket') and existing.bucket != module.params['bucket']:
        return True
    if module.params.get('region') and existing.region != module.params['region']:
        return True
    # Credentials are write-only; always send if provided
    if module.params.get('access_key') or module.params.get('secret_key'):
        return True
    return False


def linstor_needs_modify(existing, module):
    """Check if LINSTOR remote parameters differ from existing state.

    The LINSTOR controller normalizes URLs internally (for example
    ``linstor://192.168.1.10`` becomes ``http://linstor:3370``), so
    the stored URL cannot be compared to the user-supplied value.
    URL changes are skipped: to change the URL, delete and recreate
    the remote.

    Passphrase and cluster_id are write-only: the API does not return
    them, so they cannot be compared.  They are always sent during
    modify when provided, but do not on their own trigger a modify.
    """
    # Passphrase is write-only; always send if provided
    if module.params.get('passphrase'):
        return True
    return False


def ebs_needs_modify(existing, module):
    """Check if EBS remote parameters differ from existing state."""
    if module.params.get('endpoint') and existing.endpoint != module.params['endpoint']:
        return True
    if module.params.get('region') and getattr(existing, 'region', None) != module.params['region']:
        return True
    if module.params.get('availability_zone') and getattr(existing, 'availability_zone', None) != module.params['availability_zone']:
        return True
    # Credentials are write-only; always send if provided
    if module.params.get('access_key') or module.params.get('secret_key'):
        return True
    return False


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        state=dict(type='str', default='present', choices=['present', 'absent', 'query']),
        type=dict(type='str', choices=['s3', 'linstor', 'ebs']),
        endpoint=dict(type='str'),
        bucket=dict(type='str'),
        region=dict(type='str'),
        access_key=dict(type='str', no_log=True),
        secret_key=dict(type='str', no_log=True),
        use_path_style=dict(type='bool', default=False),
        url=dict(type='str'),
        passphrase=dict(type='str', no_log=True),
        cluster_id=dict(type='str'),
        availability_zone=dict(type='str'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ('state', 'present', ['type']),
        ],
    )

    name = module.params['name']
    state = module.params['state']
    remote_type = module.params.get('type')

    lin = get_linstor_connection(module)

    try:
        existing_type, existing_remote = find_remote(lin, name)

        if state == 'query':
            if existing_type is None:
                module.exit_json(changed=False, name=name, exists=False)
            result = dict(changed=False, name=name, exists=True,
                          type=existing_type)
            if existing_type == 's3':
                result['endpoint'] = getattr(existing_remote, 'endpoint', None)
                result['bucket'] = getattr(existing_remote, 'bucket', None)
                result['region'] = getattr(existing_remote, 'region', None)
            elif existing_type == 'linstor':
                result['url'] = getattr(existing_remote, 'url', None)
            elif existing_type == 'ebs':
                result['endpoint'] = getattr(existing_remote, 'endpoint', None)
                result['region'] = getattr(existing_remote, 'region', None)
                result['availability_zone'] = getattr(
                    existing_remote, 'availability_zone', None)
            module.exit_json(**result)

        if state == 'absent':
            if existing_type is None:
                module.exit_json(changed=False, name=name)
            if module.check_mode:
                module.exit_json(changed=True, name=name,
                                 type=existing_type)
            replies = lin.remote_delete(name)
            check_api_response(module, replies, 'delete remote %s' % name)
            module.exit_json(changed=True, name=name, type=existing_type)

        # state == 'present'
        # Validate type-specific required parameters
        if remote_type == 's3':
            missing = [p for p in ('endpoint', 'bucket', 'region', 'access_key', 'secret_key')
                       if not module.params.get(p)]
            if existing_type is None and missing:
                module.fail_json(
                    msg="type=s3 requires: %s" % ', '.join(missing))
        elif remote_type == 'linstor':
            if existing_type is None and not module.params.get('url'):
                module.fail_json(msg="type=linstor requires: url")
        elif remote_type == 'ebs':
            missing = [p for p in ('availability_zone', 'access_key', 'secret_key')
                       if not module.params.get(p)]
            if existing_type is None and missing:
                module.fail_json(
                    msg="type=ebs requires: %s" % ', '.join(missing))

        if existing_type is not None:
            # Remote exists: check type mismatch
            if existing_type != remote_type:
                module.warn(
                    "Remote '%s' exists with type '%s' but '%s' was requested. "
                    "Remote type cannot be changed after creation." % (
                        name, existing_type, remote_type))
                module.exit_json(
                    changed=False, name=name, type=existing_type)

            # Check if modify is needed
            needs_modify = False
            if remote_type == 's3':
                needs_modify = s3_needs_modify(existing_remote, module)
            elif remote_type == 'linstor':
                needs_modify = linstor_needs_modify(existing_remote, module)
            elif remote_type == 'ebs':
                needs_modify = ebs_needs_modify(existing_remote, module)

            if not needs_modify:
                module.exit_json(changed=False, name=name, type=remote_type)

            if module.check_mode:
                module.exit_json(changed=True, name=name, type=remote_type)

            # Modify existing remote
            if remote_type == 's3':
                kwargs = {}
                if module.params.get('endpoint'):
                    kwargs['endpoint'] = module.params['endpoint']
                if module.params.get('region'):
                    kwargs['region'] = module.params['region']
                if module.params.get('bucket'):
                    kwargs['bucket'] = module.params['bucket']
                if module.params.get('access_key'):
                    kwargs['access_key'] = module.params['access_key']
                if module.params.get('secret_key'):
                    kwargs['secret_key'] = module.params['secret_key']
                replies = lin.remote_modify_s3(name, **kwargs)
            elif remote_type == 'linstor':
                kwargs = {}
                if module.params.get('url'):
                    kwargs['url'] = module.params['url']
                if module.params.get('passphrase'):
                    kwargs['passphrase'] = module.params['passphrase']
                if module.params.get('cluster_id'):
                    kwargs['cluster_id'] = module.params['cluster_id']
                replies = lin.remote_modify_linstor(name, **kwargs)
            elif remote_type == 'ebs':
                kwargs = {}
                if module.params.get('endpoint'):
                    kwargs['endpoint'] = module.params['endpoint']
                if module.params.get('region'):
                    kwargs['region'] = module.params['region']
                if module.params.get('availability_zone'):
                    kwargs['availability_zone'] = module.params['availability_zone']
                if module.params.get('access_key'):
                    kwargs['access_key'] = module.params['access_key']
                if module.params.get('secret_key'):
                    kwargs['secret_key'] = module.params['secret_key']
                replies = lin.remote_modify_ebs(name, **kwargs)

            check_api_response(module, replies,
                               'modify remote %s' % name)
            module.exit_json(changed=True, name=name, type=remote_type)

        # Remote does not exist: create it
        if module.check_mode:
            module.exit_json(changed=True, name=name, type=remote_type)

        if remote_type == 's3':
            replies = lin.remote_create_s3(
                name,
                endpoint=module.params['endpoint'],
                region=module.params['region'],
                bucket=module.params['bucket'],
                access_key=module.params['access_key'],
                secret_key=module.params['secret_key'],
                use_path_style=module.params['use_path_style'],
            )
        elif remote_type == 'linstor':
            kwargs = dict(
                remote_name=name,
                url=module.params['url'],
            )
            if module.params.get('passphrase'):
                kwargs['passphrase'] = module.params['passphrase']
            if module.params.get('cluster_id'):
                kwargs['cluster_id'] = module.params['cluster_id']
            replies = lin.remote_create_linstor(**kwargs)
        elif remote_type == 'ebs':
            kwargs = dict(
                remote_name=name,
                availability_zone=module.params['availability_zone'],
                access_key=module.params['access_key'],
                secret_key=module.params['secret_key'],
            )
            if module.params.get('endpoint'):
                kwargs['endpoint'] = module.params['endpoint']
            if module.params.get('region'):
                kwargs['region'] = module.params['region']
            replies = lin.remote_create_ebs(**kwargs)

        check_api_response(module, replies, 'create remote %s' % name)
        module.exit_json(changed=True, name=name, type=remote_type)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error managing remote '%s': %s" % (name, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
