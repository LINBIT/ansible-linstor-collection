# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# Non-module plugins run in the Ansible controller process and must be
# GPL-3.0-or-later per the Ansible community package inclusion rules.
# The rest of the linbit.* collections remain MIT-licensed.
from __future__ import absolute_import, division, print_function
__metaclass__ = type


class ModuleDocFragment(object):

    DOCUMENTATION = r'''
options:
  controllers:
    description:
      - Comma-separated list of LINSTOR controller URIs.
      - If omitted, reads from C(LS_CONTROLLERS) env, then the C(controllers) key of
        the LINSTOR client configuration (see O(config_file)), then falls back to
        C(linstor://localhost).
    type: str
  auth_token:
    description:
      - LINSTOR auth token for clusters with token authentication enabled.
      - If omitted, reads C(auth-token) from the LINSTOR client configuration (see
        O(config_file)), then falls back to C(/var/lib/linstor.d/auth.json) on
        satellite nodes.
    type: str
  config_file:
    description:
      - Path to a C(linstor-client.conf) to read the controller list, auth token, and
        TLS certificate paths from, in place of the default locations.
      - If omitted, or if the file does not exist, reads C(~/.config/linstor/linstor-client.conf),
        then C(/etc/linstor/linstor-client.conf), the same locations the C(linstor) CLI reads.
      - >-
        When the module runs on the Ansible control node, the collection's action plugin fills
        this in from the C(linstor_client_config_file) variable if it is defined, so one
        inventory variable points every LINSTOR module at a per-inventory client configuration.
    type: path
    version_added: 0.9.10
'''
