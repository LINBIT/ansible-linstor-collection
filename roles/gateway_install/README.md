# gateway_install

Install the `linstor-gateway` binary and service.

The role installs the `linstor-gateway` daemon (via package manager or GitHub release), deploys its configuration, opens firewall port `8337/tcp`, and starts the service.

On satellite nodes, the role also installs satellite-side components via `linbit.linstor.gateway_satellite` (NFS/iSCSI resource agents, DRBD Reactor, supplemental packages).
Standalone controllers receive the `linstor-gateway` binary only.

By default, satellite related components are installed on all `linstor_satellites`.
In larger clusters, where LINSTOR Gateway resources might be restricted to a small subset of nodes, define hosts as members of the `linstor_gateway_satellites` group to restrict installation to those nodes only.

## Requirements

The following inventory groups must be defined:

| Group | Description |
|---|---|
| `linstor_controllers` | Controller nodes (`linstor-gateway` binary only) |
| `linstor_satellites` | All satellite nodes |
| `linstor_gateway_satellites` | (optional) Satellites to install LINSTOR Gateway components on; falls back to all `linstor_satellites` if not defined |

## Role variables

| Variable | Default | Description |
|---|---|---|
| `gateway_install_package_state` | `present` | Package state for `linstor-gateway`; set `latest` to upgrade |
| `gateway_install_from_github` | `false` | Skip the package manager and install the latest release binary from GitHub; useful when the package repositories lag behind an upstream release |
| `gateway_install_firewall_rules` | `true` | Manage firewall rules for LINSTOR Gateway ports; set `false` to skip |
| `gateway_install_firewall_ports` | `8337/tcp` | Ports to open in firewalld or UFW for LINSTOR Gateway |
| `gateway_install_force_reconfigure` | `false` | Force the configure phase to re-run even when the package install is unchanged; also re-runs `gateway_satellite` on satellites (drift correction) |
| `linstor_api_delegate` | `localhost` | Delegation target for LINSTOR API tasks; override to a cluster node (for example `{{ groups['linstor_controllers'][0] }}`) when the Ansible control node cannot directly reach the LINSTOR controller API endpoint |

## Controller REST endpoint

The `controllers` list in `linstor-gateway.toml` has to name the scheme and port the controller actually serves.
The role writes `https://<address>:3371` when the REST API runs over HTTPS and `http://<address>:3370` otherwise.

HTTPS applies when `linstor_ssl` is set for a cluster initialized with [`ssl_init`](../ssl_init/README.md), or when the controller has token authentication enabled, which turns on auto-HTTPS unless `auth_init_no_https` was set during [`auth_init`](../auth_init/README.md).
Token authentication is auto-detected from the controller, and `gateway_satellite_token_auth` forces it either way.

Plain HTTP against a token-authenticated controller does not work.
The controller answers port 3370 with a redirect to the HTTPS endpoint, and the daemon's Go client drops the `Authorization` header across the scheme and port change, so every LINSTOR Gateway operation fails with a misleading `404 Not Found`.

## Token authentication

On a token-authenticated cluster the role adds a `token_file` key to the `[linstor]` section, which `linstor-gateway` 2.3.0 and later read natively.
It points at `/var/lib/linstor.d/auth.json` when the controller has already distributed a satellite token to the node, and otherwise at the dedicated gateway token that [`gateway_satellite`](../gateway_satellite/README.md) creates at `/etc/linstor-gateway/auth-token`.
Either file works, because `linstor-gateway` accepts a token file containing the bare token or the JSON that `auth.json` stores it in.
The role never writes the `token` key, so the two can never be set at the same time, which `linstor-gateway` rejects.

The key is left out entirely on a node that gets neither file, which is the standalone controller case, because `linstor-gateway server` exits when `token_file` names a file it cannot read.
Give such a node a token by adding it to `linstor_gateway_satellites`, or point `token_file` at a token of your own.

Earlier `linstor-gateway` releases ignore `token_file` and fail against a token-authenticated controller.

## Dependencies

No formal role dependencies.
On satellite nodes, conditionally includes `linbit.linstor.gateway_satellite`.

## Example playbook

To install LINSTOR Gateway as part of a new LINSTOR cluster deployment, set `cluster_init_linstor_gateway: true` when using the `linbit.linstor.cluster_init` role:

```yaml
- name: Deploy LINSTOR
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install and initialize LINSTOR with LINSTOR Gateway
      ansible.builtin.import_role:
        name: linbit.linstor.cluster_init
      vars:
        cluster_init_linstor_gateway: true
```

Standalone LINSTOR Gateway install against an existing LINSTOR cluster:

```yaml
- name: Install LINSTOR Gateway
  hosts: linstor_satellites
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install LINSTOR Gateway
      ansible.builtin.import_role:
        name: linbit.linstor.gateway_install
```

To use SCST as the iSCSI target backend, add `gateway_satellite_scst: true`:

```yaml
- name: Install LINSTOR Gateway
  hosts: linstor_satellites
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install LINSTOR Gateway
      ansible.builtin.import_role:
        name: linbit.linstor.gateway_install
      vars:
        gateway_satellite_scst: true
```

## License

MIT

## Author information

[LINBIT](https://linbit.com)
