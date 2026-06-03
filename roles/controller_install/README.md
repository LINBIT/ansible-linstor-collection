# controller_install

Install and configure the LINSTOR controller.

## Requirements

The following inventory group must be defined:

| Group | Description |
|---|---|
| `linstor_controllers` | Nodes to install the LINSTOR controller on |

## Role variables

| Variable | Default | Description |
|---|---|---|
| `controller_install_package_state` | `latest` | Package state for LINSTOR controller packages; set `present` to skip upgrades |
| `controller_install_gui` | `true` | Install the `linstor-gui` web UI alongside `linstor-controller`; set `false` to skip |
| `controller_install_firewall_rules` | `true` | Manage firewall rules for LINSTOR controller ports; set `false` to skip |
| `controller_install_firewall_ports` | `3370/tcp` | Ports to open in firewalld or UFW for the LINSTOR controller |
| `controller_install_force_reconfigure` | `false` | Force the configure phase to re-run even when the package install is unchanged, re-asserts firewall and controller service state; **briefly restarts the active controller on a running cluster** (drift correction) |

See `defaults/main.yml` for additional variables.

## Dependencies

`linbit.linstor.client_install`

## Example playbook

```yaml
- name: Install LINSTOR controller
  hosts: linstor_controllers
  any_errors_fatal: true
  become: true
  tasks:
    - ansible.builtin.import_role:
        name: linbit.linstor.controller_install
```

## License

MIT

## Author information

[LINBIT](https://linbit.com)
