controller_install
==================

Install and configure the LINSTOR controller.

Requirements
------------

None.

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
    - ansible.builtin.include_role:
        name: linbit.linstor.controller_install
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
