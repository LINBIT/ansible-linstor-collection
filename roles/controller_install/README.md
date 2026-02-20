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

See `defaults/main.yml`.

Dependencies
------------

`linbit.linstor.linstor_client`

Example Playbook
----------------

```yaml
- name: Install LINSTOR controller
  hosts: linstor_controllers
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
