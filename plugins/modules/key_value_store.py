#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: key_value_store
short_description: Manage LINSTOR key-value store
version_added: "0.10.0"
description:
  - Reads, sets, and deletes entries in a LINSTOR key-value store instance.
  - LINSTOR key-value stores are named dictionaries of string key-value pairs
    stored in the LINSTOR controller database.
  - Idempotent. Only entries that differ from the current state are modified.
  - When C(state=absent), deletes the entire key-value store instance by
    removing all entries.
options:
  name:
    description: Name of the key-value store instance.
    type: str
    required: true
  state:
    description: Desired state of the key-value store instance.
    type: str
    default: present
    choices: [present, absent]
  entries:
    description:
      - Dictionary of key-value pairs to set.
      - Values are converted to strings before storing.
    type: dict
    default: {}
  delete_entries:
    description: List of entry keys to remove from the store.
    type: list
    elements: str
    default: []
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
  - This module issues cluster-wide API calls via C(python-linstor) to the LINSTOR controller.
  - Requires the L(linstor-api-py,https://github.com/LINBIT/linstor-api-py) package
    (C(python-linstor)) on the play host.
  - "Use C(run_once=true) or a single-host play such as C(hosts: linstor_controllers[0])."
  - LINSTOR key-value stores are created implicitly when entries are set.
    There is no separate create operation.
  - "Due to historical implementation details, keys stored with a leading
    C(/) are returned without it. Avoid leading slashes in keys."
seealso:
  - name: LINSTOR User's Guide
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/
    description: LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Set entries in a key-value store
  linbit.linstor.key_value_store:
    name: cluster-metadata
    entries:
      environment: production
      region: us-east-1
      version: "2.1.0"
  run_once: true  # noqa: run-once[task]

- name: Read key-value store (no changes)
  linbit.linstor.key_value_store:
    name: cluster-metadata
  register: kv_result
  changed_when: false
  run_once: true  # noqa: run-once[task]

- name: Remove specific entries
  linbit.linstor.key_value_store:
    name: cluster-metadata
    delete_entries:
      - version
  run_once: true  # noqa: run-once[task]

- name: Delete entire key-value store
  linbit.linstor.key_value_store:
    name: cluster-metadata
    state: absent
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
name:
  description: Name of the key-value store instance.
  type: str
  returned: always
entries:
  description: Key-value store entries after the operation.
  type: dict
  returned: success
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
    check_api_response,
    compute_property_diff,
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
        state=dict(type='str', default='present', choices=['present', 'absent']),
        entries=dict(type='dict', default={}),
        delete_entries=dict(type='list', elements='str', default=[]),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params['name']
    state = module.params['state']
    entries = module.params['entries'] or {}
    delete_entries = module.params['delete_entries'] or []

    lin = get_linstor_connection(module)
    changed = False

    try:
        current_entries = get_kv_entries(lin, name)

        if state == 'absent':
            if not current_entries:
                module.exit_json(changed=False, name=name, entries={})
            if module.check_mode:
                module.exit_json(changed=True, name=name, entries={})
            # Delete all entries by passing them as delete_props
            all_keys = list(current_entries.keys())
            replies = lin.keyvaluestore_modify(
                name, delete_props=all_keys)
            check_api_response(module, replies,
                               'delete key-value store %s' % name)
            module.exit_json(changed=True, name=name, entries={})

        # state == 'present'
        entries_to_set, entries_to_delete = compute_property_diff(
            current_entries, entries, delete_entries)

        if not entries_to_set and not entries_to_delete:
            module.exit_json(changed=False, name=name,
                             entries=current_entries)

        if module.check_mode:
            final = dict(current_entries, **entries_to_set)
            for key in entries_to_delete:
                final.pop(key, None)
            module.exit_json(changed=True, name=name, entries=final)

        replies = lin.keyvaluestore_modify(
            name,
            property_dict=entries_to_set or None,
            delete_props=entries_to_delete or None,
        )
        check_api_response(module, replies,
                           'modify key-value store %s' % name)
        changed = True

        # Re-read entries after update
        final_entries = get_kv_entries(lin, name)

        module.exit_json(changed=changed, name=name,
                         entries=final_entries)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error managing key-value store '%s': %s" % (
                name, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
