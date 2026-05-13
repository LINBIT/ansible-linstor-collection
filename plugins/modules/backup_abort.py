#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: backup_abort
short_description: Abort an in-progress LINSTOR backup operation
version_added: "0.9.7"
description:
  - Aborts an in-progress backup operation on a remote.
  - This module is NOT idempotent; it always invokes the abort API and
    reports C(changed=true). Use M(linbit.linstor.backup_info) with
    C(kind=queued) first if no-op behavior is needed when nothing is in
    flight.
options:
  remote:
    description: Name of the remote.
    type: str
    required: true
  resource:
    description: Resource name whose backup operation to abort.
    type: str
    required: true
  abort_restore:
    description: Abort an in-progress restore operation.
    type: bool
  abort_create:
    description: Abort an in-progress create operation.
    type: bool
  abort_snapshot:
    description:
      - Snapshot name for aborting a specific operation.
      - Requires LINSTOR controller 1.27+.
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
  - "Use C(run_once=true) or a single-host play such as C(hosts: linstor_controllers[0])."
seealso:
  - module: linbit.linstor.backup
  - module: linbit.linstor.backup_info
  - module: linbit.linstor.backup_ship
  - module: linbit.linstor.backup_restore
  - module: linbit.linstor.remote
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Abort an in-progress backup for a resource
  linbit.linstor.backup_abort:
    remote: remote-s3-backup
    resource: res-data
  run_once: true  # noqa: run-once[task]

- name: Abort only a restore, leaving creates running
  linbit.linstor.backup_abort:
    remote: remote-s3-backup
    resource: res-data
    abort_restore: true
    abort_create: false
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
remote:
  description: Name of the remote.
  type: str
  returned: always
resource:
  description: Resource name whose operation was aborted.
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


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        remote=dict(type='str', required=True),
        resource=dict(type='str', required=True),
        abort_restore=dict(type='bool'),
        abort_create=dict(type='bool'),
        abort_snapshot=dict(type='str'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    remote = module.params['remote']
    resource = module.params['resource']

    if module.check_mode:
        module.exit_json(changed=True, remote=remote, resource=resource)

    lin = get_linstor_connection(module)

    try:
        kwargs = dict(
            remote_name=remote,
            resource_name=resource,
        )
        if module.params.get('abort_restore') is not None:
            kwargs['restore'] = module.params['abort_restore']
        if module.params.get('abort_create') is not None:
            kwargs['create'] = module.params['abort_create']
        if module.params.get('abort_snapshot'):
            kwargs['snapshot'] = module.params['abort_snapshot']

        replies = lin.backup_abort(**kwargs)
        check_api_response(module, replies,
                           'abort backup operation for %s' % resource)
        module.exit_json(changed=True, remote=remote, resource=resource)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error aborting backup for '%s' on remote '%s': %s" % (
                resource, remote, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
