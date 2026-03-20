satellite_install
=================

Install and configure LINSTOR satellite nodes.

When `linstor-satellite` is already installed and `satellite_install_package_state` is `present` (the default), the role skips package installation entirely for faster subsequent runs.

Requirements
------------

The following inventory group must be defined:

| Group | Description |
|---|---|
| `linstor_satellites` | Nodes to install the LINSTOR satellite on |

Role Variables
--------------

| Variable | Default | Description |
|---|---|---|
| `satellite_install_package_state` | `present` | Package state for LINSTOR satellite packages; set `latest` to check for upgrades |
| `satellite_install_zfs` | `true` | Install ZFS utilities on Debian OS family nodes |
| `satellite_install_zfs_all_distros` | `false` | Install ZFS on RedHat and SUSE OS family nodes (see ZFS Support below) |
| `satellite_install_firewall_rules` | `true` | Manage firewall rules for LINSTOR satellite ports; set `false` to skip |
| `satellite_install_firewall_ports` | `3366-3367/tcp`, `7000-8000/tcp` | Ports to open in firewalld or UFW for the LINSTOR satellite |

See `defaults/main.yml` and `vars/` for additional variables.

ZFS Support
-----------

ZFS storage pool support is installed per OS family.
LINBIT does not support ZFS on non-Debian family operating systems.
Use ZFS on RedHat and SUSE at your own risk and for testing purposes only.

Set `satellite_install_zfs_all_distros: true` to enable ZFS installation on RedHat and SUSE nodes.

| OS Family | Default | Method | Notes |
|---|---|---|---|
| Debian (excluding Proxmox VE) | enabled | Enables contrib repository, installs `zfsutils-linux` | Contrib repo not needed for Ubuntu or Proxmox VE |
| Ubuntu | enabled | Installs `zfsutils-linux` | Package available in default repositories |
| Proxmox VE | enabled | Installs `zfsutils-linux` | Package available in Proxmox repositories |
| RedHat (standard kernel) | disabled | Installs EPEL and ZFS kmod repository, uses prebuilt kernel modules | Disables DKMS repo, enables kmod repo |
| RedHat (UEK kernel) | disabled | Installs EPEL and ZFS DKMS repository, builds module from source | Requires `gcc-toolset-11` on EL8 to match the UEK build compiler; EL9+ uses the system GCC |
| SUSE | disabled | Adds openSUSE filesystems repository, installs prebuilt `zfs` package | Configures `allow_unsupported_modules` for kernel module loading; installs `zfs-ueficert` and reboots on UEFI systems for Secure Boot MOK enrollment |

On RedHat and SUSE, the role also creates `/etc/modules-load.d/zfs.conf` so the ZFS kernel module loads automatically at boot.
Debian family distributions handle module auto-loading through their own package hooks.

Dependencies
------------

`linbit.drbd.drbd_install`, `linbit.linstor.client_install`

Example Playbook
----------------

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

To enable ZFS on all distributions:

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
        satellite_install_zfs_all_distros: true
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
