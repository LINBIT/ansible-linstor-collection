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
options:
  name:
    description: Name of the resource (becomes the resource definition name).
    type: str
    required: true
  state:
    description: Desired state of the resource.
    type: str
    default: present
    choices: [present, absent]
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
  diskless:
    description:
      - Manual mode only. Create a diskless (TieBreaker/client) resource.
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
seealso:
  - name: LINSTOR User's Guide - Resource Groups
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-resource-groups
    description: Spawning resources from resource groups in the LINSTOR User's Guide.
  - name: LINSTOR User's Guide - Manual Placement
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-manual_placement
    description: Manual resource placement in the LINSTOR User's Guide.
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
    sizes: ['64M', '1G']
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

- name: Create diskless resource on a node
  linbit.linstor.resource:
    name: res-data
    mode: manual
    node: node-3
    diskless: true
  run_once: true  # noqa: run-once[task]

- name: Remove a resource
  linbit.linstor.resource:
    name: res-0
    state: absent
  run_once: true  # noqa: run-once[task]

- name: Place resource on all satellite nodes from one host
  # LINSTOR recommends no more than 3 diskful replicas per resource
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


def get_rd_props(rd):
    """Extract properties from a resource definition."""
    if hasattr(rd, 'properties') and rd.properties:
        return dict(rd.properties)
    return {}


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        state=dict(type='str', default='present', choices=['present', 'absent']),
        mode=dict(type='str', default='autoplace',
                  choices=['autoplace', 'spawn', 'manual']),
        resource_group=dict(type='str', default='DfltRscGrp'),
        size=dict(type='str'),
        sizes=dict(type='list', elements='str'),
        definitions_only=dict(type='bool', default=False),
        node=dict(type='str'),
        storage_pool=dict(type='str'),
        place_count=dict(type='int', default=2),
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
    diskless = module.params['diskless']
    properties = module.params['properties'] or {}
    delete_properties = module.params['delete_properties'] or []

    lin = get_linstor_connection(module)
    changed = False

    try:
        existing_rd = get_resource_definition(lin, name)

        if state == 'absent':
            if existing_rd is None:
                module.exit_json(changed=False, name=name)
            if module.check_mode:
                module.exit_json(changed=True, name=name)
            replies = lin.resource_dfn_delete(name)
            check_api_response(module, replies, 'delete resource %s' % name)
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
