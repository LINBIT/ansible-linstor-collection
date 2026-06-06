#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: key_value_store_info
short_description: Query a LINSTOR key-value store
version_added: "1.0.0"
description:
  - Returns the entries of a LINSTOR key-value store instance.
  - Read-only; C(changed) is always C(false).
  - O(name) is required; this module returns a single key-value store.
options:
  name:
    description: Name of the key-value store instance to query.
    type: str
    required: true
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
  - module: linbit.linstor.key_value_store
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Query a key-value store
  linbit.linstor.key_value_store_info:
    name: my-kvs
  register: kvs_state
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Show the stored key-value entries
  ansible.builtin.debug:
    var: kvs_state.entries
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
name:
  description: Key-value store instance name.
  type: str
  returned: always
exists:
  description: Whether the key-value store exists and has entries.
  type: bool
  returned: always
entries:
  description: Key-value pairs stored in the instance.
  type: dict
  returned: always
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)


def get_kv_entries(lin, name):
    """Get key-value store entries for an instance. Returns dict."""
    kv = lin.keyvaluestore_list(name)
    if hasattr(kv, 'properties') and kv.properties:
        return dict(kv.properties)
    return {}


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params['name']

    lin = get_linstor_connection(module)

    try:
        current_entries = get_kv_entries(lin, name)
        if not current_entries:
            module.exit_json(changed=False, name=name, exists=False, entries={})
        module.exit_json(changed=False, name=name, exists=True,
                         entries=current_entries)
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying key-value store '%s': %s" % (name, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
