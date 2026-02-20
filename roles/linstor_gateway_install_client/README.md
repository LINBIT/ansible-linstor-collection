linstor_gateway_install_client
==============================

Install LINSTOR Gateway client components.

Requirements
------------

The following inventory group must be defined:

| Group | Description |
|---|---|
| `linstor_satellites` | Nodes to install LINSTOR Gateway on |

Role Variables
--------------

See `defaults/main.yml`.

Dependencies
------------

None.

Example Playbook
----------------

```yaml
- name: Install LINSTOR Gateway client
  hosts: linstor_satellites
  become: true
  tasks:
    - ansible.builtin.import_role:
        name: linbit.linstor.linstor_gateway_install_client
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
