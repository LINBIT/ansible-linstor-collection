linstor_gateway_install
=======================

Install the `linstor-gateway` binary and service.

Installs the `linstor-gateway` daemon (via package manager or GitHub release),
deploys its configuration, opens firewall port `8337/tcp`, and starts the service.

On satellite nodes (members of `linstor_satellites`), also installs satellite-side
components via `linbit.linstor.linstor_gateway_satellite` (NFS/iSCSI resource agents,
DRBD Reactor, supplemental packages). Standalone controllers receive the binary only.

Requirements
------------

The following inventory groups must be defined:

| Group | Description |
|---|---|
| `linstor_controllers` | Controller nodes (receive the binary) |
| `linstor_satellites` | Satellite nodes (also receive satellite-side components) |

Role Variables
--------------

| Variable | Default | Description |
|---|---|---|
| `linstor_gw_github_release` | latest amd64 release | GitHub download URL, used as fallback when package is unavailable |

Dependencies
------------

No formal role dependencies.
On satellite nodes, conditionally includes `linbit.linstor.linstor_gateway_satellite`.

Example Playbook
----------------

```yaml
- name: Install LINSTOR Gateway
  hosts: all
  become: true
  tasks:
    - ansible.builtin.import_role:
        name: linbit.linstor.linstor_gateway_install
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
