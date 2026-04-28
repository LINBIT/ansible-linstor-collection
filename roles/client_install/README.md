client_install
==============

Install and configure the LINSTOR client.

Requirements
------------

None.

Role Variables
--------------

See `defaults/main.yml`.

| Variable | Default | Description |
|---|---|---|
| `linstor_controller_addresses` | *(from inventory)* | List of controller IPs for `linstor-client.conf`. Auto-discovered from `linstor_controllers` group `replication_ip` values. |
| `client_install_vip_discovery` | `true` | Query the controller for the `Aux/ha_database_vip` property and use it as the controller address. Set to `false` to always use `linstor_controller_addresses`. |
| `client_install_force_reconfigure` | `false` | Force re-running the configure phase even when the package install reports unchanged. Re-asserts `/etc/linstor/`, re-queries the controller for the HA VIP, and re-templates `linstor-client.conf`. Use for drift correction. |

On subsequent runs, the role queries the LINSTOR controller for the `Aux/ha_database_vip` property.
If set (by the `ha_database` role), the VIP replaces the inventory-derived addresses automatically.
No manual variable override is needed.

Dependencies
------------

None.

Example Playbook
----------------

```yaml
- name: Install LINSTOR client
  hosts: all
  any_errors_fatal: true
  become: true
  tasks:
    - ansible.builtin.import_role:
        name: linbit.linstor.client_install
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
