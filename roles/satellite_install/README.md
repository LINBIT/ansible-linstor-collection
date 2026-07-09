# satellite_install

Install and configure LINSTOR satellite nodes.

When `linstor-satellite` is already installed and `satellite_install_package_state` is `present` (the default), the role skips package installation entirely for faster subsequent runs.

## Requirements

The following inventory group must be defined:

| Group | Description |
|---|---|
| `linstor_satellites` | Nodes to install the LINSTOR satellite on |

## Role variables

| Variable | Default | Description |
|---|---|---|
| `satellite_install_package_state` | `present` | Package state for LINSTOR satellite packages; set `latest` to check for upgrades |
| `linstor_install_version` | `""` | Pin `linstor-satellite` and `linstor-common` to a version, for example `1.33.3`, and lock them against upgrades; shared with `controller_install` for lockstep, empty installs newest |
| `satellite_install_zfs` | `false` | Install ZFS on Debian (non-Ubuntu/Proxmox), Red Hat, and SUSE nodes (see [ZFS Support](#zfs-support)) |
| `satellite_install_firewall_rules` | `true` | Manage firewall rules for LINSTOR satellite ports; set `false` to skip |
| `satellite_install_firewall_ports` | `3366-3367/tcp`, `7000-8000/tcp` | Ports to open in firewalld or UFW for the LINSTOR satellite |
| `satellite_install_force_reconfigure` | `false` | Force the configure phase to re-run even when the package install is unchanged, re-asserts firewall ports and the LVM `global_filter` for DRBD devices (drift correction) |

See `defaults/main.yml` and `vars/` for additional variables.

## Removing a version lock

Setting `linstor_install_version` locks `linstor-satellite` and `linstor-common` against upgrades.
Clearing the variable alone does not release the lock on a node where the packages are already installed, because the role only touches the lock when it installs.
Release the lock in one of these ways:

- Move the pin: set `linstor_install_version` to the new version and re-run the role, which unlocks, installs that version, and re-locks at it.
- Unpin and upgrade to newest: clear `linstor_install_version`, set `satellite_install_package_state: latest`, and re-run the role, which unlocks and does not re-lock.

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

## ZFS support

ZFS behavior varies by OS family.
LINBIT does not support ZFS on non-Debian family operating systems, use at your own risk.

Ubuntu and Proxmox VE always have ZFS available with no flag required:

| OS Family | Method |
|---|---|
| Ubuntu | `zfsutils-linux` installed unconditionally as a prerequisite (userspace only, no DKMS) |
| Proxmox VE | Ships with ZFS in the distribution; no additional packages |

For all other distributions, set `satellite_install_zfs: true` to include the [`linbit.common.zfs_install`](https://gitlab.at.linbit.com/ansible-collections/linbit.common/-/tree/main/roles/zfs_install) role.
See that role's documentation for the per-distribution installation methods (Debian DKMS, Red Hat kmod and UEK DKMS, SUSE filesystems repository).

## Dependencies

`linbit.drbd.drbd_install`, `linbit.linstor.client_install`; includes `linbit.common.zfs_install` when `satellite_install_zfs: true`

## Example playbook

```yaml
- name: Install LINSTOR satellites
  hosts: linstor_satellites
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install and configure LINSTOR satellite
      ansible.builtin.import_role:
        name: linbit.linstor.satellite_install
```

To enable ZFS on Red Hat, SUSE, and non-Ubuntu Debian nodes:

```yaml
- name: Install LINSTOR satellites with ZFS
  hosts: linstor_satellites
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install and configure LINSTOR satellite
      ansible.builtin.import_role:
        name: linbit.linstor.satellite_install
      vars:
        satellite_install_zfs: true
```

## License

MIT

## Author information

[LINBIT](https://linbit.com)
