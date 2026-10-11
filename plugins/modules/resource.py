#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: resource
short_description: Deploy LINSTOR resources
version_added: "0.9.7"
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
    description:
      - Desired state of the resource.
      - When C(absent) with C(node) specified, removes the resource from that node only.
      - When C(absent) without C(node), deletes the entire resource definition and all replicas.
      - C(available) runs LINSTOR's C(make-available) for O(node). It creates the copy when it is
        missing, diskless unless O(available_diskful) is set or diskless is not possible,
        activates an C(INACTIVE) copy, and turns a TieBreaker into a wanted diskless copy.
        The resource definition must exist.
      - C(unavailable) runs LINSTOR's C(unmake-available) for O(node). It removes a diskless
        copy, which LINSTOR can keep as a TieBreaker for quorum instead. It removes a copy in a
        shared storage pool while another usable copy shares its data. It keeps other diskful
        copies and TieBreakers.
      - C(available) and C(unavailable) require O(node). They report C(changed) when the copy on
        that node appears, disappears, or changes flags.
    type: str
    default: present
    choices: [present, absent, available, unavailable]
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
      - Target node name for single-node manual placement.
      - Mutually exclusive with C(nodes).
    type: str
  nodes:
    description:
      - List of node placement entries for batch manual placement.
      - Each entry is a dict with C(node) (required) and optional C(diskless) (default false),
        C(storage_pool), and C(active) (default O(active)).
      - All nodes are placed in a single API call, avoiding TieBreaker race conditions.
      - Mutually exclusive with C(node).
    type: list
    elements: dict
    default: []
  storage_pool:
    description: Storage pool to use for placement.
    type: str
  layer_list:
    description:
      - Layer stack for the resource definition (for example C([DRBD, LUKS, STORAGE])).
      - Applied in C(manual) and C(autoplace) modes; C(spawn) takes layers from the resource group.
      - With O(state=available), the layer stack for a copy that C(make-available) creates.
    type: list
    elements: str
  place_count:
    description:
      - Number of replicas for autoplace mode.
      - When omitted, the resource group's place count applies, which LINSTOR
        defaults to 2 when the group sets none.
    type: int
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
  active:
    description:
      - Manual mode only. Whether the copy on O(node), or on each entry of O(nodes),
        is active.
      - C(false) creates a missing copy C(INACTIVE) and deactivates an active one.
      - C(true) activates an C(INACTIVE) copy.
      - When omitted, new copies are created active and existing copies keep their state.
      - On a diskless copy, also set O(diskless=true), since the default O(diskless=false)
        toggles the copy to diskful.
      - Copies that LINSTOR marks C(EVICTED) or C(INACTIVE_PERMANENTLY) are left alone.
      - LINSTOR refuses to deactivate a copy that is in use, and to activate a second copy
        of a resource in the same shared storage pool.
    type: bool
    version_added: "0.9.11"
  available_diskful:
    description:
      - Create the copy diskful even where a diskless copy is possible, or toggle a diskless copy
        to diskful.
      - Only used when O(state=available).
    type: bool
    default: false
    version_added: "0.9.11"
  available_dual_primary:
    description:
      - Prepare the copy for a live migration. For DRBD resources, LINSTOR allows two Primaries
        between this node and the node that uses the resource. In a shared storage pool, LINSTOR
        activates the copy on both nodes.
      - Revert with O(state=unavailable) on the migration source node.
      - Only used when O(state=available). Requires LINSTOR 1.29.0 or later.
    type: bool
    default: false
    version_added: "0.9.11"
  properties:
    description: Dictionary of LINSTOR properties to set on the resource.
    type: dict
    default: {}
  delete_properties:
    description: List of property keys to remove from the resource.
    type: list
    elements: str
    default: []
extends_documentation_fragment:
  - linbit.linstor.connection
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
  - "For C(mode=autoplace) and C(mode=spawn), use C(run_once=true) or a
    single-host play such as C(hosts: linstor_controllers[0])."
  - For C(mode=manual), two usage patterns are supported.
  - Centralized, use C(run_once=true) with a loop over inventory hosts to send
    all API calls from a single host.
  - Per-host, let each play host call the module with its own host variables
    such as C(inventory_hostname).
  - "In C(mode=manual), use C(nodes) instead of C(node) for multi-node placement.
    All nodes are placed in a single API call, which prevents LINSTOR from
    auto-creating a TieBreaker between placements. With C(node) and a loop,
    LINSTOR may auto-create a TieBreaker after placing the second replica,
    resulting in an extra node."
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
  delegate_to: localhost
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

- name: Place resource on a single node
  linbit.linstor.resource:
    name: res-data
    mode: manual
    node: node-1
    storage_pool: sp-lvm-thin
    size: 10G
  run_once: true  # noqa: run-once[task]

# Batch placement: all nodes in a single API call.
# With 2 diskful nodes, LINSTOR auto-creates a TieBreaker on a third
# satellite for quorum. No explicit diskless placement needed.
- name: Place 2-replica resource (auto TieBreaker)
  linbit.linstor.resource:
    name: res-ha
    mode: manual
    nodes:
      - node: node-1
        storage_pool: sp-lvm-thin
      - node: node-2
        storage_pool: sp-lvm-thin
    sizes:
      - 64M
      - 1G
  run_once: true  # noqa: run-once[task]

# With 3 diskful nodes, quorum is inherent. No TieBreaker created.
- name: Place 3-replica resource (no TieBreaker)
  linbit.linstor.resource:
    name: res-critical
    mode: manual
    nodes:
      - node: node-1
        storage_pool: sp-lvm-thin
      - node: node-2
        storage_pool: sp-lvm-thin
      - node: node-3
        storage_pool: sp-lvm-thin
    sizes:
      - 64M
      - 1G
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

# Shared storage plugins normally do this; useful to reproduce their behavior in tests
- name: Create a copy INACTIVE, as the second leg of a shared storage pool
  linbit.linstor.resource:
    name: res-data
    mode: manual
    node: node-2
    storage_pool: sp-shared
    active: false
  run_once: true  # noqa: run-once[task]

- name: Activate the copy
  linbit.linstor.resource:
    name: res-data
    mode: manual
    node: node-2
    active: true
  run_once: true  # noqa: run-once[task]

- name: Remove a resource from a specific node
  linbit.linstor.resource:
    name: res-data
    state: absent
    node: node-3
  run_once: true  # noqa: run-once[task]

# What a LINSTOR hypervisor plugin runs when a VM disk attaches to a node
- name: Make a resource available on a node
  linbit.linstor.resource:
    name: res-data
    node: node-3
    state: available
  run_once: true  # noqa: run-once[task]

# Adds a full copy on node-3, or converts its diskless copy to one
- name: Make a resource available on a node with a diskful copy
  linbit.linstor.resource:
    name: res-data
    node: node-3
    state: available
    available_diskful: true
  run_once: true  # noqa: run-once[task]

- name: Revert make-available after the disk detaches
  linbit.linstor.resource:
    name: res-data
    node: node-3
    state: unavailable
  run_once: true  # noqa: run-once[task]

# The live migration of a VM disk from node-1 to node-2, as a hypervisor plugin runs it
- name: Prepare the target node for a live migration
  linbit.linstor.resource:
    name: res-vm-disk
    node: node-2
    state: available
    available_dual_primary: true
  run_once: true  # noqa: run-once[task]

- name: Revert the dual-primary settings on the source node after the migration
  linbit.linstor.resource:
    name: res-vm-disk
    node: node-1
    state: unavailable
  run_once: true  # noqa: run-once[task]

# To delete an entire resource (definition + all replicas), prefer
# linbit.linstor.resource_definition with state=absent instead.
- name: Remove a resource definition and all replicas
  linbit.linstor.resource_definition:
    name: res-0
    state: absent
  run_once: true  # noqa: run-once[task]

# Delegate to a cluster controller when the control node cannot reach
# the LINSTOR API directly (SSH jump host, segmented management network)
- name: Autoplace a resource via a delegated controller
  linbit.linstor.resource:
    name: res-0
    mode: autoplace
    place_count: 2
  delegate_to: controller-0
  environment:
    LS_CONTROLLERS: linstor://localhost
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


def is_resource_diskless(resources, node):
    """Check if the resource on a given node is diskless."""
    for rsc in resources:
        if rsc.node_name == node:
            return 'DRBD_DISKLESS' in getattr(rsc, 'flags', [])
    return False


def copy_activation(resources, node):
    """Return 'active' or 'inactive' for the copy on a node.

    None when the node has no copy, or when the copy is INACTIVE_PERMANENTLY or EVICTED:
    both carry the INACTIVE bit, but activate and deactivate do not apply to them.
    """
    for rsc in resources:
        if rsc.node_name == node:
            flags = getattr(rsc, 'flags', []) or []
            if 'INACTIVE_PERMANENTLY' in flags or 'EVICTED' in flags:
                return None
            return 'inactive' if 'INACTIVE' in flags else 'active'
    return None


def wanted_activation(node, nodes, active):
    """List the (node, active) pairs that O(node), O(nodes), and O(active) ask for."""
    wanted = []
    if node and active is not None:
        wanted.append((node, active))
    for entry in nodes:
        entry_state = entry_active(entry, active)
        if entry_state is not None:
            wanted.append((entry.get('node') or entry.get('name'), entry_state))
    return wanted


def reconcile_activation(module, lin, name, wanted, deployed, want_active):
    """Activate (want_active=True) or deactivate the wanted copies; True if any changed."""
    changed = False
    for n, want in wanted:
        if want != want_active:
            continue
        state = copy_activation(deployed, n)
        if state is None or state == ('active' if want else 'inactive'):
            continue
        if not module.check_mode:
            if want:
                replies = lin.resource_activate(n, name)
            else:
                replies = lin.resource_deactivate(n, name)
            check_api_response(
                module, replies,
                '%s resource %s on %s' % (
                    'activate' if want else 'deactivate', name, n))
        changed = True
    return changed


def resource_data(node, name, diskless=False, storage_pool=None, active=None):
    """Build the ResourceData for one copy; active=None creates it active."""
    if diskless:
        return linstor.ResourceData(
            node, name, diskless=True, active=active is not False)
    return linstor.ResourceData(
        node, name, storage_pool=storage_pool if storage_pool else None,
        active=active is not False)


def entry_active(entry, default):
    """Per-entry active state in O(nodes), falling back to O(active)."""
    active = entry.get('active')
    return default if active is None else active


def node_resource_flags(resources, node):
    """Sorted flags of the copy on a node, or None when it has no copy."""
    for rsc in resources:
        if rsc.node_name == node:
            return sorted(getattr(rsc, 'flags', []) or [])
    return None


def unmake_removes_copy(lin, deployed, node, flags):
    """Predict whether unmake-available changes the copy on a node, as LINSTOR decides it."""
    if flags is None:
        return False
    pools = set(vlm.storage_pool_name for rsc in deployed if rsc.node_name == node
                for vlm in (rsc.volumes or [])) - set([None])
    if pools:
        shared_spaces = dict(
            ((sp.node_name, sp.name), sp.free_space_mgr_name)
            for sp in lin.storage_pool_list_raise(filter_by_stor_pools=list(pools)).storage_pools)
        own = set(shared_spaces.get((node, p)) for p in pools) - set([None])
        peers = [rsc for rsc in deployed if rsc.node_name != node
                 and any(shared_spaces.get((rsc.node_name, vlm.storage_pool_name)) in own
                         for vlm in (rsc.volumes or []))]
        if peers:
            # a copy in a shared storage pool goes only while another usable copy keeps the data
            return any(not set(rsc.flags or []) & set(['DELETE', 'INACTIVE_PERMANENTLY'])
                       for rsc in peers)
    if 'TIE_BREAKER' in flags:
        return False
    return 'DRBD_DISKLESS' in flags


def manage_availability(module, lin, name, existing_rd, node, state):
    """Run make-available or unmake-available for one node and exit."""
    if not node:
        module.fail_json(msg="state=%s requires the 'node' parameter" % state)
    if existing_rd is None:
        if state == 'unavailable':
            module.exit_json(changed=False, name=name, nodes=[])
        module.fail_json(
            msg="Resource definition '%s' does not exist, cannot make it "
                "available on %s" % (name, node))

    deployed = get_resources(lin, name)
    before = node_resource_flags(deployed, node)

    if module.check_mode:
        if state == 'available':
            expected_change = (
                before is None
                or copy_activation(deployed, node) == 'inactive'
                or 'TIE_BREAKER' in before
                or (module.params['available_diskful'] and 'DRBD_DISKLESS' in before))
        else:
            expected_change = unmake_removes_copy(lin, deployed, node, before)
        module.exit_json(changed=expected_change, name=name,
                         nodes=get_resource_nodes(deployed))

    if state == 'available':
        kwargs = dict(diskful=module.params['available_diskful'])
        if module.params.get('layer_list'):
            kwargs['layer_list'] = module.params['layer_list']
        if module.params['available_dual_primary']:
            kwargs['auto_manage_dual_primary'] = True
        replies = lin.resource_make_available(node, name, **kwargs)
        action = 'make resource %s available on %s'
    else:
        replies = lin.resource_unmake_available(node, name)
        action = 'unmake resource %s available on %s'
    check_api_response(module, replies, action % (name, node))

    deployed = get_resources(lin, name)
    after = node_resource_flags(deployed, node)
    module.exit_json(changed=before != after, name=name,
                     nodes=get_resource_nodes(deployed))


def get_rd_props(rd):
    """Extract properties from a resource definition."""
    if hasattr(rd, 'properties') and rd.properties:
        return dict(rd.properties)
    return {}


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        state=dict(type='str', default='present',
                   choices=['present', 'absent', 'available', 'unavailable']),
        mode=dict(type='str', default='autoplace',
                  choices=['autoplace', 'spawn', 'manual']),
        resource_group=dict(type='str', default='DfltRscGrp'),
        size=dict(type='str'),
        sizes=dict(type='list', elements='str'),
        definitions_only=dict(type='bool', default=False),
        node=dict(type='str'),
        nodes=dict(type='list', elements='dict', default=[]),
        storage_pool=dict(type='str'),
        place_count=dict(type='int'),
        do_not_place_with_regex=dict(type='str'),
        diskless=dict(type='bool', default=False),
        properties=dict(type='dict', default={}),
        delete_properties=dict(type='list', elements='str', default=[]),
        layer_list=dict(type='list', elements='str'),
        active=dict(type='bool'),
        available_diskful=dict(type='bool', default=False),
        available_dual_primary=dict(type='bool', default=False),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ('size', 'sizes'),
            ('node', 'nodes'),
        ],
        required_if=[],
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
    nodes = module.params.get('nodes') or []
    if state == 'present' and mode == 'manual' and not node and not nodes:
        module.fail_json(msg="mode=manual requires 'node' or 'nodes' parameter")
    storage_pool = module.params.get('storage_pool')
    place_count = module.params['place_count']
    do_not_place_with_regex = module.params.get('do_not_place_with_regex')
    diskless = module.params['diskless']
    properties = module.params['properties'] or {}
    delete_properties = module.params['delete_properties'] or []
    layer_list = module.params.get('layer_list')
    active = module.params['active']

    lin = get_linstor_connection(module)
    changed = False

    try:
        existing_rd = get_resource_definition(lin, name)

        if state in ('available', 'unavailable'):
            manage_availability(module, lin, name, existing_rd, node, state)

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

            # toggle-disk fails on an inactive copy, so activate before it and deactivate after
            wanted = wanted_activation(node, nodes, active) if mode == 'manual' else []
            if reconcile_activation(module, lin, name, wanted, deployed, True):
                changed = True
                if not module.check_mode:
                    deployed = get_resources(lin, name)

            # For manual mode with batch nodes, place any missing nodes
            if mode == 'manual' and nodes:
                missing = []
                for entry in nodes:
                    n = entry.get('node') or entry.get('name')
                    if n not in node_list:
                        missing.append(entry)
                if missing:
                    if module.check_mode:
                        new_nodes = [e.get('node') or e.get('name')
                                     for e in missing]
                        module.exit_json(
                            changed=True, name=name, mode=mode,
                            resource_group=resource_group,
                            nodes=node_list + new_nodes,
                            properties=get_rd_props(existing_rd))
                    create_data = []
                    for entry in missing:
                        n = entry.get('node') or entry.get('name')
                        create_data.append(resource_data(
                            n, name,
                            diskless=entry.get('diskless', False),
                            storage_pool=entry.get('storage_pool', storage_pool),
                            active=entry_active(entry, active)))
                    replies = lin.resource_create(create_data)
                    placed = ', '.join(
                        e.get('node') or e.get('name') for e in missing)
                    check_api_response(module, replies,
                                       'place resource %s on %s' % (
                                           name, placed))
                    changed = True
                    deployed = get_resources(lin, name)
                    node_list = get_resource_nodes(deployed)

            # For manual mode with single node, check if the resource is on the target node
            elif mode == 'manual' and node and node not in node_list:
                if module.check_mode:
                    module.exit_json(
                        changed=True, name=name, mode=mode,
                        resource_group=resource_group,
                        nodes=node_list + [node],
                        properties=get_rd_props(existing_rd))

                replies = lin.resource_create([resource_data(
                    node, name, diskless=diskless,
                    storage_pool=storage_pool, active=active)])
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

            if reconcile_activation(module, lin, name, wanted, deployed, False):
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
            if layer_list:
                create_kwargs['layer_list'] = layer_list
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
            if layer_list:
                create_kwargs['layer_list'] = layer_list
            replies = lin.resource_dfn_create(**create_kwargs)
            check_api_response(module, replies,
                               'create resource definition %s' % name)

            # Create volume definitions if sizes are provided
            for i, size_str in enumerate(sizes or []):
                size_kib = parse_size(size_str)
                replies = lin.volume_dfn_create(rsc_name=name, size=size_kib)
                check_api_response(module, replies,
                                   'create volume definition %d in %s' % (i, name))

            # Place on specified node(s)
            if nodes:
                # Batch placement: all nodes in one API call
                create_data = []
                for entry in nodes:
                    n = entry.get('node') or entry.get('name')
                    if not n:
                        module.fail_json(
                            msg="Each entry in 'nodes' must have a 'node' key")
                    create_data.append(resource_data(
                        n, name,
                        diskless=entry.get('diskless', False),
                        storage_pool=entry.get('storage_pool', storage_pool),
                        active=entry_active(entry, active)))
                replies = lin.resource_create(create_data)
                placed = ', '.join(
                    e.get('node') or e.get('name') for e in nodes)
                check_api_response(module, replies,
                                   'place resource %s on %s' % (name, placed))
            else:
                replies = lin.resource_create([resource_data(
                    node, name, diskless=diskless,
                    storage_pool=storage_pool, active=active)])
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
