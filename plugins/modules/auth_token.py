#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: auth_token
short_description: Manage LINSTOR auth tokens
version_added: "1.0.0"
description:
  - Creates, modifies, or revokes LINSTOR REST API auth tokens.
  - Requires token authentication to be initialized first; see
    M(linbit.linstor.auth_init).
  - Token descriptions are not unique in LINSTOR, so existing tokens are
    addressed by their numeric O(tokenid) only.
  - C(state=present) without O(tokenid) creates a new token. This is an
    event operation, NOT idempotent; every invocation creates another
    token and reports C(changed=true). The raw token value is returned
    once and never again.
  - C(state=present) with O(tokenid) modifies the existing token.
    Idempotent; the module compares O(description), O(ip_filter), and
    O(active) against the current token and only issues a modify call
    when something differs.
  - C(state=absent) revokes the token with O(tokenid). Idempotent;
    a missing or already revoked token reports C(changed=false).
    Revoked tokens are permanently invalidated.
options:
  state:
    description:
      - Desired token state.
    type: str
    default: present
    choices: [present, absent]
  tokenid:
    description:
      - Numeric ID of an existing token, as shown by
        M(linbit.linstor.auth_token_info).
      - Required for C(state=absent) and for modification.
      - Omit with C(state=present) to create a new token.
    type: int
  description:
    description:
      - Description label for the token.
      - Required when creating a token.
    type: str
  ip_filter:
    description:
      - Restrict the token to requests from this IP address.
      - LINSTOR accepts a single address, not a CIDR range.
      - Pass an empty string to remove an existing filter on modification.
    type: str
  expires_at:
    description:
      - Expiry date in ISO 8601 format, for example C(2026-12-31).
      - Only applied at creation time; LINSTOR does not support changing
        the expiry of an existing token.
    type: str
  active:
    description:
      - Whether the token is accepted by the controller.
      - Set C(false) to disable a token temporarily without revoking it.
      - Only applies to modification of an existing token.
    type: bool
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
  - Requires LINSTOR 1.34.0 or later on the controller and a python-linstor
    release with token authentication support on the play host.
seealso:
  - module: linbit.linstor.auth_init
  - module: linbit.linstor.auth_token_info
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Create a token for a monitoring system
  linbit.linstor.auth_token:
    description: monitoring-system
    ip_filter: 192.168.222.50
    expires_at: "2026-12-31"
  register: monitoring_token
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Disable a token temporarily
  linbit.linstor.auth_token:
    tokenid: 20
    active: false
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Remove the IP filter from a token
  linbit.linstor.auth_token:
    tokenid: 20
    ip_filter: ""
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Revoke a token
  linbit.linstor.auth_token:
    tokenid: 20
    state: absent
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
token:
  description:
    - The raw token value of a newly created token.
    - Shown once; LINSTOR stores only its hash.
  type: str
  returned: when a token was created
tokenid:
  description: Numeric ID of the created or managed token.
  type: int
  returned: when known
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
    check_api_response,
)


def list_tokens(lin):
    """Return the token list as a list of dicts."""
    result = lin.controller_list_auth_tokens()
    if isinstance(result, list) and result:
        data = result[0].data_v1
        if isinstance(data, dict):
            return data.get('list', [])
    return []


def find_token(tokens, tokenid):
    for token in tokens:
        if token.get('id') == tokenid:
            return token
    return None


def create_token(module, lin):
    description = module.params.get('description')
    if not description:
        module.fail_json(msg="description is required when creating a token.")
    if module.check_mode:
        module.exit_json(changed=True)
    replies = lin.controller_create_auth_token(
        description,
        ip_filter=module.params.get('ip_filter') or None,
        expires_at=module.params.get('expires_at') or None)
    check_api_response(module, replies, 'create auth token')
    token = ''
    for reply in replies:
        refs = getattr(reply, 'object_refs', None)
        if refs and 'token' in refs:
            token = refs['token']
            break
    tokens = list_tokens(lin)
    tokenid = max((t.get('id', 0) for t in tokens), default=None)
    module.exit_json(changed=True, token=token, tokenid=tokenid)


def modify_token(module, lin, current):
    tokenid = module.params['tokenid']
    changes = {}

    description = module.params.get('description')
    if description is not None and description != current.get('description'):
        changes['description'] = description

    ip_filter = module.params.get('ip_filter')
    if ip_filter is not None and ip_filter != current.get('ip_filter', ''):
        changes['ip_filter'] = ip_filter

    active = module.params.get('active')
    if active is not None and active != current.get('is_active'):
        changes['is_active'] = active

    if not changes:
        module.exit_json(changed=False, tokenid=tokenid)
    if module.check_mode:
        module.exit_json(changed=True, tokenid=tokenid)

    replies = lin.controller_modify_auth_token(tokenid, **changes)
    check_api_response(module, replies, 'modify auth token %d' % tokenid)
    module.exit_json(changed=True, tokenid=tokenid)


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        state=dict(type='str', default='present',
                   choices=['present', 'absent']),
        tokenid=dict(type='int', no_log=False),
        description=dict(type='str'),
        ip_filter=dict(type='str'),
        expires_at=dict(type='str'),
        active=dict(type='bool'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ('state', 'absent', ['tokenid']),
        ],
    )

    state = module.params['state']
    tokenid = module.params.get('tokenid')

    lin = get_linstor_connection(module)

    try:
        if state == 'present' and tokenid is None:
            create_token(module, lin)

        tokens = list_tokens(lin)
        current = find_token(tokens, tokenid)

        if state == 'absent':
            if current is None:
                module.exit_json(changed=False, tokenid=tokenid)
            if module.check_mode:
                module.exit_json(changed=True, tokenid=tokenid)
            replies = lin.controller_delete_auth_token(tokenid)
            check_api_response(module, replies,
                               'revoke auth token %d' % tokenid)
            module.exit_json(changed=True, tokenid=tokenid)

        if current is None:
            module.fail_json(
                msg="Auth token %d not found. Tokens are addressed by ID; "
                    "omit tokenid to create a new token." % tokenid)
        modify_token(module, lin, current)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error managing auth token: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
