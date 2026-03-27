#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: storage_pool
short_description: Manage LINSTOR storage pools
version_added: "0.10.0"
description:
  - Creates, modifies, or deletes LINSTOR storage pools on cluster nodes.
  - Idempotent. If the pool already exists on the node, only property changes are applied.
  - Use C(state=query) to check whether a storage pool exists and retrieve its details.
options:
  name:
    description: Name of the storage pool.
    type: str
    required: true
  node:
    description: Name of the node where the storage pool resides.
    type: str
    required: true
  state:
    description: Desired state of the storage pool.
    type: str
    default: present
    choices: [present, absent, query]
  driver:
    description:
      - Storage driver type.
      - Required when C(state=present).
      - The target satellite node must have the backing storage subsystem
        installed (for example, LVM tools for C(lvm) or C(lvmthin), ZFS
        utilities for C(zfs) or C(zfsthin)).
      - Run C(linstor node info) to check which drivers each satellite
        supports. See L(LINSTOR User's Guide,
        https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-node-info).
    type: str
    choices: [lvm, lvmthin, zfs, zfsthin, file, filethin, spdk, remote_spdk]
  driver_pool:
    description:
      - Backend storage identifier.
      - For LVM, the volume group name (e.g. C(drbdpool)).
      - For LVM thin, the VG/thinpool path (e.g. C(drbdpool/thinpool)).
      - For ZFS, the zpool name (e.g. C(drbdpool)).
      - For file, the directory path.
      - Required when C(state=present).
    type: str
  shared_space:
    description: Shared storage space name for shared storage pools.
    type: str
  properties:
    description: Dictionary of LINSTOR properties to set on the storage pool.
    type: dict
    default: {}
  delete_properties:
    description: List of property keys to remove from the storage pool.
    type: list
    elements: str
    default: []
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
  - This module issues cluster-wide API calls via C(python-linstor) to the LINSTOR controller.
  - Requires the L(linstor-api-py,https://github.com/LINBIT/linstor-api-py) package
    (C(python-linstor)) on the play host.
  - Two usage patterns are supported.
  - Centralized, use C(run_once=true) with a loop over inventory hosts to send
    all API calls from a single host.
  - Per-host, let each play host call the module with its own host variables
    such as C(inventory_hostname).
  - The C(node) parameter must refer to a LINSTOR satellite that has local
    storage (for example nodes in the C(linstor_diskful_satellites) inventory group).
  - "Over-provisioning: C(MaxFreeCapacityOversubscriptionRatio),
    C(MaxTotalCapacityOversubscriptionRatio), and C(MaxOversubscriptionRatio)
    (all default to 20). LINSTOR uses the lower of the free and total ratios.
    Set on the storage pool for per-pool limits, or on the controller via
    M(linbit.linstor.controller) for cluster-wide defaults."
  - "QoS throttling: C(sys/fs/blkio_throttle_read), C(sys/fs/blkio_throttle_write),
    C(sys/fs/blkio_throttle_read_iops), and C(sys/fs/blkio_throttle_write_iops)
    can be set on storage pools to limit I/O bandwidth and IOPS."
seealso:
  - name: LINSTOR User's Guide - Storage Pools
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-storage_pools
    description: Storage pool concepts and configuration in the LINSTOR User's Guide.
  - name: LINSTOR User's Guide - Over-Provisioning
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-over-provisioning
    description: Thin provisioning and over-subscription ratios in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Create LVM storage pool
  linbit.linstor.storage_pool:
    name: sp-lvm
    node: node-1
    driver: lvm
    driver_pool: drbdpool
  run_once: true  # noqa: run-once[task]

- name: Create LVM thin storage pool with striping
  linbit.linstor.storage_pool:
    name: sp-lvm-thin
    node: node-1
    driver: lvmthin
    driver_pool: "drbdpool/thinpool"
    properties:
      StorDriver/LvcreateOptions: "-i2 -I64"
  run_once: true  # noqa: run-once[task]

- name: Create ZFS storage pool on multiple nodes
  linbit.linstor.storage_pool:
    name: sp-zfs
    node: "{{ item }}"
    driver: zfs
    driver_pool: drbdpool
  loop:
    - node-1
    - node-2
    - node-3
  run_once: true  # noqa: run-once[task]

- name: Create storage pools on all satellite nodes from one host
  linbit.linstor.storage_pool:
    name: sp-lvm-thin
    node: "{{ item }}"
    driver: lvmthin
    driver_pool: "drbdpool/thinpool"
  loop: "{{ groups['linstor_diskful_satellites'] }}"
  run_once: true  # noqa: run-once[task]

- name: Set thin provisioning over-subscription ratios on a storage pool
  linbit.linstor.storage_pool:
    name: sp-lvm-thin
    node: node-1
    driver: lvmthin
    driver_pool: "drbdpool/thinpool"
    properties:
      MaxFreeCapacityOversubscriptionRatio: "3"
      MaxTotalCapacityOversubscriptionRatio: "3"
  run_once: true  # noqa: run-once[task]

- name: Query a storage pool
  linbit.linstor.storage_pool:
    name: sp-lvm
    node: node-1
    state: query
  register: sp_result
  run_once: true  # noqa: run-once[task]

- name: Remove a storage pool
  linbit.linstor.storage_pool:
    name: sp-lvm
    node: node-1
    state: absent
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
name:
  description: Name of the storage pool.
  type: str
  returned: always
node:
  description: Node name.
  type: str
  returned: always
exists:
  description: Whether the storage pool exists. Only returned with C(state=query).
  type: bool
  returned: query
driver:
  description: Storage driver type.
  type: str
  returned: success
driver_pool:
  description: Backend storage identifier.
  type: str
  returned: success
provider_kind:
  description: LINSTOR provider kind string (e.g. C(LVM_THIN), C(ZFS)).
  type: str
  returned: query
free_capacity:
  description: Free capacity in KiB.
  type: int
  returned: query
total_capacity:
  description: Total capacity in KiB.
  type: int
  returned: query
properties:
  description: Storage pool properties after the operation.
  type: dict
  returned: success
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
    check_api_response,
    compute_property_diff,
    HAS_LINSTOR,
)

if HAS_LINSTOR:
    import linstor

DRIVER_MAP = {
    'lvm': 'LVM',
    'lvmthin': 'LVMThin',
    'zfs': 'ZFS',
    'zfsthin': 'ZFSThin',
    'file': 'FILE',
    'filethin': 'FILEThin',
    'spdk': 'SPDK',
    'remote_spdk': 'REMOTE_SPDK',
}


def get_storage_pool(lin, node, name):
    """Get a storage pool by node and name. Returns the pool object or None."""
    sp_list = lin.storage_pool_list_raise(
        filter_by_nodes=[node],
        filter_by_stor_pools=[name],
    )
    if sp_list.storage_pools:
        return sp_list.storage_pools[0]
    return None


def get_sp_props(pool):
    """Extract the properties dict from a storage pool object."""
    if hasattr(pool, 'properties') and pool.properties:
        return dict(pool.properties)
    return {}


def get_driver_kind(driver_str):
    """Map user-friendly driver name to linstor StoragePoolDriver constant."""
    const_name = DRIVER_MAP.get(driver_str)
    if const_name and hasattr(linstor.StoragePoolDriver, const_name):
        return getattr(linstor.StoragePoolDriver, const_name)
    return None


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        node=dict(type='str', required=True),
        state=dict(type='str', default='present', choices=['present', 'absent', 'query']),
        driver=dict(type='str', choices=list(DRIVER_MAP.keys())),
        driver_pool=dict(type='str'),
        shared_space=dict(type='str'),
        properties=dict(type='dict', default={}),
        delete_properties=dict(type='list', elements='str', default=[]),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params['name']
    node = module.params['node']
    state = module.params['state']
    driver = module.params['driver']
    driver_pool = module.params['driver_pool']
    shared_space = module.params['shared_space']
    properties = module.params['properties'] or {}
    delete_properties = module.params['delete_properties'] or []

    lin = get_linstor_connection(module)
    changed = False

    try:
        existing_pool = get_storage_pool(lin, node, name)

        if state == 'query':
            if existing_pool is None:
                module.exit_json(changed=False, name=name, node=node, exists=False)
            fs = getattr(existing_pool, 'free_space', None)
            free_cap = getattr(fs, 'free_capacity', None) if fs else None
            total_cap = getattr(fs, 'total_capacity', None) if fs else None
            module.exit_json(
                changed=False, name=name, node=node, exists=True,
                provider_kind=str(getattr(existing_pool, 'provider_kind', '')),
                driver_pool=getattr(existing_pool, 'backing_pool', ''),
                free_capacity=free_cap,
                total_capacity=total_cap,
                properties=get_sp_props(existing_pool))

        if state == 'absent':
            if existing_pool is None:
                module.exit_json(changed=False, name=name, node=node)
            if module.check_mode:
                module.exit_json(changed=True, name=name, node=node)
            replies = lin.storage_pool_delete(node, name)
            check_api_response(module, replies, 'delete storage pool %s on %s' % (name, node))
            module.exit_json(changed=True, name=name, node=node)

        # state == 'present'
        if existing_pool is None:
            if module.check_mode:
                module.exit_json(
                    changed=True, name=name, node=node,
                    driver=driver, driver_pool=driver_pool,
                    properties=properties)

            if not driver or not driver_pool:
                module.fail_json(
                    msg="'driver' and 'driver_pool' are required "
                        "to create storage pool %s on %s" % (name, node))

            driver_kind = get_driver_kind(driver)
            if driver_kind is None:
                module.fail_json(msg="Unknown storage driver: %s" % driver)

            create_kwargs = dict(
                node_name=node,
                storage_pool_name=name,
                storage_driver=driver_kind,
                driver_pool_name=driver_pool,
            )
            if shared_space:
                create_kwargs['shared_space'] = shared_space

            replies = lin.storage_pool_create(**create_kwargs)
            check_api_response(module, replies, 'create storage pool %s on %s' % (name, node))
            changed = True

            # Set properties via modify (some create calls ignore property_dict)
            if properties:
                prop_dict = {k: str(v) for k, v in properties.items()}
                replies = lin.storage_pool_modify(
                    node, name, property_dict=prop_dict)
                check_api_response(
                    module, replies,
                    'set properties on storage pool %s/%s' % (node, name))

            # Read back the pool to confirm capacity is reported.
            # storage_pool_create() returns only an acknowledgement;
            # this list call triggers a synchronous capacity query to the
            # satellite, ensuring the free space tracker is populated
            # before downstream roles (e.g. ha_database) run autoplace.
            created_pool = get_storage_pool(lin, node, name)
            if created_pool:
                fs = getattr(created_pool, 'free_space', None)
                free_cap = getattr(fs, 'free_capacity', None) if fs else None
                total_cap = getattr(fs, 'total_capacity', None) if fs else None
                module.exit_json(
                    changed=True, name=name, node=node,
                    driver=driver, driver_pool=driver_pool,
                    free_capacity=free_cap,
                    total_capacity=total_cap,
                    properties=get_sp_props(created_pool))
            module.exit_json(
                changed=True, name=name, node=node,
                driver=driver, driver_pool=driver_pool,
                properties=properties)

        # Pool exists: compare and update properties
        current_props = get_sp_props(existing_pool)
        props_to_set, props_to_delete = compute_property_diff(
            current_props, properties, delete_properties)

        if not props_to_set and not props_to_delete:
            module.exit_json(
                changed=False, name=name, node=node,
                driver=driver, driver_pool=driver_pool,
                properties=current_props)

        if module.check_mode:
            module.exit_json(
                changed=True, name=name, node=node,
                driver=driver, driver_pool=driver_pool,
                properties=dict(current_props, **props_to_set))

        replies = lin.storage_pool_modify(
            node, name,
            property_dict=props_to_set,
            delete_props=props_to_delete or None,
        )
        check_api_response(
            module, replies,
            'modify properties on storage pool %s/%s' % (node, name))
        changed = True

        # Re-read properties after update
        updated_pool = get_storage_pool(lin, node, name)
        final_props = get_sp_props(updated_pool) if updated_pool else current_props

        module.exit_json(
            changed=changed, name=name, node=node,
            driver=driver, driver_pool=driver_pool,
            properties=final_props)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error managing storage pool '%s' on '%s': %s" % (
                name, node, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
