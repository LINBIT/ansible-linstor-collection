#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: error_report_info
short_description: Query LINSTOR error reports
version_added: "0.9.11"
description:
  - Returns the error reports that the LINSTOR controller and satellites logged,
    filtered by node, time range, or ID.
  - Read-only; C(changed) is always C(false).
  - Record a timestamp before a step and query the reports since then to fail a
    play when the step logged a new error report.
options:
  nodes:
    description:
      - Return only the error reports of these nodes.
      - If omitted, the reports of every node and of the controller are returned.
    type: list
    elements: str
  since:
    description:
      - Return only the error reports logged at or after this time.
      - An ISO 8601 timestamp such as C(2026-10-10T14:05:00Z), or an age such as
        C(90s), C(30m), C(2h), C(1d), or C(1h30m).
      - A timestamp without a time zone is local time on the host that runs the module.
    type: str
  to:
    description:
      - Return only the error reports logged at or before this time.
      - Takes the same formats as O(since).
    type: str
  ids:
    description:
      - Return only the error reports whose ID starts with one of these strings.
      - Mutually exclusive with O(nodes), O(since), and O(to).
    type: list
    elements: str
  with_content:
    description: Include the full text of each error report.
    type: bool
    default: false
extends_documentation_fragment:
  - linbit.linstor.connection
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
  - "For cluster-wide tasks use C(run_once=true) or a single-host play such as
    C(hosts: linstor_controllers[0])."
seealso:
  - module: linbit.linstor.sos_report
  - name: LINSTOR User's Guide - Getting Help
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-getting-help
    description: Error reports and SOS reports in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Record the time before the step
  ansible.builtin.set_fact:
    step_start: "{{ now(utc=true, fmt='%Y-%m-%dT%H:%M:%SZ') }}"
  run_once: true  # noqa: run-once[task]

- name: Delete a resource from one node
  linbit.linstor.resource:
    name: res-0
    node: node-3
    state: absent
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Fail when the step logged an error report
  linbit.linstor.error_report_info:
    since: "{{ step_start }}"
  register: new_reports
  failed_when: new_reports.error_reports | length > 0
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Query the last hour of error reports on two nodes
  linbit.linstor.error_report_info:
    nodes:
      - node-1
      - node-2
    since: 1h
  register: recent_reports
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Read the full text of one error report
  linbit.linstor.error_report_info:
    ids:
      - 6704A1B2-00000-000001
    with_content: true
  register: report
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
error_reports:
  description: Error reports that match the filters, oldest first.
  type: list
  elements: dict
  returned: always
  contains:
    id:
      description: Error report ID, as C(linstor error-reports show) takes it.
      type: str
    node_name:
      description: Node that logged the error report.
      type: str
    time:
      description: Time of the error report, as an ISO 8601 timestamp in UTC.
      type: str
    module:
      description:
        - LINSTOR component that logged the report (for example C(CONTROLLER) or
          C(SATELLITE)).
      type: str
    version:
      description: LINSTOR version that logged the report.
      type: str
    peer:
      description: Peer that the failed operation came from, if any.
      type: str
    exception:
      description: Exception class name.
      type: str
    exception_message:
      description: Exception message.
      type: str
    origin_file:
      description: Source file that raised the exception.
      type: str
    origin_line:
      description: Source line that raised the exception.
      type: int
    text:
      description: Full text of the error report.
      type: str
      returned: when O(with_content=true)
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_time import (
    TIME_FORMATS_HELP,
    format_epoch_ms,
    parse_linstor_time,
)


def report_to_dict(report, with_content):
    """Flatten an error report into a JSON-serializable dict."""
    data = report.data_v1
    error_time = data.get('error_time')
    result = dict(
        id=report.id,
        node_name=data.get('node_name', ''),
        time=format_epoch_ms(error_time) if error_time is not None else None,
        module=data.get('module', ''),
        version=data.get('version', ''),
        peer=data.get('peer', ''),
        exception=data.get('exception', ''),
        exception_message=data.get('exception_message', ''),
        origin_file=data.get('origin_file', ''),
        origin_line=int(data['origin_line']) if 'origin_line' in data else None,
    )
    if with_content:
        result['text'] = data.get('text')
    return result, error_time or 0


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        nodes=dict(type='list', elements='str'),
        since=dict(type='str'),
        to=dict(type='str'),
        ids=dict(type='list', elements='str'),
        with_content=dict(type='bool', default=False),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ('ids', 'nodes'),
            ('ids', 'since'),
            ('ids', 'to'),
        ],
    )

    with_content = module.params['with_content']
    window = {}
    for key in ('since', 'to'):
        value = module.params[key]
        if value is None:
            continue
        window[key] = parse_linstor_time(value)
        if window[key] is None:
            module.fail_json(msg="'%s' must be %s, got '%s'" % (
                key, TIME_FORMATS_HELP, value))

    lin = get_linstor_connection(module)

    try:
        reports = lin.error_report_list(
            nodes=module.params['nodes'],
            with_content=with_content,
            since=window.get('since'),
            to=window.get('to'),
            ids=module.params['ids'],
        )
        flattened = sorted(
            (report_to_dict(r, with_content) for r in reports),
            key=lambda pair: pair[1])
        module.exit_json(changed=False,
                         error_reports=[report for report, dummy in flattened])
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying error reports: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
