cluster_init
============

Convenience role that installs LINSTOR cluster components and registers cluster membership based on inventory group membership.
Runs `satellite_install` on nodes in `linstor_satellites`, `controller_install` on nodes in `linstor_controllers`, then `cluster_membership` on all: allowing the full cluster to be installed and registered with a single role against the entire inventory.

Requirements
------------

The following inventory groups must be defined:

| Group | Description |
|---|---|
| `linstor_satellites` | Nodes to install the LINSTOR satellite on |
| `linstor_controllers` | Nodes to install the LINSTOR controller on |

Role Variables
--------------

See `linbit.linstor.satellite_install`, `linbit.linstor.controller_install`, and `linbit.linstor.cluster_membership` for available variables.

Dependencies
------------

`linbit.linstor.satellite_install`, `linbit.linstor.controller_install`, `linbit.linstor.cluster_membership`

Example Playbook
----------------

```yaml
- name: Install LINSTOR cluster
  hosts: linstor_cluster
  become: true
  tasks:
    - ansible.builtin.import_role:
        name: linbit.linstor.cluster_init
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
