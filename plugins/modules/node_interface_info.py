#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: node_interface_info
short_description: Query LINSTOR node network interfaces
version_added: "1.0.0"
description:
  - Returns the network interfaces of a LINSTOR node.
  - Read-only; C(changed) is always C(false).
  - O(node) is required. Omit O(name) to return all interfaces on the node,
    or set it to return a single interface.
options:
  node:
    description: Node whose network interfaces to query.
    type: str
    required: true
  name:
    description:
      - Interface name to filter by.
      - If omitted, all interfaces on the node are returned.
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
  - module: linbit.linstor.node_interface
  - module: linbit.linstor.node
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Query all interfaces on a node
  linbit.linstor.node_interface_info:
    node: node-1
  register: node1_netifs
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Query the replication interface on a node
  linbit.linstor.node_interface_info:
    node: node-1
    name: replication
  register: repl_netif
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Show the replication interface address
  ansible.builtin.debug:
    msg: "replication IP: {{ repl_netif.net_interfaces[0].ip }}"
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
node:
  description: The node the interfaces belong to.
  type: str
  returned: always
net_interfaces:
  description: List of network interfaces on the node, filtered by O(name) when supplied.
  type: list
  elements: dict
  returned: always
  contains:
    name:
      description: Interface name.
      type: str
    ip:
      description: Interface address.
      type: str
    port:
      description: Satellite port, when set.
      type: int
    com_type:
      description: Satellite encryption type (Plain or SSL), when set.
      type: str
    satellite_connection:
      description: Whether this interface is the active satellite connection.
      type: bool
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)


def netif_to_dict(data):
    """Flatten a net interface data_v1 dict into a JSON-serializable dict."""
    return dict(
        name=data.get('name'),
        ip=data.get('address'),
        port=data.get('satellite_port'),
        com_type=data.get('satellite_encryption_type'),
        satellite_connection=data.get('is_active'),
    )


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        node=dict(type='str', required=True),
        name=dict(type='str'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    node = module.params['node']
    name = module.params['name']

    lin = get_linstor_connection(module)

    try:
        interfaces = []
        for netif in lin.net_interface_list(node):
            data = getattr(netif, 'data_v1', None) or {}
            if not data:
                continue
            if name and data.get('name') != name:
                continue
            interfaces.append(netif_to_dict(data))
        module.exit_json(changed=False, node=node, net_interfaces=interfaces)
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying net interfaces on node '%s': %s" % (
                node, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
