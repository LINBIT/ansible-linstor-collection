# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# Non-module plugins run in the Ansible controller process and must be
# GPL-3.0-or-later per the Ansible community package inclusion rules.
# The rest of the linbit.* collections remain MIT-licensed.
"""Filter plugin: build the LINSTOR Aux properties for a platform_storage value."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.linbit.linstor.plugins.plugin_utils.platform_storage import properties

DOCUMENTATION = '''
  name: platform_storage_properties
  short_description: Build the LINSTOR properties for a platform_storage value
  version_added: "0.9.12"
  description:
    - Returns the C(Aux/PlatformStorage) properties for the C(platform_storage) key of a
      C(linstor_resource_groups) entry, which names the platform storage objects that the
      resource group backs.
    - C(true) returns C(Aux/PlatformStorage=True), for the platform's defaults. C(false) or
      null returns no properties.
    - A list of purposes, or a dict of purpose to name, returns C(Aux/PlatformStorage) with the
      purposes joined by commas in the order given, plus C(Aux/PlatformStorage/<purpose>/Name)
      for each purpose with a name. A purpose with an empty, whitespace-only or null name keeps
      the platform's default name.
    - Purposes are free strings that the platform integration roles interpret. Each must be a
      non-empty string without C(/), C(,) or whitespace that does not read as a boolean, such
      as C(yes) or C(1), and the filter fails on any other value.
    - The C(resource_group) role sets these properties on each resource group.
  positional: _input, owner
  options:
    _input:
      description: The C(platform_storage) value.
      type: raw
      required: true
    owner:
      description: The object the value belongs to, named in error messages.
      type: str
      default: the entry
  author:
    - Ryan Ronnander (@rronnander)
'''

EXAMPLES = '''
- name: The properties of a resource group entry
  ansible.builtin.set_fact:
    rg_properties: >-
      {{ {'system': 'fast_vms', 'image': ''}
         | linbit.linstor.platform_storage_properties('resource group rg-vm') }}
  # => {'Aux/PlatformStorage': 'system,image',
  #     'Aux/PlatformStorage/system/Name': 'fast_vms'}

- name: The properties of an entry that takes the platform's defaults
  ansible.builtin.set_fact:
    rg_properties: "{{ true | linbit.linstor.platform_storage_properties }}"
  # => {'Aux/PlatformStorage': 'True'}
'''

RETURN = '''
  _value:
    description:
      - The C(Aux/PlatformStorage) properties, keyed by full property name, or an empty dict
        when the value is C(false) or null.
    type: dict
'''


class FilterModule:
    def filters(self):
        return {'platform_storage_properties': properties}
