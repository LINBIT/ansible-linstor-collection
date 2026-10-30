# resource_group

Create LINSTOR resource groups, each with its volume groups.

The role loops over `linstor_resource_groups`, an inventory list of resource group definitions, and creates each resource group and its volume groups through the `linbit.linstor.resource_group` and `linbit.linstor.volume_group` modules.
Resource groups are cluster-wide objects, so the role runs its API calls once per play, from `linstor_api_delegate`.
Call the role from any play that targets `linstor_cluster` or a broader set of hosts.
With `linstor_resource_groups` empty or undefined, the role does nothing.

Use this role to create resource groups when bootstrapping a cluster.
Platform integrations, such as the `linstor-proxmox` plugin, the CloudStack and OpenNebula drivers, and the `linbit.linstor_integrations` roles, reference resource groups by name and never create them.
To change or remove resource groups later, use the `linbit.linstor.resource_group` and `linbit.linstor.volume_group` modules or the `linstor` CLI.

## Requirements

A running LINSTOR controller service with cluster nodes and storage pools that you register through `cluster_init`, or through `cluster_membership` and `storage_pool`.

`python-linstor` on the delegation target (the Ansible control node by default).

## Role variables

### `linstor_resource_groups` (inventory variable)

A list of resource group definitions, typically in `all: vars:` of the inventory.
Each item supports the following keys:

| Key | Required | Default | Description |
|---|---|---|---|
| `name` | yes |  | Resource group name |
| `description` | no |  | Human-readable description |
| `place_count` | no | `2` | Number of replicas to place |
| `storage_pool` | no |  | Default storage pool for the resource group |
| `diskless_on_remaining` | no |  | Create diskless resources on the remaining nodes |
| `do_not_place_with` | no |  | Resource names to avoid co-locating with |
| `do_not_place_with_regex` | no |  | Regex of resource names to avoid co-locating with |
| `replicas_on_same` | no |  | Node properties for same-node placement, with the `Aux/` prefix |
| `replicas_on_different` | no |  | Node properties for different-node placement, with the `Aux/` prefix |
| `layer_list` | no |  | Ordered layer list, for example `[DRBD, CACHE, STORAGE]` |
| `provider_list` | no |  | Storage provider types |
| `peer_slots` | no |  | Maximum number of DRBD peer slots |
| `properties` | no |  | LINSTOR properties to set on the resource group |
| `drbd_options` | no |  | DRBD options by category (`resource`, `net`, `disk`, `peer_device`) |
| `use_for_plugin` | no | `false` | Adds the `Aux/UseForPlugin=True` property, which marks the resource group for the platform's LINSTOR plugin |
| `volume_groups` | no | `[{volume_nr: 0}]` | Volume groups of the resource group, see below |

The role passes every key other than `name`, `use_for_plugin`, and `volume_groups` to the `linbit.linstor.resource_group` module option of the same name.
An omitted key takes that module's default, so the module documentation is the reference for each value.

> [!NOTE]
> Raising `place_count` from 2 to 3 doubles the write traffic on the replication network, because DRBD sends every write to each peer replica.
> Each replica beyond three adds more traffic and can quickly saturate the replication network for little benefit.
> With three replicas, a copy of the data survives the loss of two nodes, so a higher count suits only niche use cases.

`volume_groups` is a list of volume group definitions.
Each entry accepts `volume_nr` (default `0`), `gross`, and `properties`, which the role passes to the `linbit.linstor.volume_group` module.
If an entry omits `volume_groups`, the role creates volume group `0` from `resource_group_defaults`.
`linstor resource-group spawn-resources` and the platform plugins need that volume group.

### `resource_group_defaults` (role default)

A dictionary of fallback values for keys that a resource group entry omits.
It contains `volume_groups`, which supplies the volume groups when an entry omits that key.
See `defaults/main.yml`.

### `linstor_api_delegate` (role default: `localhost`)

Delegation target for LINSTOR API tasks.
Default `localhost` runs the `python-linstor` calls on the Ansible control node.
Override to a cluster node (for example `{{ groups['linstor_controllers'][0] }}`) when the Ansible control node cannot directly reach the LINSTOR controller API endpoint (SSH jump host, segmented management network).

## Dependencies

No hard role dependencies.

## Example playbook

The playbook does not need to pass any variables to the role:

```yaml
- name: LINSTOR resource groups
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    - name: Create LINSTOR resource groups
      ansible.builtin.import_role:
        name: linbit.linstor.resource_group
```

The role reads `linstor_resource_groups` directly from inventory.

## Inventory examples

Two resource groups for the platform's LINSTOR plugin, both on the same storage pool, with a third replica for the database volumes:

```yaml
all:
  vars:
    linstor_resource_groups:
      - name: rg-vm
        storage_pool: sp-lvm-thin
        place_count: 2
        use_for_plugin: true
      - name: rg-db
        storage_pool: sp-lvm-thin
        place_count: 3
        use_for_plugin: true
        drbd_options:
          resource:
            quorum: majority
            on-no-quorum: io-error
```

A resource group with a write cache in front of the data volumes.
The cache pool is a second entry in `linstor_storage_pools`, on faster disks of the same nodes, and the `Writecache/*` properties on the resource group apply to every resource spawned from it:

```yaml
all:
  vars:
    linstor_storage_pools:
      - name: sp-lvm-thin
        type: lvmthin
        vg: drbdpool
        physical_devices:
          - /dev/vdb
      - name: sp-cache
        type: lvm
        vg: cachepool
        physical_devices:
          - /dev/vdc
    linstor_resource_groups:
      - name: rg-writecache
        storage_pool: sp-lvm-thin
        place_count: 2
        layer_list: [DRBD, WRITECACHE, STORAGE]
        properties:
          Writecache/PoolName: sp-cache
          Writecache/Size: "10%"
```

A resource group with encrypted volumes.
The LUKS layer needs the LINSTOR master passphrase, which the controller creates and unlocks from `linstor_master_passphrase` (see the `controller_install` role README), and `cryptsetup` on the satellites, which `satellite_install` installs:

```yaml
all:
  vars:
    linstor_master_passphrase: "{{ vault_linstor_master_passphrase }}"
    linstor_resource_groups:
      - name: rg-luks
        storage_pool: sp-lvm-thin
        place_count: 2
        layer_list: [DRBD, LUKS, STORAGE]
```

## License

MIT

## Author information

[LINBIT](https://linbit.com)
