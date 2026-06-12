#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: resource_info
short_description: Query LINSTOR resources
version_added: "1.0.0"
description:
  - Returns information about LINSTOR resources (resource definitions and
    their deployments).
  - Read-only; C(changed) is always C(false).
  - Omit O(name) to return all resources, or set it to query a single one.
  - A defined resource with no deployments is returned with an empty
    C(nodes) list.
options:
  name:
    description:
      - Resource name to query.
      - If omitted, all resources are returned.
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
  - module: linbit.linstor.resource
  - module: linbit.linstor.resource_definition
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Query all resources
  linbit.linstor.resource_info:
  register: all_resources
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Query a single resource and inspect its placement
  linbit.linstor.resource_info:
    name: res-0
  register: resource_state
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Show which nodes the resource is deployed on
  ansible.builtin.debug:
    msg: "res-0 is deployed on {{ resource_state.resources[0].nodes }}"
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
resources:
  description: List of LINSTOR resources, filtered by O(name) when supplied.
  type: list
  elements: dict
  returned: always
  contains:
    name:
      description: Resource (resource definition) name.
      type: str
    nodes:
      description: Node names where the resource is deployed.
      type: list
      elements: str
    flags:
      description: Per-node resource flags (for example DRBD_DISKLESS or TIE_BREAKER).
      type: dict
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
    """Extract properties from a resource definition."""
    if hasattr(rd, 'properties') and rd.properties:
        return dict(rd.properties)
    return {}


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
            rd_list = lin.resource_dfn_list_raise(filter_by_resource_definitions=[name])
            rsc_list = lin.resource_list_raise(filter_by_resources=[name])
        else:
            rd_list = lin.resource_dfn_list_raise()
            rsc_list = lin.resource_list_raise()

        # Bucket deployments by resource-definition name in a single pass so
        # listing all resources stays at two API calls, not one per RD.
        by_rd = {}
        for rsc in (rsc_list.resources or []):
            rd_name = getattr(rsc, 'name', None)
            if rd_name is None:
                continue
            by_rd.setdefault(rd_name, []).append(rsc)

        resources = []
        for rd in (rd_list.resource_definitions or []):
            rd_name = getattr(rd, 'name', '')
            deployed = by_rd.get(rd_name, [])
            nodes = [r.node_name for r in deployed if hasattr(r, 'node_name')]
            flags = {}
            for r in deployed:
                if hasattr(r, 'node_name'):
                    flags[r.node_name] = list(getattr(r, 'flags', []) or [])
            resources.append(dict(
                name=rd_name,
                nodes=nodes,
                flags=flags,
                properties=get_rd_props(rd),
            ))

        module.exit_json(changed=False, resources=resources)
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying resources: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
