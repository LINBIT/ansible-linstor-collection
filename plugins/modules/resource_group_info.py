#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: resource_group_info
short_description: Query LINSTOR resource groups
version_added: "1.0.0"
description:
  - Returns information about LINSTOR resource groups.
  - Read-only; C(changed) is always C(false).
  - Omit O(name) to return all resource groups, or set it to query a single one.
options:
  name:
    description:
      - Resource group name to query.
      - If omitted, all resource groups are returned.
    type: str
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
  - module: linbit.linstor.resource_group
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Query all resource groups
  linbit.linstor.resource_group_info:
  register: all_rgs
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Query a single resource group
  linbit.linstor.resource_group_info:
    name: rg-0
  register: rg_state
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Show the resource group's place count
  ansible.builtin.debug:
    msg: "rg-0 place_count is {{ rg_state.resource_groups[0].place_count }}"
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
resource_groups:
  description: List of LINSTOR resource groups, filtered by O(name) when supplied.
  type: list
  elements: dict
  returned: always
  contains:
    name:
      description: Resource group name.
      type: str
    description:
      description: Resource group description.
      type: str
    place_count:
      description: Replica place count from the select filter.
      type: int
    storage_pool:
      description: Storage pool from the select filter, or null if unset.
      type: str
    replicas_on_same:
      description: Replicas-on-same properties from the select filter.
      type: list
      elements: str
    replicas_on_different:
      description: Replicas-on-different properties from the select filter.
      type: list
      elements: str
    properties:
      description: Resource group properties.
      type: dict
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)


def get_rg_props(rg):
    """Extract the properties dict from a resource group object."""
    if hasattr(rg, 'properties') and rg.properties:
        return dict(rg.properties)
    return {}


def rg_to_dict(rg):
    """Flatten a resource group object into a JSON-serializable dict."""
    sf = getattr(rg, 'select_filter', None)
    sp_list = (getattr(sf, 'storage_pool_list', None)
               or getattr(sf, 'storage_pool', None)) if sf else None
    if isinstance(sp_list, list) and sp_list:
        sp = sp_list[0]
    elif isinstance(sp_list, str):
        sp = sp_list
    else:
        sp = None
    return dict(
        name=getattr(rg, 'name', ''),
        description=getattr(rg, 'description', ''),
        place_count=getattr(sf, 'place_count', None) if sf else None,
        storage_pool=sp,
        replicas_on_same=list(getattr(sf, 'replicas_on_same', []) or []) if sf else [],
        replicas_on_different=list(getattr(sf, 'replicas_on_different', []) or []) if sf else [],
        properties=get_rg_props(rg),
    )


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params['name']

    lin = get_linstor_connection(module)

    try:
        if name:
            rg_list = lin.resource_group_list_raise(filter_by_resource_groups=[name])
        else:
            rg_list = lin.resource_group_list_raise()
        rgs = [rg_to_dict(rg) for rg in (rg_list.resource_groups or [])]
        module.exit_json(changed=False, resource_groups=rgs)
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying resource groups: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
