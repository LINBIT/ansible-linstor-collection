ha_gateway
==========

Configure HA NFS and iSCSI gateway resources using DRBD Reactor promoter configs.

This role is the Ansible-driven alternative to the [`linstor-gateway`](https://github.com/LINBIT/linstor-gateway) CLI tool.
Instead of running `linstor-gateway nfs create` or `linstor-gateway iscsi create` directly, this role performs equivalent operations declaratively via inventory variables: spawning LINSTOR resources, formatting partitions, and writing DRBD Reactor promoter TOML configs.

> **Work in progress.**
> The `linstor-gateway` CLI is the recommended and feature-complete tool for managing HA NFS and iSCSI resources.
> This role covers common use cases but is not a complete replacement.
> **Use at your own risk.**

Requirements
------------

Install `linstor_gateway_install_common` on all satellite nodes before using this role to ensure NFS/iSCSI resource agents, supplemental packages, and DRBD Reactor are present.

```yaml
- name: Install LINSTOR Gateway components
  hosts: linstor_satellites
  become: true
  tasks:
    - ansible.builtin.import_role:
        name: linbit.linstor.linstor_gateway_install_common
```

Role Variables
--------------

See `defaults/main.yml`.

| Variable | Default | Description |
|---|---|---|
| `ha_gateway_nfs_exports` | `[]` | List of NFS exports to create |
| `ha_gateway_iscsi_targets` | `[]` | List of iSCSI targets to create |
| `ha_gateway_rg` | `DfltRscGrp` | LINSTOR resource group for spawned resources |
| `ha_gateway_linstor_spawn` | `true` | Whether to spawn LINSTOR resources (set `false` if already spawned) |
| `ha_gateway_prefer_diskful` | `true` | Prefer diskful nodes as promoter targets |

Dependencies
------------

No hard role dependencies. `linbit.linstor.linstor_gateway_install_common` must be run on all
satellite nodes before this role (see Requirements above). It will install DRBD Reactor
(`linbit.drbd_reactor.reactor_install`) transitively.

Example Playbook
----------------

```yaml
- name: Deploy HA resources with DRBD Reactor
  hosts: linstor_satellites
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install LINSTOR Gateway components
      ansible.builtin.import_role:
        name: linbit.linstor.linstor_gateway_install_common

    - name: Create HA resources
      vars:
        ha_gateway_nfs_exports:
          - name: example-export
            size: 1G
            vip: 192.168.222.250
            # cidr_netmask: 24
            # fstype: ext4
        ha_gateway_iscsi_targets:
          - name: example-target
            size: 2G
            vip: 192.168.222.251
            # cidr_netmask: 24
            # target_port: 3260
            # iqn_base: 'iqn.2026-02.com.linbit'
            # fstype: ext4
      ansible.builtin.import_role:
        name: linbit.linstor.ha_gateway
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
