#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: schedule
short_description: Manage LINSTOR backup schedules
version_added: "0.10.0"
description:
  - Creates, modifies, or deletes LINSTOR backup schedules.
  - Optionally enables or disables a schedule for a specific remote and
    resource or resource group combination.
  - Schedule definition CRUD is fully idempotent.
  - Enable and disable operations are idempotent when the current state
    can be queried.
  - Use C(state=query) to retrieve schedule properties without modification.
options:
  name:
    description: Name of the backup schedule.
    type: str
    required: true
  state:
    description: Desired state of the schedule.
    type: str
    default: present
    choices: [present, absent, query]
  full_cron:
    description:
      - Cron expression for full backups.
      - Required when C(state=present) and creating a new schedule.
    type: str
  incremental_cron:
    description: Cron expression for incremental backups.
    type: str
  keep_local:
    description: Number of local snapshots to retain.
    type: int
  keep_remote:
    description: Number of remote backups to retain.
    type: int
  on_failure:
    description:
      - Behavior when a scheduled backup fails.
      - C(SKIP) skips the failed run. C(RETRY) retries up to O(max_retries) times.
    type: str
    choices: [SKIP, RETRY]
  max_retries:
    description:
      - Maximum retry count when O(on_failure=RETRY).
    type: int
  enabled:
    description:
      - Enable or disable the schedule for a specific remote and resource
        or resource group combination.
      - When C(true), enables the schedule. When C(false), disables it.
      - Requires O(remote) to be set.
      - Exactly one of O(resource) or O(resource_group) should be set.
    type: bool
  remote:
    description:
      - Remote name to enable or disable the schedule for.
      - Required when O(enabled) is set.
    type: str
  resource:
    description:
      - Resource name to enable or disable the schedule for.
      - Mutually exclusive with O(resource_group).
    type: str
  resource_group:
    description:
      - Resource group name to enable or disable the schedule for.
      - Mutually exclusive with O(resource).
    type: str
  preferred_node:
    description:
      - Preferred node for scheduled backups.
      - Only used when O(enabled=true).
    type: str
  dst_storage_pool:
    description:
      - Destination storage pool for scheduled restore.
      - Only used when O(enabled=true).
    type: str
  storage_pool_rename:
    description:
      - Storage pool rename map for scheduled restore.
      - Only used when O(enabled=true).
    type: dict
  force_restore:
    description:
      - Force restore on schedule enable.
      - Only used when O(enabled=true).
    type: bool
    default: false
  dst_resource_group:
    description:
      - Destination resource group for scheduled restore.
      - Only used when O(enabled=true).
    type: str
  force_move_resource_group:
    description:
      - Force moving the resource to a different resource group.
      - Only used when O(enabled=true).
    type: bool
    default: false
  dst_resource:
    description:
      - Destination resource name for scheduled restore.
      - Only used when O(enabled=true).
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
  - The M(linbit.linstor.remote) module must be used first to configure the
    remote before enabling a schedule.
seealso:
  - module: linbit.linstor.remote
  - module: linbit.linstor.backup
  - module: linbit.linstor.backup_info
  - module: linbit.linstor.backup_ship
  - module: linbit.linstor.backup_restore
  - module: linbit.linstor.backup_abort
  - name: LINSTOR User's Guide - Scheduled Backups
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-scheduled-backups
    description: Scheduled backup concepts in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Create a backup schedule
  linbit.linstor.schedule:
    name: sched-daily
    full_cron: "0 2 * * 0"
    incremental_cron: "0 2 * * 1-6"
    keep_local: 3
    keep_remote: 7
  run_once: true  # noqa: run-once[task]

- name: Enable schedule for a resource
  linbit.linstor.schedule:
    name: sched-daily
    enabled: true
    remote: remote-s3-backup
    resource: res-data
  run_once: true  # noqa: run-once[task]

- name: Enable schedule for a resource group
  linbit.linstor.schedule:
    name: sched-daily
    enabled: true
    remote: remote-s3-backup
    resource_group: rg-ha
  run_once: true  # noqa: run-once[task]

- name: Disable schedule for a resource
  linbit.linstor.schedule:
    name: sched-daily
    enabled: false
    remote: remote-s3-backup
    resource: res-data
  run_once: true  # noqa: run-once[task]

- name: Query a backup schedule
  linbit.linstor.schedule:
    name: sched-daily
    state: query
  register: sched_result
  run_once: true  # noqa: run-once[task]

- name: Remove a backup schedule
  linbit.linstor.schedule:
    name: sched-daily
    state: absent
  run_once: true  # noqa: run-once[task]

- name: Create schedule with retry on failure
  linbit.linstor.schedule:
    name: sched-hourly
    full_cron: "0 * * * *"
    on_failure: RETRY
    max_retries: 3
    keep_remote: 24
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
name:
  description: Name of the schedule.
  type: str
  returned: always
exists:
  description: Whether the schedule exists. Only returned with C(state=query).
  type: bool
  returned: query
full_cron:
  description: Cron expression for full backups.
  type: str
  returned: success
incremental_cron:
  description: Cron expression for incremental backups.
  type: str
  returned: success
keep_local:
  description: Number of local snapshots retained.
  type: int
  returned: success
keep_remote:
  description: Number of remote backups retained.
  type: int
  returned: success
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
    check_api_response,
)


def get_schedule(lin, name):
    """Get a schedule by name. Returns the schedule object or None."""
    sched_list = lin.schedule_list()
    for sched in sched_list.schedules:
        if sched.schedule_name == name:
            return sched
    return None


def schedule_needs_modify(existing, module):
    """Check if schedule definition parameters differ from existing state."""
    if module.params.get('full_cron') is not None:
        if existing.full_cron != module.params['full_cron']:
            return True
    if module.params.get('incremental_cron') is not None:
        if getattr(existing, 'inc_cron', None) != module.params['incremental_cron']:
            return True
    if module.params.get('keep_local') is not None:
        if getattr(existing, 'keep_local', None) != module.params['keep_local']:
            return True
    if module.params.get('keep_remote') is not None:
        if getattr(existing, 'keep_remote', None) != module.params['keep_remote']:
            return True
    if module.params.get('on_failure') is not None:
        if getattr(existing, 'on_failure', None) != module.params['on_failure']:
            return True
    if module.params.get('max_retries') is not None:
        if getattr(existing, 'max_retries', None) != module.params['max_retries']:
            return True
    return False


def build_schedule_result(sched):
    """Build result dict from a schedule object."""
    return dict(
        full_cron=sched.full_cron,
        incremental_cron=getattr(sched, 'inc_cron', None),
        keep_local=getattr(sched, 'keep_local', None),
        keep_remote=getattr(sched, 'keep_remote', None),
    )


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        state=dict(type='str', default='present', choices=['present', 'absent', 'query']),
        full_cron=dict(type='str'),
        incremental_cron=dict(type='str'),
        keep_local=dict(type='int'),
        keep_remote=dict(type='int'),
        on_failure=dict(type='str', choices=['SKIP', 'RETRY']),
        max_retries=dict(type='int'),
        enabled=dict(type='bool'),
        remote=dict(type='str'),
        resource=dict(type='str'),
        resource_group=dict(type='str'),
        preferred_node=dict(type='str'),
        dst_storage_pool=dict(type='str'),
        storage_pool_rename=dict(type='dict'),
        force_restore=dict(type='bool', default=False),
        dst_resource_group=dict(type='str'),
        force_move_resource_group=dict(type='bool', default=False),
        dst_resource=dict(type='str'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ('resource', 'resource_group'),
        ],
    )

    name = module.params['name']
    state = module.params['state']
    enabled = module.params.get('enabled')

    # Validate: enabled requires remote
    if enabled is not None and not module.params.get('remote'):
        module.fail_json(msg="'remote' is required when 'enabled' is set")

    lin = get_linstor_connection(module)
    changed = False

    try:
        existing = get_schedule(lin, name)

        if state == 'query':
            if existing is None:
                module.exit_json(changed=False, name=name, exists=False)
            result = build_schedule_result(existing)
            result['name'] = name
            result['exists'] = True
            result['on_failure'] = getattr(existing, 'on_failure', None)
            result['max_retries'] = getattr(existing, 'max_retries', None)
            module.exit_json(changed=False, **result)

        if state == 'absent':
            if existing is None:
                module.exit_json(changed=False, name=name)
            if module.check_mode:
                module.exit_json(changed=True, name=name)
            replies = lin.schedule_delete(name)
            check_api_response(module, replies,
                               'delete schedule %s' % name)
            module.exit_json(changed=True, name=name)

        # state == 'present'
        if existing is None:
            # Create new schedule
            if not module.params.get('full_cron'):
                module.fail_json(
                    msg="'full_cron' is required when creating a new schedule")

            if module.check_mode:
                module.exit_json(
                    changed=True, name=name,
                    full_cron=module.params['full_cron'],
                    incremental_cron=module.params.get('incremental_cron'),
                    keep_local=module.params.get('keep_local'),
                    keep_remote=module.params.get('keep_remote'))

            kwargs = dict(
                schedule_name=name,
                full_cron=module.params['full_cron'],
            )
            if module.params.get('incremental_cron') is not None:
                kwargs['incremental_cron'] = module.params['incremental_cron']
            if module.params.get('keep_local') is not None:
                kwargs['keep_local'] = module.params['keep_local']
            if module.params.get('keep_remote') is not None:
                kwargs['keep_remote'] = module.params['keep_remote']
            if module.params.get('on_failure') is not None:
                kwargs['on_failure'] = module.params['on_failure']
            if module.params.get('max_retries') is not None:
                kwargs['max_retries'] = module.params['max_retries']

            replies = lin.schedule_create(**kwargs)
            check_api_response(module, replies,
                               'create schedule %s' % name)
            changed = True

        elif schedule_needs_modify(existing, module):
            # Modify existing schedule definition
            if module.check_mode:
                result = build_schedule_result(existing)
                result['name'] = name
                module.exit_json(changed=True, **result)

            kwargs = dict(schedule_name=name)
            if module.params.get('full_cron') is not None:
                kwargs['full_cron'] = module.params['full_cron']
            if module.params.get('incremental_cron') is not None:
                kwargs['incremental_cron'] = module.params['incremental_cron']
            if module.params.get('keep_local') is not None:
                kwargs['keep_local'] = module.params['keep_local']
            if module.params.get('keep_remote') is not None:
                kwargs['keep_remote'] = module.params['keep_remote']
            if module.params.get('on_failure') is not None:
                kwargs['on_failure'] = module.params['on_failure']
            if module.params.get('max_retries') is not None:
                kwargs['max_retries'] = module.params['max_retries']

            replies = lin.schedule_modify(**kwargs)
            check_api_response(module, replies,
                               'modify schedule %s' % name)
            changed = True

        # Handle enable/disable
        if enabled is not None:
            remote = module.params['remote']
            resource = module.params.get('resource')
            resource_group = module.params.get('resource_group')

            if enabled:
                if module.check_mode:
                    changed = True
                else:
                    kwargs = dict(
                        remote_name=remote,
                        schedule_name=name,
                    )
                    if resource:
                        kwargs['resource_name'] = resource
                    if resource_group:
                        kwargs['resource_group_name'] = resource_group
                    if module.params.get('preferred_node'):
                        kwargs['preferred_node'] = module.params['preferred_node']
                    if module.params.get('dst_storage_pool'):
                        kwargs['dst_stor_pool'] = module.params['dst_storage_pool']
                    if module.params.get('storage_pool_rename'):
                        kwargs['storpool_rename_map'] = module.params['storage_pool_rename']
                    if module.params['force_restore']:
                        kwargs['force_restore'] = True
                    if module.params.get('dst_resource_group'):
                        kwargs['dst_rsc_grp'] = module.params['dst_resource_group']
                    if module.params['force_move_resource_group']:
                        kwargs['force_mv_rsc_grp'] = True
                    if module.params.get('dst_resource'):
                        kwargs['dst_rsc_name'] = module.params['dst_resource']

                    replies = lin.backup_schedule_enable(**kwargs)
                    check_api_response(module, replies,
                                       'enable schedule %s on %s' % (name, remote))
                    changed = True
            else:
                if module.check_mode:
                    changed = True
                else:
                    kwargs = dict(
                        remote_name=remote,
                        schedule_name=name,
                    )
                    if resource:
                        kwargs['resource_name'] = resource
                    if resource_group:
                        kwargs['resource_group_name'] = resource_group

                    replies = lin.backup_schedule_disable(**kwargs)
                    check_api_response(module, replies,
                                       'disable schedule %s on %s' % (name, remote))
                    changed = True

        # Build final result
        final_sched = get_schedule(lin, name)
        if final_sched:
            result = build_schedule_result(final_sched)
        else:
            result = dict(
                full_cron=module.params.get('full_cron'),
                incremental_cron=module.params.get('incremental_cron'),
                keep_local=module.params.get('keep_local'),
                keep_remote=module.params.get('keep_remote'),
            )
        result['name'] = name

        module.exit_json(changed=changed, **result)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error managing schedule '%s': %s" % (name, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
