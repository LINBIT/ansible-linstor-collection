#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: node_interface
short_description: Manage LINSTOR node network interfaces
version_added: "0.10.0"
description:
  - Creates, modifies, or deletes network interfaces on LINSTOR nodes.
  - Idempotent. If the interface already exists, only changed attributes are updated.
  - Use C(state=query) to retrieve interface information without modification.
options:
  node:
    description: Name of the LINSTOR node.
    type: str
    required: true
  name:
    description: Name of the network interface.
    type: str
    required: true
  ip:
    description:
      - IP address for the network interface.
      - Required when creating a new interface.
    type: str
  port:
    description: Satellite port for the network interface.
    type: int
  com_type:
    description: Communication type for the network interface.
    type: str
    choices: [Plain, SSL]
  satellite_connection:
    description:
      - Set to C(true) to designate this interface as the node's satellite connection.
        The controller uses this address to communicate with the satellite.
      - Each node has exactly one satellite connection. Designating a new one
        replaces whichever interface previously held the role.
      - Setting C(false) is a no-op against the LINSTOR controller; the controller
        does not unset the satellite connection without a replacement.
        Designate a different interface instead.
      - Omit to leave the current designation unchanged.
    type: bool
  state:
    description: Desired state of the network interface.
    type: str
    default: present
    choices: [present, absent, query]
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
  - This module manages network interfaces on existing LINSTOR nodes.
  - The C(default) interface is created automatically when a node is registered
    and serves as the satellite connection unless another interface is designated.
seealso:
  - module: linbit.linstor.node
    description: Manage LINSTOR cluster nodes.
  - name: LINSTOR User's Guide - Managing Network Interface Cards
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-managing_network_interface_cards
    description: LINSTOR net interface, PrefNic, and satellite connection concepts in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Create a replication network interface
  linbit.linstor.node_interface:
    node: node-1
    name: replication
    ip: 192.168.100.11
  run_once: true  # noqa: run-once[task]

- name: Create an SSL network interface
  linbit.linstor.node_interface:
    node: node-1
    name: replication
    ip: 192.168.100.11
    com_type: SSL
    port: 3367
  run_once: true  # noqa: run-once[task]

- name: Designate management as the satellite connection
  linbit.linstor.node_interface:
    node: node-1
    name: management
    satellite_connection: true
  run_once: true  # noqa: run-once[task]

- name: Query a network interface
  linbit.linstor.node_interface:
    node: node-1
    name: replication
    state: query
  register: netif_result
  run_once: true  # noqa: run-once[task]

- name: Remove a network interface
  linbit.linstor.node_interface:
    node: node-1
    name: replication
    state: absent
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
node:
  description: Name of the LINSTOR node.
  type: str
  returned: always
name:
  description: Name of the network interface.
  type: str
  returned: always
exists:
  description: Whether the interface exists. Only returned with C(state=query).
  type: bool
  returned: query
ip:
  description: IP address of the network interface.
  type: str
  returned: success
port:
  description: Satellite port of the network interface.
  type: int
  returned: success
com_type:
  description: Communication type (C(Plain) or C(SSL)).
  type: str
  returned: success
satellite_connection:
  description: Whether this interface is the node's satellite connection.
  type: bool
  returned: success
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
    check_api_response,
)


def _netif_data(netif):
    return getattr(netif, 'data_v1', None) or {}


def get_netif(lin, node_name, interface_name):
    for netif in lin.net_interface_list(node_name):
        data = _netif_data(netif)
        if data.get('name') == interface_name:
            return data
    return None


def netif_to_dict(data):
    return {
        'ip': data.get('address'),
        'port': data.get('satellite_port'),
        'com_type': data.get('satellite_encryption_type'),
        'satellite_connection': data.get('is_active'),
    }


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        node=dict(type='str', required=True),
        name=dict(type='str', required=True),
        ip=dict(type='str'),
        port=dict(type='int'),
        com_type=dict(type='str', choices=['Plain', 'SSL']),
        satellite_connection=dict(type='bool'),
        state=dict(type='str', default='present',
                   choices=['present', 'absent', 'query']),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    node = module.params['node']
    name = module.params['name']
    ip = module.params['ip']
    port = module.params['port']
    com_type = module.params['com_type']
    satellite_connection = module.params['satellite_connection']
    state = module.params['state']

    lin = get_linstor_connection(module)

    try:
        existing = get_netif(lin, node, name)

        if state == 'query':
            if existing is None:
                module.exit_json(changed=False, node=node, name=name,
                                 exists=False)
            info = netif_to_dict(existing)
            module.exit_json(changed=False, node=node, name=name,
                             exists=True, **info)

        if state == 'absent':
            if existing is None:
                module.exit_json(changed=False, node=node, name=name)
            if module.check_mode:
                module.exit_json(changed=True, node=node, name=name)
            replies = lin.netinterface_delete(node, name)
            check_api_response(module, replies,
                               'delete interface %s on node %s' % (name, node))
            module.exit_json(changed=True, node=node, name=name)

        # state == 'present'
        if existing is None:
            if not ip:
                module.fail_json(
                    msg="'ip' is required when creating a new interface")
            if module.check_mode:
                module.exit_json(changed=True, node=node, name=name, ip=ip)
            replies = lin.netinterface_create(
                node_name=node,
                interface_name=name,
                ip=ip,
                port=port,
                com_type=com_type,
                is_active=bool(satellite_connection),
            )
            check_api_response(module, replies,
                               'create interface %s on node %s' % (name, node))
            module.exit_json(changed=True, node=node, name=name, ip=ip,
                             port=port, com_type=com_type,
                             satellite_connection=satellite_connection)

        # Interface exists: check for changes
        info = netif_to_dict(existing)
        needs_modify = False

        if ip and ip != info.get('ip'):
            needs_modify = True
        if port is not None and port != info.get('port'):
            needs_modify = True
        if com_type and (com_type.upper() != (info.get('com_type') or 'Plain').upper()):
            needs_modify = True
        if satellite_connection is not None and \
                satellite_connection != bool(info.get('satellite_connection')):
            needs_modify = True

        if not needs_modify:
            module.exit_json(changed=False, node=node, name=name, **info)

        if module.check_mode:
            module.exit_json(changed=True, node=node, name=name, **info)

        replies = lin.netinterface_modify(
            node_name=node,
            interface_name=name,
            ip=ip,
            port=port,
            com_type=com_type,
            is_active=satellite_connection,
        )
        check_api_response(module, replies,
                           'modify interface %s on node %s' % (name, node))

        updated = get_netif(lin, node, name)
        updated_info = netif_to_dict(updated) if updated else info
        module.exit_json(changed=True, node=node, name=name, **updated_info)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error managing interface '%s' on node '%s': %s"
                % (name, node, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
