#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: backup_ship
short_description: Ship a LINSTOR backup between clusters or remotes
version_added: "0.9.7"
description:
  - Initiates a LINSTOR backup shipment to a remote cluster or S3 remote.
  - Each invocation initiates a new shipment and reports C(changed=true).
  - This module is NOT idempotent. Use M(linbit.linstor.backup_info) with
    C(kind=queued) to check whether a shipment is already in flight before
    invoking this module if idempotency matters.
options:
  remote:
    description: Name of the destination remote.
    type: str
    required: true
  src_resource:
    description: Source resource name to ship.
    type: str
    required: true
  dst_resource:
    description: Destination resource name on the target.
    type: str
    required: true
  src_node:
    description: Preferred source node for the shipment.
    type: str
  dst_node:
    description: Destination node for the shipment.
    type: str
  dst_net_if:
    description: Destination network interface for the shipment.
    type: str
  dst_storage_pool:
    description:
      - Destination storage pool name.
      - Use when the target cluster uses a different storage pool name
        than the source.
    type: str
  storage_pool_rename:
    description:
      - Storage pool rename map.
      - Keys are source pool names, values are target pool names.
    type: dict
  dst_resource_group:
    description:
      - Resource group name for the resource on the destination.
      - Requires LINSTOR controller 1.24+.
    type: str
  force_move_resource_group:
    description:
      - Force moving the resource to a different resource group.
      - Requires LINSTOR controller 1.24+.
    type: bool
    default: false
  download_only:
    description:
      - Download the backup without placing resources.
      - Mutually exclusive with O(force_restore).
    type: bool
    default: false
  force_restore:
    description:
      - Force restore even if the backup was created from a different cluster.
      - Mutually exclusive with O(download_only).
      - Requires LINSTOR controller 1.21+.
    type: bool
    default: false
  force_full:
    description:
      - Force a full backup instead of incremental.
      - Requires LINSTOR controller 1.14+.
    type: bool
  src_snap:
    description:
      - Source snapshot name to ship.
      - Requires LINSTOR controller 1.27+.
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
  - "Use C(run_once=true) or a single-host play such as C(hosts: linstor_controllers[0])."
  - LINSTOR-to-LINSTOR shipping requires bidirectional remotes
    (each cluster has a remote pointing at the other with C(cluster_id) set).
  - "Concurrent shipments can be throttled via
    C(BackupShipping/MaxConcurrentBackupsPerNode) on the controller or
    individual nodes (via M(linbit.linstor.controller) or M(linbit.linstor.node))."
seealso:
  - module: linbit.linstor.backup
  - module: linbit.linstor.backup_info
  - module: linbit.linstor.backup_restore
  - module: linbit.linstor.backup_abort
  - module: linbit.linstor.remote
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Ship a backup to another LINSTOR cluster
  linbit.linstor.backup_ship:
    remote: remote-dr-site
    src_resource: res-data
    dst_resource: res-data-dr
  run_once: true  # noqa: run-once[task]

- name: Ship with a different storage pool on the target cluster
  linbit.linstor.backup_ship:
    remote: remote-dr-site
    src_resource: res-data
    dst_resource: res-data-dr
    dst_storage_pool: dr-storage
  run_once: true  # noqa: run-once[task]

- name: Force a full ship to S3
  linbit.linstor.backup_ship:
    remote: remote-s3-backup
    src_resource: res-data
    dst_resource: res-data
    force_full: true
  run_once: true  # noqa: run-once[task]

# Delegate to a cluster controller when the control node cannot reach
# the LINSTOR API directly (SSH jump host, segmented management network)
- name: Ship a backup to a peer cluster via a delegated controller
  linbit.linstor.backup_ship:
    remote: remote-dr-site
    src_resource: res-data
    dst_resource: res-data-dr
  delegate_to: controller-0
  environment:
    LS_CONTROLLERS: linstor://localhost
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
remote:
  description: Name of the destination remote.
  type: str
  returned: always
resource:
  description: Source resource name.
  type: str
  returned: always
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
        src_resource=dict(type='str', required=True),
        dst_resource=dict(type='str', required=True),
        src_node=dict(type='str'),
        dst_node=dict(type='str'),
        dst_net_if=dict(type='str'),
        dst_storage_pool=dict(type='str'),
        storage_pool_rename=dict(type='dict'),
        dst_resource_group=dict(type='str'),
        force_move_resource_group=dict(type='bool', default=False),
        download_only=dict(type='bool', default=False),
        force_restore=dict(type='bool', default=False),
        force_full=dict(type='bool'),
        src_snap=dict(type='str'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ['download_only', 'force_restore'],
        ],
    )

    remote = module.params['remote']
    src_resource = module.params['src_resource']

    if module.check_mode:
        module.exit_json(changed=True, remote=remote, resource=src_resource)

    lin = get_linstor_connection(module)

    try:
        kwargs = dict(
            remote_name=remote,
            src_rsc_name=src_resource,
            dst_rsc_name=module.params['dst_resource'],
            download_only=module.params['download_only'],
            force_restore=module.params['force_restore'],
        )
        if module.params.get('src_node'):
            kwargs['src_node'] = module.params['src_node']
        if module.params.get('dst_node'):
            kwargs['dst_node'] = module.params['dst_node']
        if module.params.get('dst_net_if'):
            kwargs['dst_net_if'] = module.params['dst_net_if']
        if module.params.get('dst_storage_pool'):
            kwargs['dst_stor_pool'] = module.params['dst_storage_pool']
        if module.params.get('storage_pool_rename'):
            kwargs['stor_pool_rename'] = module.params['storage_pool_rename']
        if module.params.get('dst_resource_group'):
            kwargs['dst_rsc_grp'] = module.params['dst_resource_group']
        if module.params['force_move_resource_group']:
            kwargs['force_mv_rsc_grp'] = True
        if module.params.get('force_full') is not None:
            kwargs['force_full'] = module.params['force_full']
        if module.params.get('src_snap'):
            kwargs['src_snap'] = module.params['src_snap']

        replies = lin.backup_ship(**kwargs)
        check_api_response(module, replies, 'ship backup via %s' % remote)
        module.exit_json(changed=True, remote=remote, resource=src_resource)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error shipping backup via remote '%s': %s" % (
                remote, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
