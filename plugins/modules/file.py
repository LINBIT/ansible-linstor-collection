#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: file
short_description: Manage LINSTOR external files
version_added: "0.9.7"
description:
  - Creates, updates, or deletes LINSTOR external files stored in the
    controller and optionally attached to resource definitions.
  - Attached files are automatically distributed by the controller to every
    satellite that holds a replica of the resource definition.
  - This is the mechanism LINSTOR Gateway uses to distribute drbd-reactor
    promoter configs, so writing a file with the path pattern
    C(/etc/drbd-reactor.d/linstor-gateway-*.toml) makes it visible to
    C(linstor-gateway list).
  - Idempotent. Content is compared byte-for-byte; deployment to resource
    definitions is attempted on every run but duplicate attaches are
    treated as no-ops.
options:
  path:
    description:
      - Absolute file path as stored in the LINSTOR controller.
      - The path also determines where the file is written on satellites
        when the controller distributes it.
    type: str
    required: true
  content:
    description:
      - File content as a string. Required when C(state=present).
      - Compared byte-for-byte against the existing content; a mismatch
        triggers an update.
    type: str
  state:
    description: Desired state of the external file.
    type: str
    default: present
    choices: [present, absent, query]
  deploy_to:
    description:
      - List of resource definition names to attach this file to.
      - Attachment triggers the controller to distribute the file to every
        satellite that has a replica of the listed resource definitions.
      - Only meaningful when C(state=present).
      - When C(state=absent), file deletion automatically undeploys from
        every resource definition, so this parameter is ignored.
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
extends_documentation_fragment: []
requirements:
  - python-linstor
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Push a drbd-reactor promoter config as a LINSTOR external file
  linbit.linstor.file:
    path: /etc/drbd-reactor.d/linstor-gateway-iscsi-example.toml
    content: "{{ lookup('ansible.builtin.template', 'promoter-iscsi.toml.j2') }}"
    deploy_to:
      - example
  run_once: true  # noqa: run-once[task]

- name: Query an external file
  linbit.linstor.file:
    path: /etc/drbd-reactor.d/linstor-gateway-iscsi-example.toml
    state: query
  register: file_result
  run_once: true  # noqa: run-once[task]

- name: Remove an external file (auto-undeploys from all attached RDs)
  linbit.linstor.file:
    path: /etc/drbd-reactor.d/linstor-gateway-iscsi-example.toml
    state: absent
  run_once: true  # noqa: run-once[task]

# Delegate to a cluster controller when the control node cannot reach
# the LINSTOR API directly (SSH jump host, segmented management network)
- name: Push an external file via a delegated controller
  linbit.linstor.file:
    path: /etc/drbd-reactor.d/linstor-gateway-iscsi-example.toml
    content: "{{ lookup('file', 'promoter.toml') }}"
  delegate_to: controller-0
  environment:
    LS_CONTROLLERS: linstor://localhost
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
path:
  description: Path of the external file.
  type: str
  returned: always
exists:
  description: Whether the file exists. Only returned with C(state=query).
  type: bool
  returned: query
content:
  description: File content. Only returned with C(state=query) when the file exists.
  type: str
  returned: query
'''

import base64
import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
    check_api_response,
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
    argument_spec.update(
        path=dict(type='str', required=True),
        content=dict(type='str'),
        state=dict(type='str', default='present',
                   choices=['present', 'absent', 'query']),
        deploy_to=dict(type='list', elements='str', default=[]),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ('state', 'present', ['content']),
        ],
    )

    path = module.params['path']
    state = module.params['state']
    desired_content = module.params.get('content')
    deploy_to = module.params.get('deploy_to') or []

    desired_bytes = desired_content.encode('utf-8') if desired_content is not None else None

    lin = get_linstor_connection(module)

    try:
        existing = get_file(lin, path)

        if state == 'query':
            if existing is None:
                module.exit_json(changed=False, path=path, exists=False)
            current_bytes = decode_content(existing)
            module.exit_json(
                changed=False,
                path=path,
                exists=True,
                content=current_bytes.decode('utf-8', errors='replace'),
            )

        if state == 'absent':
            if existing is None:
                module.exit_json(changed=False, path=path)
            if module.check_mode:
                module.exit_json(changed=True, path=path)
            replies = lin.file_delete(path)
            check_api_response(module, replies, 'delete external file %s' % path)
            module.exit_json(changed=True, path=path)

        # state == 'present'
        changed = False

        if existing is None:
            if module.check_mode:
                module.exit_json(changed=True, path=path)
            replies = lin.file_modify(path, desired_bytes)
            check_api_response(module, replies, 'create external file %s' % path)
            changed = True
        else:
            current_bytes = decode_content(existing)
            if current_bytes != desired_bytes:
                if module.check_mode:
                    module.exit_json(changed=True, path=path)
                replies = lin.file_modify(path, desired_bytes)
                check_api_response(module, replies, 'update external file %s' % path)
                changed = True

        # Attach to each resource definition in deploy_to. LINSTOR returns a
        # no-op-style success when the file is already attached, so we call
        # unconditionally and let check_api_response filter real errors.
        for rd_name in deploy_to:
            if module.check_mode:
                continue
            replies = lin.file_deploy(path, rd_name)
            # Treat "already deployed" as success; LINSTOR distinguishes via
            # info-level response codes that check_api_response accepts.
            check_api_response(
                module, replies,
                'attach external file %s to resource definition %s' % (path, rd_name))

        module.exit_json(changed=changed, path=path)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error managing external file '%s': %s" % (path, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
