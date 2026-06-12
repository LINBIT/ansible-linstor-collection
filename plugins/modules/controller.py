#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: controller
short_description: Manage LINSTOR controller properties
version_added: "0.9.7"
description:
  - Reads, sets, and deletes cluster-wide properties on the LINSTOR controller.
  - The controller is a cluster-wide singleton, so no C(name) parameter is needed.
  - Idempotent. Only properties that differ from the current state are modified.
options:
  state:
    description: >-
      Operation mode. C(present) sets or deletes properties.
    type: str
    default: present
    choices: [present]
  properties:
    description: Dictionary of LINSTOR properties to set on the controller.
    type: dict
    default: {}
  aux_properties:
    description:
      - Dictionary of auxiliary properties to set on the controller.
      - Keys are automatically prefixed with C(Aux/).
    type: dict
    default: {}
  delete_properties:
    description: List of property keys to remove from the controller.
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
  - Requires the L(linstor-api-py,https://github.com/LINBIT/linstor-api-py) package
    (C(python-linstor)) on the play host.
  - "For cluster-wide tasks use C(run_once=true) or a single-host play such as C(hosts: linstor_controllers[0])."
  - "Auto-quorum: set C(DrbdOptions/auto-quorum) to C(disabled), C(suspend-io), or
    C(io-error) (default C(io-error)). When enabled, LINSTOR auto-manages
    C(DrbdOptions/Resource/quorum) and C(DrbdOptions/Resource/on-no-quorum).
    Set to C(disabled) to control those options manually."
  - "Auto-evict: C(DrbdOptions/AutoEvictAfterTime) (default 60 minutes),
    C(DrbdOptions/AutoEvictMaxDisconnectedNodes) (default 34%),
    C(DrbdOptions/AutoEvictAllowEviction) (default C(true)).
    Controller-level defaults that can be overridden per node via
    M(linbit.linstor.node)."
  - "Concurrent backup shipments: C(BackupShipping/MaxConcurrentBackupsPerNode).
    Negative value means unlimited, C(0) disables, positive value sets the limit.
    Controller-level default that can be overridden per node via
    M(linbit.linstor.node)."
seealso:
  - name: LINSTOR User's Guide
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/
    description: >-
      Search for C(linstor controller set-property) for all controller
      properties documented in the User's Guide.
  - name: LINSTOR User's Guide - Auto-Quorum
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-auto-quorum
    description: Automatic quorum management in the LINSTOR User's Guide.
  - name: LINSTOR User's Guide - Auto-Evict
    link: https://linbit.com/drbd-user-guide/linstor-guide-1_0-en/#s-linstor-auto-evict
    description: Automatic node eviction in the LINSTOR User's Guide.
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Set multiple controller properties
  linbit.linstor.controller:
    properties:
      MaxOversubscriptionRatio: "5"
      TcpPortAutoRange: "14000-16000"
  delegate_to: localhost
  run_once: true  # noqa: run-once[task]

- name: Set auxiliary property at the controller level
  linbit.linstor.controller:
    aux_properties:
      region: middle-coast
  run_once: true  # noqa: run-once[task]

- name: Allow mixing storage pool drivers
  linbit.linstor.controller:
    properties:
      AllowMixingStoragePoolDriver: "true"
  run_once: true  # noqa: run-once[task]

# Requires DRBD Proxy https://linbit.com/drbd-proxy/
- name: Enable automatic DRBD Proxy for remote sites
  linbit.linstor.controller:
    properties:
      DrbdProxy/AutoEnable: "true"
  run_once: true  # noqa: run-once[task]

- name: Set cluster-wide auto-quorum policy to suspend-io
  linbit.linstor.controller:
    properties:
      DrbdOptions/auto-quorum: suspend-io
  run_once: true  # noqa: run-once[task]

- name: Configure auto-evict timing and thresholds
  linbit.linstor.controller:
    properties:
      DrbdOptions/AutoEvictAfterTime: "120"
      DrbdOptions/AutoEvictMaxDisconnectedNodes: "50"
      DrbdOptions/AutoEvictAllowEviction: "true"
  run_once: true  # noqa: run-once[task]

- name: Limit concurrent backup shipments per node
  linbit.linstor.controller:
    properties:
      BackupShipping/MaxConcurrentBackupsPerNode: "2"
  run_once: true  # noqa: run-once[task]

- name: Unset a controller property (revert to LINSTOR default)
  linbit.linstor.controller:
    delete_properties:
      - MaxOversubscriptionRatio
  run_once: true  # noqa: run-once[task]

- name: Remove an auxiliary property
  linbit.linstor.controller:
    delete_properties:
      - Aux/region
  run_once: true  # noqa: run-once[task]

# Delegate to a cluster controller when the control node cannot reach
# the LINSTOR API directly (SSH jump host, segmented management network)
- name: Set a controller property via a delegated controller
  linbit.linstor.controller:
    properties:
      DrbdOptions/auto-quorum: io-error
  delegate_to: controller-0
  environment:
    LS_CONTROLLERS: linstor://localhost
  run_once: true  # noqa: run-once[task]

# Share delegation across a sequence of LINSTOR module tasks via block.
# Cleaner than repeating delegate_to and environment on every task.
- name: Cluster bootstrap through a delegated controller
  block:
    - name: Set controller properties
      linbit.linstor.controller:
        properties:
          DrbdOptions/auto-quorum: io-error

    - name: Create resource group rg-0
      linbit.linstor.resource_group:
        name: rg-0
        place_count: 2
  delegate_to: controller-0
  environment:
    LS_CONTROLLERS: linstor://localhost
  run_once: true  # noqa: run-once[task]
'''

RETURN = r'''
properties:
  description: Controller properties after the operation.
  type: dict
  returned: always
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linbit.linstor.plugins.module_utils.linstor_connection import (
    linstor_argument_spec,
    get_linstor_connection,
    check_api_response,
    compute_property_diff,
)


def get_controller_props(lin):
    """Get the current controller properties as a dict."""
    result = lin.controller_props()
    if isinstance(result, list) and result:
        item = result[0]
        if hasattr(item, 'properties') and item.properties:
            return dict(item.properties)
    return {}


def main():
    argument_spec = linstor_argument_spec()
    argument_spec.update(dict(
        state=dict(type='str', default='present', choices=['present']),
        properties=dict(type='dict', default={}),
        aux_properties=dict(type='dict', default={}),
        delete_properties=dict(type='list', elements='str', default=[]),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    state = module.params['state']
    properties = module.params['properties'] or {}
    aux_properties = module.params['aux_properties'] or {}
    delete_properties = module.params['delete_properties'] or []

    # Merge aux_properties with Aux/ prefix into properties
    all_properties = dict(properties)
    for key, value in aux_properties.items():
        aux_key = key if key.startswith('Aux/') else 'Aux/' + key
        all_properties[aux_key] = value

    lin = get_linstor_connection(module)
    changed = False

    try:
        current_props = get_controller_props(lin)

        props_to_set, props_to_delete = compute_property_diff(
            current_props, all_properties, delete_properties)

        if not props_to_set and not props_to_delete:
            module.exit_json(changed=False, properties=current_props)

        if module.check_mode:
            final_props = dict(current_props, **props_to_set)
            for key in props_to_delete:
                final_props.pop(key, None)
            module.exit_json(changed=True, properties=final_props)

        for key, value in props_to_set.items():
            replies = lin.controller_set_prop(key, value)
            check_api_response(module, replies, 'set controller property %s' % key)

        for key in props_to_delete:
            replies = lin.controller_del_prop(key)
            check_api_response(module, replies, 'delete controller property %s' % key)

        changed = True

        # Re-read properties after update
        final_props = get_controller_props(lin)

        module.exit_json(changed=changed, properties=final_props)

    except Exception as e:
        module.fail_json(
            msg="Unexpected error managing controller properties: %s" % str(e),
            exception=traceback.format_exc())
    finally:
        lin.disconnect()


if __name__ == '__main__':
    main()
