#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: file_info
short_description: Query a LINSTOR external file
version_added: "1.0.0"
description:
  - Returns a LINSTOR external file's existence and content.
  - Read-only; C(changed) is always C(false).
  - O(path) is required; this module returns a single external file.
options:
  path:
    description: Path of the external file to query.
    type: str
    required: true
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
seealso:
  - module: linbit.linstor.file
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Query a LINSTOR external file
  linbit.linstor.file_info:
    path: /etc/drbd-reactor.d/linstor-gateway-nfs-export1.toml
  register: gw_file
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Show the file content when it exists
  ansible.builtin.debug:
    var: gw_file.content
  when: gw_file.exists
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
path:
  description: The external file path.
  type: str
  returned: always
exists:
  description: Whether the external file exists.
  type: bool
  returned: always
content:
  description: The file content, decoded as UTF-8.
  type: str
  returned: when the file exists
'''

import base64
import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)


def get_file(lin, path):
    """Return the ExternalFile object for the given path, or None if missing."""
    try:
        resp = lin.file_show(path)
    except Exception:
        return None
    if resp is None:
        return None
    files = resp.files if hasattr(resp, 'files') else resp
    if isinstance(files, list):
        return files[0] if files else None
    return files


def decode_content(external_file):
    """Return the file's content as bytes, decoding base64 if needed."""
    content = external_file.content
    if content is None:
        return b''
    if isinstance(content, bytes):
        return content
    try:
        return base64.b64decode(content)
    except Exception:
        return content.encode('utf-8')


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        path=dict(type='str', required=True),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    path = module.params['path']

    lin = get_linstor_connection(module)

    try:
        existing = get_file(lin, path)
        if existing is None:
            module.exit_json(changed=False, path=path, exists=False)
        current_bytes = decode_content(existing)
        module.exit_json(
            changed=False, path=path, exists=True,
            content=current_bytes.decode('utf-8', errors='replace'))
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying external file '%s': %s" % (path, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
