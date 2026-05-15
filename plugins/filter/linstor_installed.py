# SPDX-License-Identifier: MIT
"""Filter plugin: detect whether LINSTOR is installed on this host."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
  name: linstor_installed
  short_description: True when a LINSTOR controller or satellite service exists on this host
  version_added: "0.9.8"
  description:
    - Returns C(True) if C(ansible_facts.services) contains either
      C(linstor-controller.service) or C(linstor-satellite.service);
      otherwise C(False).
    - Use after C(ansible.builtin.service_facts) to gate plays that
      should only run when LINSTOR is deployed (for example, integration
      playbooks that consume LINSTOR resources or call the LINSTOR API).
    - The service may be C(disabled) (DRBD Reactor manages the
      controller in HA setups) but is still reported as defined; this
      filter treats "unit file exists" as "LINSTOR is installed".
  options:
    _input:
      description: The C(ansible_facts.services) dictionary.
      type: dict
      required: true
  author:
    - Ryan Ronnander (@rronnander)
'''

EXAMPLES = '''
- name: Gather service facts
  ansible.builtin.service_facts:

- name: Skip play if LINSTOR is not installed on this host
  ansible.builtin.meta: end_play
  when: not (ansible_facts.services | linbit.linstor.linstor_installed)
'''

RETURN = '''
  _value:
    description: C(True) when controller or satellite service is defined; C(False) otherwise.
    type: bool
'''


def linstor_installed(services):
    if not isinstance(services, dict):
        return False
    return (
        services.get('linstor-controller.service') is not None
        or services.get('linstor-satellite.service') is not None
    )


class FilterModule:
    def filters(self):
        return {'linstor_installed': linstor_installed}
