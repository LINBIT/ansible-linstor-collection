# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# Non-module plugins run in the Ansible controller process and must be
# GPL-3.0-or-later per the Ansible community package inclusion rules.
# The rest of the linbit.* collections remain MIT-licensed.
"""Filter plugin: select the storage pools from linstor_storage_pools that target a host."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
  name: host_storage_pools
  short_description: Select the linstor_storage_pools entries that target a given host
  version_added: "0.9.7"
  description:
    - Returns the entries of C(linstor_storage_pools) that apply to a given host, which is
      the per-host pool list the C(storage_pool) role creates (its C(_my_pools)).
    - A pool with neither C(nodes) nor C(groups) targets all C(linstor_satellites).
    - A pool with C(nodes) and/or C(groups) targets those hosts plus the members of those
      inventory groups (union).
    - This is the single home for the storage-pool placement logic. A node that no pool
      targets creates nothing and is therefore diskless; placement, not a separate group,
      is the source of truth.
  options:
    _input:
      description: The C(linstor_storage_pools) list of pool definitions.
      type: list
      elements: dict
      required: true
    hostname:
      description: The host to select pools for, usually C(inventory_hostname).
      type: str
      required: true
    groups:
      description: The Ansible C(groups) dictionary, used to resolve generic and group targeting.
      type: dict
      required: true
  author:
    - Ryan Ronnander (@rronnander)
'''

EXAMPLES = '''
- name: Pools this host should create
  ansible.builtin.set_fact:
    _my_pools: >-
      {{ linstor_storage_pools | default([])
         | linbit.linstor.host_storage_pools(inventory_hostname, groups) }}
'''

RETURN = '''
  _value:
    description: The subset of C(linstor_storage_pools) that target the given host.
    type: list
    elements: dict
'''


def host_storage_pools(storage_pools, hostname, groups):
    groups = groups or {}
    result = []
    for pool in (storage_pools or []):
        if 'nodes' not in pool and 'groups' not in pool:
            # Generic pool: every satellite (scope to a subset with the pool's own nodes/groups).
            targets = groups.get('linstor_satellites', [])
        else:
            targets = list(pool.get('nodes') or [])
            for grp in (pool.get('groups') or []):
                targets += groups.get(grp, []) or []
        if hostname in targets:
            result.append(pool)
    return result


class FilterModule:
    def filters(self):
        return {'host_storage_pools': host_storage_pools}
