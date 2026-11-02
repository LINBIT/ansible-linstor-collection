# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# Non-module plugins run in the Ansible controller process and must be
# GPL-3.0-or-later per the Ansible community package inclusion rules.
# The rest of the linbit.* collections remain MIT-licensed.
"""Shared parsing of the platform_storage key of resource groups and ha_gateway targets."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from collections.abc import Mapping

from ansible.errors import AnsibleFilterError
from ansible.module_utils.common.collections import is_sequence
from ansible.module_utils.parsing.convert_bool import boolean


def _fail(owner, message):
    raise AnsibleFilterError('platform_storage of %s %s' % (owner, message))


def _check_key(owner, key):
    if not isinstance(key, str) or not key.strip():
        _fail(owner, "has the invalid key %r: use a non-empty string" % (key,))
    try:
        boolean(key, strict=True)
    except TypeError:
        return key
    _fail(owner, "has the key %r, which reads as a boolean: set platform_storage to true for "
                 "the defaults of the platform, or use a key the platform accepts" % (key,))


def _entry(owner, key, entry):
    if entry is None or isinstance(entry, str):
        return (entry or '').strip()
    if not isinstance(entry, Mapping):
        _fail(owner, "has the invalid name %r for the key %s: use a string, null or empty for the "
                     "default name of the platform, or a dict of a name and platform options"
                     % (entry, key))
    name = entry.get('name')
    if name is not None and not isinstance(name, str):
        _fail(owner, "has the invalid name %r for the key %s: use a string, or null or empty for "
                     "the default name of the platform" % (name, key))
    invalid = [option for option in entry if not isinstance(option, str)]
    if invalid:
        _fail(owner, "has the invalid options %s for the key %s: use strings as option names"
                     % (', '.join(repr(option) for option in invalid), key))
    return dict(entry, name=(name or '').strip())


def normalize(value, owner):
    """Return None, False, True, or a dict that maps each key to a name, or to a dict of
    platform options with a 'name' key, '' for the default name in either form."""
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
        for key, entry in value.items():
            key = _check_key(owner, key)
            keys[key] = _entry(owner, key, entry)
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
