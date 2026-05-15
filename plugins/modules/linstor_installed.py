#!/usr/bin/python
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: linstor_installed
short_description: Detect whether LINSTOR is installed on the target host
version_added: "0.9.8"
description:
  - Returns I(installed=true) when either C(linstor-controller.service) or
    C(linstor-satellite.service) has a systemd unit file present in
    C(/usr/lib/systemd/system) or C(/etc/systemd/system).
  - Use as a gating step in playbooks that should only run when LINSTOR
    is deployed on the host, without paying the cost of
    M(ansible.builtin.service_facts).
options: {}
author:
  - Ryan Ronnander (@rronnander)
'''

EXAMPLES = r'''
- name: Check if LINSTOR is installed
  linbit.linstor.linstor_installed:
  register: linstor

- name: Skip play if LINSTOR is not installed on this host
  ansible.builtin.meta: end_play
  when: not linstor.installed
'''

RETURN = r'''
installed:
  description: True when at least one LINSTOR systemd unit is present.
  type: bool
  returned: always
controller:
  description: True when C(linstor-controller.service) is present.
  type: bool
  returned: always
satellite:
  description: True when C(linstor-satellite.service) is present.
  type: bool
  returned: always
'''

import os

from ansible.module_utils.basic import AnsibleModule

UNIT_DIRS = ('/usr/lib/systemd/system', '/etc/systemd/system')


def unit_present(name):
    return any(os.path.exists(os.path.join(d, name)) for d in UNIT_DIRS)


def main():
    module = AnsibleModule(argument_spec={}, supports_check_mode=True)
    controller = unit_present('linstor-controller.service')
    satellite = unit_present('linstor-satellite.service')
    module.exit_json(
        changed=False,
        installed=controller or satellite,
        controller=controller,
        satellite=satellite,
    )


if __name__ == '__main__':
    main()
