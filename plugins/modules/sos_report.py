#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: sos_report
short_description: Create and download a LINSTOR SOS report
version_added: "0.9.11"
description:
  - Has the LINSTOR controller create an SOS report and downloads the archive into a
    directory on the host that runs the module, which is the Ansible control node with
    the default C(delegate_to=localhost).
  - The SOS report holds logs, configuration, error reports, and DRBD state from the
    controller and the satellites, so it collects evidence while a fault is still there.
  - Every run creates a new archive and reports C(changed=true). In check mode the module
    creates nothing.
options:
  dest:
    description:
      - Directory to save the archive in, under the file name that the controller gives
        it. The module creates the directory when it is missing.
    type: path
    required: true
  nodes:
    description:
      - Include only these nodes.
      - If omitted, every node is included.
    type: list
    elements: str
  resources:
    description:
      - Include only the nodes that have one of these resources deployed.
      - If omitted, every node is included.
    type: list
    elements: str
  exclude_nodes:
    description: Leave these nodes out of the report.
    type: list
    elements: str
  include_controller:
    description: Include the files of the controller.
    type: bool
    default: true
  since:
    description:
      - Limit the journal entries in the report to this time and later.
      - An ISO 8601 timestamp such as C(2026-10-10T14:05:00Z), or an age such as
        C(30m), C(2h), or C(1d).
      - A timestamp without a time zone is local time on the host that runs the module.
    type: str
extends_documentation_fragment:
  - linbit.linstor.connection
requirements:
  - python-linstor
notes:
  - "The collection's action plugins force C(become: false) on the task
    automatically, so a parent play's C(become: true) does not bleed into
    the delegated call."
  - This module issues API calls via C(python-linstor) to the LINSTOR controller.
  - "Use C(run_once=true) or a single-host play such as
    C(hosts: linstor_controllers[0]), since every run creates a report."
  - "With a delegate other than C(localhost), the archive lands on that host. Fetch it
    from there with M(ansible.builtin.fetch)."
seealso:
  - module: linbit.linstor.error_report_info
  - name: LINSTOR User's Guide - SOS reports
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-sos-reports
    description: Creating SOS reports in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Collect an SOS report of the whole cluster
  linbit.linstor.sos_report:
    dest: "{{ playbook_dir }}/evidence"
  register: sos
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Collect an SOS report of the nodes that hold a resource, for the last hour
  linbit.linstor.sos_report:
    dest: "{{ playbook_dir }}/evidence"
    resources:
      - res-0
    since: 1h
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Show where the archive is
  ansible.builtin.debug:
    msg: "SOS report saved to {{ sos.path }}"
  run_once: true  # noqa: run-once[task]

- name: Run the bug trigger and keep the evidence when it fails
  run_once: true  # noqa: run-once[task]
  delegate_to: localhost
  block:
    - name: Delete the snapshot while the copy on node-3 is INACTIVE
      linbit.linstor.snapshot:
        resource: res-0
        name: snap-0
        state: absent
  rescue:
    - name: Collect an SOS report while the failed state is still there
      linbit.linstor.sos_report:
        dest: "{{ playbook_dir }}/evidence"
        resources:
          - res-0
        since: 1h

    - name: Fail the play after collecting the evidence
      ansible.builtin.fail:
        msg: "{{ ansible_failed_result.msg }}"
'''

RETURN = r'''
path:
  description: Absolute path of the downloaded archive.
  type: str
  returned: success, not in check mode
  sample: /home/user/evidence/sos_2026-10-10_14-05-00.tar.gz
'''

import os
import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_native
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
    check_api_response,
)
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_time import (
    TIME_FORMATS_HELP,
    parse_linstor_time,
)


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        dest=dict(type='path', required=True),
        nodes=dict(type='list', elements='str'),
        resources=dict(type='list', elements='str'),
        exclude_nodes=dict(type='list', elements='str'),
        include_controller=dict(type='bool', default=True),
        since=dict(type='str'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    dest = os.path.abspath(module.params['dest'])
    since = None
    if module.params['since'] is not None:
        since = parse_linstor_time(module.params['since'])
        if since is None:
            module.fail_json(msg="'since' must be %s, got '%s'" % (
                TIME_FORMATS_HELP, module.params['since']))

    if module.check_mode:
        module.exit_json(changed=True)

    try:
        if not os.path.isdir(dest):
            os.makedirs(dest)
    except OSError as e:
        module.fail_json(msg="Cannot create '%s': %s" % (dest, to_native(e)))

    lin = get_linstor_connection(module)

    try:
        # python-linstor saves under the controller's file name only in the current directory
        os.chdir(dest)
        replies = lin.sos_report_download(
            since=since,
            nodes=module.params['nodes'],
            rscs=module.params['resources'],
            exclude=module.params['exclude_nodes'],
            include_ctrl=module.params['include_controller'],
        )
        check_api_response(module, replies, 'download SOS report')
        saved = replies[0].object_refs.get('path') if replies else None
        if not saved:
            module.fail_json(msg="The controller sent no SOS report: %s" % replies)
        module.exit_json(changed=True, path=os.path.join(dest, saved))
    except Exception as e:
        module.fail_json(
            msg="Unexpected error creating the SOS report: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
