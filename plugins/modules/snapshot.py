#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: snapshot
short_description: Manage LINSTOR snapshots
version_added: "0.9.7"
description:
  - Creates, deletes, rolls back, restores, or queries LINSTOR snapshots.
  - Idempotent for C(state=present), C(state=absent), and C(state=restored).
  - C(state=rolled_back) is NOT idempotent. It always executes the rollback
    if the snapshot exists, because LINSTOR does not expose enough state to
    detect whether a rollback has already been applied.
  - Use C(state=query) to check whether a snapshot exists and retrieve its
    details without modification.
options:
  resource:
    description: Name of the resource definition to snapshot.
    type: str
    required: true
  name:
    description: Name of the snapshot.
    type: str
    required: true
  state:
    description:
      - Desired state of the snapshot.
      - C(present) creates the snapshot if it does not exist.
      - C(absent) deletes the snapshot if it exists.
      - C(rolled_back) rolls back the resource to the snapshot state.
        This is NOT idempotent and always executes if the snapshot exists.
      - C(restored) restores the snapshot to a new resource definition
        specified by O(restore_to). Idempotent based on whether the
        target resource definition already exists.
      - C(query) returns snapshot details without modification.
    type: str
    default: present
    choices: [present, absent, rolled_back, restored, query]
  nodes:
    description:
      - List of nodes to include in the snapshot.
      - When empty (the default), LINSTOR snapshots all nodes that have
        the resource deployed.
    type: list
    elements: str
    default: []
  restore_to:
    description:
      - Name of the new resource definition to restore the snapshot into.
      - Required when C(state=restored).
    type: str
  restore_nodes:
    description:
      - List of nodes to restore the snapshot onto.
      - When empty (the default), restores to the same nodes where the
        snapshot was taken.
    type: list
    elements: str
    default: []
  storage_pool_map:
    description:
      - Storage pool rename map for snapshot restore.
      - Keys are source storage pool names, values are target storage pool names.
    type: dict
    default: {}
  properties:
    description: Dictionary of LINSTOR properties to set on the snapshot definition.
    type: dict
    default: {}
  delete_properties:
    description: List of property keys to remove from the snapshot definition.
    type: list
    elements: str
    default: []
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
  - "C(state=rolled_back) is destructive. It overwrites current resource data with
    the snapshot contents. Use with caution."
seealso:
  - name: LINSTOR User's Guide - Snapshots
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-snapshots
    description: Snapshot concepts and operations in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Create a snapshot of a resource
  linbit.linstor.snapshot:
    resource: res-data
    name: snap-before-upgrade
  run_once: true  # noqa: run-once[task]

- name: Create a snapshot on specific nodes
  linbit.linstor.snapshot:
    resource: res-data
    name: snap-partial
    nodes:
      - node-1
      - node-2
  run_once: true  # noqa: run-once[task]

- name: Delete a snapshot
  linbit.linstor.snapshot:
    resource: res-data
    name: snap-before-upgrade
    state: absent
  run_once: true  # noqa: run-once[task]

- name: Rollback a resource to a snapshot
  linbit.linstor.snapshot:
    resource: res-data
    name: snap-before-upgrade
    state: rolled_back
  run_once: true  # noqa: run-once[task]

- name: Restore a snapshot to a new resource
  linbit.linstor.snapshot:
    resource: res-data
    name: snap-before-upgrade
    state: restored
    restore_to: res-data-restored
  run_once: true  # noqa: run-once[task]

- name: Restore with storage pool remapping
  linbit.linstor.snapshot:
    resource: res-data
    name: snap-before-upgrade
    state: restored
    restore_to: res-data-copy
    storage_pool_map:
      sp-lvm-thin: sp-zfs
  run_once: true  # noqa: run-once[task]

- name: Set properties on a snapshot definition
  linbit.linstor.snapshot:
    resource: res-data
    name: snap-before-upgrade
    properties:
      Aux/purpose: pre-upgrade-backup
  run_once: true  # noqa: run-once[task]

- name: Query a snapshot
  linbit.linstor.snapshot:
    resource: res-data
    name: snap-before-upgrade
    state: query
  register: snap_result
  run_once: true  # noqa: run-once[task]

# Delegate to a cluster controller when the control node cannot reach
# the LINSTOR API directly (SSH jump host, segmented management network)
- name: Create a snapshot via a delegated controller
  linbit.linstor.snapshot:
    resource: res-data
    name: snap-before-upgrade
  delegate_to: controller-0
  environment:
    LS_CONTROLLERS: linstor://localhost
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
resource:
  description: Name of the resource definition.
  type: str
  returned: always
name:
  description: Name of the snapshot.
  type: str
  returned: always
exists:
  description: Whether the snapshot exists. Only returned with C(state=query).
  type: bool
  returned: query
nodes:
  description: Nodes where the snapshot exists.
  type: list
  returned: success
flags:
  description: Snapshot flags. Only returned with C(state=query).
  type: list
  returned: query
properties:
  description: Snapshot definition properties after the operation.
  type: dict
  returned: success
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
    check_api_response,
    compute_property_diff,
)


def get_snapshot(lin, resource, name):
    """Get a snapshot definition by resource and name. Returns the object or None."""
    snap_list = lin.snapshot_dfn_list_raise(
        filter_by_resources=[resource])
    for snap in snap_list.snapshots:
        if snap.snapshot_name == name:
            return snap
    return None


def get_snap_props(snap):
    """Extract properties from a snapshot definition."""
    if hasattr(snap, 'properties') and snap.properties:
        return dict(snap.properties)
    return {}


def resource_definition_exists(lin, name):
    """Check if a resource definition exists."""
    rd_list = lin.resource_dfn_list_raise(
        filter_by_resource_definitions=[name])
    return bool(rd_list.resource_definitions)


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        resource=dict(type='str', required=True),
        name=dict(type='str', required=True),
        state=dict(type='str', default='present',
                   choices=['present', 'absent', 'rolled_back', 'restored', 'query']),
        nodes=dict(type='list', elements='str', default=[]),
        restore_to=dict(type='str'),
        restore_nodes=dict(type='list', elements='str', default=[]),
        storage_pool_map=dict(type='dict', default={}),
        properties=dict(type='dict', default={}),
        delete_properties=dict(type='list', elements='str', default=[]),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ('state', 'restored', ['restore_to']),
        ],
    )

    resource = module.params['resource']
    name = module.params['name']
    state = module.params['state']
    nodes = module.params['nodes'] or []
    restore_to = module.params.get('restore_to')
    restore_nodes = module.params['restore_nodes'] or []
    storage_pool_map = module.params['storage_pool_map'] or {}
    properties = module.params['properties'] or {}
    delete_properties = module.params['delete_properties'] or []

    lin = get_linstor_connection(module)
    changed = False

    try:
        existing_snap = get_snapshot(lin, resource, name)

        if state == 'query':
            if existing_snap is None:
                module.exit_json(
                    changed=False, name=name, resource=resource,
                    exists=False)
            module.exit_json(
                changed=False, name=name, resource=resource,
                exists=True,
                nodes=existing_snap.nodes,
                flags=list(existing_snap.flags) if hasattr(existing_snap, 'flags') and existing_snap.flags else [],
                properties=get_snap_props(existing_snap))

        if state == 'absent':
            if existing_snap is None:
                module.exit_json(changed=False, resource=resource, name=name)
            if module.check_mode:
                module.exit_json(changed=True, resource=resource, name=name)
            replies = lin.snapshot_delete(resource, name)
            check_api_response(module, replies,
                               'delete snapshot %s/%s' % (resource, name))
            module.exit_json(changed=True, resource=resource, name=name)

        if state == 'rolled_back':
            if existing_snap is None:
                module.fail_json(
                    msg="Snapshot '%s' does not exist on resource '%s', "
                        "cannot rollback" % (name, resource))
            if module.check_mode:
                module.exit_json(
                    changed=True, resource=resource, name=name,
                    nodes=existing_snap.nodes,
                    properties=get_snap_props(existing_snap))
            replies = lin.snapshot_rollback(resource, name)
            check_api_response(module, replies,
                               'rollback snapshot %s/%s' % (resource, name))
            module.exit_json(
                changed=True, resource=resource, name=name,
                nodes=existing_snap.nodes,
                properties=get_snap_props(existing_snap))

        if state == 'restored':
            # Idempotent: skip if the target resource definition already exists
            if resource_definition_exists(lin, restore_to):
                module.exit_json(
                    changed=False, resource=resource, name=name,
                    nodes=existing_snap.nodes if existing_snap else [],
                    properties=get_snap_props(existing_snap) if existing_snap else {})
            if existing_snap is None:
                module.fail_json(
                    msg="Snapshot '%s' does not exist on resource '%s', "
                        "cannot restore" % (name, resource))
            if module.check_mode:
                module.exit_json(
                    changed=True, resource=resource, name=name,
                    nodes=existing_snap.nodes,
                    properties=get_snap_props(existing_snap))
            # Create target resource definition, restore volume defs, then place
            replies = lin.resource_dfn_create(restore_to)
            check_api_response(module, replies,
                               'create resource definition %s for restore' % restore_to)
            replies = lin.snapshot_volume_definition_restore(
                resource, name, restore_to)
            check_api_response(module, replies,
                               'restore volume definitions from %s/%s to %s' % (
                                   resource, name, restore_to))
            target_nodes = restore_nodes if restore_nodes else existing_snap.nodes
            replies = lin.snapshot_resource_restore(
                target_nodes, resource, name, restore_to,
                storpool_rename_map=storage_pool_map or None)
            check_api_response(module, replies,
                               'restore resources from %s/%s to %s' % (
                                   resource, name, restore_to))
            module.exit_json(
                changed=True, resource=resource, name=name,
                nodes=target_nodes,
                properties=get_snap_props(existing_snap))

        # state == 'present'
        if existing_snap is not None:
            # Snapshot exists: check for property changes
            current_props = get_snap_props(existing_snap)
            props_to_set, props_to_delete = compute_property_diff(
                current_props, properties, delete_properties)

            if not props_to_set and not props_to_delete:
                module.exit_json(
                    changed=False, resource=resource, name=name,
                    nodes=existing_snap.nodes,
                    properties=current_props)

            if module.check_mode:
                module.exit_json(
                    changed=True, resource=resource, name=name,
                    nodes=existing_snap.nodes,
                    properties=dict(current_props, **props_to_set))

            replies = lin.snapshot_dfn_modify(
                resource, name,
                property_dict=props_to_set,
                delete_props=props_to_delete or None,
            )
            check_api_response(module, replies,
                               'modify properties on snapshot %s/%s' % (
                                   resource, name))
            changed = True

            # Re-read properties
            updated_snap = get_snapshot(lin, resource, name)
            final_props = get_snap_props(updated_snap) if updated_snap else current_props

            module.exit_json(
                changed=changed, resource=resource, name=name,
                nodes=existing_snap.nodes,
                properties=final_props)

        # Snapshot does not exist: create it
        if module.check_mode:
            module.exit_json(
                changed=True, resource=resource, name=name,
                nodes=nodes, properties=properties)

        replies = lin.snapshot_create(nodes, resource, name)
        check_api_response(module, replies,
                           'create snapshot %s/%s' % (resource, name))
        changed = True

        # Set properties on newly created snapshot
        if properties or delete_properties:
            prop_dict = {k: str(v) for k, v in properties.items()}
            replies = lin.snapshot_dfn_modify(
                resource, name,
                property_dict=prop_dict,
                delete_props=delete_properties or None,
            )
            check_api_response(module, replies,
                               'set properties on snapshot %s/%s' % (
                                   resource, name))

        # Re-read to get final state
        final_snap = get_snapshot(lin, resource, name)
        final_nodes = final_snap.nodes if final_snap else nodes
        final_props = get_snap_props(final_snap) if final_snap else properties

        module.exit_json(
            changed=changed, resource=resource, name=name,
            nodes=final_nodes, properties=final_props)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error managing snapshot '%s/%s': %s" % (
                resource, name, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
