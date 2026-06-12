# auth_init

Initialize bearer token authentication for the LINSTOR&reg; REST API.

LINSTOR 1.34.0 adds bearer-token authentication for the REST API, which also enables HTTPS with a self-signed certificate.
This role initializes it on a deployed cluster.
It enables token authentication, creates the first user token, and distributes a per-satellite token to `/var/lib/linstor.d/auth.json`.

The user token is saved where the collection needs it: the control-node `~/.config/linstor/linstor-client.conf` for the `linbit.linstor` modules, and the controller's `/root/.config/linstor/linstor-client.conf` for the `linstor` CLI.
Satellite nodes are left untouched; their CLI uses the satellite token automatically.

It gates on the controller's running version reported by the REST API, so it skips cleanly on controllers older than 1.34.0 and is safe to run by default.
Re-running is a no-op, and because LINSTOR reveals the user token only once, the saved configs are its only durable copy.

## Relationship to ssl_init

Token authentication supersedes mutual TLS (mTLS) for controlling REST API access.
Relying on mTLS to authenticate clients is no longer necessary.
The `ssl_init` role does not enable mTLS by default.
HTTPS enablement secures the client-to-controller REST API channel only.

Use `ssl_init` for:

- Wire-encrypting the controller-to-satellite channel (port 3367), which token authentication does not do.
- Providing CA-verifiable certificates for strict TLS clients.

When running this role on an already SSL-enabled cluster, set `auth_init_no_https: true` so it adds token authentication only and keeps the existing certificate, rather than overwriting it with a self-signed one.
The `cluster_init` role sets this automatically when `cluster_init_ssl` is enabled.

## Requirements

LINSTOR 1.34.0 or later on the cluster (older clusters skip through the version gate), and a python-linstor release with token authentication support on the Ansible control node.

Run after `cluster_membership`: satellite tokens are distributed to connected satellites.
Satellites that join later receive their token automatically on connect.

## Role variables

| Variable | Default | Description |
|---|---|---|
| `auth_init_description` | `ansible-managed` | Description label for the initial user token |
| `auth_init_no_https` | `false` | Skip the automatic HTTPS setup (use with `ssl_init`-managed HTTPS) |
| `auth_init_no_log` | `true` | Hide the raw token in task output |
| `auth_init_save_control_node` | `true` | Save the token to the control-node client config |
| `auth_init_save_controllers` | `true` | Save the token to the root user's `/root/.config/linstor/linstor-client.conf` on controllers |
| `auth_init_client_https` | `{{ linstor_ssl \| default(false) }}` | Render client configs with the `linstor+ssl://` scheme |
| `auth_init_local_cafile` | `ssl_init` CA path when HTTPS, else empty | CA file for the control-node client config |
| `auth_init_cluster_cafile` | `ssl_init` CA path when HTTPS, else empty | CA file for the controller-node client config |

The HTTPS variables only matter on clusters that ran `ssl_init` previously.
Authentication token initialization does not require `linstor-client.conf` configuration changes: the controller redirects a plain `linstor://` connection to HTTPS, and the client follows the redirect automatically.

## Dependencies

None.

## Example playbook

```yaml
- name: Secure the LINSTOR REST API with token authentication
  hosts: linstor_cluster
  become: true
  tasks:
    - name: Initialize LINSTOR token authentication
      ansible.builtin.import_role:
        name: linbit.linstor.auth_init
```

To rotate satellite tokens or manage user tokens after initialization, use the `linbit.linstor.auth_init`, `linbit.linstor.auth_token`, and `linbit.linstor.auth_token_info` modules directly.

## How it works

On connect, the module reads the controller's running version from the REST API (`/v1/controller/version`) and compares the major.minor prefix against 1.34.
A controller older than 1.34.0 is skipped with a warning and no change.

Initialization itself is a single controller API call (`controller auth init`) that enables token authentication, enables HTTPS, mints the first user token, and distributes a satellite token to every connected satellite.
The raw user token is returned exactly once by that call and is never retrievable again; LINSTOR stores only its hash.

The role captures that one-time token and writes it into the client configuration files so the rest of the collection keeps working:

- Control node: `~/.config/linstor/linstor-client.conf`, so `linbit.linstor` modules (which run delegated to the control node) authenticate automatically.
- Controller nodes: `/root/.config/linstor/linstor-client.conf`, the location native `linstor controller auth init` uses, so the `linstor` CLI on a controller keeps working.
- Satellite nodes: not touched. Each already has its own token in `/var/lib/linstor.d/auth.json`, which the `linstor` CLI reads automatically.

Token reading is handled once at the collection's base level (`module_utils`), mirroring the `linstor` CLI resolution order: the `auth_token` parameter, then `auth-token` in `linstor-client.conf`, then the satellite `auth.json` fallback.
Every module inherits this, so no module or role needs token-specific code.

On re-runs the module detects authentication is already enabled, skips the init call, and returns no token, so the role reuses the token already saved in the control-node config.
This keeps re-runs idempotent and the saved configs stable.

## Recovering from a lockout

Because the user token is shown only once, losing it while authentication is enabled locks you out of the API (every request returns HTTP 401).
This can happen if the saved client configs are deleted, or if initialization enabled authentication but did not save the token.
The role detects this state on a later run (authentication enabled, but no token available on the control node) and prints a warning with the two recovery paths below.

Recovery requires root (or equivalent) access to a node, and does not need the lost token:

- From any satellite, mint a fresh user token using the satellite's own token, which the CLI reads automatically from `/var/lib/linstor.d/auth.json`:

  ```sh
  linstor controller auth create recovery-admin
  ```

  Copy the printed token into the `[global]` section of `~/.config/linstor/linstor-client.conf` on the control node as `auth-token = <token>`, then re-run the role.

- Or disable token authentication on the controller, which requires brief controller downtime:

  ```sh
  systemctl stop linstor-controller
  /usr/share/linstor-server/bin/linstor-config disable-token-auth
  systemctl start linstor-controller
  ```

  Re-running the role then re-initializes authentication and saves a fresh token.

## License

MIT

## Author information

[LINBIT](https://linbit.com)
