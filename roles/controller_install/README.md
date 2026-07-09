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
| `controller_install_package_state` | `present` | Package state for LINSTOR controller packages; `latest` installs or upgrades, `present` installs only |
| `linstor_install_version` | `""` | Pin `linstor-controller` and `linstor-common` to a version, for example `1.33.3`, and lock them against upgrades; shared with `satellite_install` for lockstep, empty installs newest |
| `controller_install_gui` | `true` | Install the `linstor-gui` web UI alongside `linstor-controller`; set `false` to skip |
| `controller_install_firewall_rules` | `true` | Manage firewall rules for LINSTOR controller ports; set `false` to skip |
| `controller_install_firewall_ports` | `3370/tcp` | Ports to open in firewalld or UFW for the LINSTOR controller |
| `controller_install_force_reconfigure` | `false` | Force the configure phase to re-run even when the package install is unchanged, re-asserts firewall and controller service state; **briefly restarts the active controller on a running cluster** (drift correction) |

See `defaults/main.yml` for additional variables.

## Removing a version lock

Setting `linstor_install_version` locks `linstor-controller` and `linstor-common` against upgrades.
Clearing the variable alone does not release the lock on a node where the packages are already installed, because the role only touches the lock when it installs.
Release the lock in one of these ways:

- Move the pin: set `linstor_install_version` to the new version and re-run the role, which unlocks, installs that version, and re-locks at it.
- Unpin and upgrade to newest: clear `linstor_install_version`, set `controller_install_package_state: latest`, and re-run the role, which unlocks and does not re-lock.

To release the lock manually, run the command for the node's package manager.
Release all LINSTOR server packages together, because they must stay in lockstep even though this role manages only its own:

```bash
# Red Hat (DNF)
dnf versionlock delete linstor-controller linstor-satellite linstor-common

# Debian and Ubuntu (APT)
apt-mark unhold linstor-controller linstor-satellite linstor-common

# SUSE (Zypper)
zypper removelock linstor-controller linstor-satellite linstor-common
```

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
