# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (https://www.gnu.org/licenses/gpl-3.0.txt)
# Non-module plugins run in the Ansible controller process and must be
# GPL-3.0-or-later per the Ansible community package inclusion rules.
# The rest of the linbit.* collections remain MIT-licensed.
"""Shared action plugin base for linbit.linstor API modules.

The modules in ``action_groups.linstor`` (meta/runtime.yml) all talk to the
LINSTOR REST API via ``python-linstor`` and are typically invoked with
``delegate_to: localhost`` (or another reachable node, see
``linstor_api_delegate``). They need no privileged execution on the control
node.

When a parent play sets ``become: true`` (common for OS-level provisioning),
that become bleeds into the delegated task and triggers a sudo prompt on the
control node, which usually fails because the local user does not have
passwordless root. This base forces become off for *local* execution so the
API modules behave correctly regardless of the surrounding play.

Become is left intact when the delegate is a remote host. ``auth_init`` saves
the cluster's auth token into ``/root/.config/linstor/linstor-client.conf`` on
controller nodes, so a remote delegate must run privileged to read it;
stripping become there makes every subsequent API task fail with "requires
token authentication, but no token was found".

Local execution is detected from the connection plugin, so an inventory entry
for ``localhost`` that connects over SSH counts as remote and keeps become.

Users who genuinely need privileged execution on a local delegate can still
set ``become_user: root`` (or use a shell wrapper) on the individual task.
"""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.plugins.action.normal import ActionModule as NormalAction


class LinstorActionModule(NormalAction):
    def _is_local_execution(self):
        """True when the module executes on the Ansible control node.

        Only local execution can hit the sudo-prompt problem this class works
        around. A remote delegate needs become preserved so it can read the
        auth token from root's linstor-client.conf.
        """
        conn = self._connection
        return conn is not None and getattr(conn, 'transport', None) in (
            'local', 'ansible.builtin.local')

    def run(self, tmp=None, task_vars=None):
        if self._is_local_execution():
            self._task.become = False
            if self._play_context is not None:
                self._play_context.become = False
            # Clear the live connection's become plugin too. PlayContext alone
            # is not enough: by the time the action plugin runs, the connection
            # has already been built with become enabled, and
            # _low_level_execute_command wraps shell commands using
            # self._connection.become directly.
            if self._connection is not None:
                self._connection.become = None
        return super(LinstorActionModule, self).run(tmp, task_vars)
