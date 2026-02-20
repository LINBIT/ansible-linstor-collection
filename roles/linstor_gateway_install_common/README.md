linstor_gateway_install_common
==============================

Install LINSTOR Gateway with NFS and iSCSI HA support.

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

`linbit.linstor.linstor_gateway_install_client`, `linbit.drbd_reactor.reactor_install`

Example Playbook
----------------

```yaml
- name: Install LINSTOR Gateway
  hosts: linstor_satellites
  become: true
  tasks:
    - ansible.builtin.import_role:
        name: linbit.linstor.linstor_gateway_install_common
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
