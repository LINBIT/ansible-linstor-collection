#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: resource_definition
short_description: Manage LINSTOR resource definitions
version_added: "0.9.7"
description:
  - Creates, modifies, or deletes LINSTOR resource definitions.
  - Supports inline volume definitions and DRBD options.
  - Idempotent. Existing volume definitions are updated if size differs.
    Missing volume definitions are added, but existing ones not in the list
    are not deleted (too destructive).
  - Use C(state=query) to retrieve resource definition properties without modification.
options:
  name:
    description: Name of the resource definition.
    type: str
    required: true
  state:
    description: Desired state of the resource definition.
    type: str
    default: present
    choices: [present, absent, query]
  port:
    description: TCP port for the DRBD resource.
    type: int
  external_name:
    description: External name for the resource definition.
    type: str
  resource_group:
    description: Resource group to assign this definition to.
    type: str
  layer_list:
    description:
      - Ordered list of layer types.
      - LINSTOR defaults to C([DRBD, STORAGE]) if not specified.
    type: list
    elements: str
  peer_slots:
    description:
      - Maximum number of peer slots for the DRBD resource.
      - LINSTOR defaults to 7 if not specified.
    type: int
  volume_definitions:
    description:
      - List of volume definitions to create inline.
      - Each item is a dict with keys C(size) (required), C(volume_nr),
        C(minor_nr), C(encrypt), C(storage_pool), C(gross).
    type: list
    elements: dict
    default: []
    suboptions:
      size:
        description: Volume size (e.g. C(1G), C(500M)).
        type: str
        required: true
      volume_nr:
        description: Volume number (auto-assigned if omitted).
        type: int
      minor_nr:
        description: DRBD minor number.
        type: int
      encrypt:
        description: Enable LUKS encryption.
        type: bool
        default: false
      storage_pool:
        description: Override storage pool for this volume.
        type: str
      gross:
        description: Use gross size calculation.
        type: bool
        default: false
  drbd_options:
    description:
      - Nested dictionary of DRBD options organized by category.
      - Categories are C(resource), C(net), C(disk), C(peer_device).
      - Values are mapped to C(DrbdOptions/<Category>/<key>) properties.
    type: dict
    default: {}
  properties:
    description: Dictionary of LINSTOR properties to set on the resource definition.
    type: dict
    default: {}
  delete_properties:
    description: List of property keys to remove from the resource definition.
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
  - "LUKS encryption: include C(LUKS) in O(layer_list) (for example C([DRBD, LUKS, STORAGE]))
    to encrypt volumes. Also requires C(encrypt: true) on individual volume definitions
    or a cluster-wide passphrase via M(linbit.linstor.encryption). C(cryptsetup) must
    be installed on satellite nodes before the satellite service starts."
  - "Auto-quorum and auto-diskful can be set at the resource-definition level
    (highest priority, overrides resource group and controller defaults).
    Use O(properties) with keys like C(DrbdOptions/auto-quorum) or
    C(DrbdOptions/auto-diskful)."
  - "External DRBD metadata: set C(StorPoolNameDrbdMeta) on a resource definition
    to override the resource group setting."
seealso:
  - name: LINSTOR User's Guide - Creating Volumes
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-new-volume
    description: Resource and volume definition concepts in the LINSTOR User's Guide.
  - name: LINSTOR User's Guide - Deleting Resource Definitions
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-deleting-resource-definitions
    description: Deleting resource definitions in the LINSTOR User's Guide.
  - name: LINSTOR User's Guide - Encrypted Volumes
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-encrypted-volumes
    description: Volume encryption concepts and configuration in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Create resource definition with volume definitions
  linbit.linstor.resource_definition:
    name: res-0
    volume_definitions:
      - size: 1G
      - size: 500M
  run_once: true  # noqa: run-once[task]

- name: Create resource definition in a resource group
  linbit.linstor.resource_definition:
    name: res-0
    resource_group: rg-0
  run_once: true  # noqa: run-once[task]

# Requires a cluster-wide passphrase via linbit.linstor.encryption
# and cryptsetup installed on all satellite nodes
- name: Create an encrypted resource definition with LUKS layer
  linbit.linstor.resource_definition:
    name: res-encrypted
    layer_list: [DRBD, LUKS, STORAGE]
    volume_definitions:
      - size: 10G
        encrypt: true
  run_once: true  # noqa: run-once[task]

- name: Set DRBD options on resource definition
  linbit.linstor.resource_definition:
    name: res-0
    drbd_options:
      resource:
        auto-promote: "no"
        on-no-quorum: io-error
  run_once: true  # noqa: run-once[task]

- name: Disable auto-quorum on a specific resource definition
  linbit.linstor.resource_definition:
    name: res-0
    properties:
      DrbdOptions/auto-quorum: disabled
    drbd_options:
      resource:
        quorum: majority
        on-no-quorum: io-error
  run_once: true  # noqa: run-once[task]

- name: Query a resource definition
  linbit.linstor.resource_definition:
    name: res-0
    state: query
  register: rd_result
  run_once: true  # noqa: run-once[task]

# Deleting a resource definition removes all associated resources and volumes
- name: Remove a resource definition
  linbit.linstor.resource_definition:
    name: res-0
    state: absent
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
name:
  description: Name of the resource definition.
  type: str
  returned: always
exists:
  description: Whether the resource definition exists. Only returned with C(state=query).
  type: bool
  returned: query
resource_group:
  description: Associated resource group name.
  type: str
  returned: success
volume_definitions:
  description: List of volume definition details after the operation.
  type: list
  returned: success
properties:
  description: Resource definition properties after the operation.
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


def get_resource_definition(lin, name):
    """Get a resource definition by name. Returns the RD object or None."""
    rd_list = lin.resource_dfn_list_raise(
        filter_by_resource_definitions=[name],
        query_volume_definitions=True,
    )
    if rd_list.resource_definitions:
        return rd_list.resource_definitions[0]
    return None


def get_rd_props(rd):
    """Extract the properties dict from a resource definition object."""
    if hasattr(rd, 'properties') and rd.properties:
        return dict(rd.properties)
    return {}


def get_volume_defs(rd):
    """Extract volume definitions from a resource definition."""
    if hasattr(rd, 'volume_definitions'):
        return rd.volume_definitions
    return []


def volume_def_info(vd):
    """Extract info dict from a volume definition object."""
    info = {}
    if hasattr(vd, 'number'):
        info['volume_nr'] = vd.number
    if hasattr(vd, 'size'):
        info['size_kib'] = vd.size
    return info


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        state=dict(type='str', default='present', choices=['present', 'absent', 'query']),
        port=dict(type='int'),
        external_name=dict(type='str'),
        resource_group=dict(type='str'),
        layer_list=dict(type='list', elements='str'),
        peer_slots=dict(type='int'),
        volume_definitions=dict(
            type='list', elements='dict', default=[],
            options=dict(
                size=dict(type='str', required=True),
                volume_nr=dict(type='int'),
                minor_nr=dict(type='int'),
                encrypt=dict(type='bool', default=False),
                storage_pool=dict(type='str'),
                gross=dict(type='bool', default=False),
            ),
        ),
        drbd_options=dict(type='dict', default={}),
        properties=dict(type='dict', default={}),
        delete_properties=dict(type='list', elements='str', default=[]),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params['name']
    state = module.params['state']
    port = module.params.get('port')
    external_name = module.params.get('external_name')
    resource_group = module.params.get('resource_group')
    layer_list = module.params['layer_list'] or []
    peer_slots = module.params.get('peer_slots')
    volume_definitions = module.params['volume_definitions'] or []
    drbd_options = module.params['drbd_options'] or {}
    properties = module.params['properties'] or {}
    delete_properties = module.params['delete_properties'] or []

    # Merge DRBD options into properties
    all_properties = dict(properties)
    all_properties.update(flatten_drbd_options(drbd_options))

    lin = get_linstor_connection(module)
    changed = False

    try:
        existing_rd = get_resource_definition(lin, name)

        if state == 'query':
            if existing_rd is None:
                module.exit_json(changed=False, name=name, exists=False)
            current_props = get_rd_props(existing_rd)
            existing_vds = get_volume_defs(existing_rd)
            vd_info_list = [volume_def_info(vd) for vd in existing_vds]
            rd_rg = getattr(existing_rd, 'resource_group_name', None)
            module.exit_json(
                changed=False, name=name, exists=True,
                resource_group=rd_rg,
                volume_definitions=vd_info_list,
                properties=current_props)

        if state == 'absent':
            if existing_rd is None:
                module.exit_json(changed=False, name=name)
            if module.check_mode:
                module.exit_json(changed=True, name=name)
            replies = lin.resource_dfn_delete(name)
            check_api_response(module, replies, 'delete resource definition %s' % name)
            module.exit_json(changed=True, name=name)

        # state == 'present'
        if existing_rd is None:
            if module.check_mode:
                module.exit_json(
                    changed=True, name=name,
                    resource_group=resource_group,
                    volume_definitions=[],
                    properties=all_properties)

            create_kwargs = dict(name=name)
            if port is not None:
                create_kwargs['port'] = port
            if external_name:
                create_kwargs['external_name'] = external_name
            if resource_group:
                create_kwargs['resource_group'] = resource_group
            if layer_list:
                create_kwargs['layer_list'] = layer_list
            if peer_slots is not None:
                create_kwargs['peer_slots'] = peer_slots

            replies = lin.resource_dfn_create(**create_kwargs)
            check_api_response(module, replies, 'create resource definition %s' % name)
            changed = True

            # Create volume definitions
            for vd_params in volume_definitions:
                size_kib = parse_size(vd_params['size'])
                vd_kwargs = dict(
                    rsc_name=name,
                    size=size_kib,
                )
                if vd_params.get('volume_nr') is not None:
                    vd_kwargs['volume_nr'] = vd_params['volume_nr']
                if vd_params.get('minor_nr') is not None:
                    vd_kwargs['minor_nr'] = vd_params['minor_nr']
                if vd_params.get('encrypt'):
                    vd_kwargs['encrypt'] = True
                if vd_params.get('storage_pool'):
                    vd_kwargs['storage_pool'] = vd_params['storage_pool']
                if vd_params.get('gross'):
                    vd_kwargs['gross'] = True

                replies = lin.volume_dfn_create(**vd_kwargs)
                check_api_response(
                    module, replies,
                    'create volume definition in %s' % name)

            # Set properties via resource_dfn_modify
            if all_properties or delete_properties:
                prop_dict = {k: str(v) for k, v in all_properties.items()}
                replies = lin.resource_dfn_modify(
                    name,
                    property_dict=prop_dict,
                    delete_props=delete_properties or None,
                )
                check_api_response(
                    module, replies,
                    'set properties on resource definition %s' % name)

            # Re-read to get volume definitions
            final_rd = get_resource_definition(lin, name)
            final_vds = []
            if final_rd:
                for vd in get_volume_defs(final_rd):
                    final_vds.append(volume_def_info(vd))

            module.exit_json(
                changed=True, name=name,
                resource_group=resource_group,
                volume_definitions=final_vds,
                properties=all_properties)

        # RD exists: check for changes
        current_props = get_rd_props(existing_rd)
        existing_vds = get_volume_defs(existing_rd)
        existing_vd_map = {}
        for vd in existing_vds:
            if hasattr(vd, 'number'):
                existing_vd_map[vd.number] = vd

        # Check volume definitions for changes
        vds_to_create = []
        vds_to_resize = []
        for i, vd_params in enumerate(volume_definitions):
            desired_size_kib = parse_size(vd_params['size'])
            vd_nr = vd_params.get('volume_nr')
            if vd_nr is None:
                vd_nr = i

            if vd_nr in existing_vd_map:
                existing_size = existing_vd_map[vd_nr].size if hasattr(existing_vd_map[vd_nr], 'size') else 0
                if existing_size != desired_size_kib:
                    vds_to_resize.append((vd_nr, desired_size_kib))
            else:
                vds_to_create.append(vd_params)

        # Compare properties
        props_to_set, props_to_delete = compute_property_diff(
            current_props, all_properties, delete_properties)

        if not vds_to_create and not vds_to_resize and not props_to_set and not props_to_delete:
            vd_info_list = [volume_def_info(vd) for vd in existing_vds]
            module.exit_json(
                changed=False, name=name,
                resource_group=resource_group,
                volume_definitions=vd_info_list,
                properties=current_props)

        if module.check_mode:
            module.exit_json(
                changed=True, name=name,
                resource_group=resource_group,
                volume_definitions=[volume_def_info(vd) for vd in existing_vds],
                properties=dict(current_props, **props_to_set))

        # Create missing volume definitions
        for vd_params in vds_to_create:
            size_kib = parse_size(vd_params['size'])
            vd_kwargs = dict(rsc_name=name, size=size_kib)
            if vd_params.get('volume_nr') is not None:
                vd_kwargs['volume_nr'] = vd_params['volume_nr']
            if vd_params.get('minor_nr') is not None:
                vd_kwargs['minor_nr'] = vd_params['minor_nr']
            if vd_params.get('encrypt'):
                vd_kwargs['encrypt'] = True
            if vd_params.get('storage_pool'):
                vd_kwargs['storage_pool'] = vd_params['storage_pool']
            if vd_params.get('gross'):
                vd_kwargs['gross'] = True
            replies = lin.volume_dfn_create(**vd_kwargs)
            check_api_response(module, replies, 'create volume definition in %s' % name)
            changed = True

        # Resize changed volume definitions
        for vd_nr, new_size_kib in vds_to_resize:
            replies = lin.volume_dfn_modify(name, vd_nr, size=new_size_kib)
            check_api_response(
                module, replies,
                'resize volume %d in %s' % (vd_nr, name))
            changed = True

        # Apply property changes via resource_dfn_modify
        if props_to_set or props_to_delete:
            replies = lin.resource_dfn_modify(
                name,
                property_dict=props_to_set,
                delete_props=props_to_delete or None,
            )
            check_api_response(
                module, replies,
                'modify properties on resource definition %s' % name)
            changed = True

        # Re-read after update
        final_rd = get_resource_definition(lin, name)
        final_vds = []
        final_props = current_props
        if final_rd:
            for vd in get_volume_defs(final_rd):
                final_vds.append(volume_def_info(vd))
            final_props = get_rd_props(final_rd)

        module.exit_json(
            changed=changed, name=name,
            resource_group=resource_group,
            volume_definitions=final_vds,
            properties=final_props)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error managing resource definition '%s': %s" % (
                name, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
