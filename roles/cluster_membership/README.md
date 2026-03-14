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

Nodes in both `linstor_controllers` and `linstor_satellites` are registered as `Combined`.
Nodes in only one group are registered as their respective type.

```yaml
# hosts.yaml
linstor_controllers:
  hosts:
    linstor-1:
      replication_ip: 10.0.0.1
    linstor-2:
      replication_ip: 10.0.0.2
linstor_satellites:
  hosts:
    linstor-1:
      replication_ip: 10.0.0.1
    linstor-2:
      replication_ip: 10.0.0.2
    linstor-3:
      replication_ip: 10.0.0.3
```

In this example, `linstor-1` and `linstor-2` appear in both groups and are registered as `Combined`.
`linstor-3` appears only in `linstor_satellites` and is registered as `Satellite`.

```yaml
- name: Register LINSTOR cluster membership
  hosts: linstor_controllers,linstor_satellites
  any_errors_fatal: true
  become: true
  tasks:
    - name: Register LINSTOR nodes
      ansible.builtin.import_role:
        name: linbit.linstor.cluster_membership
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
