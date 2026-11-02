# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# Non-module plugins run in the Ansible controller process and must be
# GPL-3.0-or-later per the Ansible community package inclusion rules.
# The rest of the linbit.* collections remain MIT-licensed.
"""Filter plugin: list the subject alternative names a certificate lacks."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
  name: san_missing
  short_description: List the subject alternative names a certificate lacks
  version_added: "0.9.12"
  description:
    - Compares the subject alternative names a certificate should have with the
      ones C(openssl x509 -noout -ext subjectAltName) prints for it.
    - Compares IP addresses as addresses, so C(IP:fd00::10) matches the
      C(IP Address:FD00:0:0:0:0:0:0:10) that OpenSSL prints.
  options:
    _input:
      description: The wanted names, comma-separated, such as C(DNS:node-0,IP:10.0.0.10).
      type: str
      required: true
    certificate:
      description: The C(openssl x509 -noout -ext subjectAltName) output of the certificate.
      type: str
      required: true
  author:
    - Ryan Ronnander (@rronnander)
'''

EXAMPLES = '''
- name: Show the names the node certificate lacks
  ansible.builtin.debug:
    msg: "{{ 'DNS:node-0,IP:10.0.0.10' | linbit.linstor.san_missing(_openssl_san.stdout) }}"
'''

RETURN = '''
  _value:
    description: The wanted names the certificate lacks, in the C(DNS:) and C(IP:) form of the input.
    type: list
    elements: str
'''

import ipaddress
import re


def _normalize(kind, value):
    if kind == 'IP':
        try:
            return 'IP', str(ipaddress.ip_address(value))
        except ValueError:
            return 'IP', value
    return kind, value


def san_missing(wanted, certificate):
    have = set()
    for kind, value in re.findall(r'(DNS|IP Address):([^,\s]+)', certificate or ''):
        have.add(_normalize('IP' if kind == 'IP Address' else kind, value))
    missing = []
    for entry in (wanted or '').split(','):
        kind, sep, value = entry.strip().partition(':')
        if sep and value and _normalize(kind, value) not in have:
            missing.append(entry.strip())
    return missing


class FilterModule:
    def filters(self):
        return {'san_missing': san_missing}
