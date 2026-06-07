# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# Non-module plugins run in the Ansible controller process and must be
# GPL-3.0-or-later per the Ansible community package inclusion rules.
# The rest of the linbit.* collections remain MIT-licensed.
"""Filter plugin: build manual placement list for ha_gateway resources."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
  name: gateway_placement
  short_description: Build the manual placement list for an ha_gateway resource
  version_added: "0.9.0"
  description:
    - Transforms an ha_gateway target dict into the C(nodes) list shape consumed
      by the M(linbit.linstor.resource) module in C(mode=manual).
    - Computes per-node C(diskless) and C(storage_pool) entries from the
      target's place count and storage pool defaults.
    - Internal helper for the C(linbit.linstor.ha_gateway) role.
  options:
    _input:
      description: List of ha_gateway target dicts with explicit C(nodes).
      type: list
      elements: dict
      required: true
    place_count_default:
      description: Fallback place count when the target does not provide one.
      type: int
      required: true
    storage_pool_default:
      description: Fallback storage pool name for diskful nodes.
      type: str
      required: true
    sizes_key:
      description: Target dict key that holds the volume size list (for example C(volumes) or C(exports)).
      type: str
      required: true
    tickle_dir_size:
      description: Size of the prepended tickle directory volume.
      type: str
      required: true
  author:
    - Ryan Ronnander (@rronnander)
'''

EXAMPLES = '''
- name: Compute manual placements for iSCSI targets
  ansible.builtin.set_fact:
    placements: >-
      {{
        explicit_targets
        | linbit.linstor.gateway_placement(2, 'sp0', 'volumes', '1M')
      }}
'''

RETURN = '''
  _value:
    description: List of placement dicts with keys C(resource_name), C(nodes), C(sizes), and C(layer_list).
    type: list
    elements: dict
'''


def gateway_placement(explicit, place_count_default, storage_pool_default,
                      sizes_key, tickle_dir_size):
    result = []
    for t in explicit:
        pc = int(t.get('place_count') or place_count_default)
        vol_sizes = [tickle_dir_size] + [v['size'] for v in t[sizes_key]]
        sp = t.get('storage_pool') or storage_pool_default or ''

        node_entries = []
        for i, n in enumerate(t['nodes']):
            is_diskless = i >= pc
            node_entries.append({
                'node': n,
                'diskless': is_diskless,
                'storage_pool': sp if not is_diskless else '',
            })

        result.append({
            'resource_name': t['_rd_name'],
            'nodes': node_entries,
            'sizes': vol_sizes,
            'layer_list': t.get('layer_list'),
        })
    return result


class FilterModule:
    def filters(self):
        return {'gateway_placement': gateway_placement}
