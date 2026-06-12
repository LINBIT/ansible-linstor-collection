#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: remote_info
short_description: Query LINSTOR remotes
version_added: "1.0.0"
description:
  - Returns LINSTOR remotes used for backup shipping (S3, LINSTOR-to-LINSTOR, EBS).
  - Read-only; C(changed) is always C(false).
  - Omit O(name) to return all remotes, or set it to query a single remote.
  - Write-only fields (access keys, secret keys, passphrases, cluster IDs) are
    never returned.
options:
  name:
    description:
      - Remote name to query.
      - If omitted, all remotes are returned.
    type: str
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
  - "For cluster-wide tasks use C(run_once=true) or a single-host play such as C(hosts: linstor_controllers[0])."
seealso:
  - module: linbit.linstor.remote
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Query all remotes
  linbit.linstor.remote_info:
  register: all_remotes
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Query a single remote
  linbit.linstor.remote_info:
    name: remote-s3-backup
  register: remote_state
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Show the remote type and endpoint
  ansible.builtin.debug:
    msg: "{{ remote_state.remotes[0].type }} endpoint {{ remote_state.remotes[0].endpoint | default('n/a') }}"
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
remotes:
  description: List of LINSTOR remotes, filtered by O(name) when supplied.
  type: list
  elements: dict
  returned: always
  contains:
    name:
      description: Remote name.
      type: str
    type:
      description: Remote type (s3, linstor, or ebs).
      type: str
    endpoint:
      description: Endpoint URL (s3 and ebs remotes).
      type: str
    bucket:
      description: Bucket name (s3 remotes).
      type: str
    region:
      description: Region (s3 and ebs remotes).
      type: str
    url:
      description: Peer controller URL (linstor remotes).
      type: str
    availability_zone:
      description: Availability zone (ebs remotes).
      type: str
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)


def build_remote_entry(remote, rtype):
    """Flatten a remote object into a JSON-serializable dict."""
    entry = dict(name=remote.remote_name, type=rtype)
    if rtype == 's3':
        entry['endpoint'] = getattr(remote, 'endpoint', None)
        entry['bucket'] = getattr(remote, 'bucket', None)
        entry['region'] = getattr(remote, 'region', None)
    elif rtype == 'linstor':
        entry['url'] = getattr(remote, 'url', None)
    elif rtype == 'ebs':
        entry['endpoint'] = getattr(remote, 'endpoint', None)
        entry['region'] = getattr(remote, 'region', None)
        entry['availability_zone'] = getattr(remote, 'availability_zone', None)
    return entry


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params['name']

    lin = get_linstor_connection(module)

    try:
        result = lin.remote_list()
        remotes = []
        if result:
            remote_list = result[0] if isinstance(result, list) else result
            for remote in getattr(remote_list, 's3_remotes', []):
                remotes.append(build_remote_entry(remote, 's3'))
            for remote in getattr(remote_list, 'linstor_remotes', []):
                remotes.append(build_remote_entry(remote, 'linstor'))
            for remote in getattr(remote_list, 'ebs_remotes', []):
                remotes.append(build_remote_entry(remote, 'ebs'))
        if name:
            remotes = [r for r in remotes if r['name'] == name]
        module.exit_json(changed=False, remotes=remotes)
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying remotes: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
