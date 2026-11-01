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
      C(linstor_resource_groups) entry or an C(ha_gateway) target. The key selects the storage
      that the platform integration roles create on the resource group or target, such as a
      Proxmox VE storage or an OpenNebula datastore.
    - C(true) returns C(Aux/PlatformStorage=True), for the defaults of the platform. C(false) or
      null returns no properties.
    - "A list of keys such as C([system, image]), or a dict that maps keys to names such as
      C({system: fast_vms}), returns C(Aux/PlatformStorage) with the keys joined by commas in
      the order given, plus C(Aux/PlatformStorage/<key>/Name) for each key with a name. An
      empty, whitespace-only or null name selects the default name of the platform."
    - The platform integration roles decide which keys they accept. This filter fails on a key
      that is empty, contains C(/), C(,) or whitespace, or reads as a boolean, such as C(yes)
      or C(1), and on any value of another type.
    - The C(platform_storage) value returned by P(linbit.linstor.gateway_targets#filter) is a
      valid input too.
    - The C(resource_group) role sets these properties on each resource group and the
      C(ha_gateway) role on the resource definition of each target.
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

- name: The properties of an entry that takes the defaults of the platform
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
