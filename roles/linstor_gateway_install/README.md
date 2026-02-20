linstor_gateway_install
=======================

Install the `linstor-gateway` binary and service.

Installs the `linstor-gateway` daemon (via package manager or GitHub release), deploys its configuration, opens firewall port `8337/tcp`, and starts the service.

On satellite nodes, also installs satellite-side components via `linbit.linstor.linstor_gateway_satellite` (NFS/iSCSI resource agents, DRBD Reactor, supplemental packages).
Standalone controllers receive the `linstor-gateway` binary only.

By default, satellite related components are installed on all `linstor_satellites`.
In larger clusters, where LINSTOR Gateway resources might be restricted to a small subset of nodes, define hosts as members of the `linstor_gateway_satellites` group to restrict installation to those nodes only.

Requirements
------------

The following inventory groups must be defined:

| Group | Description |
|---|---|
| `linstor_controllers` | Controller nodes (`linstor-gateway` binary only) |
| `linstor_satellites` | All satellite nodes |
| `linstor_gateway_satellites` | (optional) Satellites to install LINSTOR Gateway components on; falls back to all `linstor_satellites` if not defined |

Role Variables
--------------

| Variable | Default | Description |
|---|---|---|
| `linstor_gateway_github_binary` | latest amd64 release | GitHub download URL, used as fallback when package is unavailable |

Dependencies
------------

No formal role dependencies.
On satellite nodes, conditionally includes `linbit.linstor.linstor_gateway_satellite`.

Example Playbook
----------------

To install LINSTOR Gateway as part of a new LINSTOR cluster deployment, set `cluster_init_linstor_gateway: true` when using the `linbit.linstor.cluster_init` role:

```yaml
- name: Deploy LINSTOR
  hosts: linstor_cluster
  become: true
  tasks:
    - name: Install and initialize LINSTOR with LINSTOR Gateway
      vars:
        cluster_init_linstor_gateway: true
      ansible.builtin.import_role:
        name: linbit.linstor.cluster_init
```

Standalone LINSTOR Gateway install against an existing LINSTOR cluster:

```yaml
- name: Install LINSTOR Gateway
  hosts: all
  become: true
  tasks:
    - name: Install LINSTOR Gateway
      ansible.builtin.import_role:
        name: linbit.linstor.linstor_gateway_install
```

To use SCST as the iSCSI target backend, add `linstor_gateway_scst: true`:

```yaml
- name: Install LINSTOR Gateway
  hosts: all
  become: true
  tasks:
    - name: Install LINSTOR Gateway
      vars:
        linstor_gateway_scst: true
      ansible.builtin.import_role:
        name: linbit.linstor.linstor_gateway_install
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
