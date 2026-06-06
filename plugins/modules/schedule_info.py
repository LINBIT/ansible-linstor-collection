#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: schedule_info
short_description: Query LINSTOR backup schedules
version_added: "1.0.0"
description:
  - Returns LINSTOR backup schedules (cron expressions and retention settings).
  - Read-only; C(changed) is always C(false).
  - Omit O(name) to return all schedules, or set it to query a single one.
options:
  name:
    description:
      - Schedule name to query.
      - If omitted, all schedules are returned.
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
  - module: linbit.linstor.schedule
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Query all schedules
  linbit.linstor.schedule_info:
  register: all_schedules
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Query a single schedule
  linbit.linstor.schedule_info:
    name: daily-backup
  register: schedule_state
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Show the schedule's full-backup cron
  ansible.builtin.debug:
    msg: "daily-backup full cron: {{ schedule_state.schedules[0].full_cron }}"
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
schedules:
  description: List of LINSTOR backup schedules, filtered by O(name) when supplied.
  type: list
  elements: dict
  returned: always
  contains:
    name:
      description: Schedule name.
      type: str
    full_cron:
      description: Cron expression for full backups.
      type: str
    incremental_cron:
      description: Cron expression for incremental backups.
      type: str
    keep_local:
      description: Number of local snapshots to keep.
      type: int
    keep_remote:
      description: Number of remote backups to keep.
      type: int
    on_failure:
      description: Failure handling policy.
      type: str
    max_retries:
      description: Maximum retry count on failure.
      type: int
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)


def sched_to_dict(sched):
    """Flatten a schedule object into a JSON-serializable dict."""
    return dict(
        name=getattr(sched, 'schedule_name', ''),
        full_cron=getattr(sched, 'full_cron', None),
        incremental_cron=getattr(sched, 'inc_cron', None),
        keep_local=getattr(sched, 'keep_local', None),
        keep_remote=getattr(sched, 'keep_remote', None),
        on_failure=getattr(sched, 'on_failure', None),
        max_retries=getattr(sched, 'max_retries', None),
    )


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params['name']

    lin = get_linstor_connection(module)

    try:
        sched_list = lin.schedule_list()
        schedules = [sched_to_dict(s)
                     for s in (getattr(sched_list, 'schedules', None) or [])]
        if name:
            schedules = [s for s in schedules if s['name'] == name]
        module.exit_json(changed=False, schedules=schedules)
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying schedules: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
