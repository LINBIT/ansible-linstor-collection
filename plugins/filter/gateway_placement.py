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
      target's resource group, place count, and storage pool defaults.
    - Internal helper for the C(linbit.linstor.ha_gateway) role.
  options:
    _input:
      description: List of ha_gateway target dicts with explicit C(nodes).
      type: list
      elements: dict
      required: true
    rg_check_results:
      description: Resource-group lookup results used to source per-target place counts.
      type: list
      elements: dict
      required: true
    place_count_default:
      description: Fallback place count when neither the target nor its resource group provides one.
      type: int
      required: true
    storage_pool_default:
      description: Fallback storage pool name for diskful nodes when the target has no resource group.
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
        | linbit.linstor.gateway_placement(
            rg_results, 2, 'sp0', 'volumes', '1M'
          )
      }}
'''

RETURN = '''
  _value:
    description: List of placement dicts with keys C(resource_name), C(nodes), and C(sizes).
    type: list
    elements: dict
'''


def gateway_placement(explicit, rg_check_results, place_count_default,
                      storage_pool_default, sizes_key, tickle_dir_size):
    rg_pc = {
        r['_target']['name']: int(r.get('place_count') or 2)
        for r in (rg_check_results or [])
    }

    result = []
    for t in explicit:
        has_rg = 'resource_group' in t
        pc_default = int(t.get('place_count') or place_count_default)
        pc = rg_pc.get(t['name'], pc_default) if has_rg else pc_default

        vol_sizes = [tickle_dir_size] + [v['size'] for v in t[sizes_key]]
        sp = t.get('storage_pool') or storage_pool_default or ''

        node_entries = []
        for i, n in enumerate(t['nodes']):
            is_diskless = i >= pc
            node_entries.append({
                'node': n,
                'diskless': is_diskless,
                'storage_pool': sp if (not has_rg and not is_diskless) else '',
            })

        result.append({
            'resource_name': t['_rd_name'],
            'nodes': node_entries,
            'sizes': vol_sizes if not has_rg else [],
        })
    return result


class FilterModule:
    def filters(self):
        return {'gateway_placement': gateway_placement}
