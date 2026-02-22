cluster_init
============

Convenience role that installs LINSTOR cluster components and registers cluster membership based on inventory group membership.
Optionally configures LINBIT package repositories before installation.
Runs `satellite_install` on nodes in `linstor_satellites`, `controller_install` on nodes in `linstor_controllers`, then `cluster_membership` on all: allowing the full cluster to be installed and registered with a single role against the entire inventory.

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
| `cluster_init_customer_repo` | `true` | Configure LINBIT customer repo before installation |
| `cluster_init_public_repo` | `false` | Configure LINBIT public repo before installation (when true, disables `cluster_init_customer_repo`) |
| `cluster_init_linstor_gateway` | `false` | Also install LINSTOR Gateway on the cluster |

See also `linbit.linstor.satellite_install`, `linbit.linstor.controller_install`, and `linbit.linstor.cluster_membership` for their available variables.

Dependencies
------------

`linbit.linstor.satellite_install`, `linbit.linstor.controller_install`, `linbit.linstor.cluster_membership`

Optional: `linbit.common.customer_repo`, `linbit.common.public_repo` (included dynamically based on variables)

Example Playbook
----------------

```yaml
- name: Deploy LINSTOR
  hosts: linstor_cluster
  become: true
  tasks:
    - name: Install and initialize LINSTOR
      vars:
        cluster_init_customer_repo: true # Set by default in defaults/main.yml
      ansible.builtin.import_role:
        name: linbit.linstor.cluster_init
```

To use the LINBIT public repo instead of the customer portal (for example, on Proxmox).
Setting `cluster_init_public_repo: true` automatically disables `cluster_init_customer_repo`, so only one repo type is configured:

```yaml
- name: Deploy LINSTOR
  hosts: linstor_cluster
  become: true
  tasks:
    - name: Install and initialize LINSTOR
      vars:
        cluster_init_public_repo: true
      ansible.builtin.import_role:
        name: linbit.linstor.cluster_init
```

To install LINSTOR Gateway as part of a new LINSTOR cluster deployment, set `cluster_init_linstor_gateway: true`:

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

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
