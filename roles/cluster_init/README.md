cluster_init
============

Convenience role that deploys a complete LINSTOR cluster with a single role call.
Includes the following roles in order:

1. `linbit.common.customer_repo` or `linbit.common.public_repo` (based on `cluster_init_repo_access`)
2. `linbit.linstor.satellite_install` (on `linstor_satellites` nodes)
3. `linbit.linstor.controller_install` (on `linstor_controllers` nodes)
4. `linbit.linstor.cluster_membership` (register all nodes)
5. `linbit.linstor.gateway_install` (when `cluster_init_linstor_gateway: true`)
6. `linbit.linstor.storage_pool` (when `cluster_init_deploy_storage: true`)
7. `linbit.linstor.ha_database` (when `cluster_init_ha_database: true`)

Steps 1 and 5-7 are optional and controlled by role variables.

Requirements
------------

The following inventory groups must be defined:

| Group | Description |
|---|---|
| `linstor_satellites` | Nodes to install the LINSTOR satellite on |
| `linstor_controllers` | Nodes to install the LINSTOR controller on |

Role Variables
--------------

| Variable | Default | Description |
|---|---|---|
| `cluster_init_repo_access` | `customer` | Repo access type: `customer` (LINBIT portal), `public` (Proxmox and open-source), or `none` (self-managed repos) |
| `cluster_init_linstor_gateway` | `false` | Also install LINSTOR Gateway on the cluster |
| `cluster_init_deploy_storage` | `false` | Create storage pools from `linstor_storage_pools` inventory variable |
| `cluster_init_ha_database` | `true` | Convert LINSTOR database to HA (requires `cluster_init_deploy_storage` and 2+ combined nodes) |

When `cluster_init_deploy_storage` is enabled, the role includes `linbit.linstor.storage_pool` which reads the `linstor_storage_pools` inventory variable.
See the `storage_pool` role README for the full variable reference.

When `cluster_init_ha_database` is enabled, the role includes `linbit.linstor.ha_database`.
Set `ha_database_pool` in the playbook vars to specify which storage pool to use.
See the `ha_database` role README for additional variables.

See also `linbit.linstor.satellite_install`, `linbit.linstor.controller_install`, and `linbit.linstor.cluster_membership` for their available variables.

Dependencies
------------

`linbit.linstor.satellite_install`, `linbit.linstor.controller_install`, `linbit.linstor.cluster_membership`

Optional: `linbit.common.customer_repo`, `linbit.common.public_repo`, `linbit.linstor.storage_pool`, `linbit.linstor.ha_database`, `linbit.linstor.gateway_install` (included dynamically based on variables)

Example Playbook
----------------

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
        cluster_init_deploy_storage: true # when true ha_database is deployed
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

Without `cluster_init`, the equivalent playbook calls each sub-role individually:

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
  tasks:
    - name: Configure LINBIT public repo
      tags:
        - linstor
        - linstor_registration
      ansible.builtin.include_role:
        name: linbit.common.public_repo
      when: cluster_init_repo_access == 'public'

    - name: Configure LINBIT customer repo
      tags:
        - linstor
        - linstor_registration
      ansible.builtin.include_role:
        name: linbit.common.customer_repo
      when: cluster_init_repo_access == 'customer'

    - name: Install LINSTOR satellite
      tags:
        - linstor
        - linstor_installation
      ansible.builtin.include_role:
        name: linbit.linstor.satellite_install
      when: inventory_hostname in groups['linstor_satellites']

    - name: Install LINSTOR controller
      tags:
        - linstor
        - linstor_installation
      ansible.builtin.include_role:
        name: linbit.linstor.controller_install
      when: inventory_hostname in groups['linstor_controllers']

    - name: Register LINSTOR cluster membership
      tags:
        - linstor
        - linstor_cluster_membership
      ansible.builtin.include_role:
        name: linbit.linstor.cluster_membership

    - name: Install LINSTOR Gateway
      tags:
        - linstor
        - linstor_installation
        - linstor_gateway
      ansible.builtin.include_role:
        name: linbit.linstor.gateway_install
      when: cluster_init_linstor_gateway | bool

    - name: Create LINSTOR storage pools
      tags:
        - linstor
        - linstor_storage_pool
      ansible.builtin.include_role:
        name: linbit.linstor.storage_pool
      when:
        - cluster_init_deploy_storage | bool
        - inventory_hostname in groups['linstor_diskful_satellites']

    # Requires a configured storage pool
    - name: Convert LINSTOR database to HA
      tags:
        - linstor
        - linstor_ha_database
      ansible.builtin.include_role:
        name: linbit.linstor.ha_database
      when:
        - cluster_init_deploy_storage | bool
        - cluster_init_ha_database | bool
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
