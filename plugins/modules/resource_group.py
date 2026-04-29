#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: resource_group
short_description: Manage LINSTOR resource groups
version_added: "0.10.0"
description:
  - Creates, modifies, or deletes LINSTOR resource groups.
  - Supports placement rules, DRBD options, and arbitrary properties.
  - Idempotent. If the resource group already exists, only diffs are applied.
  - Use C(state=query) to retrieve resource group properties without modification.
options:
  name:
    description: Name of the resource group.
    type: str
    required: true
  state:
    description: Desired state of the resource group.
    type: str
    default: present
    choices: [present, absent, query]
  description:
    description: Human-readable description of the resource group.
    type: str
  place_count:
    description:
      - Number of replicas to place.
    type: int
    default: 2
  storage_pool:
    description: Default storage pool for the resource group.
    type: str
  diskless_on_remaining:
    description: Whether to create diskless resources on remaining nodes.
    type: bool
  do_not_place_with:
    description: List of resource names to avoid co-locating with.
    type: list
    elements: str
    default: []
  do_not_place_with_regex:
    description: Regex pattern of resource names to avoid co-locating with.
    type: str
  replicas_on_same:
    description:
      - List of node property values for same-node placement.
      - Values should be in C(key=value) format using the full property path.
      - "User-defined auxiliary properties require the C(Aux/) prefix
        (for example C(Aux/site=east)), because C(python-linstor) passes
        values directly to the REST API unlike the CLI which auto-prepends it."
    type: list
    elements: str
    default: []
  replicas_on_different:
    description:
      - List of node property keys for different-node placement.
      - "User-defined auxiliary properties require the C(Aux/) prefix.
        See O(replicas_on_same) for details."
    type: list
    elements: str
    default: []
  layer_list:
    description:
      - Ordered list of layer types (e.g. C([DRBD, CACHE, STORAGE])).
      - LINSTOR defaults to C([DRBD, STORAGE]) if not specified.
    type: list
    elements: str
  provider_list:
    description: List of storage provider types.
    type: list
    elements: str
    default: []
  peer_slots:
    description:
      - Maximum number of peer slots for DRBD resources.
      - LINSTOR defaults to 7 if not specified.
    type: int
  properties:
    description:
      - Dictionary of LINSTOR properties to set on the resource group.
      - Use for properties like C(Cache/CachePool), C(Cache/Cachesize).
    type: dict
    default: {}
  delete_properties:
    description: List of property keys to remove from the resource group.
    type: list
    elements: str
    default: []
  drbd_options:
    description:
      - Nested dictionary of DRBD options organized by category.
      - Categories are C(resource), C(net), C(disk), C(peer_device).
      - Values are mapped to C(DrbdOptions/<Category>/<key>) properties.
    type: dict
    default: {}
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
  - "Auto-quorum override: set C(DrbdOptions/auto-quorum) to C(disabled) on a
    resource group to manually control C(DrbdOptions/Resource/quorum) and
    C(DrbdOptions/Resource/on-no-quorum) for resources spawned from it."
  - "Auto-diskful: C(DrbdOptions/auto-diskful) (integer, minutes) toggles a
    diskless-but-primary resource to diskful after N minutes.
    C(DrbdOptions/auto-diskful-allow-cleanup) (boolean, default C(true)) controls
    whether excess replicas are removed from secondaries to satisfy the place count."
  - "Auto-evict minimum replicas: C(DrbdOptions/AutoEvictMinReplicaCount) sets
    the minimum replicas auto-evict must maintain. Defaults to the resource
    group's place count if unset."
  - "External DRBD metadata: set C(StorPoolNameDrbdMeta) on a resource group
    to apply an external metadata storage pool to all spawned resources."
seealso:
  - name: LINSTOR User's Guide - Resource Groups
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-resource-groups
    description: Resource group concepts and configuration in the LINSTOR User's Guide.
  - name: LINSTOR User's Guide - Auto-Quorum
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-auto-quorum
    description: Automatic quorum management in the LINSTOR User's Guide.
  - name: LINSTOR User's Guide - Auto-Evict
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-auto-evict
    description: Automatic node eviction in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Create a simple resource group
  linbit.linstor.resource_group:
    name: rg-0
    storage_pool: sp-lvm-thin
    place_count: 2
  run_once: true  # noqa: run-once[task]

- name: Create resource group with cache layer
  linbit.linstor.resource_group:
    name: rg-cached
    storage_pool: sp-hdd
    place_count: 2
    layer_list: [DRBD, CACHE, STORAGE]
    properties:
      Cache/CachePool: sp-ssd
      Cache/Cachesize: "10%"
  run_once: true  # noqa: run-once[task]

- name: Create resource group with DRBD options
  linbit.linstor.resource_group:
    name: rg-ha
    storage_pool: sp-lvm-thin
    place_count: 3
    drbd_options:
      resource:
        auto-promote: "no"
        quorum: majority
        on-no-quorum: io-error
  run_once: true  # noqa: run-once[task]

- name: Create resource group with availability zone placement
  linbit.linstor.resource_group:
    name: rg-multi-az
    storage_pool: sp-lvm-thin
    place_count: 3
    # Aux properties must be prefixed with 'Aux/'
    replicas_on_different:
      - "Aux/availability-zone"
  run_once: true  # noqa: run-once[task]

- name: Disable auto-quorum on a resource group with manual quorum settings
  linbit.linstor.resource_group:
    name: rg-manual-quorum
    storage_pool: sp-lvm-thin
    place_count: 3
    properties:
      DrbdOptions/auto-quorum: disabled
    drbd_options:
      resource:
        quorum: majority
        on-no-quorum: io-error
  run_once: true  # noqa: run-once[task]

- name: Set auto-diskful timer on a resource group
  linbit.linstor.resource_group:
    name: rg-auto-diskful
    storage_pool: sp-lvm-thin
    place_count: 2
    properties:
      DrbdOptions/auto-diskful: "15"
      DrbdOptions/auto-diskful-allow-cleanup: "true"
  run_once: true  # noqa: run-once[task]

- name: Set external DRBD metadata pool on a resource group
  linbit.linstor.resource_group:
    name: rg-ext-meta
    storage_pool: sp-lvm-thin
    place_count: 2
    properties:
      StorPoolNameDrbdMeta: sp-meta-ssd
  run_once: true  # noqa: run-once[task]

- name: Query a resource group
  linbit.linstor.resource_group:
    name: rg-0
    state: query
  register: rg_result
  run_once: true  # noqa: run-once[task]

- name: Remove a resource group
  linbit.linstor.resource_group:
    name: rg-0
    state: absent
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
name:
  description: Name of the resource group.
  type: str
  returned: always
exists:
  description: Whether the resource group exists. Only returned with C(state=query).
  type: bool
  returned: query
place_count:
  description: Configured replica count.
  type: int
  returned: success
storage_pool:
  description: Default storage pool.
  type: str
  returned: success
description:
  description: Human-readable description.
  type: str
  returned: query
replicas_on_same:
  description: List of same-node placement constraints.
  type: list
  returned: query
replicas_on_different:
  description: List of different-node placement constraints.
  type: list
  returned: query
properties:
  description: Resource group properties after the operation.
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


DRBD_CATEGORY_MAP = {
    'resource': 'Resource',
    'net': 'Net',
    'disk': 'Disk',
    'peer_device': 'PeerDevice',
}


def flatten_drbd_options(drbd_options):
    """Convert nested drbd_options dict to flat DrbdOptions/ properties."""
    flat = {}
    if not drbd_options:
        return flat
    for category, options in drbd_options.items():
        category_key = DRBD_CATEGORY_MAP.get(category, category.capitalize())
        if options:
            for key, value in options.items():
                prop_key = 'DrbdOptions/%s/%s' % (category_key, key)
                flat[prop_key] = str(value)
    return flat


def get_resource_group(lin, name):
    """Get a resource group by name. Returns the RG object or None."""
    rg_list = lin.resource_group_list_raise(
        filter_by_resource_groups=[name])
    if rg_list.resource_groups:
        return rg_list.resource_groups[0]
    return None


def get_rg_props(rg):
    """Extract the properties dict from a resource group object."""
    if hasattr(rg, 'properties') and rg.properties:
        return dict(rg.properties)
    return {}


def build_modify_kwargs(module, existing_rg):
    """Build kwargs for resource_group_modify based on parameter diffs."""
    kwargs = {}

    description = module.params.get('description')
    if description is not None:
        if not hasattr(existing_rg, 'description') or existing_rg.description != description:
            kwargs['description'] = description

    place_count = module.params.get('place_count')
    if place_count is not None:
        existing_count = getattr(existing_rg, 'select_filter', None)
        if existing_count:
            existing_pc = getattr(existing_count, 'place_count', None)
            if existing_pc != place_count:
                kwargs['place_count'] = place_count
        else:
            kwargs['place_count'] = place_count

    storage_pool = module.params.get('storage_pool')
    if storage_pool is not None:
        existing_sp = None
        sf = getattr(existing_rg, 'select_filter', None)
        if sf:
            sp_list = getattr(sf, 'storage_pool_list', None) or getattr(sf, 'storage_pool', None)
            if isinstance(sp_list, list) and sp_list:
                existing_sp = sp_list[0]
            elif isinstance(sp_list, str):
                existing_sp = sp_list
        if existing_sp != storage_pool:
            kwargs['storage_pool'] = storage_pool

    diskless_on_remaining = module.params.get('diskless_on_remaining')
    if diskless_on_remaining is not None:
        kwargs['diskless_on_remaining'] = diskless_on_remaining

    do_not_place_with = module.params.get('do_not_place_with')
    if do_not_place_with:
        kwargs['do_not_place_with'] = do_not_place_with

    do_not_place_with_regex = module.params.get('do_not_place_with_regex')
    if do_not_place_with_regex is not None:
        kwargs['do_not_place_with_regex'] = do_not_place_with_regex

    replicas_on_same = module.params.get('replicas_on_same')
    if replicas_on_same:
        kwargs['replicas_on_same'] = replicas_on_same

    replicas_on_different = module.params.get('replicas_on_different')
    if replicas_on_different:
        kwargs['replicas_on_different'] = replicas_on_different

    layer_list = module.params.get('layer_list')
    if layer_list:
        kwargs['layer_list'] = layer_list

    provider_list = module.params.get('provider_list')
    if provider_list:
        kwargs['provider_list'] = provider_list

    peer_slots = module.params.get('peer_slots')
    if peer_slots is not None:
        kwargs['peer_slots'] = peer_slots

    return kwargs


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        state=dict(type='str', default='present', choices=['present', 'absent', 'query']),
        description=dict(type='str'),
        place_count=dict(type='int', default=2),
        storage_pool=dict(type='str'),
        diskless_on_remaining=dict(type='bool'),
        do_not_place_with=dict(type='list', elements='str', default=[]),
        do_not_place_with_regex=dict(type='str'),
        replicas_on_same=dict(type='list', elements='str', default=[]),
        replicas_on_different=dict(type='list', elements='str', default=[]),
        layer_list=dict(type='list', elements='str'),
        provider_list=dict(type='list', elements='str', default=[]),
        peer_slots=dict(type='int'),
        properties=dict(type='dict', default={}),
        delete_properties=dict(type='list', elements='str', default=[]),
        drbd_options=dict(type='dict', default={}),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params['name']
    state = module.params['state']
    properties = module.params['properties'] or {}
    delete_properties = module.params['delete_properties'] or []
    drbd_options = module.params['drbd_options'] or {}

    # Merge DRBD options into properties
    all_properties = dict(properties)
    all_properties.update(flatten_drbd_options(drbd_options))

    lin = get_linstor_connection(module)
    changed = False

    try:
        existing_rg = get_resource_group(lin, name)

        if state == 'query':
            if existing_rg is None:
                module.exit_json(changed=False, name=name, exists=False)
            sf = getattr(existing_rg, 'select_filter', None)
            sp_list = getattr(sf, 'storage_pool_list', None) or getattr(sf, 'storage_pool', None) if sf else None
            if isinstance(sp_list, list) and sp_list:
                sp = sp_list[0]
            elif isinstance(sp_list, str):
                sp = sp_list
            else:
                sp = None
            module.exit_json(
                changed=False, name=name, exists=True,
                description=getattr(existing_rg, 'description', ''),
                place_count=getattr(sf, 'place_count', None) if sf else None,
                storage_pool=sp,
                replicas_on_same=list(getattr(sf, 'replicas_on_same', []) or []) if sf else [],
                replicas_on_different=list(getattr(sf, 'replicas_on_different', []) or []) if sf else [],
                properties=get_rg_props(existing_rg))

        if state == 'absent':
            if existing_rg is None:
                module.exit_json(changed=False, name=name)
            if module.check_mode:
                module.exit_json(changed=True, name=name)
            replies = lin.resource_group_delete(name)
            check_api_response(module, replies, 'delete resource group %s' % name)
            module.exit_json(changed=True, name=name)

        # state == 'present'
        if existing_rg is None:
            if module.check_mode:
                module.exit_json(
                    changed=True, name=name,
                    place_count=module.params.get('place_count'),
                    storage_pool=module.params.get('storage_pool'),
                    properties=all_properties)

            create_kwargs = dict(name=name)
            if module.params.get('description'):
                create_kwargs['description'] = module.params['description']
            if module.params.get('place_count') is not None:
                create_kwargs['place_count'] = module.params['place_count']
            if module.params.get('storage_pool'):
                create_kwargs['storage_pool'] = module.params['storage_pool']
            if module.params.get('diskless_on_remaining') is not None:
                create_kwargs['diskless_on_remaining'] = module.params['diskless_on_remaining']
            if module.params.get('do_not_place_with'):
                create_kwargs['do_not_place_with'] = module.params['do_not_place_with']
            if module.params.get('do_not_place_with_regex'):
                create_kwargs['do_not_place_with_regex'] = module.params['do_not_place_with_regex']
            if module.params.get('replicas_on_same'):
                create_kwargs['replicas_on_same'] = module.params['replicas_on_same']
            if module.params.get('replicas_on_different'):
                create_kwargs['replicas_on_different'] = module.params['replicas_on_different']
            if module.params.get('layer_list'):
                create_kwargs['layer_list'] = module.params['layer_list']
            if module.params.get('provider_list'):
                create_kwargs['provider_list'] = module.params['provider_list']
            if module.params.get('peer_slots') is not None:
                create_kwargs['peer_slots'] = module.params['peer_slots']

            replies = lin.resource_group_create(**create_kwargs)
            check_api_response(module, replies, 'create resource group %s' % name)
            changed = True

            # resource_group_create ignores property_dict, so set
            # properties (including DRBD options) via a modify call.
            if all_properties:
                prop_dict = {k: str(v) for k, v in all_properties.items()}
                replies = lin.resource_group_modify(
                    name, property_dict=prop_dict)
                check_api_response(
                    module, replies,
                    'set properties on resource group %s' % name)

            module.exit_json(
                changed=True, name=name,
                place_count=module.params.get('place_count'),
                storage_pool=module.params.get('storage_pool'),
                properties=all_properties)

        # RG exists: check for attribute changes via modify
        modify_kwargs = build_modify_kwargs(module, existing_rg)

        # Compare properties
        current_props = get_rg_props(existing_rg)
        props_to_set, props_to_delete = compute_property_diff(
            current_props, all_properties, delete_properties)

        if not modify_kwargs and not props_to_set and not props_to_delete:
            module.exit_json(
                changed=False, name=name,
                place_count=module.params.get('place_count'),
                storage_pool=module.params.get('storage_pool'),
                properties=current_props)

        if module.check_mode:
            module.exit_json(
                changed=True, name=name,
                place_count=module.params.get('place_count'),
                storage_pool=module.params.get('storage_pool'),
                properties=dict(current_props, **props_to_set))

        # Merge property changes into modify_kwargs
        if props_to_set:
            modify_kwargs['property_dict'] = props_to_set
        if props_to_delete:
            modify_kwargs['delete_props'] = props_to_delete

        replies = lin.resource_group_modify(name, **modify_kwargs)
        check_api_response(module, replies, 'modify resource group %s' % name)
        changed = True

        # Re-read after update
        updated_rg = get_resource_group(lin, name)
        final_props = get_rg_props(updated_rg) if updated_rg else current_props

        module.exit_json(
            changed=changed, name=name,
            place_count=module.params.get('place_count'),
            storage_pool=module.params.get('storage_pool'),
            properties=final_props)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error managing resource group '%s': %s" % (name, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
