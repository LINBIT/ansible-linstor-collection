#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: controller_info
short_description: Query LINSTOR controller properties
version_added: "1.0.0"
description:
  - Returns the cluster-wide LINSTOR controller properties.
  - Read-only; C(changed) is always C(false).
  - The controller is a cluster-wide singleton, so this module takes no
    filter and returns a single properties dict.
options:
  controllers:
    description:
      - Comma-separated list of LINSTOR controller URIs.
      - If omitted, reads from C(LS_CONTROLLERS) env, then
        C(/etc/linstor/linstor-client.conf), then falls back to
        C(linstor://localhost).
    type: str
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
  - This module issues API calls via C(python-linstor) to the LINSTOR controller.
  - "For cluster-wide tasks use C(run_once=true) or a single-host play such as C(hosts: linstor_controllers[0])."
seealso:
  - module: linbit.linstor.controller
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Query controller properties
  linbit.linstor.controller_info:
  register: controller_state
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Show the cluster-wide auto-quorum policy
  ansible.builtin.debug:
    var: controller_state.properties['DrbdOptions/auto-quorum']
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
properties:
  description: Cluster-wide controller properties.
  type: dict
  returned: always
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)


def get_controller_props(lin):
    """Get the current controller properties as a dict."""
    result = lin.controller_props()
    if isinstance(result, list) and result:
        item = result[0]
        if hasattr(item, 'properties') and item.properties:
            return dict(item.properties)
    return {}


def main():
    argument_spec = linstor_argument_spec()

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    lin = get_linstor_connection(module)

    try:
        module.exit_json(changed=False, properties=get_controller_props(lin))
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying controller properties: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
