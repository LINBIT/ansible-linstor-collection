scst_install
============

Install SCST for iSCSI target support.

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
- name: Install SCST
  hosts: linstor_satellites
  become: true
  tasks:
    - ansible.builtin.include_role:
        name: linbit.linstor.scst_install
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
