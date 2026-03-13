satellite_install
=================

Install and configure LINSTOR satellite nodes.

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
| `satellite_install_firewall_rules` | `true` | Manage firewall rules for LINSTOR satellite ports; set `false` to skip |
| `satellite_install_firewall_ports` | `3366-3367/tcp`, `7000-8000/tcp` | Ports to open in firewalld or UFW for the LINSTOR satellite |

See `defaults/main.yml` and `vars/` for additional variables.

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
    - ansible.builtin.import_role:
        name: linbit.linstor.satellite_install
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
