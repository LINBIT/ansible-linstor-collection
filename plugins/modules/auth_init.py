#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: auth_init
short_description: Initialize LINSTOR token authentication
version_added: "1.0.0"
description:
  - Initializes bearer token authentication for the LINSTOR REST API.
  - This is a singleton module (no C(name) parameter) similar to
    M(linbit.linstor.controller).
  - Initialization enables token authentication on the controller, enables
    HTTPS on the REST API with an auto-generated self-signed certificate
    (unless O(no_https) is set), creates the first user token, and creates
    and distributes individual satellite tokens to every connected
    satellite node (saved to C(/var/lib/linstor.d/auth.json) on each).
  - Idempotent. If token authentication is already enabled, the module
    exits without changes. Detection uses the
    C(Auth/TokenAuthenticationEnabled) controller property, falling back
    to interpreting an unauthorized API response as already enabled.
  - With O(only_satellites) the module regenerates and redistributes the
    satellite tokens without touching user tokens. This rotation is an
    event operation and always reports C(changed=true).
options:
  description:
    description:
      - Description label for the initial user token.
      - Not used with O(only_satellites).
    type: str
    required: true
  only_satellites:
    description:
      - Only regenerate and redistribute satellite tokens.
      - Requires token authentication to be enabled already.
      - No user token is created or returned in this mode.
    type: bool
    default: false
  no_https:
    description:
      - Skip the automatic HTTPS setup during initialization.
      - Use when HTTPS has already been configured manually, for example
        through the C(ssl_init) role.
    type: bool
    default: false
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
  - The raw token value is returned only by the initializing run and is
    never shown again. Save it; subsequent module calls against the
    cluster need it (through O(auth_token) or C(linstor-client.conf)).
  - Requires LINSTOR 1.34.0 or later on the controller and a python-linstor
    release with token authentication support on the play host.
  - Satellite tokens are distributed only to satellites connected at
    initialization time, and are rotated automatically on every satellite
    reconnect.
  - "Recovery: if all user tokens are lost, disable token authentication
    with C(linstor-config disable-token-auth) on the controller node
    (controller service stopped), then initialize again."
seealso:
  - module: linbit.linstor.auth_token
  - module: linbit.linstor.auth_token_info
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Initialize token authentication
  linbit.linstor.auth_init:
    description: admin-initial
  register: linstor_auth
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Initialize token authentication without automatic HTTPS
  linbit.linstor.auth_init:
    description: admin-initial
    no_https: true
  register: linstor_auth
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Rotate all satellite tokens
  linbit.linstor.auth_init:
    description: unused
    only_satellites: true
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
initialized:
  description: Whether token authentication is enabled after the operation.
  type: bool
  returned: always
token:
  description:
    - The raw user token created by the initializing run.
    - Shown once; LINSTOR stores only its hash.
    - Empty when token authentication was already enabled and with
      O(only_satellites).
  type: str
  returned: when a user token was created
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
    check_api_response,
)


def get_auth_enabled(lin):
    """Return whether token authentication is enabled.

    Reads the Auth/TokenAuthenticationEnabled controller property.
    An unauthorized API response also means enabled (the connection has
    no usable token, which can only happen with token auth active).
    """
    try:
        result = lin.controller_props()
    except Exception as e:
        if 'unauthorized' in str(e).lower():
            return True
        raise
    props = {}
    if isinstance(result, list) and result:
        item = result[0]
        if hasattr(item, 'properties') and item.properties:
            props = dict(item.properties)
    return str(props.get('Auth/TokenAuthenticationEnabled', 'false')).lower() == 'true'


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        description=dict(type='str', required=True),
        only_satellites=dict(type='bool', default=False),
        no_https=dict(type='bool', default=False),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    description = module.params['description']
    only_satellites = module.params['only_satellites']
    no_https = module.params['no_https']

    lin = get_linstor_connection(module, unauthorized_ok=True)
    if lin is None:
        # Unauthorized connect: token authentication is enabled but no
        # usable token is available, so the cluster is already initialized.
        if only_satellites:
            module.fail_json(
                msg="Token authentication is enabled but no valid auth "
                    "token is available; only_satellites needs one.")
        module.exit_json(changed=False, initialized=True)

    try:
        enabled = get_auth_enabled(lin)

        if only_satellites:
            if not enabled:
                module.fail_json(
                    msg="Token authentication is not enabled; "
                        "only_satellites requires an initialized cluster.")
            if module.check_mode:
                module.exit_json(changed=True, initialized=True)
            replies = lin.controller_init_auth_token(
                description, only_satellites=True, no_https=no_https)
            check_api_response(module, replies, 'rotate satellite tokens')
            module.exit_json(changed=True, initialized=True)

        if enabled:
            module.exit_json(changed=False, initialized=True)

        if module.check_mode:
            module.exit_json(changed=True, initialized=True)

        replies = lin.controller_init_auth_token(
            description, only_satellites=False, no_https=no_https)
        check_api_response(module, replies, 'initialize token authentication')

        token = ''
        for reply in replies:
            refs = getattr(reply, 'object_refs', None)
            if refs and 'token' in refs:
                token = refs['token']
                break

        module.exit_json(changed=True, initialized=True, token=token)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error initializing token authentication: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
