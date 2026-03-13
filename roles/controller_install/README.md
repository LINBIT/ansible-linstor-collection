controller_install
==================

Install and configure the LINSTOR controller.

Requirements
------------

The following inventory group must be defined:

| Group | Description |
|---|---|
| `linstor_controllers` | Nodes to install the LINSTOR controller on |

Role Variables
--------------

| Variable | Default | Description |
|---|---|---|
| `controller_install_package_state` | `latest` | Package state for LINSTOR controller packages; set `present` to skip upgrades |
| `controller_install_firewall_rules` | `true` | Manage firewall rules for LINSTOR controller ports; set `false` to skip |
| `controller_install_firewall_ports` | `3370/tcp` | Ports to open in firewalld or UFW for the LINSTOR controller |

See `defaults/main.yml` for additional variables.

Dependencies
------------

`linbit.linstor.client_install`

Example Playbook
----------------

```yaml
- name: Install LINSTOR controller
  hosts: linstor_controllers
  any_errors_fatal: true
  become: true
  tasks:
    - ansible.builtin.import_role:
        name: linbit.linstor.controller_install
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
