#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: encryption_info
short_description: Query LINSTOR encryption status
version_added: "1.0.0"
description:
  - Returns the cluster-wide LINSTOR master passphrase (encryption) status.
  - Read-only; C(changed) is always C(false).
  - The master passphrase is a cluster-wide singleton, so this module takes no
    filter and returns a single status value.
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
  - module: linbit.linstor.encryption
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Query encryption status
  linbit.linstor.encryption_info:
  register: crypt_state
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Fail unless the master passphrase is unlocked
  ansible.builtin.assert:
    that: crypt_state.status == 'unlocked'
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
status:
  description:
    - Master passphrase status.
    - One of C(unset) (no passphrase configured), C(locked) (configured but
      not entered for this controller session), or C(unlocked).
  type: str
  returned: always
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)


def get_crypt_status(lin):
    """Get the current encryption passphrase status.

    Returns 'unset', 'locked', or 'unlocked'.
    """
    result = lin.crypt_status()
    if isinstance(result, list) and result:
        item = result[0]
        if hasattr(item, 'status'):
            return item.status
        if isinstance(item, str):
            return item
    if isinstance(result, str):
        return result
    return 'unset'


def main():
    argument_spec = linstor_argument_spec()

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    lin = get_linstor_connection(module)

    try:
        module.exit_json(changed=False, status=get_crypt_status(lin))
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying encryption status: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
