# ha_controller_proxy

Deploy a dedicated TCP-passthrough HAProxy instance on each LINSTOR controller node.
The instance forwards LINSTOR API and GUI traffic to whichever node currently runs the active controller, so a client can reach the controller from any controller node.
This is an alternative to a floating virtual IP address for presenting a single controller endpoint, and it works in routed and cloud networks where a layer 2 virtual IP address is not possible.

## How it works

In an HA database cluster, DRBD Reactor runs `linstor-controller` only on the active node, so the controller ports (`3370` plain, `3371` SSL) are open on that node alone.
HAProxy listens on `4370` and `4371` on every controller node and forwards in TCP mode to the controller ports across the controller nodes.
A plain TCP connect health check marks only the active node as available, so traffic is always routed there.
TCP passthrough never inspects the bytes, so the same configuration serves both plain and SSL clusters, and a TLS handshake completes end to end between the client and the active controller.

The role runs its own `linstor-haproxy.service` with its own configuration file and PID file.
It does not modify the distribution `haproxy.service`, so it coexists with an existing HAProxy, such as one fronting a Proxmox VE GUI.

## Requirements

The `haproxy` package must be available in the repositories of each controller node.
On SUSE Linux Enterprise Server, `haproxy` ships in the High Availability Extension, which must be registered first.
openSUSE Leap includes `haproxy` in the standard repository.

On RHEL-family nodes with SELinux, the role enables the `haproxy_connect_any` boolean so HAProxy can connect to the controller ports.

## Role Variables

| Variable | Default | Description |
|---|---|---|
| `ha_controller_proxy_plain_port` | `4370` | Front-door port for plain HTTP traffic |
| `ha_controller_proxy_ssl_port` | `4371` | Front-door port for SSL HTTPS traffic |

Other settings (health-check timing, timeouts, and the service, config, and PID file paths) are internal constants in `vars/main.yml`. The LINSTOR controller ports it forwards to (`3370`/`3371`) are fixed, matching the rest of the collection.

## Controller resolution

The role forwards to the `linstor_controllers` group, the same group the rest of the collection uses.
When that group is undefined or has a single member, it falls back to the hosts the play targets, so a standalone run covers exactly the nodes it is called against.
The role does nothing when fewer than two controllers resolve, because a single controller is already a single endpoint and needs no proxy.

## SSL clusters

On an SSL cluster, the proxied connection presents the certificate of the active controller, not the certificate of the node that the client dialed.
A client that verifies the certificate hostname against its subject alternative name (SAN) fails unless every proxy endpoint address is present in each controller certificate.
The `linstor` client only verifies when a `cafile` is configured, so the cluster-node `linstor-client.conf` (which carries no `cafile`) reaches the proxy without trouble.
To support verifying clients, add every proxy endpoint address to each controller certificate SAN list in `ssl_init`.

## Dependencies

None.

## Example Playbook

```yaml
- name: Deploy the HA controller proxy
  hosts: linstor_controllers
  become: true
  tasks:
    - name: Deploy the HA controller proxy
      ansible.builtin.import_role:
        name: linbit.linstor.ha_controller_proxy
```

The `ha_database` role can deploy this role automatically after conversion when `ha_database_haproxy` is `true`.

## License

MIT
