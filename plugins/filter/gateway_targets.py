# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# Non-module plugins run in the Ansible controller process and must be
# GPL-3.0-or-later per the Ansible community package inclusion rules.
# The rest of the linbit.* collections remain MIT-licensed.
"""Filter plugin: normalize ha_gateway target lists with the names and addresses clients use."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import re

from ansible.errors import AnsibleFilterError
from ansible.module_utils.parsing.convert_bool import boolean

DOCUMENTATION = '''
  name: gateway_targets
  short_description: Normalize an ha_gateway target list into the targets clients connect to
  version_added: "0.9.12"
  description:
    - Returns one entry per entry of C(linstor_iscsi_targets), C(linstor_nfs_exports) or
      C(linstor_nvmeof_targets), in order, with the LINSTOR resource name, the IQN or NQN, the
      port and the export paths that the C(ha_gateway) role creates for it.
    - The C(ha_gateway) role deploys its targets from this output, and the platform integration
      roles in C(linbit.linstor_integrations) read it to attach the targets marked with
      C(use_for_plugin) to the platform, so the two cannot drift.
    - Each output entry keeps the keys of its input entry and sets C(type), C(resource),
      C(state), C(use_for_plugin) as a boolean, C(service_ips) without prefixes, C(address)
      (the first service IP) and C(port).
    - An C(iscsi) entry gets C(iqn), an C(nvmeof) entry C(nqn) and C(transport), and each entry
      of an C(nfs) entry's C(exports) list gets C(export), its full path under
      C(/srv/gateway-exports/<resource>).
    - Names are used as given, like C(linstor-gateway) does. An entry named C(nfs-shared) gets
      the resource C(nfs-shared), and an C(iscsi) entry named C(iscsi-web) without C(iqn) gets
      the IQN C(base:iscsi-web) and the resource C(iscsi-web).
  positional: _input, type, base, port
  options:
    _input:
      description: One of the three C(ha_gateway) target lists.
      type: list
      elements: dict
      required: true
    type:
      description: The type of the targets in the list.
      type: str
      choices:
        - iscsi
        - nfs
        - nvmeof
      required: true
    base:
      description:
        - The IQN base or NQN base put before the name as C(base:name) when an C(iscsi) or
          C(nvmeof) entry sets no C(iqn) or C(nqn). Ignored for C(nfs).
        - Defaults to the C(ha_gateway) default, C(iqn.2026-06.com.linbit) or
          C(nqn.2026-06.io.linbit:nvme).
      type: str
    port:
      description:
        - The port of the entries that set no C(target_port) (C(iscsi), C(nvmeof)) or C(port)
          (C(nfs)).
        - Defaults to the C(ha_gateway) default, 3260, 2049 or 4420.
      type: int
  author:
    - Ryan Ronnander (@rronnander)
'''

EXAMPLES = '''
- name: The iSCSI targets with the IQN and port ha_gateway gives them
  ansible.builtin.set_fact:
    iscsi_targets: >-
      {{ linstor_iscsi_targets | default([])
         | linbit.linstor.gateway_targets('iscsi', ha_gateway_iscsi_iqn_base,
                                          ha_gateway_iscsi_port) }}

- name: The NFS exports and iSCSI targets marked for the platform plugin
  ansible.builtin.set_fact:
    plugin_targets: >-
      {{ (linstor_nfs_exports | default([]) | linbit.linstor.gateway_targets('nfs')
          + linstor_iscsi_targets | default([]) | linbit.linstor.gateway_targets('iscsi'))
         | selectattr('use_for_plugin') | selectattr('state', 'eq', 'present') | list }}
'''

RETURN = '''
  _value:
    description:
      - The input entries with C(type), C(resource), C(state), C(use_for_plugin),
        C(service_ips), C(address) and C(port) set, plus C(iqn), or C(nqn) and C(transport), or
        C(export) on each entry of C(exports), by type.
      - For example an entry of C(linstor_nfs_exports) named C(shared) with the exports C(/data)
        and C(/home) returns C(resource=shared), C(port=2049) and the exports with
        C(export=/srv/gateway-exports/shared/data) and C(export=/srv/gateway-exports/shared/home).
    type: list
    elements: dict
'''

EXPORT_ROOT = '/srv/gateway-exports'

# linstor-gateway pkg/iscsi/iqn.go: rtslib rejects '_' in a WWN, which is also the LINSTOR resource name
ISCSI_WWN = re.compile(r'^[a-z][a-z0-9-]+$')

DEFAULTS = {
    'iscsi': {'base': 'iqn.2026-06.com.linbit', 'port': 3260, 'port_key': 'target_port'},
    'nfs': {'base': None, 'port': 2049, 'port_key': 'port'},
    'nvmeof': {'base': 'nqn.2026-06.io.linbit:nvme', 'port': 4420, 'port_key': 'target_port'},
}


def _value(entry, key, default):
    value = entry.get(key)
    return default if value is None or value == '' else value


def gateway_targets(targets, type, base=None, port=None):
    if type not in DEFAULTS:
        raise AnsibleFilterError(
            "gateway_targets: type must be iscsi, nfs or nvmeof, not %r" % type)
    defaults = DEFAULTS[type]
    base = base or defaults['base']
    port = port or defaults['port']

    result = []
    for entry in (targets or []):
        if not isinstance(entry, dict) or not entry.get('name'):
            raise AnsibleFilterError(
                "gateway_targets: every %s entry needs a name, got %r" % (type, entry))
        name = entry['name']
        service_ips = [str(ip).partition('/')[0] for ip in (entry.get('service_ips') or [])]
        target = dict(entry)
        target.update({
            'type': type,
            'state': entry.get('state') or 'present',
            'use_for_plugin': boolean(_value(entry, 'use_for_plugin', False), strict=False),
            'service_ips': service_ips,
            'address': service_ips[0] if service_ips else None,
            'port': int(_value(entry, defaults['port_key'], port)),
        })
        if type == 'iscsi':
            target['iqn'] = _value(entry, 'iqn', base + ':' + name)
            target['resource'] = target['iqn'].split(':')[-1]
            if not ISCSI_WWN.match(target['resource']):
                raise AnsibleFilterError(
                    "gateway_targets: iSCSI target %s has the WWN %r, which LINSTOR Gateway rejects: "
                    "a lowercase letter, then lowercase letters, digits or '-'"
                    % (name, target['resource']))
        elif type == 'nvmeof':
            target['nqn'] = _value(entry, 'nqn', base + ':' + name)
            parts = target['nqn'].split(':')
            if len(parts) != 3:
                raise AnsibleFilterError(
                    "gateway_targets: NVMe-oF target %s has the NQN %r, which LINSTOR Gateway rejects: "
                    "it needs exactly three ':' separated parts, <vendor>:nvme:<subsystem>"
                    % (name, target['nqn']))
            target['resource'] = parts[2]
            target['transport'] = 'tcp'
        else:
            target['resource'] = name
            exports = []
            for export in (entry.get('exports') or []):
                path = EXPORT_ROOT + '/' + name + (export.get('path') or '/')
                exports.append(dict(export, export=path[:-1] if path.endswith('/') else path))
            target['exports'] = exports
        result.append(target)
    return result


class FilterModule:
    def filters(self):
        return {'gateway_targets': gateway_targets}
