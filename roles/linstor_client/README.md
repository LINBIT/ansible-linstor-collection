linstor_client
==============

Install and configure the LINSTOR client.

Requirements
------------

None.

Role Variables
--------------

See `defaults/main.yml`.

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
