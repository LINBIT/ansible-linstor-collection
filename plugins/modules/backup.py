#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: backup
short_description: Create or delete LINSTOR backups on a remote
version_added: "0.9.7"
description:
  - Creates or deletes LINSTOR backups on a remote.
  - C(state=present) creates a new S3 backup and is NOT idempotent;
    each invocation produces a new point-in-time backup.
  - C(state=absent) deletes backups matching the supplied criteria.
    Idempotent when invoked with O(backup_id).
  - Read operations are exposed by M(linbit.linstor.backup_info).
  - Shipping, restoring, and aborting are exposed by
    M(linbit.linstor.backup_ship), M(linbit.linstor.backup_restore),
    and M(linbit.linstor.backup_abort).
options:
  remote:
    description: Name of the remote where the backup is stored.
    type: str
    required: true
  state:
    description: Whether the backup should be created or deleted.
    type: str
    default: present
    choices: [present, absent]
  resource:
    description:
      - Resource name.
      - Required when C(state=present).
      - Optional filter for C(state=absent).
    type: str
  incremental:
    description:
      - Create an incremental backup (true) or full backup (false).
      - Only used when C(state=present).
    type: bool
    default: true
  node:
    description:
      - Preferred node for the backup operation.
      - Only used when C(state=present).
    type: str
  snap_name:
    description:
      - Snapshot name override for the underlying LINSTOR snapshot.
      - Only used when C(state=present).
    type: str
  backup_id:
    description:
      - Specific backup ID to delete.
      - Used when C(state=absent).
    type: str
  backup_id_prefix:
    description:
      - Backup ID prefix; deletes all matching backups.
      - Only used when C(state=absent).
    type: str
  cascade:
    description:
      - Cascade delete to dependent backups.
      - Only used when C(state=absent).
    type: bool
    default: false
  timestamp:
    description:
      - Delete backups older than this timestamp.
      - Only used when C(state=absent).
    type: str
  all_linstor:
    description:
      - Delete all LINSTOR-managed backups on the remote.
      - Only used when C(state=absent).
    type: bool
    default: false
  all_local_cluster:
    description:
      - Delete all backups created by this local LINSTOR cluster.
      - Only used when C(state=absent).
    type: bool
    default: false
  s3_key:
    description:
      - Delete a specific S3 key.
      - Only used when C(state=absent).
    type: str
  dryrun:
    description:
      - Simulate the delete operation without actually deleting.
      - Only used when C(state=absent).
    type: bool
  keep_snaps:
    description:
      - Keep local snapshots when deleting backups.
      - Only used when C(state=absent).
    type: bool
  controllers:
    description:
      - Comma-separated list of LINSTOR controller URIs.
      - If omitted, reads from C(LS_CONTROLLERS) env, then
        C(/etc/linstor/linstor-client.conf), then falls back to
        C(linstor://localhost).
    type: str
  auth_token:
    description:
      - LINSTOR auth token for clusters with token authentication enabled.
      - If omitted, reads C(auth-token) from C(linstor-client.conf) (user
        configuration overriding system configuration), then falls back to
        C(/var/lib/linstor.d/auth.json) on satellite nodes.
    type: str
requirements:
  - python-linstor
notes:
  - "Recommended play structure: dedicate a play with a single host such
    as C(hosts: linstor_controllers[0]) and C(connection: local) for
    directly accessing the LINSTOR controller, or set C(delegate_to: localhost)
    on the task (or a wrapping C(block:)) when mixing into a multi-host play."
  - "The collection's action plugins force C(become: false) on the task
    automatically, so a parent play's C(become: true) does not bleed into
    the delegated call."
  - This module issues API calls via C(python-linstor) to the LINSTOR controller.
  - Requires the L(linstor-api-py,https://github.com/LINBIT/linstor-api-py) package
    (C(python-linstor)) on the play host.
  - "For cluster-wide tasks use C(run_once=true) or a single-host play such as C(hosts: linstor_controllers[0])."
  - C(state=present) only works with S3-compatible remotes. For
    LINSTOR-to-LINSTOR remotes, use M(linbit.linstor.backup_ship) instead.
  - The M(linbit.linstor.remote) module must be used first to configure
    the remote target before creating backups.
seealso:
  - module: linbit.linstor.backup_info
  - module: linbit.linstor.backup_ship
  - module: linbit.linstor.backup_restore
  - module: linbit.linstor.backup_abort
  - module: linbit.linstor.remote
  - module: linbit.linstor.schedule
  - name: LINSTOR User's Guide - Backups
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-backups
    description: Backup concepts and operations in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Create a full backup
  linbit.linstor.backup:
    remote: remote-s3-backup
    resource: res-data
    incremental: false
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Create an incremental backup
  linbit.linstor.backup:
    remote: remote-s3-backup
    resource: res-data
  run_once: true  # noqa: run-once[task]

- name: Delete a specific backup
  linbit.linstor.backup:
    remote: remote-s3-backup
    state: absent
    backup_id: res-data_20240101_120000
  run_once: true  # noqa: run-once[task]

- name: Delete all backups from this cluster
  linbit.linstor.backup:
    remote: remote-s3-backup
    state: absent
    all_local_cluster: true
  run_once: true  # noqa: run-once[task]

# Delegate to a cluster controller when the control node cannot reach
# the LINSTOR API directly (SSH jump host, segmented management network)
- name: Create an S3 backup via a delegated controller
  linbit.linstor.backup:
    remote: remote-s3-backup
    resource: res-data
  delegate_to: controller-0
  environment:
    LS_CONTROLLERS: linstor://localhost
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
remote:
  description: Name of the remote.
  type: str
  returned: always
resource:
  description: Resource name passed in.
  type: str
  returned: when supplied
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
    check_api_response,
)


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        remote=dict(type='str', required=True),
        state=dict(type='str', default='present',
                   choices=['present', 'absent']),
        resource=dict(type='str'),
        incremental=dict(type='bool', default=True),
        node=dict(type='str'),
        snap_name=dict(type='str'),
        backup_id=dict(type='str'),
        backup_id_prefix=dict(type='str'),
        cascade=dict(type='bool', default=False),
        timestamp=dict(type='str'),
        all_linstor=dict(type='bool', default=False),
        all_local_cluster=dict(type='bool', default=False),
        s3_key=dict(type='str', no_log=False),
        dryrun=dict(type='bool'),
        keep_snaps=dict(type='bool'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ('state', 'present', ['resource']),
        ],
    )

    remote = module.params['remote']
    state = module.params['state']
    resource = module.params.get('resource')

    if module.check_mode:
        module.exit_json(changed=True, remote=remote, resource=resource)

    lin = get_linstor_connection(module)

    try:
        if state == 'present':
            kwargs = dict(
                remote_name=remote,
                resource_name=resource,
                incremental=module.params['incremental'],
            )
            if module.params.get('node'):
                kwargs['node_name'] = module.params['node']
            if module.params.get('snap_name'):
                kwargs['snap_name'] = module.params['snap_name']

            replies = lin.backup_create(**kwargs)
            check_api_response(module, replies,
                               'create backup of %s to %s' % (resource, remote))
            module.exit_json(changed=True, remote=remote, resource=resource)

        elif state == 'absent':
            kwargs = dict(remote_name=remote)
            if module.params.get('backup_id'):
                kwargs['bak_id'] = module.params['backup_id']
            if module.params.get('backup_id_prefix'):
                kwargs['bak_id_prefix'] = module.params['backup_id_prefix']
            if module.params['cascade']:
                kwargs['cascade'] = True
            if module.params.get('timestamp'):
                kwargs['timestamp'] = module.params['timestamp']
            if module.params.get('resource'):
                kwargs['resource_name'] = module.params['resource']
            if module.params.get('node'):
                kwargs['node_name'] = module.params['node']
            if module.params['all_linstor']:
                kwargs['all_linstor'] = True
            if module.params['all_local_cluster']:
                kwargs['all_local_cluster'] = True
            if module.params.get('s3_key'):
                kwargs['s3_key'] = module.params['s3_key']
            if module.params.get('dryrun') is not None:
                kwargs['dryrun'] = module.params['dryrun']
            if module.params.get('keep_snaps') is not None:
                kwargs['keep_snaps'] = module.params['keep_snaps']

            replies = lin.backup_delete(**kwargs)
            check_api_response(module, replies,
                               'delete backup from %s' % remote)
            module.exit_json(changed=True, remote=remote, resource=resource)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error managing backup on remote '%s': %s" % (
                remote, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
