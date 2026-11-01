# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# Non-module plugins run in the Ansible controller process and must be
# GPL-3.0-or-later per the Ansible community package inclusion rules.
# The rest of the linbit.* collections remain MIT-licensed.
"""Shared parsing of the platform_storage key of resource groups and ha_gateway targets, and of
the Aux/PlatformStorage properties that store it."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import re
from collections.abc import Mapping

from ansible.errors import AnsibleFilterError
from ansible.module_utils.common.collections import is_sequence
from ansible.module_utils.parsing.convert_bool import boolean

PROPERTY = 'Aux/PlatformStorage'

# A purpose becomes a property key path element and an entry of a comma-separated value
PURPOSE = re.compile(r'[^/,\s]+')


def _fail(owner, message):
    raise AnsibleFilterError('platform_storage of %s %s' % (owner, message))


def _check_purpose(owner, purpose):
    if not isinstance(purpose, str) or not PURPOSE.fullmatch(purpose):
        _fail(owner, "has the purpose %r, which must be a non-empty string without '/', ',' "
                     "or whitespace" % (purpose,))
    try:
        boolean(purpose, strict=True)
    except TypeError:
        return purpose
    _fail(owner, "has the purpose %r, which reads as a boolean: set true for the platform's "
                 "defaults" % (purpose,))


def normalize(value, owner):
    """Return None, False, True, or a dict of purpose to name, with '' for a default name."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        try:
            return boolean(value, strict=True)
        except TypeError:
            _fail(owner, "is the string %r: set true, false, a list of purposes or a dict of "
                         "purpose to name" % (value,))
    if isinstance(value, Mapping):
        purposes = {}
        for purpose, name in value.items():
            purpose = _check_purpose(owner, purpose)
            if name is not None and not isinstance(name, str):
                _fail(owner, "gives the purpose %s the name %r, which must be a string, or empty "
                             "for the platform's default name" % (purpose, name))
            purposes[purpose] = (name or '').strip()
    elif is_sequence(value):
        purposes = {}
        for purpose in value:
            purposes[_check_purpose(owner, purpose)] = ''
    else:
        _fail(owner, "is %r: set true, false, a list of purposes or a dict of purpose to name"
                     % (value,))
    if not purposes:
        _fail(owner, "names no purpose: set true for the platform's defaults or false for none")
    return purposes


def properties(value, owner='the entry'):
    """Return the Aux properties that tag a LINSTOR object with a platform_storage value."""
    purposes = normalize(value, owner)
    if not purposes:
        return {}
    if purposes is True:
        return {PROPERTY: 'True'}
    result = {PROPERTY: ','.join(purposes)}
    for purpose, name in purposes.items():
        if name:
            result['%s/%s/Name' % (PROPERTY, purpose)] = name
    return result


def from_properties(props, owner='the entry'):
    """Return the normal form of the value that the Aux/PlatformStorage properties store.

    The reverse of properties(): None without the property, True or False for a boolean value,
    or a dict of each purpose of the comma-separated value, in order, to its
    Aux/PlatformStorage/<purpose>/Name property, '' when that is missing or blank.
    """
    props = props or {}
    value = props.get(PROPERTY)
    if value is None:
        return None
    value = str(value).strip()
    try:
        return boolean(value, strict=True)
    except TypeError:
        pass
    purposes = {}
    for purpose in value.split(','):
        purpose = purpose.strip()
        if purpose:
            purposes[purpose] = str(props.get('%s/%s/Name' % (PROPERTY, purpose)) or '').strip()
    if not purposes:
        _fail(owner, "is the property %s=%r, which names no purpose" % (PROPERTY, value))
    return purposes
