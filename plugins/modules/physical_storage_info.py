#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: physical_storage_info
short_description: Query unused block devices on LINSTOR satellites
version_added: "1.0.0"
description:
  - Returns the block devices that LINSTOR satellites report as unused and
    eligible for M(linbit.linstor.physical_storage), the same data as
    C(linstor physical-storage list).
  - Read-only; C(changed) is always C(false).
  - A satellite lists a device only when it is larger than 1 GiB, is a root
    device without partitions or other children, carries no file system or
    other C(blkid) signature, and is not a DRBD device.
options:
  node:
    description:
      - Node name to filter by.
      - If omitted, devices on all nodes are returned.
    type: str
extends_documentation_fragment:
  - linbit.linstor.connection
requirements:
  - python-linstor
notes:
  - "Recommended play structure: dedicate a play with a single host such
    as C(hosts: linstor_controllers[0]) and C(connection: local) for
    directly accessing the LINSTOR controller, or set C(delegate_to: localhost)
    on the task (or a wrapping C(block:)) when mixing into a multi-host play."
  - "The collection's action plugins force C(become: false) on the task
    automatically, so a parent play's C(become: true) does not bleed into
    the delegated call."
  - This module issues API calls through C(python-linstor) to the LINSTOR controller.
  - "For cluster-wide tasks use C(run_once=true) or a single-host play such as C(hosts: linstor_controllers[0])."
seealso:
  - module: linbit.linstor.physical_storage
  - name: LINSTOR User's Guide - Creating storage pools by using the physical storage command
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-physical-storage-command
    description: Eligibility rules and the physical storage commands in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: List unused devices on every satellite
  linbit.linstor.physical_storage_info:
  register: unused
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: List unused devices on one node
  linbit.linstor.physical_storage_info:
    node: node-1
  register: node1_unused
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Show the device paths LINSTOR expects
  ansible.builtin.debug:
    msg: "{{ node1_unused.physical_devices | map(attribute='device') | list }}"
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
physical_devices:
  description: Unused block devices, one entry per device and node, filtered by O(node) when supplied.
  type: list
  elements: dict
  returned: always
  contains:
    node:
      description: Node the device is attached to.
      type: str
    device:
      description: Device path as the satellite names it (for example C(/dev/sdb)).
      type: str
    size:
      description: Device size in bytes.
      type: int
    rotational:
      description: Whether the device is a rotational disk.
      type: bool
    model:
      description: Device model, or null if the satellite did not report one.
      type: str
    serial:
      description: Device serial number, or null if the satellite did not report one.
      type: str
    wwn:
      description: Device World Wide Name, or null if the satellite did not report one.
      type: str
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)


def list_physical_devices(lin, node=None):
    """Flatten the grouped physical storage list into one dict per device."""
    phys_list = lin.physical_storage_list()
    devices = []
    for group in (phys_list.physical_devices if phys_list else []):
        for node_name, entries in group.nodes.items():
            if node and node_name != node:
                continue
            for entry in entries:
                devices.append(dict(
                    node=node_name,
                    device=entry.device,
                    size=group.size,
                    rotational=group.rotational,
                    model=entry.model,
                    serial=entry.serial,
                    wwn=entry.wwn,
                ))
    return devices


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        node=dict(type='str'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    lin = get_linstor_connection(module)

    try:
        devices = list_physical_devices(lin, module.params['node'])
        module.exit_json(changed=False, physical_devices=devices)
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying physical storage: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
