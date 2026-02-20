linstor_gateway_satellite
=========================

Install LINSTOR Gateway satellite-side components on LINSTOR satellite nodes.

Installs NFS/iSCSI resource agents, supplemental packages, and patches `linstor_satellite.toml` to allow DRBD Reactor to manage systemd drop-in files.
Dynamically includes `linbit.drbd_reactor.reactor_install` if DRBD Reactor is not already present.

This role is the prerequisite for both `linbit.linstor.linstor_gateway_install` (satellite nodes) and `linbit.linstor.ha_gateway`.
It does **not** install the `linstor-gateway` binary; that is handled by `linstor_gateway_install`.

Requirements
------------

Target nodes must be LINSTOR satellites with `linstor-satellite` already installed.

In larger clusters where only a subset of satellites serve LINSTOR Gateway resources, define a `linstor_gateway_satellites` inventory group (as a child of `linstor_satellites`) and `linstor_gateway_install` will automatically restrict satellite-side installation to those nodes.
No group definition is needed for smaller clusters.

Role Variables
--------------

| Variable | Default | Description |
|---|---|---|
| `linstor_gateway_portblock_ra_url` | ClusterLabs v4.16.0 | URL to fetch the portblock resource agent |
| `linstor_gateway_portblock_fix` | `true` | Overwrite and pin the portblock RA to fix iptables issues |
| `linstor_gateway_firewalld_services` | NFS + iSCSI ports | firewalld services/ports to open (RedHat/SUSE only) |
| `linstor_gateway_scst` | `false` | LIO alternative. Compile and install SCST iSCSI target from source |
| `scst_install_version` | `3.9.x` | SCST git tag to build from source; only used when `linstor_gateway_scst=true` |

Dependencies
------------

No formal role dependencies.
Dynamically includes `linbit.drbd_reactor.reactor_install` when DRBD Reactor is not present.

Example Playbook
----------------

```yaml
- name: Install LINSTOR Gateway satellite components
  hosts: linstor_satellites
  become: true
  tasks:
    - ansible.builtin.import_role:
        name: linbit.linstor.linstor_gateway_satellite
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
