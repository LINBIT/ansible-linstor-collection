gateway_satellite
=================

Install LINSTOR Gateway satellite-side components on LINSTOR satellite nodes.

Installs NFS/iSCSI resource agents, supplemental packages, and patches `linstor_satellite.toml` to allow DRBD Reactor to manage systemd drop-in files.
Sets the `Aux/GatewaySatellite=True` node property so that gateway resource groups can constrain placement to gateway-ready nodes.
Depends on `linbit.drbd_reactor.reactor_install` so OCF resource agents and the `drbd-reactor.service` enable state are guaranteed regardless of whether DRBD Reactor was previously installed by another path.

This role is the prerequisite for both `linbit.linstor.gateway_install` (satellite nodes) and `linbit.linstor.ha_gateway`.
It does **not** install the `linstor-gateway` binary; that is handled by `gateway_install`.

Requirements
------------

Target nodes must be LINSTOR satellites with `linstor-satellite` already installed.

In larger clusters where only a subset of satellites serve LINSTOR Gateway resources, define a `linstor_gateway_satellites` inventory group (as a child of `linstor_satellites`) and `gateway_install` will automatically restrict satellite-side installation to those nodes.
No group definition is needed for smaller clusters.

Role Variables
--------------

| Variable | Default | Description |
|---|---|---|
| `gateway_satellite_firewall_rules` | `true` | Manage firewall rules for LINSTOR Gateway satellite ports; set `false` to skip |
| `gateway_satellite_firewall_ports` | NFS + iSCSI ports | Ports to open in firewalld or UFW (111/tcp, 2049/tcp, 3260/tcp) |
| `gateway_satellite_nfsv4_only` | `false` | Skip NFSv3-only ports (rpcbind 111, mountd 20048). Matches `ha_gateway_nfsv4_only` default. |
| `gateway_satellite_scst` | `false` | LIO alternative. Compile and install [SCST](https://github.com/SCST-project/scst) iSCSI target from source |
| `gateway_satellite_scst_version` | `3.10.x` | SCST git tag to build from source (see [tags](https://github.com/SCST-project/scst/tags)); only used when `gateway_satellite_scst=true` |
| `linstor_api_delegate` | `localhost` | Delegation target for LINSTOR API tasks; override to a cluster node (for example `{{ groups['linstor_controllers'][0] }}`) when the control node cannot reach the controller directly |

Dependencies
------------

`linbit.drbd_reactor.reactor_install` (hard dependency via `meta/main.yml`), invoked with `reactor_install_drbd: false` and `reactor_install_resource_agents_upstream: true` so that the `drbd-reactor` package, the `drbd-reactor.service` enable state, and the OCF resource agents DRBD Reactor uses are always present before `gateway_satellite`'s tasks run.

Example Playbook
----------------

```yaml
- name: Install LINSTOR Gateway satellite components
  hosts: linstor_satellites
  any_errors_fatal: true
  become: true
  tasks:
    - ansible.builtin.import_role:
        name: linbit.linstor.gateway_satellite
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
