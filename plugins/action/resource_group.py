# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# Non-module plugins run in the Ansible controller process and must be
# GPL-3.0-or-later per the Ansible community package inclusion rules.
# The rest of the linbit.* collections remain MIT-licensed.
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.linbit.linstor.plugins.action._linstor_api import LinstorActionModule


class ActionModule(LinstorActionModule):
    pass
