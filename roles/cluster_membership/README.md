# cluster_membership

Register LINSTOR nodes into the cluster.
The role runs `linstor node create` for controller, combined (controller+satellite), and satellite node types.
Idempotent: nodes already registered are skipped.

## Requirements

The following inventory groups must be defined:

| Group | Description |
|---|---|
| `linstor_controllers` | Controller nodes (registers as `Controller` or `Combined`) |
| `linstor_satellites` | Satellite nodes (registers as `Satellite` or `Combined`) |

## Role variables

| Variable | Default | Description |
|---|---|---|
| `linstor_ip` | falls back to `replication_ip`, then `ansible_host` | LINSTOR node registration IP; becomes the `default` net interface |
| `replication_ip` | unset | Optional dedicated DRBD replication IP; when different from the registration IP, registers a `replication` net interface and sets node-level `PrefNic` |
| `cluster_membership_replication_netif` | `replication` | Name for the optional dedicated DRBD net interface |
| `cluster_membership_com_type` | unset | Override `Plain` or `SSL` for node registration; auto-detected from satellite/controller TOML when unset |
| `cluster_membership_port` | unset | Override registration port; defaults to standard LINSTOR ports based on node type and SSL state |
| `linstor_api_delegate` | `localhost` | Delegation target for LINSTOR API tasks; override to a cluster node (for example `{{ groups['linstor_controllers'][0] }}`) when the control node cannot reach the controller directly |

## Delegation

LINSTOR API tasks (`linbit.linstor.node`, `linbit.linstor.node_interface`) run on `linstor_api_delegate`, defaulting to `localhost`.
When the Ansible control node cannot reach the LINSTOR controller API endpoint directly (for example, an SSH jump host setup or a segmented management network), set:

```yaml
linstor_api_delegate: "{{ groups['linstor_controllers'][0] }}"
```

This routes the python-linstor calls through Ansible's SSH transport (which already handles ProxyJump) and lets the controller node make the API call locally.

## Network interfaces

Two deployment patterns are supported:

**Single-network** (default): set only `replication_ip` (or omit it and rely on `ansible_host`).
The node registers with that IP as the `default` interface, which carries both LINSTOR management traffic and DRBD replication.

**PrefNic-separated**: set `linstor_ip` to the address LINSTOR registers with, and `replication_ip` to a different address for DRBD replication.
The role registers a second net interface named `replication` (configurable via `cluster_membership_replication_netif`) and sets node-level `PrefNic` so DRBD routes through it.
LINSTOR management traffic stays on the `default` interface (`linstor_ip`).

The `replication` interface is registered as an IP-only NIC (no port or communication type).
This is intentional: it makes the interface a DRBD-only path (used via `PrefNic`), not a satellite-connection candidate.
LINSTOR's reconnect logic only considers interfaces with a satellite port and encryption type, so omitting them keeps the controller from autonomously moving the satellite connection onto the replication interface.

The role does not explicitly designate a satellite connection.
LINSTOR sets it automatically: every node has exactly one satellite connection, and at `linstor node create` time the `default` interface (the only candidate) gets the role.
For SSL clusters, `ssl_init` adds both `linstor_ip` and `replication_ip` to the node certificate's SAN list when both are set.

## Dependencies

None.

## Example playbook

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

## License

MIT

## Author information

[LINBIT](https://linbit.com)
