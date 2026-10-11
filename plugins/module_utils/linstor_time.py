# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import calendar
import re
import time
from datetime import datetime

ISO_RE = re.compile(
    r'^(\d{4})-(\d{2})-(\d{2})'
    r'(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?'
    r'\s*(Z|[+-]\d{2}:?\d{2})?$')
AGE_RE = re.compile(r'^(?:\d+[smhd])+$')
AGE_PART_RE = re.compile(r'(\d+)([smhd])')
AGE_SECONDS = dict(s=1, m=60, h=3600, d=86400)

TIME_FORMATS_HELP = "an ISO 8601 timestamp or an age such as 30m"


def parse_epoch(value):
    """Turn an ISO 8601 timestamp or an age such as 1h30m into seconds since the epoch.

    A timestamp without a time zone is local time. Returns None for anything else.
    """
    value = value.strip()
    if AGE_RE.match(value):
        age = sum(int(n) * AGE_SECONDS[unit] for n, unit in AGE_PART_RE.findall(value))
        return time.time() - age
    match = ISO_RE.match(value)
    if not match:
        return None
    year, month, day, hour, minute, second, zone = match.groups()
    fields = (int(year), int(month), int(day),
              int(hour or 0), int(minute or 0), int(second or 0))
    if zone is None:
        return time.mktime(fields + (0, 0, -1))
    epoch = calendar.timegm(fields + (0, 0, 0))
    if zone != 'Z':
        sign = -1 if zone[0] == '-' else 1
        digits = zone[1:].replace(':', '')
        epoch -= sign * (int(digits[:2]) * 3600 + int(digits[2:]) * 60)
    return epoch


def parse_linstor_time(value):
    """Parse a time option into the datetime python-linstor takes, or None if invalid."""
    epoch = parse_epoch(value)
    if epoch is None:
        return None
    # python-linstor converts with time.mktime(), which reads a naive datetime as local time
    return datetime.fromtimestamp(epoch)


def format_epoch_ms(epoch_ms):
    """Format milliseconds since the epoch as an ISO 8601 timestamp in UTC."""
    seconds, millis = divmod(int(epoch_ms), 1000)
    return '%s.%03dZ' % (time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(seconds)), millis)
