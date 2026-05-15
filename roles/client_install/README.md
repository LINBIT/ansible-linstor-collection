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
| `client_install_force_reconfigure` | `false` | Force re-running the configure phase even when the package install reports unchanged. Re-asserts `/etc/linstor/` and re-templates `linstor-client.conf`. Use for drift correction. |

The role always writes the full list of controller addresses to `linstor-client.conf`.
The LINSTOR client walks the list and connects to the first responder, so HA failover works without a virtual IP.
If `linstor_ha_vip` is set in inventory it is used by the `ha_database` role to wire up a floating IP for the LINSTOR GUI and external API users, but the client config does not consume it.

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
