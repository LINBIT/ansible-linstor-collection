# gateway_install

Install the `linstor-gateway` binary and service.

The role installs the `linstor-gateway` daemon (via package manager or GitHub release), deploys its configuration, opens firewall port `8337/tcp`, and starts the service.

On satellite nodes, the role also installs satellite-side components via `linbit.linstor.gateway_satellite` (NFS/iSCSI resource agents, DRBD Reactor, supplemental packages).
Standalone controllers receive the `linstor-gateway` binary only.

By default, satellite related components are installed on all `linstor_satellites`.
In larger clusters, where LINSTOR Gateway resources might be restricted to a small subset of nodes, define hosts as members of the `linstor_gateway_satellites` group to restrict installation to those nodes only.

## Requirements

The following inventory groups must be defined:

| Group | Description |
|---|---|
| `linstor_controllers` | Controller nodes (`linstor-gateway` binary only) |
| `linstor_satellites` | All satellite nodes |
| `linstor_gateway_satellites` | (optional) Satellites to install LINSTOR Gateway components on; falls back to all `linstor_satellites` if not defined |

## Role variables

| Variable | Default | Description |
|---|---|---|
| `gateway_install_package_state` | `present` | Package state for `linstor-gateway`; set `latest` to upgrade |
| `gateway_install_firewall_rules` | `true` | Manage firewall rules for LINSTOR Gateway ports; set `false` to skip |
| `gateway_install_firewall_ports` | `8337/tcp` | Ports to open in firewalld or UFW for LINSTOR Gateway |
| `gateway_install_force_reconfigure` | `false` | Force the configure phase to re-run even when the package install is unchanged; also re-runs `gateway_satellite` on satellites (drift correction) |

## Dependencies

No formal role dependencies.
On satellite nodes, conditionally includes `linbit.linstor.gateway_satellite`.

## Example playbook

To install LINSTOR Gateway as part of a new LINSTOR cluster deployment, set `cluster_init_linstor_gateway: true` when using the `linbit.linstor.cluster_init` role:

```yaml
- name: Deploy LINSTOR
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install and initialize LINSTOR with LINSTOR Gateway
      ansible.builtin.import_role:
        name: linbit.linstor.cluster_init
      vars:
        cluster_init_linstor_gateway: true
```

Standalone LINSTOR Gateway install against an existing LINSTOR cluster:

```yaml
- name: Install LINSTOR Gateway
  hosts: linstor_satellites
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install LINSTOR Gateway
      ansible.builtin.import_role:
        name: linbit.linstor.gateway_install
```

To use SCST as the iSCSI target backend, add `gateway_satellite_scst: true`:

```yaml
- name: Install LINSTOR Gateway
  hosts: linstor_satellites
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install LINSTOR Gateway
      ansible.builtin.import_role:
        name: linbit.linstor.gateway_install
      vars:
        gateway_satellite_scst: true
```

## License

MIT

## Author information

[LINBIT](https://linbit.com)
