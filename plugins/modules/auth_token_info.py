#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: auth_token_info
short_description: Query LINSTOR auth tokens
version_added: "1.0.0"
description:
  - Returns the list of active LINSTOR REST API auth tokens.
  - Read-only; C(changed) is always C(false).
  - Returns both user tokens and satellite tokens; filter on the
    C(is_user_token) field to separate them.
  - Revoked tokens are not returned.
options:
  controllers:
    description:
      - Comma-separated list of LINSTOR controller URIs.
      - If omitted, reads from C(LS_CONTROLLERS) env, then
        C(/etc/linstor/linstor-client.conf), then falls back to
        C(linstor://localhost).
    type: str
  auth_token:
    description:
      - LINSTOR auth token for clusters with token authentication enabled.
      - If omitted, reads C(auth-token) from C(linstor-client.conf) (user
        configuration overriding system configuration), then falls back to
        C(/var/lib/linstor.d/auth.json) on satellite nodes.
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
  - Raw token values are never returned; LINSTOR stores only token hashes.
  - Requires LINSTOR 1.34.0 or later on the controller and a python-linstor
    release with token authentication support on the play host.
seealso:
  - module: linbit.linstor.auth_init
  - module: linbit.linstor.auth_token
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Query all auth tokens
  linbit.linstor.auth_token_info:
  register: all_tokens
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Show user tokens only
  ansible.builtin.debug:
    msg: "{{ all_tokens.tokens | selectattr('is_user_token') | list }}"
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
tokens:
  description: List of active auth tokens.
  type: list
  elements: dict
  returned: always
  contains:
    id:
      description: Numeric token ID.
      type: int
    description:
      description: Description label.
      type: str
    created_at:
      description: Creation timestamp as reported by the controller.
      type: str
    is_active:
      description: Whether the token is currently accepted.
      type: bool
    is_user_token:
      description: C(true) for user tokens, C(false) for satellite tokens.
      type: bool
    ip_filter:
      description: IP address restriction, if set.
      type: str
    expires_at:
      description: Expiry timestamp, if set.
      type: str
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)


def main():
    argument_spec = linstor_argument_spec()

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    lin = get_linstor_connection(module)

    try:
        result = lin.controller_list_auth_tokens()
        tokens = []
        if isinstance(result, list) and result:
            data = result[0].data_v1
            if isinstance(data, dict):
                tokens = data.get('list', [])
        module.exit_json(changed=False, tokens=tokens)
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying auth tokens: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
