# SPDX-License-Identifier: MIT
"""Filter plugin for Proxmox VE hostname normalization."""


class FilterModule:
    """Proxmox VE hostname filters."""

    def filters(self):
        return {'pve_hostname': self.pve_hostname}

    @staticmethod
    def pve_hostname(facts, hostname):
        """Return the short hostname on Proxmox VE, full hostname otherwise."""
        if 'pve' in facts.get('kernel', ''):
            return hostname.split('.')[0]
        return hostname
