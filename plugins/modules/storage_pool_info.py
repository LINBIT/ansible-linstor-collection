#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: storage_pool_info
short_description: Query LINSTOR storage pools
version_added: "1.0.0"
description:
  - Returns information about LINSTOR storage pools.
  - Read-only; C(changed) is always C(false).
  - Omit O(name) and O(node) to return all storage pools, or set either to
    narrow the results.
options:
  name:
    description:
      - Storage pool name to filter by.
      - If omitted, pools with any name are returned.
    type: str
  node:
    description:
      - Node name to filter by.
      - If omitted, pools on any node are returned.
    type: str
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
  - "Recommended play structure: dedicate a play with a single host such
    as C(hosts: linstor_controllers[0]) and C(connection: local) for
    directly accessing the LINSTOR controller, or set C(delegate_to: localhost)
    on the task (or a wrapping C(block:)) when mixing into a multi-host play."
  - "The collection's action plugins force C(become: false) on the task
    automatically, so a parent play's C(become: true) does not bleed into
    the delegated call."
  - This module issues API calls via C(python-linstor) to the LINSTOR controller.
  - "For cluster-wide tasks use C(run_once=true) or a single-host play such as C(hosts: linstor_controllers[0])."
seealso:
  - module: linbit.linstor.storage_pool
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Query all storage pools
  linbit.linstor.storage_pool_info:
  register: all_pools
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Query a specific pool on a specific node
  linbit.linstor.storage_pool_info:
    name: sp-lvm-thin
    node: node-1
  register: pool_state
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Show the pool's free and total capacity
  ansible.builtin.debug:
    msg: "{{ pool_state.storage_pools[0].free_capacity }} of {{ pool_state.storage_pools[0].total_capacity }} KiB free"
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
storage_pools:
  description: List of LINSTOR storage pools, filtered by O(name) and O(node) when supplied.
  type: list
  elements: dict
  returned: always
  contains:
    name:
      description: Storage pool name.
      type: str
    node:
      description: Node the storage pool resides on.
      type: str
    provider_kind:
      description: LINSTOR provider kind string (for example LVM_THIN or ZFS).
      type: str
    driver_pool:
      description: Backend storage identifier (volume group, thin pool, or zpool).
      type: str
    free_capacity:
      description: Free capacity in KiB, or null if not reported.
      type: int
    total_capacity:
      description: Total capacity in KiB, or null if not reported.
      type: int
    properties:
      description: Storage pool properties.
      type: dict
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)


def get_sp_props(pool):
    """Extract the properties dict from a storage pool object."""
    if hasattr(pool, 'properties') and pool.properties:
        return dict(pool.properties)
    return {}


def pool_to_dict(pool):
    """Flatten a storage pool object into a JSON-serializable dict."""
    fs = getattr(pool, 'free_space', None)
    free_cap = getattr(fs, 'free_capacity', None) if fs else None
    total_cap = getattr(fs, 'total_capacity', None) if fs else None
    return dict(
        name=getattr(pool, 'name', ''),
        node=getattr(pool, 'node_name', ''),
        provider_kind=str(getattr(pool, 'provider_kind', '')),
        driver_pool=getattr(pool, 'backing_pool', ''),
        free_capacity=free_cap,
        total_capacity=total_cap,
        properties=get_sp_props(pool),
    )


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str'),
        node=dict(type='str'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params['name']
    node = module.params['node']

    lin = get_linstor_connection(module)

    try:
        kwargs = {}
        if node:
            kwargs['filter_by_nodes'] = [node]
        if name:
            kwargs['filter_by_stor_pools'] = [name]
        sp_list = lin.storage_pool_list_raise(**kwargs)
        pools = [pool_to_dict(p) for p in (sp_list.storage_pools or [])]
        module.exit_json(changed=False, storage_pools=pools)
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying storage pools: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
