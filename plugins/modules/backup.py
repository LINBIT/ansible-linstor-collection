#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: backup
short_description: Manage LINSTOR backups to remotes
version_added: "0.10.0"
description:
  - Creates, deletes, restores, ships, or aborts LINSTOR backups.
  - Backups are always associated with a remote defined via the
    M(linbit.linstor.remote) module.
  - C(state=present) creates a new backup and is NOT idempotent. Each
    invocation creates a new backup (full or incremental).
  - C(state=absent) deletes backups matching the specified criteria.
    Idempotent when using O(backup_id).
  - C(state=restored) restores a backup to a new resource. Idempotent
    based on whether the target resource definition already exists.
  - C(state=shipped) ships a backup between remotes or clusters and is
    NOT idempotent.
  - C(state=aborted) aborts an in-progress backup operation and is NOT
    idempotent.
options:
  remote:
    description: Name of the remote where the backup is stored.
    type: str
    required: true
  state:
    description:
      - Desired operation.
      - See the module description for idempotency details per state.
    type: str
    default: present
    choices: [present, absent, restored, shipped, aborted]
  resource:
    description:
      - Resource name.
      - Required when C(state=present) or C(state=aborted).
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
      - Snapshot name override.
      - Used when C(state=present) to name the underlying snapshot.
      - Used when C(state=restored) to filter which backup to restore.
    type: str
  backup_id:
    description:
      - Specific backup ID for C(state=absent) or C(state=restored).
    type: str
  backup_id_prefix:
    description:
      - Backup ID prefix for C(state=absent) to delete matching backups.
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
  target_node:
    description:
      - Node to restore the backup onto.
      - Required when C(state=restored).
    type: str
  target_resource:
    description:
      - Name of the resource to create from the restored backup.
      - Required when C(state=restored).
    type: str
  source_passphrase:
    description:
      - Passphrase for encrypted backups.
      - Only used when C(state=restored).
    type: str
  storage_pool_map:
    description:
      - Storage pool rename map for restore.
      - Keys are source pool names, values are target pool names.
      - Only used when C(state=restored).
    type: dict
    default: {}
  download_only:
    description:
      - Download the backup without placing resources.
      - Used when C(state=restored) or C(state=shipped).
    type: bool
    default: false
  force_restore:
    description:
      - Force restore even if the backup was created from a different cluster.
      - Used when C(state=restored) or C(state=shipped).
    type: bool
    default: false
  target_resource_group:
    description:
      - Resource group for the restored resource.
      - Used when C(state=restored) or C(state=shipped).
    type: str
  force_move_resource_group:
    description:
      - Force moving the resource to a different resource group on restore.
      - Used when C(state=restored) or C(state=shipped).
    type: bool
    default: false
  src_resource:
    description:
      - Source resource name for backup shipping.
      - Required when C(state=shipped).
    type: str
  dst_resource:
    description:
      - Destination resource name for backup shipping.
      - Required when C(state=shipped) or optionally for C(state=restored).
    type: str
  src_node:
    description:
      - Preferred source node for shipping.
      - Only used when C(state=shipped).
    type: str
  dst_node:
    description:
      - Destination node for shipping.
      - Only used when C(state=shipped).
    type: str
  dst_net_if:
    description:
      - Destination network interface for shipping.
      - Only used when C(state=shipped).
    type: str
  dst_storage_pool:
    description:
      - Destination storage pool for shipping.
      - Only used when C(state=shipped).
    type: str
  storage_pool_rename:
    description:
      - Storage pool rename map for shipping.
      - Only used when C(state=shipped).
    type: dict
  force_full:
    description:
      - Force a full backup instead of incremental for shipping.
      - Only used when C(state=shipped).
    type: bool
  src_snap:
    description:
      - Source snapshot name for shipping.
      - Only used when C(state=shipped).
    type: str
  abort_restore:
    description:
      - Abort a restore operation.
      - Only used when C(state=aborted).
    type: bool
  abort_create:
    description:
      - Abort a create operation.
      - Only used when C(state=aborted).
    type: bool
  abort_snapshot:
    description:
      - Snapshot name for aborting a specific operation.
      - Only used when C(state=aborted).
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
  - C(state=present) always creates a new backup and reports C(changed=true).
    It is NOT idempotent by design, since each invocation produces a new
    point-in-time backup.
  - C(state=shipped) always initiates a new shipping operation and reports
    C(changed=true). It is NOT idempotent.
  - The M(linbit.linstor.remote) module must be used first to configure
    the remote target before creating backups.
seealso:
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
  run_once: true  # noqa: run-once[task]

- name: Create an incremental backup
  linbit.linstor.backup:
    remote: remote-s3-backup
    resource: res-data
  run_once: true  # noqa: run-once[task]

- name: Restore a backup to a new resource
  linbit.linstor.backup:
    remote: remote-s3-backup
    state: restored
    resource: res-data
    target_node: node-1
    target_resource: res-data-restored
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

- name: Ship a backup to another LINSTOR cluster
  linbit.linstor.backup:
    remote: remote-dr-site
    state: shipped
    src_resource: res-data
    dst_resource: res-data-dr
  run_once: true  # noqa: run-once[task]

- name: Abort an in-progress backup
  linbit.linstor.backup:
    remote: remote-s3-backup
    state: aborted
    resource: res-data
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
remote:
  description: Name of the remote.
  type: str
  returned: always
resource:
  description: Resource name associated with the operation.
  type: str
  returned: when applicable
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
    check_api_response,
)


def resource_definition_exists(lin, name):
    """Check if a resource definition exists."""
    rd_list = lin.resource_dfn_list_raise(
        filter_by_resource_definitions=[name])
    return bool(rd_list.resource_definitions)


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        remote=dict(type='str', required=True),
        state=dict(type='str', default='present',
                   choices=['present', 'absent', 'restored', 'shipped', 'aborted']),
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
        s3_key=dict(type='str'),
        dryrun=dict(type='bool'),
        keep_snaps=dict(type='bool'),
        target_node=dict(type='str'),
        target_resource=dict(type='str'),
        source_passphrase=dict(type='str', no_log=True),
        storage_pool_map=dict(type='dict', default={}),
        download_only=dict(type='bool', default=False),
        force_restore=dict(type='bool', default=False),
        target_resource_group=dict(type='str'),
        force_move_resource_group=dict(type='bool', default=False),
        src_resource=dict(type='str'),
        dst_resource=dict(type='str'),
        src_node=dict(type='str'),
        dst_node=dict(type='str'),
        dst_net_if=dict(type='str'),
        dst_storage_pool=dict(type='str'),
        storage_pool_rename=dict(type='dict'),
        force_full=dict(type='bool'),
        src_snap=dict(type='str'),
        abort_restore=dict(type='bool'),
        abort_create=dict(type='bool'),
        abort_snapshot=dict(type='str'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ('state', 'present', ['resource']),
            ('state', 'restored', ['target_node', 'target_resource']),
            ('state', 'shipped', ['src_resource', 'dst_resource']),
            ('state', 'aborted', ['resource']),
        ],
    )

    remote = module.params['remote']
    state = module.params['state']
    resource = module.params.get('resource')

    lin = get_linstor_connection(module)

    try:
        if state == 'present':
            # NOT idempotent: always creates a new backup
            if module.check_mode:
                module.exit_json(changed=True, remote=remote,
                                 resource=resource)

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
            if module.check_mode:
                module.exit_json(changed=True, remote=remote,
                                 resource=resource)

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

        elif state == 'restored':
            target_resource = module.params['target_resource']

            # Idempotent: skip if target resource already exists
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
            module.exit_json(changed=True, remote=remote,
                             resource=target_resource)

        elif state == 'shipped':
            # NOT idempotent: always ships
            if module.check_mode:
                module.exit_json(changed=True, remote=remote,
                                 resource=module.params['src_resource'])

            kwargs = dict(
                remote_name=remote,
                src_rsc_name=module.params['src_resource'],
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
            if module.params.get('target_resource_group'):
                kwargs['dst_rsc_grp'] = module.params['target_resource_group']
            if module.params['force_move_resource_group']:
                kwargs['force_mv_rsc_grp'] = True
            if module.params.get('force_full') is not None:
                kwargs['force_full'] = module.params['force_full']
            if module.params.get('src_snap'):
                kwargs['src_snap'] = module.params['src_snap']

            replies = lin.backup_ship(**kwargs)
            check_api_response(module, replies,
                               'ship backup via %s' % remote)
            module.exit_json(changed=True, remote=remote,
                             resource=module.params['src_resource'])

        elif state == 'aborted':
            # NOT idempotent: always attempts abort
            if module.check_mode:
                module.exit_json(changed=True, remote=remote,
                                 resource=resource)

            kwargs = dict(
                remote_name=remote,
                resource_name=resource,
            )
            if module.params.get('abort_restore') is not None:
                kwargs['restore'] = module.params['abort_restore']
            if module.params.get('abort_create') is not None:
                kwargs['create'] = module.params['abort_create']
            if module.params.get('abort_snapshot'):
                kwargs['snapshot'] = module.params['abort_snapshot']

            replies = lin.backup_abort(**kwargs)
            check_api_response(module, replies,
                               'abort backup operation for %s' % resource)
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
