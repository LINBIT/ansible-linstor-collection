ha_gateway
==========

Create highly available iSCSI targets, NFS exports, and NVMe-oF targets using DRBD Reactor promoter configs.
This is an Ansible-only implementation of [LINSTOR Gateway](https://github.com/LINBIT/linstor-gateway), interoperable with the `linstor-gateway` CLI: resources created by this role show up in `linstor-gateway iscsi list`, `linstor-gateway nfs list`, and `linstor-gateway nvme list`, and that CLI can inspect or remove them.

This role processes three inventory variables (`linstor_iscsi_targets`, `linstor_nfs_exports`, `linstor_nvmeof_targets`) through a shared task flow:

1. Validate target definitions and pre-flight checks
1. Place LINSTOR resources (manual or autoplace)
1. Format partitions
1. Set DRBD resource options
1. Push promoter TOML configs to LINSTOR as external files and attach them to each resource definition

Targets with explicit `nodes` use manual placement; targets without `nodes` use LINSTOR autoplace.
A pre-flight check asserts that `drbd-reactor.service` exists on each target's satellites.
Setting `state: absent` on a target removes the promoter config (undeploying from all satellites) and deletes the LINSTOR resource.

Requirements
------------

The `ansible.utils` collection and `netaddr` Python library are required on the Ansible control node for service IP subnet validation.
Install `netaddr` with your package manager:

```
# APT (Ubuntu, Debian)
apt install python3-netaddr

# DNF (RHEL, AlmaLinux, Fedora)
dnf install python3-netaddr

# Zypper (openSUSE, SLES)
zypper install python3-netaddr
```

Install `gateway_satellite` on all satellite nodes before using this role.
It installs iSCSI and NFS resource agents, the portblock RA fix, and DRBD Reactor.

```yaml
- name: Install LINSTOR Gateway satellite components
  hosts: linstor_satellites
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install gateway satellite prerequisites
      ansible.builtin.import_role:
        name: linbit.linstor.gateway_satellite
```

Role Variables
--------------

See `defaults/main.yml`.

| Variable | Default | Description |
|---|---|---|
| `ha_gateway_storage_pool` | `""` | Default storage pool for resource placement; empty for LINSTOR auto-select |
| `ha_gateway_place_count` | `2` | Default replica count |
| `ha_gateway_tickle_dir_size` | `64M` | Size of the portblock tickle_dir volume |
| `ha_gateway_fstype` | `ext4` | Filesystem for the portblock tickle_dir and data volumes |
| `ha_gateway_filesystem_blocksize` | `4096` | Filesystem block size; forces 4K for cross-node 4Kn sector compatibility |
| `ha_gateway_drbd_options` | see defaults | DRBD resource options for HA operation |
| `ha_gateway_iscsi_port` | `3260` | Default iSCSI target port |
| `ha_gateway_iscsi_iqn_base` | `iqn.2026-06.com.linbit` | Default IQN base when `iqn` is not set on target |
| `ha_gateway_nfs_port` | `2049` | NFS service port |
| `ha_gateway_nfs_allowed_ips` | `["0.0.0.0/0"]` | Default client CIDRs for NFS exports |
| `ha_gateway_nfs_options` | `rw,all_squash,anonuid=0,anongid=0` | Default NFS export options |
| `ha_gateway_nvmeof_port` | `4420` | Default NVMe-oF target port |
| `ha_gateway_nvmeof_nqn_base` | `nqn.2026-06.io.linbit:nvme` | Default NQN base when `nqn` is not set on target. Must include `:nvme` segment per NVMe-oF spec (`<vendor>:nvme:<subsystem>`) |
| `linstor_hostname` | auto-detected | Node hostname for LINSTOR; forces short hostnames on Proxmox VE |

Resource Naming
---------------

LINSTOR resource definition names follow the LINSTOR Gateway scheme so the CLI can recognize them:

| Protocol | LINSTOR resource name | Example |
|---|---|---|
| iSCSI | WWN (last colon-separated part of IQN) | `iqn.2026-06.com.linbit:web` → `web` |
| NFS | target name as-is | `name: shared` → `shared` |
| NVMe-oF | NQN subsystem (last colon-separated part of NQN) | `nqn.2026-06.io.linbit:nvme:fast` → `fast` |

When `iqn` or `nqn` is omitted, defaults `ha_gateway_iscsi_iqn_base:{name}` / `ha_gateway_nvmeof_nqn_base:{name}` are used, so the WWN/subsystem becomes `{name}`.
Because the resource namespace is shared across protocols (no per-protocol prefix), an iSCSI target `name: data` collides with an NFS export `name: data`. The role asserts uniqueness across all targets.

Promoter config files are stored in LINSTOR as external files with the path pattern `/etc/drbd-reactor.d/linstor-gateway-{protocol}-{name}.toml`. The LINSTOR controller distributes them to every satellite holding a replica of the attached resource definition. This filename pattern is what makes the resources visible to `linstor-gateway <protocol> list`.

DRBD device paths follow the resource name, for example `/dev/drbd/by-res/shared/0`.

iSCSI Targets
-------------

Each entry in `linstor_iscsi_targets`:

| Key | Required | Default | Description |
|---|---|---|---|
| `name` | yes | | Target name (WWN portion of IQN; see Resource Naming) |
| `service_ips` | yes | | List of VIPs in CIDR notation (iSCSI portals) |
| `volumes` | yes | | List of volume definitions (`size` key) |
| `nodes` | no | (autoplace) | List of inventory hostnames for placement (at least `place_count`, max 3); omit for autoplace |
| `resource_group` | no | | Pre-existing LINSTOR resource group (must already exist) |
| `storage_pool` | no | `ha_gateway_storage_pool` | Storage pool (ignored when `resource_group` is set) |
| `place_count` | no | `ha_gateway_place_count` | Replica count; for autoplace targets with `resource_group`, the resource group controls this |
| `iqn` | no | `{{ iqn_base }}:{{ name }}` | iSCSI Qualified Name |
| `target_port` | no | `3260` | iSCSI target port |
| `implementation` | no | (auto) | iSCSI implementation: `lio`, `tgt`, or `scst` |
| `allowed_initiators` | no | `[]` | List of initiator IQNs for ACLs |
| `username` | no | | CHAP authentication username |
| `password` | no | | CHAP authentication password |
| `fstype` | no | `ext4` | Portblock tickle_dir filesystem |
| `state` | no | `present` | `present` or `absent` |

NFS Exports
-----------

Each entry in `linstor_nfs_exports`:

| Key | Required | Default | Description |
|---|---|---|---|
| `name` | yes | | Export name (becomes the LINSTOR resource name; see Resource Naming) |
| `service_ips` | yes | | List of VIPs in CIDR notation |
| `exports` | yes | | List of export definitions (see below) |
| `nodes` | no | (autoplace) | List of inventory hostnames for placement (at least `place_count`, max 3); omit for autoplace |
| `resource_group` | no | | Pre-existing LINSTOR resource group (must already exist) |
| `storage_pool` | no | `ha_gateway_storage_pool` | Storage pool (ignored when `resource_group` is set) |
| `place_count` | no | `ha_gateway_place_count` | Replica count; for autoplace targets with `resource_group`, the resource group controls this |
| `fstype` | no | `ext4` | Default filesystem for all volumes |
| `port` | no | `2049` | NFS service port |
| `state` | no | `present` | `present` or `absent` |

Each entry in `exports`:

| Key | Required | Default | Description |
|---|---|---|---|
| `size` | yes | | Export volume size (for example `50G`) |
| `path` | no | `/` | Path under `/srv/gateway-exports/<resource_name>/`; clients mount via the full server path (for example `mount -t nfs <VIP>:/srv/gateway-exports/shared/data /mnt`) |
| `allowed_ips` | no | `ha_gateway_nfs_allowed_ips` | List of client CIDRs |
| `export_options` | no | `ha_gateway_nfs_options` | NFS export options |
| `fstype` | no | service-level `fstype` | Filesystem for this volume |

Multiple exports within a single NFS service are supported and fail over together as a unit.
The kernel NFS server cannot have more than one instance per node, so multiple NFS service definitions must use non-overlapping nodes.
When multiple NFS exports use autoplace, `do_not_place_with_regex` prevents LINSTOR from placing two NFS resources on the same node.
A post-placement validation confirms non-overlapping nodes across all NFS exports.

NVMe-oF Targets
---------------

Each entry in `linstor_nvmeof_targets`:

| Key | Required | Default | Description |
|---|---|---|---|
| `name` | yes | | Target name (NQN subsystem; see Resource Naming) |
| `nqn` | no | `{{ nqn_base }}:{{ name }}` | NVMe Qualified Name; auto-generated from `ha_gateway_nvmeof_nqn_base` and target name if omitted |
| `service_ips` | yes | | List of VIPs in CIDR notation |
| `volumes` | yes | | List of volume definitions (`size` key) |
| `nodes` | no | (autoplace) | List of inventory hostnames for placement (at least `place_count`, max 3); omit for autoplace |
| `resource_group` | no | | Pre-existing LINSTOR resource group (must already exist) |
| `storage_pool` | no | `ha_gateway_storage_pool` | Storage pool (ignored when `resource_group` is set) |
| `place_count` | no | `ha_gateway_place_count` | Replica count; for autoplace targets with `resource_group`, the resource group controls this |
| `target_port` | no | `4420` | NVMe-oF target port |
| `fstype` | no | `ext4` | Portblock tickle_dir filesystem |
| `state` | no | `present` | `present` or `absent` |

Per-target Placement
--------------------

Each target supports two placement modes:

**Explicit nodes** (recommended for production): provide a `nodes` list with at least `place_count` entries (max 3).
The first `place_count` nodes receive diskful replicas.
Any additional nodes are placed as diskless (explicit TieBreaker control).
All nodes are placed in a single batch API call.

Examples with `place_count: 2` (default):
- `nodes: [A, B]` — 2 diskful, LINSTOR auto-creates TieBreaker on a random satellite.
- `nodes: [A, B, C]` — 2 diskful on A and B, diskless on C (you control the TieBreaker node).

With `place_count: 3` and `nodes: [A, B, C]`, all three are diskful and quorum is inherent.
All diskful nodes must be in the `linstor_diskful_satellites` inventory group.

**Autoplace**: omit `nodes` (or set `nodes: []`) to let LINSTOR select nodes automatically based on `place_count`.
The role queries LINSTOR after placement to discover the selected nodes and deploys promoter configs accordingly.

Dependencies
------------

No hard role dependencies.
`linbit.linstor.gateway_satellite` must run on all satellite nodes before this role (see Requirements above).
It installs DRBD Reactor (`linbit.drbd_reactor.reactor_install`) transitively.

The `ansible.utils` collection and `netaddr` Python library are required on the Ansible control node (see Requirements above).

Example Playbook
----------------

```yaml
- name: Deploy HA gateway targets
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    - name: Create HA gateway targets
      ansible.builtin.import_role:
        name: linbit.linstor.ha_gateway
```

With `group_vars/all/ha-gateway.yaml`:

```yaml
# iSCSI target with 2 replicas (default) -> LINSTOR resource "web" (= IQN WWN)
# LINSTOR auto-creates a TieBreaker on a third satellite for quorum
linstor_iscsi_targets:
  - name: web
    iqn: iqn.2026-06.com.linbit:web
    service_ips:
      - 192.168.222.240/24
    volumes:
      - size: 10G
    storage_pool: sp-fast
    nodes:
      - node-1
      - node-2

# NFS export with 2 replicas -> LINSTOR resource "shared"
linstor_nfs_exports:
  - name: shared
    service_ips:
      - 192.168.222.241/24
    exports:
      - path: /data
        size: 50G
      - path: /home
        size: 100G
    nodes:
      - node-4
      - node-5

# NVMe-oF target with 2 replicas -> LINSTOR resource "fast" (= NQN subsystem)
# NQN auto-generated from ha_gateway_nvmeof_nqn_base when omitted
linstor_nvmeof_targets:
  - name: fast
    service_ips:
      - 192.168.222.242/24
    volumes:
      - size: 20G
    nodes:
      - node-1
      - node-2
```

Autoplace targets (omit `nodes` to let LINSTOR select nodes automatically):

```yaml
# group_vars/all/ha-autoplace.yaml
# No 'nodes' key — LINSTOR autoplace selects satellites based on place_count
linstor_iscsi_targets:
  - name: auto
    service_ips:
      - 192.168.222.246/24
    volumes:
      - size: 10G
    storage_pool: sp0

linstor_nfs_exports:
  - name: auto
    service_ips:
      - 192.168.222.247/24
    exports:
      - path: /data
        size: 50G
```

NVMe-oF target with 3 diskful replicas (inherent quorum, no dedicated TieBreaker needed):

```yaml
# group_vars/all/ha-3-replica-nvmeof.yaml
linstor_nvmeof_targets:
  - name: critical
    nqn: nqn.2026-06.io.linbit:nvme:critical
    service_ips:
      - 192.168.222.243/24
    volumes:
      - size: 100G
    place_count: 3
    nodes:
      - node-1
      - node-2
      - node-3
```

Explicit TieBreaker placement (2 diskful + 1 diskless on a specific node):

```yaml
# group_vars/all/ha-explicit-tiebreaker.yaml
linstor_iscsi_targets:
  - name: pinned
    service_ips:
      - 192.168.222.250/24
    volumes:
      - size: 10G
    # place_count defaults to 2: node-1 and node-2 are diskful,
    # node-3 is placed as diskless (TieBreaker)
    nodes:
      - node-1
      - node-2
      - node-3
```

Multiple NFS services on non-overlapping nodes:

```yaml
# group_vars/all/ha-multi-nfs.yaml
# The kernel NFS server cannot have more than one instance per node
linstor_nfs_exports:
  - name: engineering
    service_ips:
      - 192.168.222.243/24
    exports:
      - path: /builds
        size: 100G
    nodes:
      - node-1
      - node-2
  - name: marketing
    service_ips:
      - 192.168.222.244/24
      - 10.0.0.244/24
    exports:
      - path: /assets
        size: 200G
    nodes:
      - node-4
      - node-5
```

Targets with a pre-existing resource group (storage pool, replica count, and constraints managed externally):

```yaml
# group_vars/all/ha-custom-rg.yaml
linstor_iscsi_targets:
  - name: database
    service_ips:
      - 192.168.222.248/24
    volumes:
      - size: 100G
    resource_group: rg-ssd-fast
    nodes:
      - node-1
      - node-2

linstor_nfs_exports:
  - name: archive
    service_ips:
      - 192.168.222.249/24
    exports:
      - path: /archive
        size: 500G
    resource_group: rg-hdd-bulk
```

iSCSI target with CHAP authentication and initiator ACLs:

```yaml
# group_vars/all/ha-iscsi-chap.yaml
linstor_iscsi_targets:
  - name: secure
    iqn: iqn.2026-06.com.linbit:secure
    service_ips:
      - 192.168.222.245/24
    # multi-LUN
    volumes:
      - size: 50G
      - size: 100G
    nodes:
      - node-1
      - node-2
    username: admin
    password: s3cret
    allowed_initiators:
      - iqn.2026-06.com.linbit:initiator1
      - iqn.2026-06.com.linbit:initiator2
```

Remove targets by setting `state: absent`:

```yaml
linstor_iscsi_targets:
  - name: web
    state: absent

linstor_nfs_exports:
  - name: shared
    state: absent

linstor_nvmeof_targets:
  - name: fast
    state: absent
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
