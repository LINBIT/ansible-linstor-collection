# SPDX-License-Identifier: MIT
"""Shared action plugin base for linbit.linstor API modules.

The modules in ``action_groups.linstor`` (meta/runtime.yml) all talk to the
LINSTOR REST API via ``python-linstor`` and are typically invoked with
``delegate_to: localhost`` (or another reachable node, see
``linstor_api_delegate``). They never need privileged execution on the
delegate.

When a parent play sets ``become: true`` (common for OS-level provisioning),
that become bleeds into the delegated task and triggers a sudo prompt on the
control node, which usually fails because the local user does not have
passwordless root. This base forces become off so the API modules behave
correctly regardless of the surrounding play.

Users who genuinely need privileged execution on the delegate can still set
``become_user: root`` (or use a shell wrapper) on the individual task.
"""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.plugins.action.normal import ActionModule as NormalAction


class LinstorActionModule(NormalAction):
    def run(self, tmp=None, task_vars=None):
        self._task.become = False
        if self._play_context is not None:
            self._play_context.become = False
        # Clear the live connection's become plugin too. PlayContext alone is
        # not enough: by the time the action plugin runs, the connection has
        # already been built with become enabled, and _low_level_execute_command
        # wraps shell commands using self._connection.become directly.
        if self._connection is not None:
            self._connection.become = None
        return super(LinstorActionModule, self).run(tmp, task_vars)
