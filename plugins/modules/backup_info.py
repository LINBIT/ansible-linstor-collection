#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: backup_info
short_description: Query LINSTOR backups, backup details, and queue status
version_added: "0.9.7"
description:
  - Returns information about LINSTOR backups stored on a remote.
  - Always read-only; C(changed) is always C(false).
  - Use O(kind) to select which view is returned.
  - C(kind=query) returns backups, backup details, and queue status in a
    single call (the default).
  - C(kind=list) returns the list of backups on a remote.
  - C(kind=info) returns details about a specific backup on a remote.
  - C(kind=queued) returns pending backup operations from the queue.
  - C(kind=list) and C(kind=info) are S3-oriented and return empty results
    for LINSTOR-to-LINSTOR remotes.
options:
  remote:
    description: Name of the remote where the backup is stored.
    type: str
    required: true
  kind:
    description:
      - Which view to return.
      - C(kind=queued) and C(kind=query) call C(backup_queue_list),
        which requires LINSTOR controller 1.20+.
    type: str
    default: query
    choices: [query, list, info, queued]
  resource:
    description:
      - Resource name filter.
    type: str
  backup_id:
    description:
      - Specific backup ID.
      - Used for C(kind=info).
    type: str
  snap_name:
    description:
      - Snapshot name filter.
    type: str
  node:
    description:
      - Node filter for queue results.
      - Only used when C(kind=queued) or C(kind=query).
    type: str
  target_node:
    description:
      - Target node for storage-pool space checks.
      - Only used when C(kind=info) or C(kind=query).
    type: str
  storage_pool_map:
    description:
      - Storage pool rename map for storage-pool space checks.
      - Keys are source pool names, values are target pool names.
      - Only used when C(kind=info) or C(kind=query).
    type: dict
    default: {}
  snap_to_node:
    description:
      - Group queue results by snapshot instead of by node.
      - Only used when C(kind=queued) or C(kind=query).
    type: bool
    default: false
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
  - "Use C(run_once=true) or a single-host play such as C(hosts: linstor_controllers[0])."
seealso:
  - module: linbit.linstor.backup
  - module: linbit.linstor.backup_ship
  - module: linbit.linstor.backup_restore
  - module: linbit.linstor.backup_abort
  - module: linbit.linstor.remote
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Combined query for a remote
  linbit.linstor.backup_info:
    remote: remote-s3-backup
  register: backup_query
  run_once: true  # noqa: run-once[task]

- name: List all backups on a remote
  linbit.linstor.backup_info:
    remote: remote-s3-backup
    kind: list
  register: backup_list
  run_once: true  # noqa: run-once[task]

- name: Get info about a specific backup
  linbit.linstor.backup_info:
    remote: remote-s3-backup
    kind: info
    resource: res-data
    backup_id: res-data_20240101_120000
  register: backup_detail
  run_once: true  # noqa: run-once[task]

- name: List queued backup operations
  linbit.linstor.backup_info:
    remote: remote-s3-backup
    kind: queued
  register: backup_queue
  run_once: true  # noqa: run-once[task]

- name: Check the queue and only ship if nothing is in flight for this resource
  linbit.linstor.backup_info:
    remote: remote-dr-site
    kind: queued
    resource: res-data
  register: ship_queue
  run_once: true  # noqa: run-once[task]

- name: Trigger a shipment only if not already queued
  linbit.linstor.backup_ship:
    remote: remote-dr-site
    src_resource: res-data
    dst_resource: res-data-dr
  when: not (ship_queue.queue.node_queues | default([]))
        and not (ship_queue.queue.snap_queues | default([]))
  run_once: true  # noqa: run-once[task]

# Delegate to a cluster controller when the control node cannot reach
# the LINSTOR API directly (SSH jump host, segmented management network)
- name: List backups on a remote via a delegated controller
  linbit.linstor.backup_info:
    remote: remote-s3-backup
    kind: list
  register: backup_list
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
  description: Resource name filter passed in.
  type: str
  returned: when supplied
backups:
  description: List of backup entries from the remote.
  type: list
  returned: when kind=list or kind=query
backup_info:
  description: Backup detail information including sizes and storage pools.
  type: dict
  returned: when kind=info or kind=query
queue:
  description: Backup queue entries grouped by node or snapshot.
  type: dict
  returned: when kind=queued or kind=query
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)


def _list_backups(lin, params):
    kwargs = dict(remote_name=params['remote'])
    if params.get('resource'):
        kwargs['resource_name'] = params['resource']
    if params.get('snap_name'):
        kwargs['snap_name'] = params['snap_name']
    result = lin.backup_list(**kwargs)
    if result and hasattr(result[0], 'data_v0'):
        return result[0].data_v0.get('linstor', [])
    return []


def _backup_info(lin, params):
    kwargs = dict(remote_name=params['remote'])
    if params.get('resource'):
        kwargs['resource_name'] = params['resource']
    if params.get('backup_id'):
        kwargs['bak_id'] = params['backup_id']
    if params.get('target_node'):
        kwargs['target_node'] = params['target_node']
    if params.get('storage_pool_map'):
        kwargs['stor_pool_map'] = params['storage_pool_map']
    if params.get('snap_name'):
        kwargs['snap_name'] = params['snap_name']
    result = lin.backup_info(**kwargs)
    if result and hasattr(result[0], 'data_v0'):
        return result[0].data_v0
    return {}


def _backup_queue(lin, params):
    kwargs = dict(
        remotes=[params['remote']],
        snap_to_node=params['snap_to_node'],
    )
    if params.get('node'):
        kwargs['nodes'] = [params['node']]
    if params.get('snap_name'):
        kwargs['snaps'] = [params['snap_name']]
    if params.get('resource'):
        kwargs['rscs'] = [params['resource']]
    result = lin.backup_queue_list(**kwargs)
    if result and hasattr(result[0], 'data_v0'):
        return result[0].data_v0
    return {}


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        remote=dict(type='str', required=True),
        kind=dict(type='str', default='query',
                  choices=['query', 'list', 'info', 'queued']),
        resource=dict(type='str'),
        backup_id=dict(type='str'),
        snap_name=dict(type='str'),
        node=dict(type='str'),
        target_node=dict(type='str'),
        storage_pool_map=dict(type='dict', default={}),
        snap_to_node=dict(type='bool', default=False),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    remote = module.params['remote']
    resource = module.params.get('resource')
    kind = module.params['kind']

    lin = get_linstor_connection(module)

    try:
        result = dict(changed=False, remote=remote, resource=resource)

        if kind == 'query':
            result['backups'] = _list_backups(lin, module.params)
            result['backup_info'] = _backup_info(lin, module.params)
            result['queue'] = _backup_queue(lin, module.params)
        elif kind == 'list':
            result['backups'] = _list_backups(lin, module.params)
        elif kind == 'info':
            result['backup_info'] = _backup_info(lin, module.params)
        elif kind == 'queued':
            result['queue'] = _backup_queue(lin, module.params)

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying backups on remote '%s': %s" % (
                remote, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
