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
| `linstor_client_config_file` | `~/.config/linstor/linstor-client.conf` | Path of the `linstor-client.conf` on the control node; LINSTOR modules that run on the control node read the same path |
| `client_install_local_config` | `true` unless `linstor_api_delegate` points at another host | Render the `linstor-client.conf` on the control node, set by `linstor_client_config_file` |
| `client_install_force_reconfigure` | `false` | Force the configure phase to re-run even when the package install is unchanged, re-asserts `/etc/linstor/` and re-templates `linstor-client.conf` (drift correction) |

The role always writes the full list of controller addresses to `linstor-client.conf`.
The LINSTOR client walks the list and connects to the first responder, so HA failover works without a virtual IP.
If `linstor_ha_vip` is set in inventory it is used by the `ha_database` role to wire up a floating IP for the LINSTOR GUI and external API users, but the client config does not consume it.

The token-bearing configs are written by the `configure-control-node` task (the Ansible control node's `linstor_client_config_file`) and the `configure-controller-node` task (a controller's `/root/.config/linstor/linstor-client.conf`), both at mode `0600`.
The `auth_init` role drives both.
The control node render preserves an `auth-token` already present in the file when the file shares at least one controller address with the inventory, so re-runs and controller additions do not strip a saved token and a cluster at other addresses never inherits it.
The system-wide `/etc/linstor/linstor-client.conf` written by `configure-client` never carries the token and stays a stock `0644` file.

## Control node configuration

By default the `linstor-client.conf` on the control node lives at `~/.config/linstor/linstor-client.conf`, the per-user location the `linstor` CLI and python-linstor read.
Every inventory run from the same control node writes that one file, so two clusters managed from one machine, or two playbook runs in parallel, overwrite each other's controller list and token.

Set `linstor_client_config_file` in inventory to give each cluster its own file:

```yaml
all:
  vars:
    linstor_client_config_file: "{{ inventory_dir }}/.linstor/linstor-client.conf"
    ssl_init_local_dir: "{{ inventory_dir }}/.linstor/ssl"
```

The collection's action plugin passes the same path to every `linbit.linstor` module that runs on the control node as its `config_file` option, so no task needs its own setting.
`ssl_init_local_dir` does the same for the `ssl_init` CA and certificates.
The directory holds an auth token and a CA private key, so keep it out of version control.
Because it is ignored, `git clean -x` deletes it, and with it the only control node copy of the token and the CA key.
When moving an existing token-authenticated cluster to a new path, copy its current `linstor-client.conf` there first, because the role does not carry the token over from the old location.

The role writes this file only when the LINSTOR modules run on the control node.
When `linstor_api_delegate` points at a controller node, `client_install_local_config` defaults to `false` and the role writes nothing on the control node.
Setting `client_install_local_config: false` without delegating leaves the modules without a saved token or CA file, which only works against a cluster without token authentication or HTTPS.

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
