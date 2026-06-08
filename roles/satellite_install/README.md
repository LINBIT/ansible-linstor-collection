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
| `satellite_install_zfs` | `false` | Install ZFS on Debian (non-Ubuntu/Proxmox), Red Hat, and SUSE nodes (see [ZFS Support](#zfs-support)) |
| `satellite_install_firewall_rules` | `true` | Manage firewall rules for LINSTOR satellite ports; set `false` to skip |
| `satellite_install_firewall_ports` | `3366-3367/tcp`, `7000-8000/tcp` | Ports to open in firewalld or UFW for the LINSTOR satellite |
| `satellite_install_force_reconfigure` | `false` | Force the configure phase to re-run even when the package install is unchanged, re-asserts firewall ports and the LVM `global_filter` for DRBD devices (drift correction) |

See `defaults/main.yml` and `vars/` for additional variables.

## ZFS support

ZFS behavior varies by OS family.
LINBIT does not support ZFS on non-Debian family operating systems, use at your own risk.

Ubuntu and Proxmox VE always have ZFS available with no flag required:

| OS Family | Method |
|---|---|
| Ubuntu | `zfsutils-linux` installed unconditionally as a prerequisite (userspace only, no DKMS) |
| Proxmox VE | Ships with ZFS in the distribution; no additional packages |

For all other distributions, set `satellite_install_zfs: true` to enable:

| OS Family | Method | Notes |
|---|---|---|
| Debian (non-Ubuntu, non-Proxmox) | Enables `contrib` repository, installs `zfsutils-linux` via DKMS | |
| Red Hat (standard kernel) | Installs EPEL and ZFS kmod repository, uses prebuilt kernel modules | Disables DKMS repo, enables kmod repo |
| Red Hat (UEK kernel) | Installs EPEL and ZFS DKMS repository, builds module from source | Matches the UEK kernel's build compiler with `gcc-toolset-N` (11 on EL8, 14 on EL9); skipped when the system GCC already matches (EL10) |
| SUSE | Adds openSUSE filesystems repository, installs prebuilt `zfs` package | Configures `allow_unsupported_modules` for kernel module loading; installs `zfs-ueficert` and reboots on UEFI systems for Secure Boot MOK enrollment |

On Red Hat and SUSE, the role also creates `/etc/modules-load.d/zfs.conf` so the ZFS kernel module loads automatically at boot.
Debian family distributions handle module auto-loading through their own package hooks.

## Dependencies

`linbit.drbd.drbd_install`, `linbit.linstor.client_install`

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
