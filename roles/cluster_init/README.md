# cluster_init

Deploy a complete LINSTOR cluster with a single role call.
The role includes the following roles in order:

1. `linbit.common.customer_repo` or `linbit.common.public_repo` (based on `cluster_init_repo_access`)
2. `linbit.linstor.satellite_install` (on `linstor_satellites` nodes)
3. `linbit.linstor.controller_install` (on `linstor_controllers` nodes)
4. `linbit.linstor.ssl_init` (when `cluster_init_ssl: true`)
5. `linbit.linstor.cluster_membership` (register all nodes)
6. `linbit.linstor.gateway_install` (when `cluster_init_linstor_gateway: true`)
7. `linbit.linstor.storage_pool` (when `cluster_init_deploy_storage: true`)
8. `linbit.linstor.ha_database` (when `cluster_init_ha_database: true`)

Steps 1, 4, 6, 7, and 8 are optional and controlled by role variables.
Steps 2, 3, and 5 always run.

## Requirements

The following inventory groups are used:

| Group | Description |
|---|---|
| `linstor_satellites` | Nodes to install the LINSTOR satellite on |
| `linstor_controllers` | Nodes to install the LINSTOR controller on |
| `linstor_diskful_satellites` | Optional child of `linstor_satellites` for inventory organization; reference it from a pool's `groups` key to scope placement |

## Role variables

| Variable | Default | Description |
|---|---|---|
| `cluster_init_repo_access` | `customer` | Repo access type: `customer` (LINBIT portal), `public` (Proxmox and open-source), or `none` (self-managed repos) |
| `cluster_init_linstor_gateway` | `false` | Also install LINSTOR Gateway on the cluster |
| `cluster_init_deploy_storage` | `false` | Create storage pools from `linstor_storage_pools` inventory variable |
| `cluster_init_ha_database` | `true` | Convert LINSTOR database to HA (requires `cluster_init_deploy_storage`, at least 2 combined controller+satellite nodes, and at least 3 total satellites) |
| `cluster_init_ssl` | `false` | Encrypt all LINSTOR communication (HTTPS REST API + satellite SSL) |
| `cluster_init_ssl_mtls` | `false` | Restrict REST API to clients with a valid certificate (requires `cluster_init_ssl`) |

When `cluster_init_deploy_storage` is enabled, the role includes `linbit.linstor.storage_pool` which reads the `linstor_storage_pools` inventory variable.
See the `storage_pool` role README for the full variable reference.

When `cluster_init_ha_database` is enabled, the role includes `linbit.linstor.ha_database`.
Set `ha_database_pool` in the playbook vars to specify which storage pool to use; when omitted, the role auto-selects from the diskful pools on the combined nodes.
See the `ha_database` role README for additional variables.

See also `linbit.linstor.satellite_install`, `linbit.linstor.controller_install`, and `linbit.linstor.cluster_membership` for their available variables.

## Dependencies

`linbit.linstor.satellite_install`, `linbit.linstor.controller_install`, `linbit.linstor.cluster_membership`

Optional: `linbit.common.customer_repo`, `linbit.common.public_repo`, `linbit.linstor.ssl_init`, `linbit.linstor.gateway_install`, `linbit.linstor.storage_pool`, `linbit.linstor.ha_database` (included dynamically based on variables)

## Example playbook

Minimal deployment (install and register only):

```yaml
- name: Deploy LINSTOR
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install and initialize LINSTOR
      ansible.builtin.import_role:
        name: linbit.linstor.cluster_init
      vars:
        cluster_init_repo_access: customer   # cluster_init default
```

Full deployment with LINSTOR Gateway, storage pools, and HA database:

```yaml
- name: Deploy LINSTOR
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install and initialize LINSTOR
      ansible.builtin.import_role:
        name: linbit.linstor.cluster_init
      vars:
        cluster_init_deploy_storage: true
        cluster_init_ha_database: true      # cluster_init default
        cluster_init_linstor_gateway: true
        cluster_init_repo_access: customer  # cluster_init default
```

Full deployment with SSL/TLS encryption:

```yaml
- name: Deploy LINSTOR
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install and initialize LINSTOR
      ansible.builtin.import_role:
        name: linbit.linstor.cluster_init
      vars:
        cluster_init_deploy_storage: true
        cluster_init_ha_database: true      # cluster_init default
        cluster_init_ssl: true
        cluster_init_repo_access: customer  # cluster_init default
```

This encrypts the REST API (HTTPS on port 3371) and all controller-to-satellite connections (SSL on port 3367).
See the `ssl_init` role README for additional variables such as certificate parameters and passwords.

To use the LINBIT public repo instead of the customer portal (for example, on Proxmox):

```yaml
- name: Deploy LINSTOR
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install and initialize LINSTOR
      ansible.builtin.import_role:
        name: linbit.linstor.cluster_init
      vars:
        cluster_init_deploy_storage: true
        cluster_init_ha_database: true      # cluster_init default
        cluster_init_repo_access: public
```

To skip repo configuration entirely (self-managed repos, building from source):

```yaml
- name: Deploy LINSTOR
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install and initialize LINSTOR
      ansible.builtin.import_role:
        name: linbit.linstor.cluster_init
      vars:
        cluster_init_repo_access: none
```

Restrict LINSTOR Gateway satellite components to a subset of nodes using the `linstor_gateway_satellites` group:

```yaml
# hosts.yaml
# cluster_init filters gateway satellite components to this group when defined,
# otherwise falls back to all linstor_satellites
linstor_gateway_satellites:
  hosts:
    linstor-1:
    linstor-2:
```

Only `linstor-1` and `linstor-2` receive NFS/iSCSI resource agents, DRBD Reactor, and other satellite-side components.
All other satellites are left untouched.

## Equivalent play without `cluster_init`

For reference, the expanded form below calls each sub-role individually and is functionally equivalent to a single `cluster_init` call.
Use this form when you want to insert custom tasks between roles, run a different subset, or pin per-role variables that `cluster_init` does not expose.
For everyday deployments, prefer `cluster_init`.

```yaml
- name: Deploy LINSTOR
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  vars:
    cluster_init_deploy_storage: false   # cluster_init default
    cluster_init_ha_database: true       # cluster_init default
    cluster_init_linstor_gateway: false  # cluster_init default
    cluster_init_repo_access: customer   # cluster_init default
    cluster_init_ssl: false              # cluster_init default
    cluster_init_ssl_mtls: false         # cluster_init default
  tasks:
    - name: Configure LINBIT public repo
      tags:
        - linstor
        - linstor_registration
      ansible.builtin.include_role:
        name: linbit.common.public_repo
        apply:
          tags:
            - linstor
            - linstor_registration
      when: cluster_init_repo_access == 'public'

    - name: Configure LINBIT customer repo
      tags:
        - linstor
        - linstor_registration
      ansible.builtin.include_role:
        name: linbit.common.customer_repo
        apply:
          tags:
            - linstor
            - linstor_registration
      when: cluster_init_repo_access == 'customer'

    - name: Install LINSTOR satellite
      tags:
        - linstor
        - linstor_installation
      ansible.builtin.include_role:
        name: linbit.linstor.satellite_install
        apply:
          tags:
            - linstor
            - linstor_installation
      when: inventory_hostname in groups['linstor_satellites']

    - name: Install LINSTOR controller
      tags:
        - linstor
        - linstor_installation
      ansible.builtin.include_role:
        name: linbit.linstor.controller_install
        apply:
          tags:
            - linstor
            - linstor_installation
      when: inventory_hostname in groups['linstor_controllers']

    - name: Configure LINSTOR SSL/TLS
      tags:
        - linstor
        - linstor_ssl
      ansible.builtin.include_role:
        name: linbit.linstor.ssl_init
        apply:
          tags:
            - linstor
            - linstor_ssl
      vars:
        ssl_init_https_mtls: "{{ cluster_init_ssl_mtls }}"
      when: cluster_init_ssl | bool

    - name: Register LINSTOR cluster membership
      tags:
        - linstor
        - linstor_cluster_membership
      ansible.builtin.include_role:
        name: linbit.linstor.cluster_membership
        apply:
          tags:
            - linstor
            - linstor_cluster_membership

    - name: Install LINSTOR Gateway
      tags:
        - linstor
        - linstor_installation
        - linstor_gateway
      ansible.builtin.include_role:
        name: linbit.linstor.gateway_install
        apply:
          tags:
            - linstor
            - linstor_installation
            - linstor_gateway
      when: cluster_init_linstor_gateway | bool

    - name: Create LINSTOR storage pools
      tags:
        - linstor
        - linstor_storage_pool
      ansible.builtin.include_role:
        name: linbit.linstor.storage_pool
        apply:
          tags:
            - linstor
            - linstor_storage_pool
      when: cluster_init_deploy_storage | bool

    # Requires a configured storage pool
    - name: Convert LINSTOR database to HA
      tags:
        - linstor
        - linstor_ha_database
      ansible.builtin.include_role:
        name: linbit.linstor.ha_database
        apply:
          tags:
            - linstor
            - linstor_ha_database
      when:
        - cluster_init_deploy_storage | bool
        - cluster_init_ha_database | bool
```

## License

MIT

## Author information

[LINBIT](https://linbit.com)
