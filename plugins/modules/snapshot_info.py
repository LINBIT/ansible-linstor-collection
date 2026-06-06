#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: snapshot_info
short_description: Query LINSTOR snapshots
version_added: "1.0.0"
description:
  - Returns the snapshots of a LINSTOR resource.
  - Read-only; C(changed) is always C(false).
  - O(resource) is required. Omit O(name) to return all snapshots of the
    resource, or set it to return a single snapshot.
options:
  resource:
    description: Resource whose snapshots to query.
    type: str
    required: true
  name:
    description:
      - Snapshot name to filter by.
      - If omitted, all snapshots of the resource are returned.
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
  - module: linbit.linstor.snapshot
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Query all snapshots of a resource
  linbit.linstor.snapshot_info:
    resource: res-0
  register: res0_snapshots
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Query a single snapshot
  linbit.linstor.snapshot_info:
    resource: res-0
    name: snap-1
  register: snap_state
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Show the snapshot's nodes and flags
  ansible.builtin.debug:
    msg: "snap-1 on {{ snap_state.snapshots[0].nodes }}, flags {{ snap_state.snapshots[0].flags }}"
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
resource:
  description: The resource the snapshots belong to.
  type: str
  returned: always
snapshots:
  description: List of snapshots for the resource, filtered by O(name) when supplied.
  type: list
  elements: dict
  returned: always
  contains:
    name:
      description: Snapshot name.
      type: str
    nodes:
      description: Nodes the snapshot exists on.
      type: list
      elements: str
    flags:
      description: Snapshot flags (for example SUCCESSFUL or FAILED).
      type: list
      elements: str
    properties:
      description: Snapshot properties.
      type: dict
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
)


def get_snap_props(snap):
    """Extract properties from a snapshot definition."""
    if hasattr(snap, 'properties') and snap.properties:
        return dict(snap.properties)
    return {}


def snap_to_dict(snap):
    """Flatten a snapshot definition into a JSON-serializable dict."""
    return dict(
        name=getattr(snap, 'snapshot_name', ''),
        nodes=list(getattr(snap, 'nodes', []) or []),
        flags=list(getattr(snap, 'flags', []) or []),
        properties=get_snap_props(snap),
    )


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        resource=dict(type='str', required=True),
        name=dict(type='str'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    resource = module.params['resource']
    name = module.params['name']

    lin = get_linstor_connection(module)

    try:
        snap_list = lin.snapshot_dfn_list_raise(filter_by_resources=[resource])
        snapshots = [snap_to_dict(s)
                     for s in (getattr(snap_list, 'snapshots', None) or [])]
        if name:
            snapshots = [s for s in snapshots if s['name'] == name]
        module.exit_json(changed=False, resource=resource, snapshots=snapshots)
    except Exception as e:
        module.fail_json(
            msg="Unexpected error querying snapshots for resource '%s': %s" % (
                resource, str(e)),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
