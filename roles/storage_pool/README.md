storage_pool
============

Create LINSTOR storage pools on diskful satellite nodes.

Supports all LINSTOR storage pool driver types: `lvm`, `lvmthin`, `zfs`, `zfsthin`, `file`, `filethin`, `spdk`, `remote_spdk`.
The role loops over the `linstor_storage_pools` inventory variable (a list of pool definitions) and creates the underlying storage (volume groups, thin pools, zpools, or directories) before registering each pool with LINSTOR.

The role filters internally to nodes in the `linstor_diskful_satellites` inventory group.
It can be called from any play targeting `linstor_cluster` or broader.
Per-host overrides work naturally via Ansible variable precedence: define `linstor_storage_pools` on a specific host to give it different pools.

Requirements
------------

The LINSTOR satellite must be installed and running on target nodes (handled by `cluster_init` or `satellite_install`).

The `community.general` collection is required for LVM and ZFS pool creation (`community.general.lvg`, `community.general.lvol`, `community.general.zpool`).

Role Variables
--------------

### `linstor_storage_pools` (inventory variable)

A list of pool definitions, typically defined in `all: vars:` of the stack's `hosts.yaml`.
Each item supports the following keys:

| Key | Required | Default | Used by types |
|---|---|---|---|
| `name` | yes | — | all |
| `type` | no | `lvmthin` | all |
| `vg` | yes | — | lvm, lvmthin |
| `vg_thinpool` | no | `thinpool` | lvmthin |
| `zpool` | yes | — | zfs, zfsthin |
| `physical_devices` | yes (non-file) | — | lvm, lvmthin, zfs, zfsthin |
| `file_path` | no | `/var/lib/linstor-filethin/` | file, filethin |
| `thinpool_size` | no | `95%VG` | lvmthin |
| `pv_create_options` | no | `""` | lvm, lvmthin |
| `lv_create_options` | no | `""` (auto-stripe) | lvm, lvmthin |
| `zfs_create_options` | no | `""` | zfs, zfsthin |
| `zpool_vdev_type` | no | `stripe` | zfs, zfsthin |
| `zpool_properties` | no | `{}` | zfs, zfsthin |
| `wipefs_force` | no | `false` | lvm, lvmthin, zfs, zfsthin |

`pv_create_options` is passed to `pvcreate` when initializing physical volumes for the volume group.

`lv_create_options` controls how LINSTOR creates LVM volumes.
For LVM non-thin pools, the value is set as the `StorDriver/LvcreateOptions` LINSTOR property.
For LVM thin pools, the value is passed to `lvcreate` when creating the thin pool itself.
When empty and multiple physical devices exist, the role auto-generates striping options (`-i N -I 64`).

`zfs_create_options` is set as the `StorDriver/ZfscreateOptions` LINSTOR property, which is appended to every `zfs create` call LINSTOR executes when creating zvols.

`zpool_vdev_type` sets the vdev topology: `stripe`, `mirror`, `raidz`, `raidz1`, `raidz2`, or `raidz3`.

`zpool_properties` is passed to `community.general.zpool` at zpool creation time for pool-level settings (for example `ashift`, `autoexpand`).

By default, `wipefs` only runs on backing disks when the volume group or zpool does not yet exist.
Set `wipefs_force: true` to always wipe disk signatures, even on subsequent runs.

### `storage_pool_defaults` (role default)

A dict providing fallback values for omitted keys in each pool item.
Override this dict to change defaults globally.
See `defaults/main.yml`.

### Other variables

| Variable | Default | Description |
|---|---|---|
| `linstor_hostname` | auto-detected | Node hostname for LINSTOR. Forces short hostnames on Proxmox VE, unaltered otherwise |

Behavior
--------

The role restarts `linstor-satellite.service` after creating new storage (LVM volume groups, thin pools, or zpools).
Restarts are batched via handlers and flushed once before registering each pool with LINSTOR, preventing redundant restarts when multiple storage changes occur.

Dependencies
------------

No hard role dependencies.

Example Playbook
----------------

Define `linstor_storage_pools` variables in inventory. This example uses per-host variable files in the `host_vars/` directory:

```yaml
# host_vars/linstor-4.yml
linstor_storage_pools:
  - name: sp-fast
    type: lvmthin
    vg: fast-pool
    physical_devices:
      - /dev/disk/by-id/nvme-INTEL_SSDPE2KX040T8_BTLJ1234567890
  - name: sp-bulk
    type: lvm
    vg: bulk-pool
    physical_devices:
      - /dev/disk/by-id/scsi-SATA_ST4000NM0035_ZDH12345
      - /dev/disk/by-id/scsi-SATA_ST4000NM0035_ZDH67890
```

```yaml
# host_vars/linstor-5.yml
linstor_storage_pools:
  - name: sp-fast
    type: lvmthin
    vg: fast-pool
    physical_devices:
      - /dev/disk/by-id/nvme-INTEL_SSDPE2KX040T8_BTLJ9876543210
```

The playbook does not need to pass any variables to the role:

```yaml
- name: LINSTOR storage pool
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    # The storage_pool role reads linstor_storage_pools directly from inventory
    - name: Create LINSTOR storage pools
      ansible.builtin.import_role:
        name: linbit.linstor.storage_pool
```

A per-host ZFS pool defined inline in the main inventory file (`hosts.yaml`):

```yaml
# hosts.yaml
# linstor_storage_pools must be defined per host when using /dev/disk/by-id/
linstor_diskful_satellites:
  hosts:
    linstor-3:
      linstor_storage_pools:
        - name: mypool1
          type: zfs
          zpool: myzpool
          zpool_vdev_type: mirror
          zpool_properties:
            ashift: "12"
          zfs_create_options: "-o compression=lz4"
          physical_devices:
            - /dev/disk/by-id/nvme-SAMSUNG_MZQL21T9HCJR_S64GNX0W123456
            - /dev/disk/by-id/nvme-SAMSUNG_MZQL21T9HCJR_S64GNX0W789012
```

Storage pools can also be defined cluster-wide, but the `physical_devices` must match on all hosts:

```yaml
# hosts.yaml — all: vars:
# Using /dev/disk/by-id/ device paths is recommended 
all:
  vars:
    linstor_storage_pools:
      - name: sp0
        type: lvmthin
        vg: drbdpool
        vg_thinpool: thinpool
        physical_devices:
          - /dev/nvme1n1
          - /dev/nvme2n1
```

Alternatively, place the same cluster-wide `linstor_storage_pools` variable in `group_vars/all` instead:

```yaml
# group_vars/all/sp0.yml
# Using /dev/disk/by-id/ device paths is recommended
linstor_storage_pools:
  - name: sp0
    type: lvmthin
    vg: drbdpool
    vg_thinpool: thinpool
    physical_devices:
      - /dev/nvme1n1
      - /dev/nvme2n1
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
