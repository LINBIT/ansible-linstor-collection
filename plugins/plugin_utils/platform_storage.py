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

# A key becomes a property key path element and an entry of a comma-separated value
KEY = re.compile(r'[^/,\s]+')


def _fail(owner, message):
    raise AnsibleFilterError('platform_storage of %s %s' % (owner, message))


def _check_key(owner, key):
    if not isinstance(key, str) or not KEY.fullmatch(key):
        _fail(owner, "has the invalid key %r: use a non-empty string without '/', ',' or "
                     "whitespace" % (key,))
    try:
        boolean(key, strict=True)
    except TypeError:
        return key
    _fail(owner, "has the key %r, which reads as a boolean: set platform_storage to true for "
                 "the defaults of the platform, or use a key the platform accepts" % (key,))


def normalize(value, owner):
    """Return None, False, True, or a dict that maps each key to a name, '' for a default name."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        try:
            return boolean(value, strict=True)
        except TypeError:
            _fail(owner, "is the string %r: use true, false, a list of keys, or a dict that maps "
                         "keys to names" % (value,))
    if isinstance(value, Mapping):
        keys = {}
        for key, name in value.items():
            key = _check_key(owner, key)
            if name is not None and not isinstance(name, str):
                _fail(owner, "has the invalid name %r for the key %s: use a string, or null or "
                             "empty for the default name of the platform" % (name, key))
            keys[key] = (name or '').strip()
    elif is_sequence(value):
        keys = {}
        for key in value:
            keys[_check_key(owner, key)] = ''
    else:
        _fail(owner, "is %r: use true, false, a list of keys, or a dict that maps keys to names"
                     % (value,))
    if not keys:
        _fail(owner, "has no keys: set true for the defaults of the platform, or false for none")
    return keys


def properties(value, owner='the entry'):
    """Return the Aux properties that tag a LINSTOR object with a platform_storage value."""
    keys = normalize(value, owner)
    if not keys:
        return {}
    if keys is True:
        return {PROPERTY: 'True'}
    result = {PROPERTY: ','.join(keys)}
    for key, name in keys.items():
        if name:
            result['%s/%s/Name' % (PROPERTY, key)] = name
    return result


def from_properties(props, owner='the entry'):
    """Read a platform_storage value back from the Aux/PlatformStorage properties.

    The reverse of properties(): None without the property, True or False for a boolean value,
    or a dict that maps each key of the comma-separated value, in order, to its
    Aux/PlatformStorage/<key>/Name property, '' when that is missing or blank.
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
    keys = {}
    for key in value.split(','):
        key = key.strip()
        if key:
            keys[key] = str(props.get('%s/%s/Name' % (PROPERTY, key)) or '').strip()
    if not keys:
        _fail(owner, "is the property %s=%r, which has no keys" % (PROPERTY, value))
    return keys
