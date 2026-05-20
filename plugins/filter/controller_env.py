# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# Non-module plugins run in the Ansible controller process and must be
# GPL-3.0-or-later per the Ansible community package inclusion rules.
# The rest of the linbit.* collections remain MIT-licensed.
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
    - All hosts in C(linstor_controllers) are resolved via the C(linstor_addr)
      precedence rule (C(linstor_ip) → C(replication_ip) → C(ansible_host))
      and joined with commas. The client walks the list and connects to the
      first responder.
    - Pass C(ssl=true) when targeting an SSL cluster; the scheme switches
      from C(linstor://) to C(linstors://). The filter takes C(ssl) as an
      explicit argument, unlike the matching lookup which reads
      C(linstor_ssl) from the variable context.
  options:
    _input:
      description: The Ansible C(groups) magic variable.
      type: dict
      required: true
    hostvars:
      description: The Ansible C(hostvars) magic variable.
      type: dict
      required: true
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

- name: Set LS_CONTROLLERS for an SSL cluster
  ansible.builtin.debug:
    msg: "{{ groups | linbit.linstor.controller_env(hostvars, ssl=true) }}"

- name: Use in environment on a delegated task
  linbit.linstor.node:
    name: "{{ inventory_hostname }}"
    state: query
  delegate_to: localhost
  become: false
  environment:
    LS_CONTROLLERS: "{{ groups | linbit.linstor.controller_env(hostvars, linstor_ssl | default(false)) }}"
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


def controller_env(groups, hostvars, ssl=False):
    scheme = 'linstors' if ssl else 'linstor'
    controllers = groups.get('linstor_controllers', [])
    uris = ['{0}://{1}'.format(scheme, _linstor_addr(hostvars[h])) for h in controllers]
    return ','.join(uris)


class FilterModule:
    def filters(self):
        return {'controller_env': controller_env}
