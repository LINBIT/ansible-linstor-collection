# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# Non-module plugins run in the Ansible controller process and must be
# GPL-3.0-or-later per the Ansible community package inclusion rules.
# The rest of the linbit.* collections remain MIT-licensed.
"""Lookup plugin: build LS_CONTROLLERS URI string from inventory context."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
  name: controller_env
  short_description: Build an LS_CONTROLLERS URI string from inventory context
  version_added: "0.9.7"
  description:
    - Returns a comma-joined URI string suitable for the C(LS_CONTROLLERS)
      environment variable on tasks delegated to localhost during
      C(cluster_init).
    - Reads C(linstor_ssl), C(groups), and C(hostvars) directly from the
      current variable context - no parameters required.
    - All hosts in C(linstor_controllers) are resolved via the C(linstor_addr)
      precedence rule (C(linstor_ip) → C(replication_ip) → C(ansible_host))
      and joined with commas. The client walks the list and connects to the
      first responder.
    - When C(linstor_ssl) is true, the scheme switches from C(linstor://)
      to C(linstor+ssl://).
    - If C(linstor_controllers_env) is set in inventory or playbook vars it is
      returned as-is, allowing full override without touching role internals.
  options:
    _terms:
      description: No terms required. Any supplied terms are ignored.
  author:
    - Ryan Ronnander (@rronnander)
'''

EXAMPLES = '''
- name: Use in environment on a delegated task
  linbit.linstor.node_info:
    name: "{{ inventory_hostname }}"
  delegate_to: localhost
  become: false
  environment:
    LS_CONTROLLERS: "{{ lookup('linbit.linstor.controller_env') }}"

- name: Debug resolved controller string
  ansible.builtin.debug:
    msg: "{{ lookup('linbit.linstor.controller_env') }}"
'''

RETURN = '''
  _raw:
    description: Comma-joined URI string, for example C(linstor://192.168.222.10,linstor://192.168.222.11).
    type: str
'''

from ansible.module_utils.parsing.convert_bool import boolean
from ansible.plugins.lookup import LookupBase
from ansible_collections.linbit.linstor.plugins.filter.linstor_addr import linstor_addr


class LookupModule(LookupBase):
    def _tmpl(self, value, variables):
        """Evaluate a variable value that may itself be a Jinja2 template."""
        if self._templar and isinstance(value, str) and '{{' in value:
            try:
                self._templar.available_variables = variables
                return self._templar.template(value)
            except Exception:
                return ''
        return value

    def run(self, terms, variables=None, **kwargs):
        variables = variables or {}

        override = self._tmpl(variables.get('linstor_controllers_env', ''), variables)
        if override:
            return [override]

        # boolean() so a string like "false" from -e linstor_ssl=false is read
        # as False, not as a truthy non-empty string
        ssl = boolean(self._tmpl(variables.get('linstor_ssl', False), variables), strict=False)
        scheme = 'linstor+ssl' if ssl else 'linstor'

        groups = variables.get('groups', {})
        hostvars = variables.get('hostvars', {})
        controllers = groups.get('linstor_controllers', [])
        uris = ['{0}://{1}'.format(scheme, linstor_addr(hostvars.get(h, {}))) for h in controllers]
        return [','.join(uris) if uris else '{0}://localhost'.format(scheme)]
