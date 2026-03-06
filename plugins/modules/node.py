#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: node
short_description: Manage LINSTOR cluster nodes
version_added: "0.10.0"
description:
  - Creates, modifies, or deletes LINSTOR cluster nodes.
  - Idempotent. If the node already exists, only property changes are applied.
  - Node type and IP address cannot be changed after creation.
    The module warns if the requested values differ from the existing node.
options:
  name:
    description: Name of the LINSTOR node.
    type: str
    required: true
  state:
    description: Desired state of the node.
    type: str
    default: present
    choices: [present, absent]
  node_type:
    description: LINSTOR node type.
    type: str
    default: Satellite
    choices: [Controller, Satellite, Combined, Auxiliary]
  ip:
    description:
      - IP address for the node's default network interface.
      - Only needed to create a new node; omit when modifying an existing node.
    type: str
  com_type:
    description: Communication type for the default network interface.
    type: str
    default: Plain
    choices: [Plain, SSL]
  port:
    description: TCP port for the default network interface.
    type: int
    default: 3366
  netif_name:
    description: Name of the default network interface.
    type: str
    default: default
  properties:
    description: Dictionary of LINSTOR properties to set on the node.
    type: dict
    default: {}
  aux_properties:
    description:
      - Dictionary of auxiliary properties to set on the node.
      - Keys are automatically prefixed with C(Aux/).
    type: dict
    default: {}
  delete_properties:
    description: List of property keys to remove from the node.
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
  - Two usage patterns are supported.
  - Centralized, use C(run_once=true) with a loop over inventory hosts to send
    all API calls from a single host.
  - Per-host, let each play host call the module with its own host variables
    such as C(inventory_hostname) and C(replication_ip).
seealso:
  - name: LINSTOR User's Guide - Initialize Cluster
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-init-cluster
    description: Node creation and cluster initialization in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Register combined node
  linbit.linstor.node:
    name: "{{ inventory_hostname }}"
    ip: "{{ replication_ip }}"  # Defined in inventory
    node_type: Combined
  run_once: true  # noqa: run-once[task]

- name: Register satellite node
  linbit.linstor.node:
    name: node-3
    ip: 10.0.0.3
    node_type: Satellite
  run_once: true  # noqa: run-once[task]

- name: Set auxiliary properties on a node
  linbit.linstor.node:
    name: node-1
    ip: 10.0.0.1
    aux_properties:
      datacenter: us-east-1
      rack: rack-3
  run_once: true  # noqa: run-once[task]

- name: Remove a node from the cluster
  linbit.linstor.node:
    name: node-3
    state: absent
  run_once: true  # noqa: run-once[task]

- name: Add all cluster nodes from one host
  vars:
    is_controller: "{{ 'linstor_controllers' in hostvars[item].group_names }}"
    is_satellite: "{{ 'linstor_satellites' in hostvars[item].group_names }}"
    node_type: >-
      {% if is_controller | bool and is_satellite | bool %}Combined
      {% elif is_controller | bool %}Controller
      {% else %}Satellite{% endif %}
  linbit.linstor.node:
    name: "{{ hostvars[item].inventory_hostname_short }}"
    ip: "{{ hostvars[item].replication_ip }}"
    node_type: "{{ node_type | trim }}"
  loop: "{{ groups['linstor_cluster'] }}"
  run_once: true  # noqa: run-once[task]

# Proxmox VE requires LINSTOR to use short hostnames (inventory_hostname_short)
# Assumes a typical 3-node LINSTOR Combined node cluster configuration
- name: Register Proxmox nodes with short hostnames
  linbit.linstor.node:
    name: "{{ hostvars[item].inventory_hostname_short }}"
    ip: "{{ hostvars[item].replication_ip }}"
    node_type: Combined
  loop: "{{ groups['linstor_cluster'] }}"
  run_once: true  # noqa: run-once[task]

- name: Register satellite nodes with management IP via DNS lookup
  vars:
    # Highly dependent on accurate DNS records;
    # defining ansible_host or a management_ip variable per host is preferred
    management_ip: "{{ lookup('community.general.dig', item) }}"
  linbit.linstor.node:
    name: "{{ item }}"
    ip: "{{ management_ip }}"
    node_type: Satellite
  loop: "{{ groups['linstor_satellites'] }}"
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
name:
  description: Name of the LINSTOR node.
  type: str
  returned: always
node_type:
  description: Node type.
  type: str
  returned: success
ip:
  description: IP address of the default network interface.
  type: str
  returned: success
properties:
  description: Node properties after the operation.
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


NODE_TYPE_MAP = {
    'Controller': 'CONTROLLER',
    'Satellite': 'SATELLITE',
    'Combined': 'COMBINED',
    'Auxiliary': 'AUXILIARY',
}


def get_node(lin, name):
    """Get a node by name. Returns the node object or None."""
    node_list = lin.node_list_raise(filter_by_nodes=[name])
    if node_list.nodes:
        return node_list.nodes[0]
    return None


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


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        state=dict(type='str', default='present', choices=['present', 'absent']),
        node_type=dict(type='str', default='Satellite',
                       choices=['Controller', 'Satellite', 'Combined', 'Auxiliary']),
        ip=dict(type='str'),
        com_type=dict(type='str', default='Plain', choices=['Plain', 'SSL']),
        port=dict(type='int', default=3366),
        netif_name=dict(type='str', default='default'),
        properties=dict(type='dict', default={}),
        aux_properties=dict(type='dict', default={}),
        delete_properties=dict(type='list', elements='str', default=[]),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params['name']
    state = module.params['state']
    node_type = module.params['node_type']
    ip = module.params['ip']
    com_type = module.params['com_type']
    port = module.params['port']
    netif_name = module.params['netif_name']
    properties = module.params['properties'] or {}
    aux_properties = module.params['aux_properties'] or {}
    delete_properties = module.params['delete_properties'] or []

    # Merge aux_properties with Aux/ prefix into properties
    all_properties = dict(properties)
    for key, value in aux_properties.items():
        aux_key = key if key.startswith('Aux/') else 'Aux/' + key
        all_properties[aux_key] = value

    lin = get_linstor_connection(module)
    changed = False

    try:
        existing_node = get_node(lin, name)

        if state == 'absent':
            if existing_node is None:
                module.exit_json(changed=False, name=name)
            if module.check_mode:
                module.exit_json(changed=True, name=name)
            replies = lin.node_delete(name)
            check_api_response(module, replies, 'delete node %s' % name)
            module.exit_json(changed=True, name=name)

        # state == 'present'
        if existing_node is None:
            if not ip:
                module.fail_json(msg="'ip' is required when creating a new node")
            if module.check_mode:
                module.exit_json(
                    changed=True, name=name, node_type=node_type,
                    ip=ip, properties=all_properties)

            node_type_const = NODE_TYPE_MAP.get(node_type, 'SATELLITE')
            replies = lin.node_create(
                node_name=name,
                node_type=node_type_const,
                ip=ip,
                com_type=com_type,
                port=port,
                netif_name=netif_name,
            )
            check_api_response(module, replies, 'create node %s' % name)
            changed = True

            # Set properties on newly created node
            if all_properties or delete_properties:
                prop_dict = {k: str(v) for k, v in all_properties.items()}
                replies = lin.node_modify(name, property_dict=prop_dict,
                                          delete_props=delete_properties or None)
                check_api_response(module, replies, 'set properties on node %s' % name)

            module.exit_json(
                changed=True, name=name, node_type=node_type,
                ip=ip, properties=all_properties)

        # Node exists: check for immutable attribute differences
        existing_type = get_node_type_str(existing_node)
        existing_ip = get_node_ip(existing_node, netif_name)

        if existing_type and node_type.upper() != existing_type.upper():
            module.warn(
                "Node '%s' exists with type '%s' but '%s' was requested. "
                "Node type cannot be changed after creation." % (
                    name, existing_type, node_type))

        if existing_ip and ip and existing_ip != ip:
            module.warn(
                "Node '%s' exists with IP '%s' but '%s' was requested. "
                "IP address cannot be changed after creation." % (
                    name, existing_ip, ip))

        # Compare and update properties
        current_props = get_node_props(existing_node)
        props_to_set, props_to_delete = compute_property_diff(
            current_props, all_properties, delete_properties)

        if not props_to_set and not props_to_delete:
            module.exit_json(
                changed=False, name=name,
                node_type=existing_type or node_type,
                ip=existing_ip or ip,
                properties=current_props)

        if module.check_mode:
            module.exit_json(
                changed=True, name=name,
                node_type=existing_type or node_type,
                ip=existing_ip or ip,
                properties=dict(current_props, **props_to_set))

        replies = lin.node_modify(
            name,
            property_dict=props_to_set,
            delete_props=props_to_delete or None,
        )
        check_api_response(module, replies, 'modify properties on node %s' % name)
        changed = True

        # Re-read properties after update
        updated_node = get_node(lin, name)
        final_props = get_node_props(updated_node) if updated_node else current_props

        module.exit_json(
            changed=changed, name=name,
            node_type=existing_type or node_type,
            ip=existing_ip or ip,
            properties=final_props)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error managing node '%s': %s" % (name, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
