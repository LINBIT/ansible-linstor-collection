#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: node
short_description: Manage LINSTOR cluster nodes
version_added: "0.9.7"
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
    description:
      - Desired state of the node.
      - C(evacuated) migrates all resources off the node for maintenance.
        Idempotent, skips if the node already has the C(EVACUATE) flag.
      - C(restored) reverses an evacuation, allowing resources to return.
        Idempotent, skips if the node does not have the C(EVACUATE) flag.
    type: str
    default: present
    choices: [present, absent, evacuated, restored]
  node_type:
    description: >-
      LINSTOR node type.
      Defaults to C(Satellite) when creating a new node.
      Omit when managing properties on existing nodes to avoid type mismatch warnings.
    type: str
    choices: [Controller, Satellite, Combined, Auxiliary]
  ip:
    description:
      - IP address for the node's default network interface.
      - Only needed to create a new node; omit when modifying an existing node.
    type: str
  com_type:
    description:
      - Communication type for the default network interface.
      - Defaults to C(Plain) when creating a new node.
      - When specified on an existing node, the module updates the network
        interface to match. Omit to leave the current setting unchanged.
    type: str
    choices: [Plain, SSL]
  port:
    description:
      - TCP port for the default network interface.
      - Defaults to C(3366) for C(Plain) or C(3367) for C(SSL) when creating a new node.
      - When C(com_type) is specified on an existing node and C(port) is omitted,
        the port defaults to C(3366) for C(Plain) or C(3367) for C(SSL).
    type: int
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
  evacuate_target:
    description:
      - List of preferred target node names for evacuation.
      - LINSTOR will prefer placing evacuated resources on these nodes.
      - Only used when C(state=evacuated).
      - Mutually exclusive with O(evacuate_do_not_target).
    type: list
    elements: str
  evacuate_do_not_target:
    description:
      - List of node names to exclude as evacuation targets.
      - Only used when C(state=evacuated).
      - Mutually exclusive with O(evacuate_target).
    type: list
    elements: str
  restore_delete_resources:
    description:
      - Delete resources on the node before restoring it.
      - Only used when C(state=restored).
    type: bool
    default: false
  restore_delete_snapshots:
    description:
      - Delete snapshots on the node before restoring it.
      - Only used when C(state=restored).
    type: bool
    default: false
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
  - This module issues API calls via C(python-linstor) to the LINSTOR controller.
  - Requires the L(linstor-api-py,https://github.com/LINBIT/linstor-api-py) package
    (C(python-linstor)) on the play host.
  - "Recommended play structure: dedicate a play with a single host such
    as C(hosts: linstor_controllers[0]) and C(connection: local) for
    directly accessing the LINSTOR controller, or set C(delegate_to: localhost)
    on the task (or a wrapping C(block:)) when mixing into a multi-host play."
  - "The collection's action plugins force C(become: false) on the task
    automatically, so a parent play's C(become: true) does not bleed into
    the delegated call."
  - Two usage patterns are supported.
  - Centralized, use C(run_once=true) with a loop over inventory hosts to send
    all API calls from a single host.
  - Per-host, let each play host call the module with its own host variables
    such as C(inventory_hostname) and C(replication_ip).
  - "Auto-evict per-node overrides: C(DrbdOptions/AutoEvictAfterTime) and
    C(DrbdOptions/AutoEvictAllowEviction) can be set on individual nodes
    to override controller-level defaults set via M(linbit.linstor.controller)."
  - "DRBD Proxy site assignment: set the C(Site) property on nodes to enable
    automatic DRBD Proxy insertion between sites. Requires C(DrbdProxy/AutoEnable)
    on the controller."
  - "External DRBD metadata: set C(StorPoolNameDrbdMeta) to select a storage pool
    for external DRBD metadata on new resources created on this node."
seealso:
  - name: LINSTOR User's Guide - Initialize Cluster
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-init-cluster
    description: Node creation and cluster initialization in the LINSTOR User's Guide.
  - name: LINSTOR User's Guide - Node Evacuate
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-node-evacuate
    description: Node evacuation for maintenance in the LINSTOR User's Guide.
  - name: LINSTOR User's Guide - DRBD Proxy
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-drbd-proxy
    description: DRBD Proxy integration with LINSTOR in the User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Create a combined node
  linbit.linstor.node:
    name: "{{ inventory_hostname }}"
    ip: "{{ replication_ip }}"  # Defined in inventory
    node_type: Combined
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Create a satellite node
  linbit.linstor.node:
    name: node-3
    ip: 10.0.0.3
    node_type: Satellite
  run_once: true  # noqa: run-once[task]

- name: Create all cluster nodes from one host
  vars:
    is_controller: "{{ 'linstor_controllers' in hostvars[item].group_names }}"
    is_satellite: "{{ 'linstor_satellites' in hostvars[item].group_names }}"
    node_type: >-
      {% if is_controller | bool and is_satellite | bool %}Combined
      {% elif is_controller | bool %}Controller
      {% else %}Satellite{% endif %}
  linbit.linstor.node:
    name: "{{ item }}"
    ip: "{{ hostvars[item].replication_ip }}"
    node_type: "{{ node_type | trim }}"
  loop: "{{ groups['linstor_cluster'] }}"
  run_once: true  # noqa: run-once[task]

- name: Create satellite nodes with management IP via DNS lookup
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

- name: Convert an existing node to SSL
  linbit.linstor.node:
    name: node-1
    com_type: SSL
    port: 3367
  run_once: true  # noqa: run-once[task]

- name: Set auxiliary properties on a node
  linbit.linstor.node:
    name: node-1
    ip: 10.0.0.1
    aux_properties:
      datacenter: us-east-1
      rack: rack-3
  run_once: true  # noqa: run-once[task]

- name: Disable auto-eviction on a specific node
  linbit.linstor.node:
    name: node-1
    properties:
      DrbdOptions/AutoEvictAllowEviction: "false"
  run_once: true  # noqa: run-once[task]

# Requires DrbdProxy/AutoEnable set on the controller
- name: Set site property for DRBD Proxy auto-enable
  linbit.linstor.node:
    name: node-1
    properties:
      Site: site-a
  run_once: true  # noqa: run-once[task]

- name: Set external DRBD metadata storage pool
  linbit.linstor.node:
    name: node-1
    properties:
      StorPoolNameDrbdMeta: sp-meta-ssd
  run_once: true  # noqa: run-once[task]

- name: Evacuate a node for maintenance
  linbit.linstor.node:
    name: node-3
    state: evacuated
  run_once: true  # noqa: run-once[task]

- name: Evacuate with preferred target nodes
  linbit.linstor.node:
    name: node-3
    state: evacuated
    evacuate_target:
      - node-1
      - node-2
  run_once: true  # noqa: run-once[task]

- name: Restore a node after maintenance
  linbit.linstor.node:
    name: node-3
    state: restored
  run_once: true  # noqa: run-once[task]

- name: Restore and clean up stale resources
  linbit.linstor.node:
    name: node-3
    state: restored
    restore_delete_resources: true
    restore_delete_snapshots: true
  run_once: true  # noqa: run-once[task]

- name: Remove a node from the cluster
  linbit.linstor.node:
    name: node-3
    state: absent
  run_once: true  # noqa: run-once[task]

# Delegate to a cluster controller when the control node cannot reach
# the LINSTOR API directly (SSH jump host, segmented management network)
- name: Register a satellite via a delegated controller
  linbit.linstor.node:
    name: node-1
    ip: 192.168.222.10
    node_type: Satellite
  delegate_to: controller-0
  environment:
    LS_CONTROLLERS: linstor://localhost
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


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        state=dict(type='str', default='present',
                   choices=['present', 'absent', 'evacuated', 'restored']),
        node_type=dict(type='str', default=None,
                       choices=['Controller', 'Satellite', 'Combined', 'Auxiliary']),
        ip=dict(type='str'),
        com_type=dict(type='str', default=None, choices=['Plain', 'SSL']),
        port=dict(type='int', default=None),
        netif_name=dict(type='str', default='default'),
        properties=dict(type='dict', default={}),
        aux_properties=dict(type='dict', default={}),
        delete_properties=dict(type='list', elements='str', default=[]),
        evacuate_target=dict(type='list', elements='str'),
        evacuate_do_not_target=dict(type='list', elements='str'),
        restore_delete_resources=dict(type='bool', default=False),
        restore_delete_snapshots=dict(type='bool', default=False),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ('evacuate_target', 'evacuate_do_not_target'),
        ],
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

        if state == 'evacuated':
            if existing_node is None:
                module.fail_json(
                    msg="Node '%s' does not exist, cannot evacuate" % name)
            node_flags = getattr(existing_node, 'flags', [])
            if 'EVACUATE' in node_flags:
                module.exit_json(changed=False, name=name,
                                 node_type=get_node_type_str(existing_node),
                                 ip=get_node_ip(existing_node, netif_name),
                                 properties=get_node_props(existing_node))
            if module.check_mode:
                module.exit_json(changed=True, name=name,
                                 node_type=get_node_type_str(existing_node),
                                 ip=get_node_ip(existing_node, netif_name),
                                 properties=get_node_props(existing_node))
            kwargs = dict(node_name=name)
            evacuate_target = module.params.get('evacuate_target')
            evacuate_do_not_target = module.params.get('evacuate_do_not_target')
            if evacuate_target:
                kwargs['target'] = evacuate_target
            if evacuate_do_not_target:
                kwargs['do_not_target'] = evacuate_do_not_target
            replies = lin.node_evacuate(**kwargs)
            check_api_response(module, replies, 'evacuate node %s' % name)
            module.exit_json(changed=True, name=name,
                             node_type=get_node_type_str(existing_node),
                             ip=get_node_ip(existing_node, netif_name),
                             properties=get_node_props(existing_node))

        if state == 'restored':
            if existing_node is None:
                module.fail_json(
                    msg="Node '%s' does not exist, cannot restore" % name)
            node_flags = getattr(existing_node, 'flags', [])
            if 'EVACUATE' not in node_flags:
                module.exit_json(changed=False, name=name,
                                 node_type=get_node_type_str(existing_node),
                                 ip=get_node_ip(existing_node, netif_name),
                                 properties=get_node_props(existing_node))
            if module.check_mode:
                module.exit_json(changed=True, name=name,
                                 node_type=get_node_type_str(existing_node),
                                 ip=get_node_ip(existing_node, netif_name),
                                 properties=get_node_props(existing_node))
            kwargs = dict(node_name=name)
            if module.params['restore_delete_resources']:
                kwargs['delete_resources'] = True
            if module.params['restore_delete_snapshots']:
                kwargs['delete_snapshots'] = True
            replies = lin.node_restore(**kwargs)
            check_api_response(module, replies, 'restore node %s' % name)
            module.exit_json(changed=True, name=name,
                             node_type=get_node_type_str(existing_node),
                             ip=get_node_ip(existing_node, netif_name),
                             properties=get_node_props(existing_node))

        # state == 'present'
        create_type = node_type or 'Satellite'
        if existing_node is None:
            if not ip:
                module.fail_json(msg="'ip' is required when creating a new node")
            create_com_type = com_type or 'Plain'
            if module.check_mode:
                module.exit_json(
                    changed=True, name=name, node_type=create_type,
                    ip=ip, properties=all_properties)

            node_type_const = NODE_TYPE_MAP.get(create_type, 'SATELLITE')
            # Work around python-linstor bug: Combined+SSL gets controller port (3371)
            # instead of satellite port (3367). Override when port is not specified.
            create_port = port
            if create_port is None and create_com_type == 'SSL':
                is_controller = create_type.upper() == 'CONTROLLER'
                create_port = 3371 if is_controller else 3367
            replies = lin.node_create(
                node_name=name,
                node_type=node_type_const,
                ip=ip,
                com_type=create_com_type,
                port=create_port,
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
                changed=True, name=name, node_type=create_type,
                ip=ip, properties=all_properties)

        # Node exists: check for immutable attribute differences
        existing_type = get_node_type_str(existing_node)
        existing_ip = get_node_ip(existing_node, netif_name)

        if existing_type and node_type and node_type.upper() != existing_type.upper():
            module.warn(
                "Node '%s' exists with type '%s' but '%s' was requested. "
                "Node type cannot be changed after creation." % (
                    name, existing_type, node_type))

        if existing_ip and ip and existing_ip != ip:
            module.warn(
                "Node '%s' exists with IP '%s' but '%s' was requested. "
                "IP address cannot be changed after creation." % (
                    name, existing_ip, ip))

        # Check and update network interface com_type and port
        if com_type is not None:
            existing_netif = get_node_netif(existing_node, netif_name)
            existing_com_type = (existing_netif.stlt_encryption_type
                                 if existing_netif else None) or 'Plain'
            existing_stlt_port = (existing_netif.stlt_port
                                  if existing_netif else None) or 3366
            modify_port = port
            if modify_port is None:
                existing_type = get_node_type_str(existing_node).upper()
                is_controller = existing_type == 'CONTROLLER'
                if com_type == 'SSL':
                    # SSL: pure Controller=3371, Satellite/Combined=3367
                    modify_port = 3371 if is_controller else 3367
                else:
                    # Plain: pure Controller=3370, Satellite/Combined=3366
                    modify_port = 3370 if is_controller else 3366
            if com_type.upper() != existing_com_type.upper() or modify_port != existing_stlt_port:
                if not module.check_mode:
                    replies = lin.netinterface_modify(
                        node_name=name,
                        interface_name=netif_name,
                        port=modify_port,
                        com_type=com_type,
                    )
                    check_api_response(
                        module, replies,
                        'modify network interface on node %s' % name)
                changed = True

        # Compare and update properties
        current_props = get_node_props(existing_node)
        props_to_set, props_to_delete = compute_property_diff(
            current_props, all_properties, delete_properties)

        if not props_to_set and not props_to_delete:
            module.exit_json(
                changed=changed, name=name,
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
