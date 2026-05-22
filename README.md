# LINBIT LINSTOR Collection

The `linbit.linstor` Ansible collection for installing and configuring [LINSTOR®](https://linbit.com/linstor/).

## Requirements

- ansible-core 2.16 or newer
- [`python-linstor`](https://pypi.org/project/python-linstor/) 1.27.1 or newer

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

See [using Ansible collections](https://docs.ansible.com/ansible/latest/collections_guide/) for more details.

## Roles

| Role | Description |
|---|---|
| [`cluster_init`](roles/cluster_init/README.md) | Convenience role: installs satellite, controller, and registers cluster membership based on inventory group membership |
| [`cluster_membership`](roles/cluster_membership/README.md) | Registers LINSTOR nodes into the cluster (controller, combined, and satellite node types) |
| [`satellite_install`](roles/satellite_install/README.md) | Installs the LINSTOR satellite and DRBD |
| [`controller_install`](roles/controller_install/README.md) | Installs the LINSTOR controller and GUI |
| [`client_install`](roles/client_install/README.md) | Installs the LINSTOR CLI client |
| [`ssl_init`](roles/ssl_init/README.md) | Configure SSL/TLS for the LINSTOR REST API (HTTPS) and satellite connections (mutual TLS), including private CA, per-node certs, and Java keystores |
| [`peer_trust`](roles/peer_trust/README.md) | Trust a peer LINSTOR cluster's CA in the local Java truststore for cross-cluster backup shipping over HTTPS |
| [`gateway_install`](roles/gateway_install/README.md) | Installs the LINSTOR Gateway binary and service; includes satellite components on satellite nodes |
| [`gateway_satellite`](roles/gateway_satellite/README.md) | Installs LINSTOR Gateway satellite-side components (NFS/iSCSI resource agents, DRBD Reactor); optionally compiles and installs SCST iSCSI target when `scst=true` |
| [`storage_pool`](roles/storage_pool/README.md) | Create LINSTOR storage pools (LVM, LVM thin, ZFS, or filethin) from inventory-defined backing devices |
| [`ha_database`](roles/ha_database/README.md) | Configure highly available LINSTOR database storage; works for new deployments and existing production clusters |
| [`ha_gateway`](roles/ha_gateway/README.md) | Ansible-driven alternative to `linstor-gateway` CLI: creates HA NFS/iSCSI resources via DRBD Reactor promoter configs |

## Modules

Custom Ansible modules for managing LINSTOR objects declaratively.
Requires `python-linstor` on the control node (or on the execution target); see `requirements.txt` for the Python dependency, install with `pip install -r requirements.txt`.

| Module | Description |
|---|---|
| `controller` | Manage controller properties (cluster-wide singleton) |
| `node` | Manage cluster nodes (create, properties, auxiliary properties) |
| `node_interface` | Manage node net interfaces (create, modify, delete, query) |
| `storage_pool` | Manage storage pools on nodes (LVM, LVM thin, ZFS, file, etc.) |
| `resource_group` | Manage resource groups with placement rules, DRBD options, properties |
| `volume_group` | Manage volume groups within a resource group |
| `resource_definition` | Manage resource definitions with inline volume definitions and DRBD options |
| `resource` | Deploy resources via spawn, autoplace, or manual placement |
| `snapshot` | Manage snapshots (create, delete, rollback, restore to new resource) |
| `remote` | Manage remotes for backup shipping (S3, LINSTOR-to-LINSTOR, EBS) |
| `backup` | Create or delete LINSTOR backups on a remote (`state: present\|absent`) |
| `backup_info` | Read-only query for backups, backup details, and queue (`kind: query\|list\|info\|queued`) |
| `backup_ship` | Initiate a backup shipment between clusters or to S3 (event module, not idempotent) |
| `backup_restore` | Restore a backup to a new resource (idempotent on target RD existence) |
| `backup_abort` | Abort an in-progress backup operation (event module, not idempotent) |
| `schedule` | Manage backup schedules (cron-based) with enable and disable |
| `encryption` | Manage cluster-wide encryption passphrase (create, enter, modify) |
| `key_value_store` | Manage LINSTOR key-value store instances |
| `file` | Manage LINSTOR external files (used by `ha_gateway` to push promoter configs) |

All modules issue cluster-wide API calls via the LINSTOR controller.
For `controller`, `resource_group`, `volume_group`, `resource_definition`, and `resource` in `autoplace` or `spawn` mode, use `run_once: true` or a single-host play (`hosts: linstor_controllers[0]`).
For `resource` in `manual` mode, `node`, and `storage_pool`, the preferred pattern is `run_once: true` with a loop over inventory hosts.
Alternatively, let each play host call the module with its own host variables.

All module tasks run on the Ansible control node.
Built-in roles delegate to `localhost` automatically, so `python-linstor` only needs to be installed on the control node, not on managed nodes.

## Using modules in your own playbooks

The collection declares a `linstor` action group in `meta/runtime.yml` (referenced as `group/linbit.linstor.linstor`), so the controller URI can be set once at the play level via `module_defaults`.
The `controller_env` lookup builds a comma-joined URI string from all hosts in `groups['linstor_controllers']`.
The LINSTOR client walks the list and connects to the first responder.
When `linstor_ssl` is truthy in the play's variable context, the lookup emits `linstors://` URIs; otherwise plain `linstor://`.
Set `linstor_ssl: true` when targeting an SSL cluster.

For a dedicated LINSTOR-management play, set `connection: local` with `hosts: linstor_controllers[0]` so every task runs on the control node without per-task delegation:

```yaml
- hosts: linstor_controllers[0]
  connection: local
  gather_facts: false
  module_defaults:
    group/linbit.linstor.linstor:
      controllers: "{{ lookup('linbit.linstor.controller_env') }}"
  tasks:
    - name: Create a resource group
      linbit.linstor.resource_group:
        name: rg-0
        storage_pool: sp-lvm
        place_count: 2
      run_once: true  # noqa: run-once[task]
```

To mix LINSTOR module tasks into a multi-host play, wrap them in a block:

```yaml
- name: Configure LINSTOR objects
  module_defaults:
    group/linbit.linstor.linstor:
      controllers: "{{ lookup('linbit.linstor.controller_env') }}"
  block:
    - linbit.linstor.node:
        name: "{{ inventory_hostname }}"
        ip: "{{ ansible_host }}"
  delegate_to: localhost
```

The action plugins shipped with this collection force `become: false` on every LINSTOR API module, so a parent play's `become: true` does not bleed into the delegated task.

If `module_defaults` is not set, modules fall back to the `LS_CONTROLLERS` environment variable, then `/etc/linstor/linstor-client.conf`, then `linstor://localhost`.
For example: `environment: { LS_CONTROLLERS: "{{ lookup('linbit.linstor.controller_env') }}" }` works at the task or play level.

## Required Inventory Groups

The following inventory groups are used to control role targeting:

| Group | Description |
|---|---|
| `linstor_controllers` | Nodes to install the LINSTOR controller on |
| `linstor_satellites` | Nodes to install the LINSTOR satellite on |
| `linstor_cluster` | All LINSTOR cluster members (controllers + satellites) |

## Playbooks

| Playbook | Description |
|---|---|
| `ha_controller.yaml` | Wrapper playbook for the `ha_database` role (HA LINSTOR database conversion) |

## Licensing

This collection is primarily licensed and distributed as a whole under the MIT License. See [LICENSE](LICENSE) for the full text.

Non-module plugin files in the following directories are licensed under the [GNU General Public License v3.0 or later](https://www.gnu.org/licenses/gpl-3.0.txt), as required by the Ansible community package inclusion rules:

- [`plugins/action/`](plugins/action/)
- [`plugins/filter/`](plugins/filter/)
- [`plugins/lookup/`](plugins/lookup/)

## Authors

Created in 2026 by [Ryan Ronnander](https://github.com/ryan-ronnander) on behalf of [LINBIT](https://linbit.com).

Inspired by pre-collection Ansible contributions from [Matt Kereczman](https://github.com/kermat), [Ryan Ronnander](https://github.com/ryan-ronnander), [Michael Troutman](https://github.com/emteelb), and [Devin Vance](https://github.com/dvance).
