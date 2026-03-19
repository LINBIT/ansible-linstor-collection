#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: resource
short_description: Deploy LINSTOR resources
version_added: "0.10.0"
description:
  - Deploys or removes LINSTOR resources via spawn, autoplace, or manual placement.
  - Idempotent. If the resource definition already exists, the module returns
    C(changed=false) unless the resource needs placement.
  - Use C(state=query) to retrieve resource information without modification.
options:
  name:
    description: Name of the resource (becomes the resource definition name).
    type: str
    required: true
  state:
    description:
      - Desired state of the resource.
      - When C(absent) with C(node) specified, removes the resource from that node only.
      - When C(absent) without C(node), deletes the entire resource definition and all replicas.
      - When C(query), returns resource information without modification.
    type: str
    default: present
    choices: [present, absent, query]
  mode:
    description:
      - Deployment mode.
      - C(autoplace) places replicas automatically.
      - C(spawn) creates the resource from a resource group (uses C(resource_group) + C(sizes)).
      - C(manual) places the resource on a specific node.
    type: str
    default: autoplace
    choices: [autoplace, spawn, manual]
  resource_group:
    description:
      - Resource group name. Used by C(mode=spawn) and optionally by C(mode=autoplace) and C(mode=manual).
      - Defaults to C(DfltRscGrp) (the LINSTOR built-in default resource group).
    type: str
    default: DfltRscGrp
  size:
    description:
      - Volume size for single-volume resources (e.g. C(10G), C(500M)).
      - Convenience alternative to C(sizes) for the common single-volume case.
      - Mutually exclusive with C(sizes).
    type: str
  sizes:
    description:
      - List of volume sizes (e.g. C(['64M', '1G'])).
      - Required when C(mode=spawn) (unless C(size) is given instead).
    type: list
    elements: str
  definitions_only:
    description:
      - Spawn mode only.
      - Create resource and volume definitions without placing actual resources.
    type: bool
    default: false
  node:
    description:
      - Target node name. Required when C(mode=manual).
    type: str
  storage_pool:
    description: Storage pool to use for placement.
    type: str
  place_count:
    description:
      - Number of replicas for autoplace mode.
    type: int
    default: 2
  do_not_place_with_regex:
    description:
      - Autoplace mode only.
      - A regex string. LINSTOR will not place the resource on nodes that
        already have a resource whose name matches this regex.
    type: str
  diskless:
    description:
      - Manual mode only. Create a diskless (DRBD client) resource.
      - If the resource already exists as diskful on the node, toggles it to diskless.
      - If C(false) and the resource exists as diskless, toggles it back to diskful.
    type: bool
    default: false
  properties:
    description: Dictionary of LINSTOR properties to set on the resource.
    type: dict
    default: {}
  delete_properties:
    description: List of property keys to remove from the resource.
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
  - "For C(mode=autoplace) and C(mode=spawn), use C(run_once=true) or a
    single-host play such as C(hosts: linstor_controllers[0])."
  - For C(mode=manual), two usage patterns are supported.
  - Centralized, use C(run_once=true) with a loop over inventory hosts to send
    all API calls from a single host.
  - Per-host, let each play host call the module with its own host variables
    such as C(inventory_hostname).
  - "When C(state=absent) with C(node) specified, LINSTOR may convert a diskful
    resource to a TieBreaker (diskless quorum voter) instead of fully deleting it.
    This only happens at the 3-to-2 diskful replica boundary when C(auto-quorum)
    is enabled. Deleting from 4 or more replicas down to 3 is a clean delete.
    The module detects the TieBreaker conversion and issues a second delete to
    fully remove the resource from the node."
  - "In C(mode=manual), setting C(diskless=true) on an existing diskful resource
    toggles it to diskless (and vice versa). This uses the LINSTOR C(toggle-disk)
    API internally."
seealso:
  - name: LINSTOR User's Guide - Resource Groups
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-resource-groups
    description: Spawning resources from resource groups in the LINSTOR User's Guide.
  - name: LINSTOR User's Guide - Manual Placement
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-manual_placement
    description: Manual resource placement in the LINSTOR User's Guide.
  - name: LINSTOR User's Guide - Toggling Diskful and Diskless
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-toggling-resources-between-diskful-and-diskless
    description: Toggling resources between diskful and diskless in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Spawn resource (uses DfltRscGrp)
  linbit.linstor.resource:
    name: res-0
    mode: spawn
    size: 1G
  run_once: true  # noqa: run-once[task]

- name: Spawn from specific resource group
  linbit.linstor.resource:
    name: res-0
    mode: spawn
    resource_group: rg-ha
    size: 1G
  run_once: true  # noqa: run-once[task]

- name: Autoplace with 3 replicas
  linbit.linstor.resource:
    name: res-data
    mode: autoplace
    place_count: 3
    size: 10G
  run_once: true  # noqa: run-once[task]

- name: Spawn multi-volume resource
  linbit.linstor.resource:
    name: res-0
    mode: spawn
    sizes:
      - 64M
      - 1G
  run_once: true  # noqa: run-once[task]

- name: Place resource on a specific node
  linbit.linstor.resource:
    name: res-data
    mode: manual
    node: node-1
    storage_pool: sp-lvm-thin
  run_once: true  # noqa: run-once[task]

- name: Manually place a 3 replica resource
  linbit.linstor.resource:
    name: res-data
    mode: manual
    node: "{{ item }}"
    storage_pool: sp-lvm-thin
  loop:
    - node-1
    - node-2
    - node-3
  run_once: true  # noqa: run-once[task]

# Creates a diskless resource if it does not exist on the node.
# If the resource exists as diskful, toggles it to diskless.
- name: Create or toggle resource to diskless on a node
  linbit.linstor.resource:
    name: res-data
    mode: manual
    node: node-3
    diskless: true
  run_once: true  # noqa: run-once[task]

- name: Toggle a diskless resource back to diskful
  linbit.linstor.resource:
    name: res-data
    mode: manual
    node: node-3
    storage_pool: sp-lvm-thin
  run_once: true  # noqa: run-once[task]

- name: Query a resource
  linbit.linstor.resource:
    name: res-data
    state: query
  register: rsc_result
  run_once: true  # noqa: run-once[task]

- name: Remove a resource from a specific node
  linbit.linstor.resource:
    name: res-data
    state: absent
    node: node-3
  run_once: true  # noqa: run-once[task]

- name: Remove a resource definition and all replicas
  linbit.linstor.resource:
    name: res-0
    state: absent
  run_once: true  # noqa: run-once[task]

# LINSTOR recommends no more than 3 diskful replicas per resource
- name: Place resource on all satellite nodes from one host
  linbit.linstor.resource:
    name: res-data
    mode: manual
    node: "{{ item }}"
    storage_pool: sp-lvm-thin
  loop: "{{ groups['linstor_satellites'] }}"
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
name:
  description: Name of the resource.
  type: str
  returned: always
exists:
  description: Whether the resource exists. Only returned with C(state=query).
  type: bool
  returned: query
mode:
  description: Deployment mode used.
  type: str
  returned: success
resource_group:
  description: Resource group used (spawn mode).
  type: str
  returned: success
nodes:
  description: List of nodes where the resource is deployed.
  type: list
  returned: success
flags:
  description: Per-node resource flags (e.g. DRBD_DISKLESS, TIE_BREAKER). Only returned with C(state=query).
  type: dict
  returned: query
properties:
  description: Resource properties after the operation.
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
    parse_size,
    HAS_LINSTOR,
)

if HAS_LINSTOR:
    import linstor


def get_resource_definition(lin, name):
    """Check if a resource definition exists. Returns the RD object or None."""
    rd_list = lin.resource_dfn_list_raise(
        filter_by_resource_definitions=[name])
    if rd_list.resource_definitions:
        return rd_list.resource_definitions[0]
    return None


def get_resources(lin, name):
    """Get deployed resources for a resource definition. Returns list."""
    rsc_list = lin.resource_list_raise(
        filter_by_resources=[name])
    if rsc_list.resources:
        return rsc_list.resources
    return []


def get_resource_nodes(resources):
    """Extract node names from deployed resources."""
    nodes = []
    for rsc in resources:
        if hasattr(rsc, 'node_name'):
            nodes.append(rsc.node_name)
    return nodes


def is_resource_diskless(resources, node):
    """Check if the resource on a given node is diskless."""
    for rsc in resources:
        if rsc.node_name == node:
            return 'DRBD_DISKLESS' in getattr(rsc, 'flags', [])
    return False


def get_rd_props(rd):
    """Extract properties from a resource definition."""
    if hasattr(rd, 'properties') and rd.properties:
        return dict(rd.properties)
    return {}


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        state=dict(type='str', default='present', choices=['present', 'absent', 'query']),
        mode=dict(type='str', default='autoplace',
                  choices=['autoplace', 'spawn', 'manual']),
        resource_group=dict(type='str', default='DfltRscGrp'),
        size=dict(type='str'),
        sizes=dict(type='list', elements='str'),
        definitions_only=dict(type='bool', default=False),
        node=dict(type='str'),
        storage_pool=dict(type='str'),
        place_count=dict(type='int', default=2),
        do_not_place_with_regex=dict(type='str'),
        diskless=dict(type='bool', default=False),
        properties=dict(type='dict', default={}),
        delete_properties=dict(type='list', elements='str', default=[]),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ('size', 'sizes'),
        ],
        required_if=[
            ('mode', 'manual', ['node']),
        ],
    )

    name = module.params['name']
    state = module.params['state']
    mode = module.params['mode']
    resource_group = module.params.get('resource_group')
    size = module.params.get('size')
    sizes = module.params.get('sizes') or []
    if size and not sizes:
        sizes = [size]

    if state == 'present' and mode == 'spawn' and not sizes:
        module.fail_json(msg="mode=spawn requires 'size' or 'sizes' parameter")
    if state == 'present' and mode == 'autoplace' and not sizes:
        module.fail_json(msg="mode=autoplace requires 'size' or 'sizes' parameter")
    definitions_only = module.params['definitions_only']
    node = module.params.get('node')
    storage_pool = module.params.get('storage_pool')
    place_count = module.params['place_count']
    do_not_place_with_regex = module.params.get('do_not_place_with_regex')
    diskless = module.params['diskless']
    properties = module.params['properties'] or {}
    delete_properties = module.params['delete_properties'] or []

    lin = get_linstor_connection(module)
    changed = False

    try:
        existing_rd = get_resource_definition(lin, name)

        if state == 'query':
            if existing_rd is None:
                module.exit_json(changed=False, name=name, exists=False)
            deployed = get_resources(lin, name)
            node_list = get_resource_nodes(deployed)
            flags = {}
            for rsc in deployed:
                flags[rsc.node_name] = list(getattr(rsc, 'flags', []))
            module.exit_json(
                changed=False, name=name, exists=True,
                nodes=node_list,
                flags=flags,
                properties=get_rd_props(existing_rd))

        if state == 'absent':
            if existing_rd is None:
                module.exit_json(changed=False, name=name)

            if node:
                # Delete resource from a specific node only
                deployed = get_resources(lin, name)
                node_list = get_resource_nodes(deployed)
                if node not in node_list:
                    module.exit_json(changed=False, name=name, nodes=node_list)
                if module.check_mode:
                    module.exit_json(
                        changed=True, name=name,
                        nodes=[n for n in node_list if n != node])
                replies = lin.resource_delete(node, name)
                check_api_response(
                    module, replies,
                    'delete resource %s from node %s' % (name, node))
                # LINSTOR may convert a diskful resource to a TieBreaker
                # instead of deleting it (to preserve quorum). If the node
                # is still present as a TieBreaker, delete again to fully
                # remove it.
                deployed = get_resources(lin, name)
                for rsc in deployed:
                    if (rsc.node_name == node
                            and 'TIE_BREAKER' in getattr(rsc, 'flags', [])):
                        replies = lin.resource_delete(node, name)
                        check_api_response(
                            module, replies,
                            'delete tiebreaker %s from node %s' % (name, node))
                        deployed = get_resources(lin, name)
                        break
                module.exit_json(
                    changed=True, name=name,
                    nodes=get_resource_nodes(deployed))
            else:
                # Delete entire resource definition and all replicas
                if module.check_mode:
                    module.exit_json(changed=True, name=name)
                replies = lin.resource_dfn_delete(name)
                check_api_response(
                    module, replies, 'delete resource definition %s' % name)
                module.exit_json(changed=True, name=name)

        # state == 'present'
        if existing_rd is not None:
            # Resource definition exists
            deployed = get_resources(lin, name)
            node_list = get_resource_nodes(deployed)

            # For manual mode, check if the resource is on the target node
            if mode == 'manual' and node and node not in node_list:
                if module.check_mode:
                    module.exit_json(
                        changed=True, name=name, mode=mode,
                        resource_group=resource_group,
                        nodes=node_list + [node],
                        properties=get_rd_props(existing_rd))

                if diskless:
                    replies = lin.resource_create([
                        linstor.ResourceData(node, name, diskless=True)])
                else:
                    create_kwargs = [linstor.ResourceData(
                        node, name,
                        storage_pool=storage_pool if storage_pool else None)]
                    replies = lin.resource_create(create_kwargs)
                check_api_response(module, replies,
                                   'place resource %s on %s' % (name, node))
                changed = True
                deployed = get_resources(lin, name)
                node_list = get_resource_nodes(deployed)

            # For manual mode, toggle disk if diskless state doesn't match
            elif mode == 'manual' and node and node in node_list:
                currently_diskless = is_resource_diskless(deployed, node)
                if diskless and not currently_diskless:
                    # Toggle diskful -> diskless
                    if not module.check_mode:
                        replies = lin.resource_toggle_disk(
                            node, name, diskless=True)
                        check_api_response(
                            module, replies,
                            'toggle resource %s to diskless on %s' % (
                                name, node))
                        deployed = get_resources(lin, name)
                        node_list = get_resource_nodes(deployed)
                    changed = True
                elif not diskless and currently_diskless:
                    # Toggle diskless -> diskful
                    if not module.check_mode:
                        toggle_kwargs = dict(diskless=False)
                        if storage_pool:
                            toggle_kwargs['storage_pool'] = storage_pool
                        replies = lin.resource_toggle_disk(
                            node, name, **toggle_kwargs)
                        check_api_response(
                            module, replies,
                            'toggle resource %s to diskful on %s' % (
                                name, node))
                        deployed = get_resources(lin, name)
                        node_list = get_resource_nodes(deployed)
                    changed = True

            # Check for property changes
            current_props = get_rd_props(existing_rd)
            props_to_set, props_to_delete = compute_property_diff(
                current_props, properties, delete_properties)

            if props_to_set or props_to_delete:
                if not module.check_mode:
                    replies = lin.resource_dfn_modify(
                        name,
                        property_dict=props_to_set,
                        delete_props=props_to_delete or None,
                    )
                    check_api_response(
                        module, replies,
                        'modify properties on resource %s' % name)
                changed = True

            # Re-read properties
            if changed and not module.check_mode:
                final_rd = get_resource_definition(lin, name)
                final_props = get_rd_props(final_rd) if final_rd else current_props
            else:
                final_props = current_props

            module.exit_json(
                changed=changed, name=name, mode=mode,
                resource_group=resource_group,
                nodes=node_list,
                properties=final_props)

        # Resource definition does not exist: create it
        if module.check_mode:
            module.exit_json(
                changed=True, name=name, mode=mode,
                resource_group=resource_group,
                nodes=[], properties=properties)

        if mode == 'spawn':
            size_list = [parse_size(s) for s in sizes]
            replies = lin.resource_group_spawn(
                rsc_grp_name=resource_group,
                rsc_dfn_name=name,
                vlm_sizes=size_list,
                definitions_only=definitions_only,
            )
            check_api_response(module, replies, 'spawn resource %s' % name)
            changed = True

        elif mode == 'autoplace':
            # Create resource definition first
            create_kwargs = dict(name=name)
            if resource_group:
                create_kwargs['resource_group'] = resource_group
            replies = lin.resource_dfn_create(**create_kwargs)
            check_api_response(module, replies,
                               'create resource definition %s' % name)

            # Create volume definitions if sizes are provided
            for i, size_str in enumerate(sizes):
                size_kib = parse_size(size_str)
                replies = lin.volume_dfn_create(rsc_name=name, size=size_kib)
                check_api_response(module, replies,
                                   'create volume definition %d in %s' % (i, name))

            # Autoplace
            ap_kwargs = dict(
                rsc_name=name,
                place_count=place_count,
            )
            if storage_pool:
                ap_kwargs['storage_pool'] = storage_pool
            if do_not_place_with_regex:
                ap_kwargs['do_not_place_with_regex'] = do_not_place_with_regex

            replies = lin.resource_auto_place(**ap_kwargs)
            check_api_response(module, replies, 'autoplace resource %s' % name)
            changed = True

        elif mode == 'manual':
            # Create resource definition first
            create_kwargs = dict(name=name)
            if resource_group:
                create_kwargs['resource_group'] = resource_group
            replies = lin.resource_dfn_create(**create_kwargs)
            check_api_response(module, replies,
                               'create resource definition %s' % name)

            # Create volume definitions if sizes are provided
            for i, size_str in enumerate(sizes or []):
                size_kib = parse_size(size_str)
                replies = lin.volume_dfn_create(rsc_name=name, size=size_kib)
                check_api_response(module, replies,
                                   'create volume definition %d in %s' % (i, name))

            # Place on specified node
            if diskless:
                replies = lin.resource_create([
                    linstor.ResourceData(node, name, diskless=True)])
            else:
                create_data = [linstor.ResourceData(
                    node, name,
                    storage_pool=storage_pool if storage_pool else None)]
                replies = lin.resource_create(create_data)
            check_api_response(module, replies,
                               'place resource %s on %s' % (name, node))
            changed = True

        # Set properties on the new resource
        if properties or delete_properties:
            prop_dict = {k: str(v) for k, v in properties.items()}
            replies = lin.resource_dfn_modify(
                name,
                property_dict=prop_dict,
                delete_props=delete_properties or None,
            )
            check_api_response(
                module, replies,
                'set properties on resource %s' % name)

        # Get final state
        deployed = get_resources(lin, name)
        node_list = get_resource_nodes(deployed)
        final_rd = get_resource_definition(lin, name)
        final_props = get_rd_props(final_rd) if final_rd else properties

        module.exit_json(
            changed=changed, name=name, mode=mode,
            resource_group=resource_group,
            nodes=node_list,
            properties=final_props)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error managing resource '%s': %s" % (name, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
