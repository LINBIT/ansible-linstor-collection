#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: volume_group_info
short_description: Query LINSTOR volume groups
version_added: "1.0.0"
description:
  - Returns the volume groups of a LINSTOR resource group.
  - Read-only; C(changed) is always C(false).
  - O(resource_group) is required. Omit O(volume_nr) to return all volume
    groups, or set it to return a single one.
options:
  resource_group:
    description: Resource group whose volume groups to query.
    type: str
    required: true
  volume_nr:
    description:
      - Volume number to filter by.
      - If omitted, all volume groups in the resource group are returned.
    type: int
  controllers:
    description:
      - Comma-separated list of LINSTOR controller URIs.
      - If omitted, reads from C(LS_CONTROLLERS) env, then
        C(/etc/linstor/linstor-client.conf), then falls back to
        C(linstor://localhost).
    type: str
  auth_token:
    description:
      - LINSTOR auth token for clusters with token authentication enabled.
      - If omitted, reads C(auth-token) from C(linstor-client.conf) (user
        configuration overriding system configuration), then falls back to
        C(/var/lib/linstor.d/auth.json) on satellite nodes.
    type: str
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
  - "For cluster-wide tasks use C(run_once=true) or a single-host play such as C(hosts: linstor_controllers[0])."
seealso:
  - module: linbit.linstor.volume_group
  - module: linbit.linstor.resource_group
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Query all volume groups in a resource group
  linbit.linstor.volume_group_info:
    resource_group: rg-0
  register: rg0_vgs
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Query a single volume group
  linbit.linstor.volume_group_info:
    resource_group: rg-0
    volume_nr: 0
  register: vg_state
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Show the volume group's properties
  ansible.builtin.debug:
    var: vg_state.volume_groups[0].properties
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
resource_group:
  description: The resource group the volume groups belong to.
  type: str
  returned: always
volume_groups:
  description: List of volume groups, filtered by O(volume_nr) when supplied.
  type: list
  elements: dict
  returned: always
  contains:
    volume_nr:
      description: Volume number.
      type: int
    properties:
      description: Volume group properties.
      type: dict
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)


def get_vg_props(vg):
    """Extract the properties dict from a volume group object."""
    if hasattr(vg, 'properties') and vg.properties:
        return dict(vg.properties)
    return {}


def vg_to_dict(vg):
    """Flatten a volume group object into a JSON-serializable dict."""
    return dict(
        volume_nr=vg.number if hasattr(vg, 'number') else None,
        properties=get_vg_props(vg),
    )


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        resource_group=dict(type='str', required=True),
        volume_nr=dict(type='int'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    resource_group = module.params['resource_group']
    volume_nr = module.params['volume_nr']

    lin = get_linstor_connection(module)

    try:
        vg_list = lin.volume_group_list_raise(resource_group)
        volume_groups = [vg_to_dict(vg)
                         for vg in (getattr(vg_list, 'volume_groups', None) or [])]
        if volume_nr is not None:
            volume_groups = [v for v in volume_groups if v['volume_nr'] == volume_nr]
        module.exit_json(changed=False, resource_group=resource_group,
                         volume_groups=volume_groups)
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying volume groups for resource group '%s': %s" % (
                resource_group, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
