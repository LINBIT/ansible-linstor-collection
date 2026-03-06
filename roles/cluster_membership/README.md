cluster_membership
==================

Register LINSTOR nodes into the cluster.
Runs `linstor node create` for controller, combined (controller+satellite), and satellite node types.
Idempotent: nodes already registered are skipped.

Requirements
------------

The following inventory groups must be defined:

| Group | Description |
|---|---|
| `linstor_controllers` | Controller nodes (registers as `Controller` or `Combined`) |
| `linstor_satellites` | Satellite nodes (registers as `Satellite` or `Combined`) |

Role Variables
--------------

| Variable | Default | Description |
|---|---|---|
| `short_hostnames` | auto-detected | Use short hostnames (true on Proxmox VE) |
| `linstor_hostname` | auto-detected | LINSTOR node name: `inventory_hostname_short` on Proxmox VE, `inventory_hostname` otherwise |
| `replication_ip` | (required) | Node IP used for DRBD replication traffic; set per host in inventory |

Dependencies
------------

None.

Example Playbook
----------------

```yaml
- name: Register LINSTOR cluster membership
  hosts: linstor_controllers,linstor_satellites
  become: true
  tasks:
    - ansible.builtin.import_role:
        name: linbit.linstor.cluster_membership
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
