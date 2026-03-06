#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: encryption
short_description: Manage LINSTOR encryption passphrase
version_added: "0.10.0"
description:
  - Creates, enters, or modifies the LINSTOR cluster-wide encryption passphrase.
  - This is a singleton module (no C(name) parameter) similar to
    M(linbit.linstor.controller).
  - C(state=created) creates a new passphrase. Idempotent, skips if a
    passphrase is already set (status is not C(unset)).
  - C(state=entered) enters (unlocks) the passphrase. Idempotent, skips
    if the passphrase is already unlocked.
  - C(state=modified) changes the passphrase. NOT idempotent, because the
    module cannot verify the current passphrase value.
options:
  state:
    description:
      - Desired encryption state.
      - C(created) sets the initial passphrase if none exists.
      - C(entered) unlocks the passphrase for use.
      - C(modified) changes the passphrase (requires O(old_passphrase)).
    type: str
    required: true
    choices: [created, entered, modified]
  passphrase:
    description: The encryption passphrase.
    type: str
    required: true
  old_passphrase:
    description:
      - The current passphrase.
      - Required when C(state=modified) to verify the old passphrase before
        setting a new one.
    type: str
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
  - Encryption status values are C(unset) (no passphrase configured),
    C(locked) (passphrase configured but not entered), and C(unlocked)
    (passphrase entered and active).
  - C(state=modified) is NOT idempotent. The module cannot detect whether
    the passphrase value has changed, so it always attempts modification.
seealso:
  - name: LINSTOR User's Guide - Encrypted Volumes
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-encrypted-volumes
    description: Encryption concepts and configuration in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Create the encryption passphrase
  linbit.linstor.encryption:
    state: created
    passphrase: "{{ vault_linstor_passphrase }}"
  run_once: true  # noqa: run-once[task]

- name: Enter the encryption passphrase (unlock)
  linbit.linstor.encryption:
    state: entered
    passphrase: "{{ vault_linstor_passphrase }}"
  run_once: true  # noqa: run-once[task]

- name: Change the encryption passphrase
  linbit.linstor.encryption:
    state: modified
    passphrase: "{{ vault_new_passphrase }}"
    old_passphrase: "{{ vault_old_passphrase }}"
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
status:
  description: Encryption status after the operation (unset, locked, or unlocked).
  type: str
  returned: always
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
    check_api_response,
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
    argument_spec.update(dict(
        state=dict(type='str', required=True,
                   choices=['created', 'entered', 'modified']),
        passphrase=dict(type='str', required=True, no_log=True),
        old_passphrase=dict(type='str', no_log=True),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ('state', 'modified', ['old_passphrase']),
        ],
    )

    state = module.params['state']
    passphrase = module.params['passphrase']
    old_passphrase = module.params.get('old_passphrase')

    lin = get_linstor_connection(module)

    try:
        status = get_crypt_status(lin)

        if state == 'created':
            if status != 'unset':
                module.exit_json(changed=False, status=status)
            if module.check_mode:
                module.exit_json(changed=True, status='locked')
            replies = lin.crypt_create_passphrase(passphrase)
            check_api_response(module, replies,
                               'create encryption passphrase')
            final_status = get_crypt_status(lin)
            module.exit_json(changed=True, status=final_status)

        elif state == 'entered':
            if status == 'unlocked':
                module.exit_json(changed=False, status=status)
            if status == 'unset':
                module.fail_json(
                    msg="No passphrase has been created yet. "
                        "Use state=created first.")
            if module.check_mode:
                module.exit_json(changed=True, status='unlocked')
            replies = lin.crypt_enter_passphrase(passphrase)
            check_api_response(module, replies,
                               'enter encryption passphrase')
            final_status = get_crypt_status(lin)
            module.exit_json(changed=True, status=final_status)

        elif state == 'modified':
            if status == 'unset':
                module.fail_json(
                    msg="No passphrase has been created yet. "
                        "Use state=created first.")
            if module.check_mode:
                module.exit_json(changed=True, status=status)
            replies = lin.crypt_modify_passphrase(old_passphrase, passphrase)
            check_api_response(module, replies,
                               'modify encryption passphrase')
            final_status = get_crypt_status(lin)
            module.exit_json(changed=True, status=final_status)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error managing encryption: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
