#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: backup_restore
short_description: Restore a LINSTOR backup to a new resource
version_added: "0.9.7"
description:
  - Restores a LINSTOR backup from a remote into a new resource definition.
  - Idempotent on the existence of O(target_resource); if the target
    resource definition already exists the module returns C(changed=false)
    without contacting the controller's restore API.
options:
  remote:
    description: Name of the remote where the backup is stored.
    type: str
    required: true
  target_node:
    description: Node on which to restore the backup.
    type: str
    required: true
  target_resource:
    description: Name of the resource definition to create from the restore.
    type: str
    required: true
  resource:
    description:
      - Source resource name in the backup.
      - Mutually exclusive with O(backup_id). Exactly one of the two
        must be supplied.
    type: str
  backup_id:
    description:
      - Specific backup ID to restore.
      - Mutually exclusive with O(resource). Exactly one of the two
        must be supplied.
    type: str
  source_passphrase:
    description: Passphrase for an encrypted backup.
    type: str
  storage_pool_map:
    description:
      - Storage pool rename map.
      - Keys are source pool names, values are target pool names.
    type: dict
    default: {}
  snap_name:
    description: Snapshot name filter.
    type: str
  target_resource_group:
    description:
      - Resource group for the restored resource.
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
  - module: linbit.linstor.backup_info
  - module: linbit.linstor.backup_ship
  - module: linbit.linstor.backup_abort
  - module: linbit.linstor.remote
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Restore a backup to a new resource
  linbit.linstor.backup_restore:
    remote: remote-s3-backup
    target_node: node-1
    target_resource: res-data-restored
    resource: res-data
  run_once: true  # noqa: run-once[task]

- name: Restore a specific backup ID with storage pool rename
  linbit.linstor.backup_restore:
    remote: remote-s3-backup
    target_node: node-1
    target_resource: res-data-restored
    resource: res-data
    backup_id: res-data_20240101_120000
    storage_pool_map:
      sp-source: sp-target
  run_once: true  # noqa: run-once[task]

# Delegate to a cluster controller when the control node cannot reach
# the LINSTOR API directly (SSH jump host, segmented management network)
- name: Restore a backup via a delegated controller
  linbit.linstor.backup_restore:
    remote: remote-s3-backup
    target_node: node-1
    target_resource: res-data-restored
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
  description: Target resource definition name.
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


def resource_definition_exists(lin, name):
    rd_list = lin.resource_dfn_list_raise(
        filter_by_resource_definitions=[name])
    return bool(rd_list.resource_definitions)


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        remote=dict(type='str', required=True),
        target_node=dict(type='str', required=True),
        target_resource=dict(type='str', required=True),
        resource=dict(type='str'),
        backup_id=dict(type='str'),
        source_passphrase=dict(type='str', no_log=True),
        storage_pool_map=dict(type='dict', default={}),
        snap_name=dict(type='str'),
        target_resource_group=dict(type='str'),
        force_move_resource_group=dict(type='bool', default=False),
        download_only=dict(type='bool', default=False),
        force_restore=dict(type='bool', default=False),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ['resource', 'backup_id'],
            ['download_only', 'force_restore'],
        ],
        required_one_of=[
            ['resource', 'backup_id'],
        ],
    )

    remote = module.params['remote']
    target_resource = module.params['target_resource']

    lin = get_linstor_connection(module)

    try:
        if resource_definition_exists(lin, target_resource):
            module.exit_json(changed=False, remote=remote,
                             resource=target_resource)

        if module.check_mode:
            module.exit_json(changed=True, remote=remote,
                             resource=target_resource)

        kwargs = dict(
            remote_name=remote,
            target_node_name=module.params['target_node'],
            target_resource_name=target_resource,
            download_only=module.params['download_only'],
            force_restore=module.params['force_restore'],
        )
        if module.params.get('resource'):
            kwargs['resource_name'] = module.params['resource']
        if module.params.get('backup_id'):
            kwargs['bak_id'] = module.params['backup_id']
        if module.params.get('source_passphrase'):
            kwargs['passphrase'] = module.params['source_passphrase']
        if module.params.get('storage_pool_map'):
            kwargs['stor_pool_map'] = module.params['storage_pool_map']
        if module.params.get('snap_name'):
            kwargs['snap_name'] = module.params['snap_name']
        if module.params.get('target_resource_group'):
            kwargs['dst_rsc_grp'] = module.params['target_resource_group']
        if module.params['force_move_resource_group']:
            kwargs['force_mv_rsc_grp'] = True

        replies = lin.backup_restore(**kwargs)
        check_api_response(module, replies,
                           'restore backup from %s to %s' % (
                               remote, target_resource))
        module.exit_json(changed=True, remote=remote, resource=target_resource)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error restoring backup from remote '%s': %s" % (
                remote, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
