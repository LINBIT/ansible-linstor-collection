# client_install

Install and configure the LINSTOR client.

## Requirements

None.

## Role variables

See `defaults/main.yml`.

| Variable | Default | Description |
|---|---|---|
| `linstor_controller_addresses` | *(from inventory)* | Controller IPs for `linstor-client.conf`; auto-discovered from the `linstor_controllers` group `replication_ip` values |
| `linstor_client_auth_token` | `""` | Auth token for clusters with token authentication enabled, emitted as `auth-token =` in `linstor-client.conf` |
| `client_install_force_reconfigure` | `false` | Force the configure phase to re-run even when the package install is unchanged, re-asserts `/etc/linstor/` and re-templates `linstor-client.conf` (drift correction) |

The role always writes the full list of controller addresses to `linstor-client.conf`.
The LINSTOR client walks the list and connects to the first responder, so HA failover works without a virtual IP.
If `linstor_ha_vip` is set in inventory it is used by the `ha_database` role to wire up a floating IP for the LINSTOR GUI and external API users, but the client config does not consume it.

The token-bearing configs are written by the `configure-control-node` task (the Ansible control node's `~/.config/linstor/linstor-client.conf`) and the `configure-controller-node` task (a controller's `/root/.config/linstor/linstor-client.conf`), both at mode `0600`.
The `auth_init` role drives both.
The control-node render preserves an `auth-token` already present in the file, so re-runs do not strip a saved token.
The system-wide `/etc/linstor/linstor-client.conf` written by `configure-client` never carries the token and stays a stock `0644` file.

## Dependencies

None.

## Example playbook

```yaml
- name: Install LINSTOR client
  hosts: all
  any_errors_fatal: true
  become: true
  tasks:
    - ansible.builtin.import_role:
        name: linbit.linstor.client_install
```

## License

MIT

## Author information

[LINBIT](https://linbit.com)
