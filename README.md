# LINBIT LINSTOR Collection

The `linbit.linstor` Ansible collection for installing and configuring [LINSTOR®](https://linbit.com/linstor/).

## Requirements

- ansible-core 2.16 or newer
- [`python-linstor`](https://pypi.org/project/python-linstor/) 1.28.1 or newer

## Installation

Install directly from GitHub using `requirements.yml` until LINBIT publishes to Ansible Galaxy:

```yaml
# requirements.yml
collections:
  - name: linbit.common
    source: https://github.com/LINBIT/ansible-common-collection.git
    type: git
  - name: linbit.drbd
    source: https://github.com/LINBIT/ansible-drbd-collection.git
    type: git
  - name: linbit.drbd_reactor
    source: https://github.com/LINBIT/ansible-drbd_reactor-collection.git
    type: git
  - name: linbit.linstor
    source: https://github.com/LINBIT/ansible-linstor-collection.git
    type: git
```

```bash
ansible-galaxy collection install -r requirements.yml
```

To upgrade to the latest commits on the default branch:

```bash
ansible-galaxy collection install -r requirements.yml --upgrade
```

For new deployments, start with the [`cluster_init`](roles/cluster_init/README.md) role.

See [using Ansible collections](https://docs.ansible.com/ansible/latest/collections_guide/) for more details.

## Roles

| Role | Description |
|---|---|
| [`cluster_init`](roles/cluster_init/README.md) | Convenience role: install satellite, controller, and register cluster membership based on inventory group membership |
| [`cluster_membership`](roles/cluster_membership/README.md) | Register LINSTOR nodes into the cluster (controller, combined, and satellite node types) |
| [`satellite_install`](roles/satellite_install/README.md) | Install the LINSTOR satellite and DRBD |
| [`controller_install`](roles/controller_install/README.md) | Install the LINSTOR controller and GUI |
| [`client_install`](roles/client_install/README.md) | Install the LINSTOR CLI client |
| [`ssl_init`](roles/ssl_init/README.md) | Configure SSL/TLS for the LINSTOR REST API (HTTPS) and satellite connections (mutual TLS), including private CA, per-node certs, and Java keystores |
| [`peer_trust`](roles/peer_trust/README.md) | Trust a peer LINSTOR cluster's CA in the local Java truststore for cross-cluster backup shipping over HTTPS |
| [`gateway_install`](roles/gateway_install/README.md) | Install the LINSTOR Gateway binary and service, with satellite components on satellite nodes |
| [`gateway_satellite`](roles/gateway_satellite/README.md) | Install LINSTOR Gateway satellite-side components (NFS/iSCSI resource agents, DRBD Reactor), optionally compiling and installing SCST iSCSI target when `scst=true` |
| [`storage_pool`](roles/storage_pool/README.md) | Create LINSTOR storage pools (LVM, LVM thin, ZFS, or filethin) from inventory-defined backing devices |
| [`ha_database`](roles/ha_database/README.md) | Configure highly available LINSTOR database storage for new deployments and existing production clusters |
| [`ha_gateway`](roles/ha_gateway/README.md) | Ansible-driven alternative to `linstor-gateway` CLI: create HA NFS/iSCSI resources via DRBD Reactor promoter configs |

## Modules

Custom Ansible modules for managing LINSTOR objects declaratively. Install [`python-linstor`](https://pypi.org/project/python-linstor/) on the Ansible control node (or wherever modules execute via delegation).

| Module | Description |
|---|---|
| `controller` | Manage controller properties (cluster-wide singleton) |
| `controller_info` | Read-only query for controller properties (cluster-wide singleton) |
| `node` | Manage cluster nodes (create, properties, auxiliary properties) |
| `node_info` | Read-only query for nodes (filter by `name`, or omit for all) |
| `node_interface` | Manage node net interfaces (create, modify, delete) |
| `node_interface_info` | Read-only query for a node's network interfaces (requires `node`, optional `name`) |
| `storage_pool` | Manage storage pools on nodes (LVM, LVM thin, ZFS, file, etc.) |
| `storage_pool_info` | Read-only query for storage pools (filter by `name` and/or `node`, or omit for all) |
| `resource_group` | Manage resource groups with placement rules, DRBD options, properties |
| `resource_group_info` | Read-only query for resource groups (filter by `name`, or omit for all) |
| `volume_group` | Manage volume groups within a resource group |
| `volume_group_info` | Read-only query for a resource group's volume groups (requires `resource_group`, optional `volume_nr`) |
| `resource_definition` | Manage resource definitions with inline volume definitions and DRBD options |
| `resource_definition_info` | Read-only query for resource definitions and volume definitions (filter by `name`, or omit for all) |
| `resource` | Deploy resources via spawn, autoplace, or manual placement |
| `resource_info` | Read-only query for resources, placement, and flags (filter by `name`, or omit for all) |
| `snapshot` | Manage snapshots (create, delete, rollback, restore to new resource) |
| `snapshot_info` | Read-only query for a resource's snapshots (requires `resource`, optional `name`) |
| `remote` | Manage remotes for backup shipping (S3, LINSTOR-to-LINSTOR, EBS) |
| `remote_info` | Read-only query for remotes (filter by `name`, or omit for all) |
| `backup` | Create or delete LINSTOR backups on a remote (`state: present\|absent`) |
| `backup_info` | Read-only query for backups, backup details, and queue (`kind: query\|list\|info\|queued`) |
| `backup_ship` | Initiate a backup shipment between clusters or to S3 (event module, not idempotent) |
| `backup_restore` | Restore a backup to a new resource (idempotent on target RD existence) |
| `backup_abort` | Abort an in-progress backup operation (event module, not idempotent) |
| `schedule` | Manage backup schedules (cron-based) with enable and disable |
| `schedule_info` | Read-only query for backup schedules (filter by `name`, or omit for all) |
| `encryption` | Manage cluster-wide encryption passphrase (create, enter, modify) |
| `encryption_info` | Read-only query for cluster-wide encryption (master passphrase) status |
| `key_value_store` | Manage LINSTOR key-value store instances |
| `key_value_store_info` | Read-only query for a key-value store's entries (requires `name`) |
| `file` | Manage LINSTOR external files (used by `ha_gateway` to push promoter configs) |
| `file_info` | Read-only query for a LINSTOR external file's content (requires `path`) |
| `linstor_installed` | Read-only check returning whether `linstor-controller` or `linstor-satellite` is installed on a node (used to gate integration plays) |

Most module tasks should use `run_once: true` or a single-host play. See [Using LINSTOR modules](#using-linstor-modules) for examples.

## Filter plugins

| Filter | Description |
|---|---|
| `linstor_addr` | Resolve a host's LINSTOR address using the `linstor_ip → replication_ip → ansible_host` precedence |
| `gateway_placement` | Build the manual placement list for `resource` in `manual` mode (used internally by `ha_gateway`) |
| `gateway_resolve_satellites` | Split LINSTOR-reported nodes per target into diskful and diskless lists (used internally by `ha_gateway`) |
| `host_storage_pools` | Select the `linstor_storage_pools` entries that target a host (via `nodes`/`groups`, or generic to the diskful satellites); used by `storage_pool` to build `_my_pools` |

## Lookup plugins

| Lookup | Description |
|---|---|
| `controller_env` | Build a comma-joined `LS_CONTROLLERS` URI string from the `linstor_controllers` inventory group, reading `linstor_ssl` from the play context |
| `group_addresses` | Return a list of LINSTOR addresses for all hosts in a given inventory group |

## LINSTOR controller connection

LINSTOR modules need a valid [controller URI](https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-using_the_linstor_client). The URI is defined by setting the `LS_CONTROLLERS` environment variable. There are a few ways to define it, depending on your LINSTOR environment.

### Set `LS_CONTROLLERS` directly

For non-SSL LINSTOR clusters:

```yaml
# Define at play, block, or task level
environment:
  LS_CONTROLLERS: "linstor://10.0.0.10:3370"
```

For SSL enabled clusters:

```yaml
environment:
  LS_CONTROLLERS: "linstor+ssl://10.0.0.10:3371"
```

For multi-controller (HA) non-SSL clusters:

```yaml
environment:
  LS_CONTROLLERS: "linstor://10.0.0.10,linstor://10.0.0.11,linstor://10.0.0.12"  # default non-SSL TCP port 3370
```

### From inventory

```yaml
# group_vars/all/linstor.yml
linstor_controllers_uri: "linstor+ssl://10.0.0.10"  # default SSL TCP port 3371
```

```yaml
environment:
  LS_CONTROLLERS: "{{ linstor_controllers_uri }}"
```

### Auto-discovered

If your inventory uses the suggested [LINSTOR groups](#required-inventory-groups), the `linbit.linstor.controller_env` lookup auto-discovers controllers. For clusters initialized with SSL (see [`ssl_init`](roles/ssl_init/README.md)), set `linstor_ssl: true`:

```yaml
# Define at play, block, or task level
environment:
  LS_CONTROLLERS: "{{ lookup('linbit.linstor.controller_env') }}"
vars:
  linstor_ssl: true  # Use linstor+ssl:// URI
```

LINSTOR modules resolve the controller URI in this order (first match wins), similarly to the [LINSTOR client](https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-using_the_linstor_client):

1. `controllers` module parameter (overrides everything else)
2. `LS_CONTROLLERS` environment variable (covered above)
3. `~/.config/linstor/linstor-client.conf` (per-user; the [`ssl_init`](roles/ssl_init/README.md) role writes this on the control node)
4. `/etc/linstor/linstor-client.conf` (system-wide; only consulted when the per-user file is absent)
5. Default: `linstor://localhost`

## Using LINSTOR modules

With the controller connection configured (see above), invoke LINSTOR modules from any play. Each example below uses the `controller_env` lookup so the `LS_CONTROLLERS:` line stays inventory-driven.

### Provision a resource group and spawn a resource

```yaml
- name: Provision LINSTOR storage
  hosts: localhost
  gather_facts: false
  environment:
    LS_CONTROLLERS: "{{ lookup('linbit.linstor.controller_env') }}"
  tasks:
    - name: Create a resource group
      linbit.linstor.resource_group:
        name: rg-0
        storage_pool: sp-lvm-thin
        place_count: 2

    - name: Spawn a 100 GiB resource from the group
      linbit.linstor.resource:
        name: res-0
        mode: spawn
        resource_group: rg-0
        size: 100G
```

### Add a node to a cluster

```yaml
- name: Add a LINSTOR node
  hosts: localhost
  gather_facts: false
  environment:
    LS_CONTROLLERS: "{{ lookup('linbit.linstor.controller_env') }}"
  tasks:
    - name: Add node-4 as a Satellite
      linbit.linstor.node:
        name: node-4
        ip: 10.0.0.13
        node_type: Satellite
```

### Configure cluster-wide controller properties

```yaml
- name: Configure LINSTOR controller properties
  hosts: localhost
  gather_facts: false
  environment:
    LS_CONTROLLERS: "{{ lookup('linbit.linstor.controller_env') }}"
  tasks:
    - name: Set cluster-wide auto-quorum policy to suspend-io
      linbit.linstor.controller:
        properties:
          DrbdOptions/auto-quorum: suspend-io
```

## Required inventory groups

The following inventory groups are used to control role targeting:

| Group | Description |
|---|---|
| `linstor_controllers` | LINSTOR controller nodes |
| `linstor_satellites` | LINSTOR satellite nodes, diskful when a storage pool targets the node, otherwise diskless |
| `linstor_diskful_satellites` | Optional child of `linstor_satellites` for inventory organization; reference it from a pool's `groups` key to scope placement |
| `linstor_diskless_satellites` | Optional child of `linstor_satellites` for organizing Tiebreaker or client-only nodes |
| `linstor_gateway_satellites` | Optional subset of satellite nodes for LINSTOR Gateway resource placement |
| `linstor_cluster` | All `linstor_controllers` and `linstor_satellites` |

## Licensing

This collection is primarily licensed and distributed as a whole under the MIT License. See [LICENSE](LICENSE) for the full text.

Non-module plugin files in the following directories are licensed under the [GNU General Public License v3.0 or later](https://www.gnu.org/licenses/gpl-3.0.txt), as required by the Ansible community package inclusion rules:

- [`plugins/action/`](plugins/action/)
- [`plugins/filter/`](plugins/filter/)
- [`plugins/lookup/`](plugins/lookup/)

## Authors

Created in 2026 by [Ryan Ronnander](https://github.com/ryan-ronnander) on behalf of [LINBIT](https://linbit.com).

Inspired by pre-collection Ansible contributions from [Matt Kereczman](https://github.com/kermat), [Ryan Ronnander](https://github.com/ryan-ronnander), [Michael Troutman](https://github.com/emteelb), and [Devin Vance](https://github.com/dvance).
