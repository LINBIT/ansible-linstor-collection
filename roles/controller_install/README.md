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
| `controller_install_firewalld_zone` | `""` | firewalld zone to open the LINSTOR controller ports in; empty uses the default zone, set it when a zone is bound to a source; ignored by UFW |
| `controller_install_firewall_ports` | `3370/tcp` | Ports to open in firewalld or UFW for the LINSTOR controller |
| `controller_install_force_reconfigure` | `false` | Force the configure phase to re-run even when the package install is unchanged, re-asserts firewall and controller service state; **briefly restarts the active controller on a running cluster** (drift correction) |
| `controller_install_db_type` | `h2` | `h2`, `mariadb`, `mysql`, or `postgresql`, in any case; `h2` keeps the built-in database and leaves `linstor.toml` alone, the others connect to an existing database by writing `[db]` in `linstor.toml` before the package install |
| `controller_install_db_host` | `""` | Database host name or IP address, required for every type but `h2` |
| `controller_install_db_port` | per type | Database port; `3306` for `mariadb` and `mysql`, `5432` for `postgresql` |
| `controller_install_db_name` | per type | Database name; `LINSTOR` for `mariadb` and `mysql`, where the controller always keeps its tables in a database named `LINSTOR`, and `linstor` for `postgresql`, where it creates a `LINSTOR` schema inside this database |
| `controller_install_db_user` | `""` | Database user, required for every type but `h2` |
| `controller_install_db_password` | `""` | Database password |
| `controller_install_db_wait_timeout` | `30` | Seconds to wait for a MariaDB, MySQL, or PostgreSQL database to accept connections |
| `controller_install_db_force` | `false` | Switch an installed controller to a different database URL and restart it there if it is running; the target must already hold the cluster's data; a first install does not need it |
| `linstor_master_passphrase` | `""` | LINSTOR master passphrase for the LUKS layer, written to `[encrypt]` in `linstor.toml` on every controller; empty writes nothing |
| `controller_install_passphrase_force` | `false` | Replace a different `[encrypt]` passphrase in `linstor.toml` after `linstor encryption modify-passphrase` |

On an installed controller, a changed database user or password restarts the running controller.
A changed URL fails unless `controller_install_db_force` is set, because the role does not move the cluster's data.
Move it first with `linstor-database export-db` and `import-db`.

`linstor.toml` holds the database password, the keystore passwords of `ssl_init`, and the master passphrase, so the role writes it with mode `0640`.
The controller unit reads it in the `linstor` group and sets that group on `/etc/linstor` at every start.

## Master passphrase

Resource groups with `LUKS` in their `layer_list` need the LINSTOR master passphrase.
With `linstor_master_passphrase` set, the controller creates the passphrase on a new cluster and unlocks it on every start, so nobody has to enter it after a restart or failover.

```yaml
all:
  vars:
    linstor_master_passphrase: "{{ vault_linstor_master_passphrase }}"
```

> [!TIP]
> Keep the value in Ansible Vault, as in the example, so it is encrypted in the inventory.

> [!WARNING]
> The variable sets the passphrase when the cluster is bootstrapped.
> To change it later, run `linstor encryption modify-passphrase` first, then update `linstor_master_passphrase` and run the role with `controller_install_passphrase_force: true`.
> A controller does not start when its `linstor.toml` holds a passphrase other than the cluster's.

Several controllers share one external database, and controllers that start together on an empty database leave it half-initialized.
On the Debian family, where the package starts the controller on install, a first install with more than one controller keeps the package from starting them.
The role then starts the controller on the first host in `linstor_controllers` and disables it on the others.

See `defaults/main.yml` for additional variables.

## Removing a version lock

Setting `linstor_install_version` installs that version and locks `linstor-controller` and `linstor-common` against upgrades.
The pin is for bringing up a cluster at a fixed version, for example for testing, not for changing the version later.
The role does not move or remove the lock, so clearing or changing the variable is not supported on a node where the packages are installed.
To change the version, release the lock by hand with the command for the node's package manager, then upgrade the packages.
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
