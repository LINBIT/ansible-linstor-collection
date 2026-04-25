# SPDX-License-Identifier: MIT
"""Filter plugins for ha_gateway placement and satellite resolution."""


class FilterModule:
    """ha_gateway filters."""

    def filters(self):
        return {
            'gateway_placement': self.gateway_placement,
            'gateway_resolve_satellites': self.gateway_resolve_satellites,
        }

    @staticmethod
    def gateway_placement(explicit, rg_check_results, place_count_default,
                          storage_pool_default, sizes_key, tickle_dir_size):
        """Build the manual placement list for linbit.linstor.resource mode=manual."""
        rg_pc = {
            r['_target']['name']: int(r.get('place_count') or 2)
            for r in (rg_check_results or [])
        }

        result = []
        for t in explicit:
            has_rg = 'resource_group' in t
            pc_default = int(t.get('place_count') or place_count_default)
            pc = rg_pc.get(t['name'], pc_default) if has_rg else pc_default

            vol_sizes = [tickle_dir_size] + [v['size'] for v in t[sizes_key]]
            sp = t.get('storage_pool') or storage_pool_default or ''

            node_entries = []
            for i, n in enumerate(t['nodes']):
                is_diskless = i >= pc
                node_entries.append({
                    'node': n,
                    'diskless': is_diskless,
                    'storage_pool': sp if (not has_rg and not is_diskless) else '',
                })

            result.append({
                'resource_name': t['_rd_name'],
                'nodes': node_entries,
                'sizes': vol_sizes if not has_rg else [],
            })
        return result

    @staticmethod
    def gateway_resolve_satellites(query_results):
        """Split query results into diskful and diskless node lists per target."""
        resolved = []
        for result in (query_results or []):
            t = result['_target']
            if t.get('nodes'):
                resolved.append(t)
                continue

            diskful = []
            diskless = []
            flags = result.get('flags', {})
            for ln in result.get('nodes', []):
                node_flags = flags.get(ln, [])
                if 'DRBD_DISKLESS' in node_flags or 'TIE_BREAKER' in node_flags:
                    diskless.append(ln)
                else:
                    diskful.append(ln)

            resolved.append({**t, 'nodes': diskful + diskless})
        return resolved
