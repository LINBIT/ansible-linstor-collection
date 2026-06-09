# gateway_satellite

Install LINSTOR Gateway satellite-side components on LINSTOR satellite nodes.

The role installs NFS/iSCSI resource agents, supplemental packages, and patches `linstor_satellite.toml` to allow DRBD Reactor to manage systemd drop-in files.
It sets the `Aux/GatewaySatellite=True` node property so that gateway resource groups can constrain placement to gateway-ready nodes.
A hard dependency on `linbit.drbd_reactor.reactor_install` guarantees OCF resource agents and the `drbd-reactor.service` enable state regardless of whether DRBD Reactor was previously installed by another path.

This role is the prerequisite for both `linbit.linstor.gateway_install` (satellite nodes) and `linbit.linstor.ha_gateway`.
It does **not** install the `linstor-gateway` binary; that is handled by `gateway_install`.

## Requirements

Target nodes must be LINSTOR satellites with `linstor-satellite` already installed.

In larger clusters where only a subset of satellites serve LINSTOR Gateway resources, define a `linstor_gateway_satellites` inventory group (as a child of `linstor_satellites`) and `gateway_install` will automatically restrict satellite-side installation to those nodes.
No group definition is needed for smaller clusters.

## Role variables

| Variable | Default | Description |
|---|---|---|
| `gateway_satellite_firewall_rules` | `true` | Manage firewall rules for LINSTOR Gateway satellite ports; set `false` to skip |
| `gateway_satellite_firewall_ports` | NFS + iSCSI ports | Ports to open in firewalld or UFW (111/tcp, 2049/tcp, 3260/tcp) |
| `gateway_satellite_nfsv4_only` | `false` | Skip NFSv3-only ports (rpcbind 111, mountd 20048); matches the `ha_gateway_nfsv4_only` default |
| `gateway_satellite_scst` | `false` | LIO alternative; compile and install [SCST](https://github.com/SCST-project/scst) iSCSI target from source |
| `gateway_satellite_scst_version` | `""` | Empty resolves the latest SCST release tag (see [releases](https://github.com/SCST-project/scst/releases)); or pin a tag, branch, or commit SHA; only used when `gateway_satellite_scst=true` |
| `linstor_api_delegate` | `localhost` | Delegation target for LINSTOR API tasks; override to a cluster node (for example `{{ groups['linstor_controllers'][0] }}`) when the control node cannot reach the controller directly |

By default the latest SCST release is built (`v3.10` today).
Its RPM build fails on newer Enterprise Linux kernels (EL9.8+, EL10), so on those nodes set `gateway_satellite_scst_version: master` until SCST 3.11 is released.
The Debian packaging of the same release carries kernel-compatibility patches, so it builds on newer Debian and Ubuntu kernels (for example Debian 13 on 6.12 and Ubuntu 24.04 on 6.8).

## Dependencies

`linbit.drbd_reactor.reactor_install` (hard dependency via `meta/main.yml`), invoked with `reactor_install_drbd: false` and `reactor_install_resource_agents_upstream: true` so that the `drbd-reactor` package, the `drbd-reactor.service` enable state, and the OCF resource agents DRBD Reactor uses are always present before `gateway_satellite`'s tasks run.

## Example playbook

```yaml
- name: Install LINSTOR Gateway satellite components
  hosts: linstor_satellites
  any_errors_fatal: true
  become: true
  tasks:
    - ansible.builtin.import_role:
        name: linbit.linstor.gateway_satellite
```

## License

MIT

## Author information

[LINBIT](https://linbit.com)
