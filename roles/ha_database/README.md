ha_database
===========

Configure highly available LINSTOR database storage using DRBD replication and DRBD Reactor.

This role works for both new deployments and existing production clusters.
It migrates the LINSTOR database onto a DRBD resource replicated across 2-3 combined controller and satellite nodes.
DRBD Reactor manages automatic failover of the controller service.

The role is idempotent: it checks the `Aux/ClusterIsHA` controller property and skips if the conversion has already been completed.
It also skips when the inventory contains fewer than 2 combined nodes or fewer than 3 total satellites.
This makes it safe to include in deployment playbooks that run repeatedly, even for standalone controller clusters.

Requirements
------------

The role requires 2-3 Combined LINSTOR nodes: hosts that are members of both `linstor_controllers` and `linstor_diskful_satellites` inventory groups.
The play can target any host group that includes the combined nodes, such as `linstor_cluster`.
The role determines which nodes to act on from inventory groups, not from the play's host list.

The total LINSTOR cluster must have at least 3 satellites (for quorum).
In a 2-node combined setup, the role places a diskless TieBreaker on a third satellite node chosen at random.
Set `ha_database_tiebreaker_node` to pin the TieBreaker to a specific satellite.

DRBD Reactor is installed automatically if not already present via a dynamic `include_role` of `linbit.drbd_reactor.reactor_install`.

Role Variables
--------------

See `defaults/main.yml`.

| Variable | Default | Description |
|---|---|---|
| `ha_database_pool` | `""` | Storage pool for the HA database resource. When empty, LINSTOR auto-selects from available pools. Set explicitly when nodes have multiple storage pools. |
| `ha_database_rg` | `linstor-db-grp` | LINSTOR resource group name |
| `ha_database_res` | `linstor_db` | LINSTOR resource name |
| `ha_database_res_size` | `200M` | Size of the HA database resource |
| `ha_database_max_controllers` | `3` | Maximum number of combined controller nodes allowed |
| `ha_database_tiebreaker_node` | `""` | Pin the TieBreaker to a specific satellite (inventory hostname); only used with 2 combined nodes, random if empty |
| `ha_database_drbd_options` | *(see defaults)* | DRBD options applied to the resource group |
| `short_hostnames` | auto-detected | Use short hostnames (true on Proxmox VE) |
| `linstor_hostname` | auto-detected | LINSTOR node name: `inventory_hostname_short` on Proxmox VE, `inventory_hostname` otherwise |

Dependencies
------------

No hard role dependencies.
`linbit.drbd_reactor.reactor_install` is included dynamically if DRBD Reactor is not present.

Example Playbook
----------------

Using the collection playbook wrapper (recommended for stack playbooks):

```yaml
- name: LINSTOR HA database conversion
  import_playbook: linbit.linstor.ha_controller.yaml
  tags:
    - linstor
    - linstor_ha_controller
```

Using the role directly in a play:

```yaml
- name: LINSTOR HA database conversion
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    - name: Convert LINSTOR database to HA
      ansible.builtin.import_role:
        name: linbit.linstor.ha_database
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
