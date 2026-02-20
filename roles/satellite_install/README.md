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

See `defaults/main.yml` and `vars/`.

Dependencies
------------

`linbit.drbd.drbd_install`, `linbit.linstor.linstor_client`

Example Playbook
----------------

```yaml
- name: Install LINSTOR satellites
  hosts: linstor_satellites
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
