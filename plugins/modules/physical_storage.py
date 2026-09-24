#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: physical_storage
short_description: Create LVM, ZFS, or SPDK device pools on LINSTOR satellites
version_added: "1.0.0"
description:
  - Prepares unused block devices on a satellite through the LINSTOR physical
    storage API, the same call behind
    C(linstor physical-storage create-device-pool).
  - LINSTOR runs C(pvcreate), C(vgcreate), and C(lvcreate) (or C(zpool create))
    on the satellite and can register the result as a storage pool in the same
    call with O(storage_pool).
  - Optionally places a VDO deduplication and compression volume under the pool
    with O(vdo). LINSTOR creates it with C(lvcreate --type vdo), so the
    satellite needs the C(vdo) userspace tools (C(vdoformat)) and the
    C(dm-vdo) kernel module.
  - LINSTOR does not manage device pools after creating them and offers no
    delete call (LINSTOR User's Guide, "Creating storage pools by using the
    physical storage command"). Only C(state=present) is supported. Remove the
    volume group or zpool on the node by hand.
options:
  node:
    description: Satellite node that owns the devices.
    type: str
    required: true
  provider_kind:
    description:
      - Kind of device pool to create.
      - C(lvm) creates a volume group named O(pool_name).
      - C(lvmthin) creates a volume group named C(linstor_<pool_name>) holding
        a thin pool named O(pool_name). Pass O(pool_name) as C(vg/thinpool) to
        pick the volume group name yourself.
      - C(zfs) and C(zfsthin) create a zpool named O(pool_name).
      - C(spdk) creates an SPDK logical volume store named O(pool_name) from
        the given PCI addresses.
    type: str
    required: true
    choices: [lvm, lvmthin, zfs, zfsthin, spdk]
  device_paths:
    description:
      - Block devices to consume, as the satellite names them (for example
        C(/dev/sdb)).
      - Use M(linbit.linstor.physical_storage_info) to list the devices
        LINSTOR considers eligible and the exact paths it expects.
    type: list
    elements: str
    required: true
  pool_name:
    description: Name of the volume group, thin pool, zpool, or SPDK store to create. See O(provider_kind).
    type: str
    required: true
  raid_level:
    description: RAID level for the pool. LINSTOR currently supports only C(JBOD).
    type: str
    default: JBOD
    choices: [JBOD]
  vdo:
    description:
      - Create the pool on top of a VDO volume.
      - LINSTOR builds a base volume group named C(<pool_name>-vdobase), creates
        a VDO volume in it with C(lvcreate --type vdo), and for C(lvmthin)
        converts that volume into the thin pool.
      - Only meaningful with C(lvm) and C(lvmthin).
    type: bool
    default: false
  vdo_logical_size:
    description:
      - Logical size the VDO volume presents, for example C(2T).
      - Set it above the physical size when you expect deduplication or
        compression savings. LVM defaults it to the physical size when omitted.
      - Ignored unless O(vdo=true).
    type: str
  vdo_slab_size:
    description:
      - VDO slab size, for example C(2G). Uses the LVM default when omitted.
      - Ignored unless O(vdo=true).
    type: str
  storage_pool:
    description:
      - Also register a LINSTOR storage pool of this name on O(node), backed
        by the new device pool.
      - Also the idempotency key. When a storage pool of this name already
        exists on O(node) the module makes no changes.
    type: str
  storage_pool_props:
    description: Properties to set on the storage pool created with O(storage_pool).
    type: dict
    default: {}
  sed:
    description:
      - Initialize self-encrypting drives (OPAL 2) with a random password that
        LINSTOR stores encrypted on the storage pool.
      - Requires O(storage_pool) and C(sedutil) on the satellite.
    type: bool
    default: false
  pv_create_arguments:
    description: Extra arguments for C(pvcreate).
    type: list
    elements: str
    default: []
  vg_create_arguments:
    description: Extra arguments for C(vgcreate).
    type: list
    elements: str
    default: []
  lv_create_arguments:
    description: Extra arguments for C(lvcreate) (thin pool and VDO volume).
    type: list
    elements: str
    default: []
  zpool_create_arguments:
    description: Extra arguments for C(zpool create).
    type: list
    elements: str
    default: []
  state:
    description:
      - Only C(present) is supported.
      - LINSTOR has no API to delete a device pool, so there is no C(absent).
    type: str
    default: present
    choices: [present]
extends_documentation_fragment:
  - linbit.linstor.connection
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
  - This module issues API calls through C(python-linstor) to the LINSTOR controller.
  - "Idempotency without O(storage_pool) relies on the physical storage list:
    when none of O(device_paths) is still listed as unused on O(node), the
    module assumes the device pool exists and reports no change. A device
    that something else consumed also drops off that list, so prefer
    O(storage_pool) as the idempotency key."
  - A request where only some of O(device_paths) are still unused fails
    rather than guessing.
  - "VDO on the satellite: the C(vdo) package (C(vdoformat)) and the
    C(dm-vdo) kernel module (in-tree since Linux 6.9, C(kmod-kvdo) on
    older Red Hat Enterprise Linux kernels). VDO with C(lvmthin) also needs
    LVM 2.3.24 or newer."
seealso:
  - module: linbit.linstor.physical_storage_info
  - module: linbit.linstor.storage_pool
  - name: LINSTOR User's Guide - Creating storage pools by using the physical storage command
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-physical-storage-command
    description: Eligibility rules and the physical storage commands in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Create an LVM thin pool and register it as a storage pool
  linbit.linstor.physical_storage:
    node: node-1
    provider_kind: lvmthin
    device_paths:
      - /dev/sdb
    pool_name: thinpool
    storage_pool: sp-thin
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Create a striped thin pool across two devices
  linbit.linstor.physical_storage:
    node: node-1
    provider_kind: lvmthin
    device_paths:
      - /dev/sdb
      - /dev/sdc
    pool_name: drbdpool/thinpool
    lv_create_arguments:
      - -i2
      - -I64
    storage_pool: sp-thin
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Create a deduplicated, compressed thin pool on VDO
  linbit.linstor.physical_storage:
    node: node-1
    provider_kind: lvmthin
    device_paths:
      - /dev/sdb
    pool_name: vdothin
    vdo: true
    vdo_logical_size: 2T
    storage_pool: sp-vdo
    storage_pool_props:
      MaxOversubscriptionRatio: "3"
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Create a zpool without registering a storage pool
  linbit.linstor.physical_storage:
    node: node-1
    provider_kind: zfs
    device_paths:
      - /dev/sdb
    pool_name: drbdpool
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Prepare every unused device on every satellite
  linbit.linstor.physical_storage:
    node: "{{ item.node }}"
    provider_kind: lvmthin
    device_paths:
      - "{{ item.device }}"
    pool_name: "thin{{ item.device | basename }}"
    storage_pool: "sp-{{ item.device | basename }}"
  loop: "{{ unused.physical_devices }}"
  loop_control:
    label: "{{ item.node }} {{ item.device }}"
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
node:
  description: Node name.
  type: str
  returned: always
pool_name:
  description: Device pool name as requested.
  type: str
  returned: always
provider_kind:
  description: Provider kind as requested.
  type: str
  returned: always
device_paths:
  description: Devices as requested.
  type: list
  elements: str
  returned: always
msg:
  description: Why no change was made, when the module skipped creation.
  type: str
  returned: when no change was made
storage_pool:
  description: Name of the LINSTOR storage pool.
  type: str
  returned: when O(storage_pool) is set
driver_pool:
  description: Backend storage identifier LINSTOR recorded for the storage pool (C(StorDriver/StorPoolName)).
  type: str
  returned: when O(storage_pool) is set and the pool could be read back
free_capacity:
  description: Free capacity of the storage pool in KiB, or null if not reported.
  type: int
  returned: when O(storage_pool) is set and the pool could be read back
total_capacity:
  description: Total capacity of the storage pool in KiB, or null if not reported.
  type: int
  returned: when O(storage_pool) is set and the pool could be read back
properties:
  description: Storage pool properties.
  type: dict
  returned: when O(storage_pool) is set and the pool could be read back
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
    check_api_response,
    parse_size,
)

PROVIDER_KIND_MAP = {
    'lvm': 'LVM',
    'lvmthin': 'LVMTHIN',
    'zfs': 'ZFS',
    'zfsthin': 'ZFSTHIN',
    'spdk': 'SPDK',
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


def unused_devices(lin, node):
    """Device paths the physical storage list reports as unused on node."""
    phys_list = lin.physical_storage_list()
    devices = set()
    for group in (phys_list.physical_devices if phys_list else []):
        for entry in group.nodes.get(node, []):
            devices.add(entry.device)
    return devices


def storage_pool_result(pool):
    """Capacity and properties of a storage pool for the module result."""
    fs = getattr(pool, 'free_space', None)
    props = dict(pool.properties) if pool.properties else {}
    return dict(
        driver_pool=props.get('StorDriver/StorPoolName'),
        free_capacity=getattr(fs, 'free_capacity', None) if fs else None,
        total_capacity=getattr(fs, 'total_capacity', None) if fs else None,
        properties=props,
    )


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        node=dict(type='str', required=True),
        provider_kind=dict(type='str', required=True, choices=list(PROVIDER_KIND_MAP.keys())),
        device_paths=dict(type='list', elements='str', required=True),
        pool_name=dict(type='str', required=True),
        raid_level=dict(type='str', default='JBOD', choices=['JBOD']),
        vdo=dict(type='bool', default=False),
        vdo_logical_size=dict(type='str'),
        vdo_slab_size=dict(type='str'),
        storage_pool=dict(type='str'),
        storage_pool_props=dict(type='dict', default={}),
        sed=dict(type='bool', default=False),
        pv_create_arguments=dict(type='list', elements='str', default=[]),
        vg_create_arguments=dict(type='list', elements='str', default=[]),
        lv_create_arguments=dict(type='list', elements='str', default=[]),
        zpool_create_arguments=dict(type='list', elements='str', default=[]),
        state=dict(type='str', default='present', choices=['present']),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    node = module.params['node']
    provider_kind = module.params['provider_kind']
    device_paths = module.params['device_paths']
    pool_name = module.params['pool_name']
    vdo = module.params['vdo']
    storage_pool = module.params['storage_pool']
    sed = module.params['sed']

    if not device_paths:
        module.fail_json(msg="'device_paths' must list at least one device")
    if sed and not storage_pool:
        module.fail_json(msg="'sed' requires 'storage_pool'")

    result = dict(
        node=node, pool_name=pool_name,
        provider_kind=provider_kind, device_paths=device_paths)

    lin = get_linstor_connection(module)

    try:
        if storage_pool:
            existing_pool = get_storage_pool(lin, node, storage_pool)
            if existing_pool is not None:
                result.update(storage_pool_result(existing_pool))
                module.exit_json(
                    changed=False, storage_pool=storage_pool,
                    msg="storage pool %s already exists on %s" % (storage_pool, node),
                    **result)

        unused = unused_devices(lin, node)
        requested = set(device_paths)
        if not requested & unused:
            module.exit_json(
                changed=False,
                msg="none of %s is listed as unused on %s, assuming the device pool exists" % (
                    ', '.join(device_paths), node),
                **result)
        if requested - unused:
            module.fail_json(
                msg="devices not listed as unused on %s: %s (unused: %s)" % (
                    node, ', '.join(sorted(requested - unused)),
                    ', '.join(sorted(unused)) or 'none'),
                **result)

        if module.check_mode:
            module.exit_json(changed=True, **result)

        create_kwargs = dict(
            node_name=node,
            provider_kind=PROVIDER_KIND_MAP[provider_kind],
            device_paths=device_paths,
            pool_name=pool_name,
            raid_level=module.params['raid_level'],
            vdo_enable=vdo,
            sed=sed,
            pv_create_arguments=module.params['pv_create_arguments'] or None,
            vg_create_arguments=module.params['vg_create_arguments'] or None,
            lv_create_arguments=module.params['lv_create_arguments'] or None,
            zpool_create_arguments=module.params['zpool_create_arguments'] or None,
        )
        if vdo:
            if module.params['vdo_logical_size']:
                create_kwargs['vdo_logical_size_kib'] = parse_size(module.params['vdo_logical_size'])
            if module.params['vdo_slab_size']:
                create_kwargs['vdo_slab_size_kib'] = parse_size(module.params['vdo_slab_size'])
        if storage_pool:
            create_kwargs['storage_pool_name'] = storage_pool
            props = module.params['storage_pool_props'] or {}
            if props:
                create_kwargs['storage_pool_props'] = {k: str(v) for k, v in props.items()}

        replies = lin.physical_storage_create_device_pool(**create_kwargs)
        check_api_response(
            module, replies,
            'create %s device pool %s on %s' % (provider_kind, pool_name, node))

        if storage_pool:
            # Read the pool back so the capacity query runs before downstream autoplace
            created_pool = get_storage_pool(lin, node, storage_pool)
            if created_pool is not None:
                result.update(storage_pool_result(created_pool))
            module.exit_json(changed=True, storage_pool=storage_pool, **result)

        module.exit_json(changed=True, **result)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error creating device pool '%s' on '%s': %s" % (
                pool_name, node, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
