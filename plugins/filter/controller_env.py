# SPDX-License-Identifier: MIT
"""Filter plugin: build LS_CONTROLLERS URI string from inventory."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
  name: controller_env
  short_description: Build an LS_CONTROLLERS URI string from inventory
  version_added: "0.9.7"
  description:
    - Returns a comma-joined URI string suitable for the C(LS_CONTROLLERS)
      environment variable or the C(controllers) key in C(linstor-client.conf).
    - When C(ha_vip) is set, the VIP address is used as the sole controller
      (CIDR prefix is stripped). Otherwise all hosts in
      C(linstor_controllers) are resolved via the C(linstor_addr) precedence
      rule (C(linstor_ip) → C(replication_ip) → C(ansible_host)).
    - Use C(ssl=true) when C(cluster_init_ssl) is enabled; the scheme switches
      from C(linstor://) to C(linstors://) automatically.
    - Intended for injecting C(LS_CONTROLLERS) via the task C(environment:)
      key on tasks delegated to localhost during C(cluster_init), so the
      correct controller is targeted at every point in the play, including
      after C(ssl_init) switches the cluster to HTTPS.
  options:
    _input:
      description: The Ansible C(groups) magic variable.
      type: dict
      required: true
    hostvars:
      description: The Ansible C(hostvars) magic variable.
      type: dict
      required: true
    ha_vip:
      description:
        - Optional HA VIP in CIDR notation (for example C(192.168.222.200/24)).
        - When set, the VIP address is used instead of individual controller
          addresses.
      type: str
      default: ''
    ssl:
      description: Use C(linstors://) scheme when true.
      type: bool
      default: false
  author:
    - Ryan Ronnander (@rronnander)
'''

EXAMPLES = '''
- name: Set LS_CONTROLLERS from inventory for a plain cluster
  ansible.builtin.debug:
    msg: "{{ groups | linbit.linstor.controller_env(hostvars) }}"

- name: Set LS_CONTROLLERS for an SSL cluster with a VIP
  ansible.builtin.debug:
    msg: "{{ groups | linbit.linstor.controller_env(hostvars, ha_vip=linstor_ha_vip, ssl=true) }}"

- name: Use in environment on a delegated task
  linbit.linstor.node:
    name: "{{ inventory_hostname }}"
    state: query
  delegate_to: localhost
  become: false
  environment:
    LS_CONTROLLERS: "{{ groups | linbit.linstor.controller_env(hostvars, linstor_ha_vip | default(''), cluster_init_ssl | default(false)) }}"
'''

RETURN = '''
  _value:
    description: Comma-joined URI string, for example C(linstor://192.168.222.10,linstor://192.168.222.11).
    type: str
'''


def _linstor_addr(host_vars):
    return (
        host_vars.get('linstor_ip')
        or host_vars.get('replication_ip')
        or host_vars.get('ansible_host')
        or 'localhost'
    )


def controller_env(groups, hostvars, ha_vip='', ssl=False):
    scheme = 'linstors' if ssl else 'linstor'

    if ha_vip:
        address = ha_vip.split('/')[0]
        return '{0}://{1}'.format(scheme, address)

    controllers = groups.get('linstor_controllers', [])
    uris = ['{0}://{1}'.format(scheme, _linstor_addr(hostvars[h])) for h in controllers]
    return ','.join(uris)


class FilterModule:
    def filters(self):
        return {'controller_env': controller_env}
