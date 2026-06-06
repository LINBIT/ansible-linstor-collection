#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: resource_definition_info
short_description: Query LINSTOR resource definitions
version_added: "1.0.0"
description:
  - Returns LINSTOR resource definitions, including their inline volume
    definitions and properties.
  - Read-only; C(changed) is always C(false).
  - Omit O(name) to return all resource definitions, or set it to query a single one.
options:
  name:
    description:
      - Resource definition name to query.
      - If omitted, all resource definitions are returned.
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
  - module: linbit.linstor.resource_definition
  - module: linbit.linstor.resource_info
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Query all resource definitions
  linbit.linstor.resource_definition_info:
  register: all_rds
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Query a single resource definition
  linbit.linstor.resource_definition_info:
    name: res-0
  register: rd_state
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Show the resource definition's volume definitions
  ansible.builtin.debug:
    var: rd_state.resource_definitions[0].volume_definitions
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
resource_definitions:
  description: List of LINSTOR resource definitions, filtered by O(name) when supplied.
  type: list
  elements: dict
  returned: always
  contains:
    name:
      description: Resource definition name.
      type: str
    resource_group:
      description: Resource group the definition belongs to.
      type: str
    volume_definitions:
      description: Inline volume definitions.
      type: list
      elements: dict
      contains:
        volume_nr:
          description: Volume number.
          type: int
        size_kib:
          description: Volume size in KiB.
          type: int
    properties:
      description: Resource definition properties.
      type: dict
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)


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


def rd_to_dict(rd):
    """Flatten a resource definition object into a JSON-serializable dict."""
    return dict(
        name=getattr(rd, 'name', ''),
        resource_group=getattr(rd, 'resource_group_name', None),
        volume_definitions=[volume_def_info(vd) for vd in get_volume_defs(rd)],
        properties=get_rd_props(rd),
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
            rd_list = lin.resource_dfn_list_raise(
                filter_by_resource_definitions=[name],
                query_volume_definitions=True)
        else:
            rd_list = lin.resource_dfn_list_raise(query_volume_definitions=True)
        rds = [rd_to_dict(rd) for rd in (rd_list.resource_definitions or [])]
        module.exit_json(changed=False, resource_definitions=rds)
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying resource definitions: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
