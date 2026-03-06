#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: volume_group
short_description: Manage LINSTOR volume groups
version_added: "0.10.0"
description:
  - Creates, modifies, or deletes LINSTOR volume groups within a resource group.
  - Idempotent. If the volume group already exists, only property changes are applied.
options:
  resource_group:
    description: Name of the parent resource group.
    type: str
    required: true
  volume_nr:
    description:
      - Volume number within the resource group.
    type: int
    default: 0
  state:
    description: Desired state of the volume group.
    type: str
    default: present
    choices: [present, absent]
  gross:
    description: Whether to use gross size calculation.
    type: bool
  properties:
    description: Dictionary of LINSTOR properties to set on the volume group.
    type: dict
    default: {}
  delete_properties:
    description: List of property keys to remove from the volume group.
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
  - "QoS throttling: C(sys/fs/blkio_throttle_read), C(sys/fs/blkio_throttle_write),
    C(sys/fs/blkio_throttle_read_iops), and C(sys/fs/blkio_throttle_write_iops) can be
    set on volume groups to limit I/O bandwidth (bytes per second) and IOPS. Resources
    spawned from the parent resource group inherit these QoS settings. Changes also
    apply to existing resources."
seealso:
  - name: LINSTOR User's Guide - Resource Groups
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-resource-groups
    description: Resource group and volume group concepts in the LINSTOR User's Guide.
  - name: LINSTOR User's Guide - QoS Settings
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-qos
    description: QoS throttling via sysfs properties in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Create volume group (auto-assigned volume number)
  linbit.linstor.volume_group:
    resource_group: rg-0
  run_once: true  # noqa: run-once[task]

- name: Create volume group with specific number
  linbit.linstor.volume_group:
    resource_group: rg-0
    volume_nr: 1
  run_once: true  # noqa: run-once[task]

# QoS: limit write bandwidth to 1 MB/s on volume group 0
# Resources spawned from rg-qos inherit this setting
- name: Set QoS write throttle on a volume group
  linbit.linstor.volume_group:
    resource_group: rg-qos
    volume_nr: 0
    properties:
      sys/fs/blkio_throttle_write: "1048576"
  run_once: true  # noqa: run-once[task]

# QoS: limit both read and write bandwidth and IOPS
- name: Set QoS read and write throttles on a volume group
  linbit.linstor.volume_group:
    resource_group: rg-qos
    volume_nr: 0
    properties:
      sys/fs/blkio_throttle_read: "10485760"
      sys/fs/blkio_throttle_write: "5242880"
      sys/fs/blkio_throttle_read_iops: "1000"
      sys/fs/blkio_throttle_write_iops: "500"
  run_once: true  # noqa: run-once[task]

- name: Delete a volume group
  linbit.linstor.volume_group:
    resource_group: rg-0
    volume_nr: 1
    state: absent
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
resource_group:
  description: Name of the parent resource group.
  type: str
  returned: always
volume_nr:
  description: Volume number.
  type: int
  returned: success
properties:
  description: Volume group properties after the operation.
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


def get_volume_groups(lin, resource_group):
    """Get all volume groups for a resource group. Returns list of VG objects."""
    vg_list = lin.volume_group_list_raise(resource_group)
    if hasattr(vg_list, 'volume_groups'):
        return vg_list.volume_groups
    return []


def find_volume_group(volume_groups, volume_nr):
    """Find a specific volume group by number. Returns the VG object or None."""
    for vg in volume_groups:
        if hasattr(vg, 'number') and vg.number == volume_nr:
            return vg
    return None


def get_vg_props(vg):
    """Extract the properties dict from a volume group object."""
    if hasattr(vg, 'properties') and vg.properties:
        return dict(vg.properties)
    return {}


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        resource_group=dict(type='str', required=True),
        volume_nr=dict(type='int', default=0),
        state=dict(type='str', default='present', choices=['present', 'absent']),
        gross=dict(type='bool'),
        properties=dict(type='dict', default={}),
        delete_properties=dict(type='list', elements='str', default=[]),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    resource_group = module.params['resource_group']
    volume_nr = module.params['volume_nr']
    state = module.params['state']
    gross = module.params.get('gross')
    properties = module.params['properties'] or {}
    delete_properties = module.params['delete_properties'] or []

    lin = get_linstor_connection(module)
    changed = False

    try:
        volume_groups = get_volume_groups(lin, resource_group)

        if state == 'absent':
            existing_vg = find_volume_group(volume_groups, volume_nr)
            if existing_vg is None:
                module.exit_json(
                    changed=False, resource_group=resource_group,
                    volume_nr=volume_nr)
            if module.check_mode:
                module.exit_json(
                    changed=True, resource_group=resource_group,
                    volume_nr=volume_nr)
            replies = lin.volume_group_delete(resource_group, volume_nr)
            check_api_response(
                module, replies,
                'delete volume group %d in %s' % (volume_nr, resource_group))
            module.exit_json(
                changed=True, resource_group=resource_group,
                volume_nr=volume_nr)

        # state == 'present'
        existing_vg = find_volume_group(volume_groups, volume_nr)

        if existing_vg is not None:
            volume_nr = existing_vg.number if hasattr(existing_vg, 'number') else volume_nr

            # Volume group exists: compare and update properties
            current_props = get_vg_props(existing_vg)
            props_to_set, props_to_delete = compute_property_diff(
                current_props, properties, delete_properties)

            if not props_to_set and not props_to_delete:
                module.exit_json(
                    changed=False, resource_group=resource_group,
                    volume_nr=volume_nr, properties=current_props)

            if module.check_mode:
                module.exit_json(
                    changed=True, resource_group=resource_group,
                    volume_nr=volume_nr,
                    properties=dict(current_props, **props_to_set))

            replies = lin.volume_group_modify(
                resource_group, volume_nr,
                property_dict=props_to_set,
                delete_props=props_to_delete or None,
            )
            check_api_response(
                module, replies,
                'modify properties on volume group %d in %s' % (
                    volume_nr, resource_group))
            changed = True

            updated_vgs = get_volume_groups(lin, resource_group)
            updated_vg = find_volume_group(updated_vgs, volume_nr)
            final_props = get_vg_props(updated_vg) if updated_vg else current_props

            module.exit_json(
                changed=changed, resource_group=resource_group,
                volume_nr=volume_nr, properties=final_props)

        # Volume group does not exist: create
        if module.check_mode:
            module.exit_json(
                changed=True, resource_group=resource_group,
                volume_nr=volume_nr, properties=properties)

        create_kwargs = dict(
            resource_grp_name=resource_group,
            volume_nr=volume_nr,
        )
        if gross is not None:
            create_kwargs['gross'] = gross

        replies = lin.volume_group_create(**create_kwargs)
        check_api_response(
            module, replies,
            'create volume group in %s' % resource_group)
        changed = True

        # Set properties via modify (some create calls ignore property_dict)
        if properties:
            prop_dict = {k: str(v) for k, v in properties.items()}
            replies = lin.volume_group_modify(
                resource_group, volume_nr,
                property_dict=prop_dict)
            check_api_response(
                module, replies,
                'set properties on volume group %d in %s' % (
                    volume_nr, resource_group))

        module.exit_json(
            changed=True, resource_group=resource_group,
            volume_nr=volume_nr, properties=properties)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error managing volume group in '%s': %s" % (
                resource_group, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
