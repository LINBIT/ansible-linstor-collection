# SPDX-License-Identifier: MIT
"""Lookup plugin: resolve LINSTOR-facing addresses for every host in a group."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
  name: group_addresses
  short_description: Resolve LINSTOR-facing addresses for every host in an Ansible group
  version_added: "0.9.7"
  description:
    - Walks the named Ansible inventory group and returns a list of resolved
      addresses using the same precedence as the C(linstor_addr) filter -
      C(linstor_ip), then C(replication_ip), then C(ansible_host), then C(localhost).
    - When the group is missing or empty, returns C(['localhost']) so the
      caller renders a usable single-node-localhost default.
    - Convenience wrapper for the common "render every controller / satellite
      address as a list" case.
  options:
    _terms:
      description: Inventory group name (for example, C(linstor_controllers)).
      type: list
      elements: str
      required: true
  author:
    - Ryan Ronnander (@rronnander)
'''

EXAMPLES = '''
# Use query() (or lookup with wantlist=True) so single-element results stay as
# a list - bare lookup() unwraps a one-item list down to its string element.
- name: Build LINSTOR controller address list
  ansible.builtin.debug:
    msg: "{{ query('linbit.linstor.group_addresses', 'linstor_controllers') }}"

- name: Iterate satellite addresses
  ansible.builtin.debug:
    msg: "Satellite at {{ item }}"
  loop: "{{ query('linbit.linstor.group_addresses', 'linstor_satellites') }}"
'''

RETURN = '''
  _list:
    description: One resolved address per host in the named group, in inventory order.
    type: list
    elements: str
'''

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from ansible_collections.linbit.linstor.plugins.filter.linstor_addr import linstor_addr


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        if not terms:
            raise AnsibleError("group_addresses requires a group name as the first argument")
        group_name = terms[0]
        variables = variables or {}
        groups = variables.get('groups', {})
        hostvars = variables.get('hostvars', {})
        hosts = groups.get(group_name, [])
        if not hosts:
            return ['localhost']
        return [linstor_addr(hostvars.get(host, {})) for host in hosts]
