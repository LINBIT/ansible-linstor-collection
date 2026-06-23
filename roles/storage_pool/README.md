# storage_pool

Create LINSTOR storage pools on diskful satellite nodes.

The role supports all LINSTOR storage pool driver types: `lvm`, `lvmthin`, `zfs`, `zfsthin`, `file`, `filethin`, `spdk`, `remote_spdk`.
It loops over the `linstor_storage_pools` inventory variable (a list of pool definitions) and creates the underlying storage (volume groups, thin pools, zpools, or directories) before registering each pool with LINSTOR.

Each satellite creates the pools from `linstor_storage_pools` that target it; a satellite no pool targets is left diskless.
It can be called from any play targeting `linstor_cluster` or broader.
Per-host overrides work naturally via Ansible variable precedence: define `linstor_storage_pools` on a specific host to give it different pools.

Pool entries support optional `nodes` and `groups` keys for targeting specific hosts from a centralized definition.
When neither key is set, the pool targets all `linstor_satellites`.
When `nodes` or `groups` is set, the pool is created only on hosts in the union of the listed node names and inventory group members.

## Requirements

The LINSTOR satellite must be installed and running on target nodes (handled by `cluster_init` or `satellite_install`).

The `community.general` collection is required for LVM and ZFS pool creation (`community.general.lvg`, `community.general.lvol`, `community.general.zpool`).

## Role variables

### `linstor_storage_pools` (inventory variable)

A list of pool definitions, typically defined in `all: vars:` of the stack's `hosts.yaml`.
Each item supports the following keys:

| Key | Required | Default | Used by types |
|---|---|---|---|
| `name` | yes |  | all |
| `type` | no | `lvmthin` | all |
| `vg` | yes |  | lvm, lvmthin |
| `vg_thinpool` | no | `thinpool` | lvmthin |
| `zpool` | yes |  | zfs, zfsthin |
| `physical_devices` | yes (non-file) |  | lvm, lvmthin, zfs, zfsthin |
| `file_path` | no | `/var/lib/linstor-filethin/` | file, filethin |
| `thinpool_size` | no | `95%VG` | lvmthin |
| `pv_create_options` | no | `""` | lvm, lvmthin |
| `lv_create_options` | no | `""` (auto-stripe) | lvm, lvmthin |
| `zfs_create_options` | no | `""` | zfs, zfsthin |
| `zpool_vdev_type` | no | `stripe` | zfs, zfsthin |
| `zpool_properties` | no | `{}` | zfs, zfsthin |
| `vdevs` | no | `[]` | zfs, zfsthin |
| `wipefs_force` | no | `false` | lvm, lvmthin, zfs, zfsthin |
| `nodes` | no |  | all (targeting) |
| `groups` | no |  | all (targeting) |

`nodes` is a list of `inventory_hostname` values.
When set, the pool is created only on the listed nodes.

`groups` is a list of inventory group names.
When set, the pool is created only on hosts that are members of the listed groups.

When both `nodes` and `groups` are set, the union is used: a host matches if it appears in `nodes` or belongs to any group in `groups`.
When neither is set, the pool targets all `linstor_satellites`.

`pv_create_options` is passed to `pvcreate` when initializing physical volumes for the volume group.

`lv_create_options` controls how LINSTOR creates LVM volumes.
For LVM non-thin pools, the value is set as the `StorDriver/LvcreateOptions` LINSTOR property.
For LVM thin pools, the value is passed to `lvcreate` when creating the thin pool itself.
When empty and multiple physical devices exist, the role auto-generates striping options (`-i N -I 64`).

`zfs_create_options` is set as the `StorDriver/ZfscreateOptions` LINSTOR property, which is appended to every `zfs create` call LINSTOR executes when creating zvols.

`zpool_vdev_type` sets the vdev topology: `stripe`, `mirror`, `raidz`, `raidz1`, `raidz2`, or `raidz3`.

`zpool_properties` is passed to `community.general.zpool` at zpool creation time for pool-level settings (for example `ashift`, `autoexpand`).

`vdevs` is an optional list of additional vdevs appended to the pool at creation time, passed through to `community.general.zpool`.
Each entry takes `disks` (a required list of device paths), an optional `type` (the same topologies as `zpool_vdev_type`: `stripe`, `mirror`, `raidz`, `raidz1`, `raidz2`, `raidz3`), and an optional `role`.
The `role` is one of `log`, `cache`, `spare`, `dedup`, or `special`: use `role: log` for a separate intent log (SLOG), `role: special` for a special allocation class vdev, and `role: cache` for an L2ARC read cache.
Omit `role` to add another data vdev, for example a second `raidz2` group.
The `physical_devices` and `zpool_vdev_type` keys remain the pool's data vdev and are still required; the `vdevs` entries are appended after it, not a replacement for it.

By default, `wipefs` only runs on backing disks when the volume group or zpool does not yet exist.
Set `wipefs_force: true` to always wipe disk signatures, even on subsequent runs.

### `storage_pool_defaults` (role default)

A dict providing fallback values for omitted keys in each pool item.
Override this dict to change defaults globally.
See `defaults/main.yml`.

### `linstor_api_delegate` (role default: `localhost`)

Delegation target for LINSTOR API tasks.
Default `localhost` runs the python-linstor calls on the Ansible control node.
Override to a cluster node (for example `{{ groups['linstor_controllers'][0] }}`) when the control node cannot reach the controller API endpoint directly (SSH jump host, segmented management network).

## Behavior

The role restarts `linstor-satellite.service` after creating new storage (LVM volume groups, thin pools, or zpools).
Restarts are batched via handlers and flushed once before registering each pool with LINSTOR, preventing redundant restarts when multiple storage changes occur.

## Dependencies

No hard role dependencies.

## Example playbook

The playbook does not need to pass any variables to the role:

```yaml
- name: LINSTOR storage pool
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    - name: Create LINSTOR storage pools
      ansible.builtin.import_role:
        name: linbit.linstor.storage_pool
```

The role reads `linstor_storage_pools` directly from inventory.
Choose the inventory pattern that best fits your cluster size and hardware layout.

## Inventory patterns

### Pattern 1: per-host definitions

Best for small clusters or hosts with truly unique pool configurations.
Define `linstor_storage_pools` per host in `host_vars/` files or inline in `hosts.yaml`:

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

Or inline in `hosts.yaml`:

```yaml
linstor_satellites:
  hosts:
    linstor-3:
      linstor_storage_pools:
        - name: sp-nvme
          type: zfs
          zpool: nvme
          zpool_vdev_type: mirror
          zpool_properties:
            ashift: "12"
          zfs_create_options: "-o compression=lz4"
          physical_devices:
            - /dev/disk/by-id/nvme-SAMSUNG_MZQL21T9HCJR_S64GNX0W123456
            - /dev/disk/by-id/nvme-SAMSUNG_MZQL21T9HCJR_S64GNX0W789012
```

A bulk HDD pool with SSD helper vdevs uses `vdevs` to add a mirrored `log` vdev (SLOG, for synchronous iSCSI or NFS writes) and a single `cache` (L2ARC read cache) device alongside the `raidz2` data vdev:

```yaml
linstor_satellites:
  hosts:
    linstor-4:
      linstor_storage_pools:
        - name: sp-tank
          type: zfs
          zpool: tank
          zpool_vdev_type: raidz2
          physical_devices:
            - /dev/disk/by-id/wwn-0x5000c500a0000001
            - /dev/disk/by-id/wwn-0x5000c500a0000002
            - /dev/disk/by-id/wwn-0x5000c500a0000003
            - /dev/disk/by-id/wwn-0x5000c500a0000004
          vdevs:
            - role: log
              type: mirror
              disks:
                - /dev/disk/by-id/nvme-slog-ssd-a
                - /dev/disk/by-id/nvme-slog-ssd-b
            - role: cache
              disks:
                - /dev/disk/by-id/nvme-l2arc-ssd
```

The role creates this pool in a single `zpool create` call: the `raidz2` data vdev first, then the `log` and `cache` vdevs.
The SLOG is mirrored for redundancy; the L2ARC `cache` device is not, since losing a read cache is harmless.

### Pattern 2: cluster-wide uniform pool

Best when all hosts use the same device paths (for example `/dev/vdb` in virtual environments).
Define `linstor_storage_pools` once in `group_vars/all` or `all: vars:`:

```yaml
# group_vars/all/storage.yaml
linstor_storage_pools:
  - name: sp0
    type: lvmthin
    vg: drbdpool
    physical_devices:
      - /dev/nvme1n1
      - /dev/nvme2n1
```

Every node in `linstor_satellites` creates this pool.

### Pattern 3: centralized with targeting (recommended for large clusters)

Best for large clusters with multiple pool types or per-host device paths.
Define pool topology once in `group_vars/all` with `nodes` or `groups` keys for targeting.
Use Jinja2 variable references for per-host values like `physical_devices`.
Guard each per-host devices reference with `default([])`: every host in the play resolves the full `linstor_storage_pools` structure, so an unguarded reference fails on hosts that do not define the variable.

Create inventory groups for pool targeting (these groups need no `group_vars` of their own):

```yaml
# hosts.yaml - groups used purely for storage pool targeting
linstor_lvm_satellites:
  hosts:
    node-1:
    node-4:
    node-6:
    node-7:

linstor_zfs_satellites:
  hosts:
    node-2:
    node-3:
    node-5:
```

Define pool topology centrally, referencing a descriptively named per-host variable for each pool's device paths:

```yaml
# group_vars/all/storage.yaml
linstor_storage_pools:
  - name: sp-lvm
    type: lvmthin
    vg: drbdpool
    physical_devices: "{{ physical_devices_lvm_striped | default([]) }}"
    groups:
      - linstor_lvm_satellites

  - name: sp-zfs
    type: zfsthin
    zpool: drbdpool
    zpool_vdev_type: raidz1
    physical_devices: "{{ physical_devices_zfs_raidz1 | default([]) }}"
    groups:
      - linstor_zfs_satellites
```

Define the per-host device mapping in `host_vars/`:

```yaml
# host_vars/node-1.yaml
physical_devices_lvm_striped:
  - /dev/disk/by-id/nvme-INTEL_SSDPE2KX040T8_BTLJ1234567890
  - /dev/disk/by-id/nvme-INTEL_SSDPE2KX040T8_BTLJ0987654321

# host_vars/node-2.yaml
physical_devices_zfs_raidz1:
  - /dev/disk/by-id/scsi-SATA_ST4000NM0035_ZDH12345
  - /dev/disk/by-id/scsi-SATA_ST4000NM0035_ZDH23456
  - /dev/disk/by-id/scsi-SATA_ST4000NM0035_ZDH34567
```

The pool topology is defined once regardless of cluster size.
Each host resolves its per-host device variable to its own device paths at task time, and the variable name documents the pool layout it feeds (striped LVM, raidz1 ZFS).
For uniform device paths (for example `/dev/vdb` in virtual environments), use a literal value instead of a variable reference.

You can also target specific nodes by hostname instead of groups:

```yaml
# group_vars/all/storage.yaml
linstor_storage_pools:
  - name: sp-local-ssd
    type: lvmthin
    vg: ssdpool
    physical_devices: "{{ physical_devices_local_ssd | default([]) }}"
    nodes:
      - node-10
      - node-11
```

When both `nodes` and `groups` are set on the same pool entry, the union is used.

## Variable precedence

Ansible replaces variables rather than merging them.
If a host defines `linstor_storage_pools` in `host_vars/`, that definition completely replaces any `group_vars` definition for the same variable.
Do not mix per-host and centralized definitions for the same variable on the same host.

Pattern 3 avoids this issue entirely: all pool definitions live in `group_vars/all`, and per-host differences are isolated in separate variables (for example `physical_devices_lvm_striped`).

## License

MIT

## Author information

[LINBIT](https://linbit.com)
