# ha_database

Configure highly available LINSTOR database storage using DRBD replication and DRBD Reactor.

This role works for both new deployments and existing production clusters.
It migrates the LINSTOR database onto a DRBD resource replicated across 2-3 combined controller and satellite nodes.
DRBD Reactor manages automatic failover of the controller service.

The role is idempotent: it checks the `Aux/ClusterIsHA` controller property and skips if the conversion has already been completed.
It also skips when the inventory contains fewer than 2 combined nodes or fewer than 3 total satellites.
This makes it safe to include in deployment playbooks that run repeatedly, even for standalone controller clusters.

## Requirements

The role requires 2-3 Combined LINSTOR nodes: hosts that are members of both `linstor_controllers` and `linstor_diskful_satellites` inventory groups.
The play can target any host group that includes the combined nodes, such as `linstor_cluster`.
The role determines which nodes to act on from inventory groups, not from the play's host list.

The total LINSTOR cluster must have at least 3 satellites (for quorum).
In a 2-node combined setup, LINSTOR auto-quorum adds a diskless TieBreaker on another satellite automatically.

DRBD Reactor is installed automatically if not already present via a dynamic `include_role` of `linbit.drbd_reactor.reactor_install`.

## Role Variables

See `defaults/main.yml`.

| Variable | Default | Description |
|---|---|---|
| `ha_database_pool` | `""` | Storage pool for the HA database resource; empty lets LINSTOR auto-select (set explicitly when nodes have multiple pools) |
| `ha_database_rg` | `linstor-db-grp` | LINSTOR resource group name |
| `ha_database_res` | `linstor_db` | LINSTOR resource name |
| `ha_database_res_size` | `200M` | Size of the HA database resource |
| `ha_database_max_controllers` | `3` | Maximum number of combined controller nodes allowed |
| `ha_database_allow_2_replica` | `false` | Allow 2-combined + tiebreaker topology when 3+ diskful satellites exist; the role otherwise fails and asks for a third combined node (ignored with only 2 diskful satellites) |
| `ha_database_vip` | `""` | Virtual IP for the HA controller, for example `10.0.0.100/24` (see [HA controller VIP](#ha-controller-vip)) |
| `ha_database_drbd_options` | *(see defaults)* | DRBD options applied to the resource group |
| `linstor_api_delegate` | `localhost` | Delegation target for LINSTOR API tasks; override to a cluster node (for example `{{ groups['linstor_controllers'][0] }}`) when the control node cannot reach the controller directly |

## HA controller VIP

`ha_database_vip` floats an IPaddr2 resource with the active controller, for example `10.0.0.100/24` (defaults to `/24` if no CIDR is given).
The IP is stored as the `Aux/ha_database_vip` controller property so `client_install` discovers it on subsequent runs.
When set, the role installs the IPaddr2 OCF resource agent through `linbit.drbd_reactor.resource_agents_upstream` (narrowed to just `IPaddr2`) on combined nodes where it is not already present.

## Dependencies

No hard role dependencies.
`linbit.drbd_reactor.reactor_install` is included dynamically if DRBD Reactor is not present.

## Example Playbook

```yaml
- name: LINSTOR HA database conversion
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    - name: Convert LINSTOR database to HA
      ansible.builtin.import_role:
        name: linbit.linstor.ha_database
      vars:
        # If ha_database_pool is omitted, LINSTOR auto-selects from available pools
        ha_database_pool: my-pool
```

With a floating VIP for the controller:

```yaml
- name: LINSTOR HA database conversion
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    - name: Convert LINSTOR database to HA
      ansible.builtin.import_role:
        name: linbit.linstor.ha_database
      vars:
        ha_database_pool: my-pool
        ha_database_vip: "10.0.0.100/24"
```

## License

MIT

## Author Information

[LINBIT](https://linbit.com)
