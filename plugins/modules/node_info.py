#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: node_info
short_description: Query LINSTOR nodes
version_added: "1.0.0"
description:
  - Returns information about LINSTOR cluster nodes.
  - Read-only; C(changed) is always C(false).
  - Omit O(name) to return all nodes, or set it to query a single node.
options:
  name:
    description:
      - Node name to query.
      - If omitted, all nodes are returned.
    type: str
  netif_name:
    description:
      - Network interface to read the address, encryption type, and
        satellite port from for each node.
    type: str
    default: default
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
  - module: linbit.linstor.node
  - module: linbit.linstor.node_interface
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Query all nodes
  linbit.linstor.node_info:
  register: all_nodes
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Query a single node and wait until it is ONLINE
  linbit.linstor.node_info:
    name: node-1
  register: node_state
  until: node_state.nodes | length > 0 and node_state.nodes[0].connection_status == 'ONLINE'
  retries: 12
  delay: 5
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
nodes:
  description: List of LINSTOR nodes, filtered by O(name) when supplied.
  type: list
  elements: dict
  returned: always
  contains:
    name:
      description: Node name.
      type: str
    node_type:
      description: Node type (Controller, Satellite, Combined, or Auxiliary).
      type: str
    connection_status:
      description: Satellite connection status (for example ONLINE or OFFLINE).
      type: str
    ip:
      description: Address of the O(netif_name) network interface.
      type: str
    com_type:
      description: Encryption type of the O(netif_name) interface (Plain or SSL).
      type: str
    satellite_port:
      description: Satellite port of the O(netif_name) interface.
      type: int
    properties:
      description: Node properties.
      type: dict
    aux_properties:
      description: Auxiliary properties with the C(Aux/) prefix stripped.
      type: dict
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)


def get_node_props(node):
    """Extract the properties dict from a node object."""
    if hasattr(node, 'properties') and node.properties:
        return dict(node.properties)
    return {}


def get_node_type_str(node):
    """Get the human-readable node type string."""
    if hasattr(node, 'type'):
        return str(node.type)
    return ''


def get_node_ip(node, netif_name='default'):
    """Get the IP address from a node's network interface."""
    if hasattr(node, 'net_interfaces'):
        for netif in node.net_interfaces:
            if netif.name == netif_name:
                return netif.address
    return ''


def get_node_netif(node, netif_name='default'):
    """Get the network interface object from a node."""
    if hasattr(node, 'net_interfaces'):
        for netif in node.net_interfaces:
            if netif.name == netif_name:
                return netif
    return None


def get_connection_status(node):
    """Get the connection status string from a node object."""
    if hasattr(node, 'connection_status'):
        return str(node.connection_status)
    return ''


def get_aux_properties(props):
    """Extract auxiliary properties with the Aux/ prefix stripped."""
    aux = {}
    for key, value in props.items():
        if key.startswith('Aux/'):
            aux[key[4:]] = value
    return aux


def node_to_dict(node, netif_name):
    """Flatten a node object into a JSON-serializable dict."""
    props = get_node_props(node)
    netif = get_node_netif(node, netif_name)
    return dict(
        name=getattr(node, 'name', ''),
        node_type=get_node_type_str(node),
        connection_status=get_connection_status(node),
        ip=get_node_ip(node, netif_name),
        com_type=netif.stlt_encryption_type if netif else None,
        satellite_port=netif.stlt_port if netif else None,
        properties=props,
        aux_properties=get_aux_properties(props),
    )


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str'),
        netif_name=dict(type='str', default='default'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params['name']
    netif_name = module.params['netif_name']

    lin = get_linstor_connection(module)

    try:
        if name:
            node_list = lin.node_list_raise(filter_by_nodes=[name])
        else:
            node_list = lin.node_list_raise()
        nodes = [node_to_dict(n, netif_name) for n in (node_list.nodes or [])]
        module.exit_json(changed=False, nodes=nodes)
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying nodes: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
