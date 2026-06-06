# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# Non-module plugins run in the Ansible controller process and must be
# GPL-3.0-or-later per the Ansible community package inclusion rules.
# The rest of the linbit.* collections remain MIT-licensed.
"""Filter plugin: split LINSTOR-reported nodes into diskful and diskless."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
  name: gateway_resolve_satellites
  short_description: Resolve diskful and diskless satellites for ha_gateway autoplaced resources
  version_added: "0.9.0"
  description:
    - Splits per-target LINSTOR query results into diskful and diskless node
      lists based on each node's C(DRBD_DISKLESS) or C(TIE_BREAKER) flag.
    - Returns the original target unchanged when it already has explicit C(nodes).
    - Internal helper for the C(linbit.linstor.ha_gateway) role.
  options:
    _input:
      description: List of dicts, each with a C(_target) entry and LINSTOR resource flags.
      type: list
      elements: dict
      required: true
  author:
    - Ryan Ronnander (@rronnander)
'''

EXAMPLES = '''
- name: Resolve diskful and diskless satellites for autoplaced targets
  ansible.builtin.set_fact:
    targets_with_nodes: >-
      {{ resource_query_results | linbit.linstor.gateway_resolve_satellites }}
'''

RETURN = '''
  _value:
    description: List of target dicts, each with C(nodes) populated as diskful followed by diskless.
    type: list
    elements: dict
'''


def gateway_resolve_satellites(query_results):
    resolved = []
    for result in (query_results or []):
        t = result['_target']
        if t.get('nodes'):
            resolved.append(t)
            continue

        diskful = []
        diskless = []
        resources = result.get('resources') or []
        info = resources[0] if resources else {}
        flags = info.get('flags', {})
        for ln in info.get('nodes', []):
            node_flags = flags.get(ln, [])
            if 'DRBD_DISKLESS' in node_flags or 'TIE_BREAKER' in node_flags:
                diskless.append(ln)
            else:
                diskful.append(ln)

        resolved.append({**t, 'nodes': diskful + diskless})
    return resolved


class FilterModule:
    def filters(self):
        return {'gateway_resolve_satellites': gateway_resolve_satellites}
