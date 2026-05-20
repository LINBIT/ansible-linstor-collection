# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# Non-module plugins run in the Ansible controller process and must be
# GPL-3.0-or-later per the Ansible community package inclusion rules.
# The rest of the linbit.* collections remain MIT-licensed.
"""Filter plugin: resolve a host's LINSTOR-facing address."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
  name: linstor_addr
  short_description: Resolve a host's LINSTOR-facing address from its hostvars
  version_added: "0.9.7"
  description:
    - Returns the first defined value among C(linstor_ip), C(replication_ip),
      C(ansible_host), falling back to C(localhost) when none are set.
    - Centralizes the address-precedence rule used across C(client_install),
      C(gateway_install), and C(cluster_membership).
  options:
    _input:
      description: A single host's hostvars dictionary (for example, C(hostvars[inventory_hostname])).
      type: dict
      required: true
  author:
    - Ryan Ronnander (@rronnander)
'''

EXAMPLES = '''
- name: Build LINSTOR controller address list
  ansible.builtin.debug:
    msg: "{{ groups['linstor_controllers'] | map('extract', hostvars) | map('linbit.linstor.linstor_addr') | list }}"

- name: Resolve this host's LINSTOR address
  ansible.builtin.debug:
    msg: "{{ hostvars[inventory_hostname] | linbit.linstor.linstor_addr }}"
'''

RETURN = '''
  _value:
    description: Resolved address string.
    type: str
'''


def linstor_addr(host_vars):
    return (
        host_vars.get('linstor_ip')
        or host_vars.get('replication_ip')
        or host_vars.get('ansible_host')
        or 'localhost'
    )


class FilterModule:
    def filters(self):
        return {'linstor_addr': linstor_addr}
