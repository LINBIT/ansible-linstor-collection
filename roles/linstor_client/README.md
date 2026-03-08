linstor_client
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
| `linstor_client_vip_discovery` | `true` | Query the controller for the `Aux/ha_database_vip` property and use it as the controller address. Set to `false` to always use `linstor_controller_addresses`. |

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
  become: true
  tasks:
    - ansible.builtin.import_role:
        name: linbit.linstor.linstor_client
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
