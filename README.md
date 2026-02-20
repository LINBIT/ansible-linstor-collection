# Ansible Collection - linbit.linstor

Installs and configures the full LINSTOR software-defined storage stack: controller, satellite, client, and LINSTOR Gateway (NFS/iSCSI HA).

## Roles

| Role | Description |
|---|---|
| `cluster_init` | Convenience role — installs satellite, controller, and registers cluster membership based on inventory group membership |
| `cluster_membership` | Registers LINSTOR nodes into the cluster (controller, combined, and satellite node types) |
| `satellite_install` | Installs the LINSTOR satellite and DRBD |
| `controller_install` | Installs the LINSTOR controller and GUI |
| `linstor_client` | Installs the LINSTOR CLI client |
| `linstor_gateway_install_client` | Installs the LINSTOR Gateway binary and service |
| `linstor_gateway_install_common` | Installs LINSTOR Gateway satellite-side components (NFS/iSCSI) |
| `scst_install` | Compiles and installs SCST iSCSI target (when `scst=true`) |

## Required Inventory Groups

The following inventory groups are used to control role targeting:

| Group | Description |
|---|---|
| `linstor_controllers` | Nodes to install the LINSTOR controller on |
| `linstor_satellites` | Nodes to install the LINSTOR satellite on |
| `linstor_cluster` | All LINSTOR cluster members (controllers + satellites) |

## Playbooks

| Playbook | Description |
|---|---|
| `cluster_storage.yaml` | Create LVM/ZFS storage pools from `physical_devices` |
| `ha_controller.yaml` | Convert LINSTOR DB to HA mode (2-3 controllers) |

## Dependencies

| Collection | Purpose |
|---|---|
| `linbit.drbd` | DRBD kernel module installation |
| `linbit.drbd_reactor` | DRBD Reactor for HA gateway resources |
| `linbit.common` | LINBIT repo setup |
| `ansible.posix` | firewalld management |
| `community.general` | filesystem, LVM, ZFS, and package management |
