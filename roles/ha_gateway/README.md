ha_gateway
==========

Create highly available iSCSI targets, NFS exports, and NVMe-oF targets using DRBD Reactor promoter configs.
This is an Ansible-only implementation of [LINSTOR Gateway](https://github.com/LINBIT/linstor-gateway).

This role processes three inventory variables (`linstor_iscsi_targets`, `linstor_nfs_exports`, `linstor_nvmeof_targets`) through a shared task flow:

1. Validate target definitions and pre-flight checks
1. Tag nodes with per-target auxiliary properties
1. Create per-target resource group
1. Spawn LINSTOR resources
1. Format partitions
1. Set DRBD resource options
1. Deploy promoter TOML configs to `/etc/drbd-reactor.d/`

Each target gets its own resource group (`rg-{{ name }}`) with `Aux/gw-{{ name }}=True` placement constraint.
A pre-flight check asserts that `drbd-reactor.service` exists on each target's satellites.
Setting `state: absent` on a target removes the promoter config and deletes the LINSTOR resource.

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
| `ha_gateway_storage_pool` | `""` | Default storage pool for per-target resource groups; empty for LINSTOR auto-select |
| `ha_gateway_place_count` | `2` | Default replica count for per-target resource groups |
| `ha_gateway_tickle_dir_size` | `64M` | Size of the portblock tickle_dir volume |
| `ha_gateway_fstype` | `ext4` | Filesystem for the portblock tickle_dir and data volumes |
| `ha_gateway_drbd_options` | see defaults | DRBD resource options for HA operation |
| `ha_gateway_iscsi_port` | `3260` | Default iSCSI target port |
| `ha_gateway_iscsi_iqn_base` | `iqn.2019-08.com.linbit` | Default IQN base when `iqn` is not set on target |
| `ha_gateway_nfs_port` | `2049` | NFS service port |
| `ha_gateway_nfs_allowed_ips` | `["0.0.0.0/0"]` | Default client CIDRs for NFS exports |
| `ha_gateway_nfs_options` | `rw,all_squash,anonuid=0,anongid=0` | Default NFS export options |
| `ha_gateway_nvmeof_port` | `4420` | Default NVMe-oF target port |

iSCSI Targets
-------------

Each entry in `linstor_iscsi_targets`:

| Key | Required | Default | Description |
|---|---|---|---|
| `name` | yes | | LINSTOR resource name |
| `service_ips` | yes | | List of VIPs in CIDR notation (iSCSI portals) |
| `volumes` | yes | | List of volume definitions (`size` key) |
| `nodes` | yes | | List of exactly 3 inventory hostnames for placement |
| `storage_pool` | no | `ha_gateway_storage_pool` | Override storage pool for this target |
| `place_count` | no | `ha_gateway_place_count` | Override replica count for this target |
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
| `name` | yes | | LINSTOR resource name |
| `service_ips` | yes | | List of VIPs in CIDR notation |
| `exports` | yes | | List of export definitions (see below) |
| `nodes` | yes | | List of exactly 3 inventory hostnames for placement |
| `storage_pool` | no | `ha_gateway_storage_pool` | Override storage pool for this export |
| `place_count` | no | `ha_gateway_place_count` | Override replica count for this export |
| `fstype` | no | `ext4` | Default filesystem for all volumes |
| `port` | no | `2049` | NFS service port |
| `state` | no | `present` | `present` or `absent` |

Each entry in `exports`:

| Key | Required | Default | Description |
|---|---|---|---|
| `size` | yes | | Export volume size (for example `50G`) |
| `path` | no | `/` | Path under `/srv/gateway-exports/<name>/` |
| `allowed_ips` | no | `ha_gateway_nfs_allowed_ips` | List of client CIDRs |
| `export_options` | no | `ha_gateway_nfs_options` | NFS export options |
| `fstype` | no | service-level `fstype` | Filesystem for this volume |

Multiple exports within a single NFS service are supported and fail over together as a unit.
The kernel NFS server cannot have more than one instance per node, so multiple NFS service definitions must use non-overlapping nodes.

NVMe-oF Targets
---------------

Each entry in `linstor_nvmeof_targets`:

| Key | Required | Default | Description |
|---|---|---|---|
| `name` | yes | | LINSTOR resource name |
| `nqn` | yes | | NVMe Qualified Name |
| `service_ips` | yes | | List of VIPs in CIDR notation |
| `volumes` | yes | | List of volume definitions (`size` key) |
| `nodes` | yes | | List of exactly 3 inventory hostnames for placement |
| `storage_pool` | no | `ha_gateway_storage_pool` | Override storage pool for this target |
| `place_count` | no | `ha_gateway_place_count` | Override replica count for this target |
| `target_port` | no | `4420` | NVMe-oF target port |
| `fstype` | no | `ext4` | Portblock tickle_dir filesystem |
| `state` | no | `present` | `present` or `absent` |

Per-target Placement
--------------------

Each target requires a `nodes` list of exactly 3 inventory hostnames for quorum.
The role sets `Aux/gw-{{ name }}=True` on each node and creates `rg-{{ name }}` with `replicas_on_same: "Aux/gw-{{ name }}=True"`.
At least 2 of the 3 nodes must be in the `linstor_diskful_satellites` inventory group.

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
# iSCSI targets (with specific 'sp-fast' storage pool)
linstor_iscsi_targets:
  - name: iscsi-web
    iqn: iqn.2026-03.com.linbit:web
    service_ips:
      - 192.168.222.240/24
    volumes:
      - size: 10G
    storage_pool: sp-fast
    nodes:
      - node-1
      - node-2
      - node-3

# NFS exports (with auto-selected storage pool)
# The kernel NFS server can have multiple exports, not multiple instances
linstor_nfs_exports:
  - name: nfs-shared
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
      - node-6

# NVMe-oF targets (with auto-selected storage pool)
linstor_nvmeof_targets:
  - name: nvme-fast
    nqn: nqn.2026-03.io.linbit:nvme-fast
    service_ips:
      - 192.168.222.242/24
    volumes:
      - size: 20G
    nodes:
      - node-1
      - node-2
      - node-3
```

NVMe-oF target with 3 diskful replicas (no tiebreaker):

```yaml
# group_vars/all/ha-3-replica-nvmeof.yaml
linstor_nvmeof_targets:
  - name: nvme-critical
    nqn: nqn.2026-03.io.linbit:nvme-critical
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

Multiple NFS services on non-overlapping nodes:

```yaml
# group_vars/all/ha-multi-nfs.yaml
# The kernel NFS server cannot have more than one instance per node
linstor_nfs_exports:
  - name: nfs-engineering
    service_ips:
      - 192.168.222.243/24
    exports:
      - path: /builds
        size: 100G
    nodes:
      - node-1
      - node-2
      - node-3
  - name: nfs-marketing
    service_ips:
      - 192.168.222.244/24
      - 10.0.0.244/24
    exports:
      - path: /assets
        size: 200G
    nodes:
      - node-4
      - node-5
      - node-6
```

iSCSI target with CHAP authentication and initiator ACLs:

```yaml
# group_vars/all/ha-iscsi-chap.yaml
linstor_iscsi_targets:
  - name: iscsi-secure
    iqn: iqn.2026-03.com.linbit:secure
    service_ips:
      - 192.168.222.245/24
    # multi-LUN
    volumes:
      - size: 50G
      - size: 100G
    nodes:
      - node-1
      - node-2
      - node-3
    username: admin
    password: s3cret
    allowed_initiators:
      - iqn.2026-03.com.linbit:initiator1
      - iqn.2026-03.com.linbit:initiator2
```

Remove targets by setting `state: absent`:

```yaml
linstor_iscsi_targets:
  - name: iscsi-web
    state: absent

linstor_nfs_exports:
  - name: nfs-shared
    state: absent

linstor_nvmeof_targets:
  - name: nvme-fast
    state: absent
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
