#!/bin/bash -eu
# SPDX-License-Identifier: MIT
# Bridge LS_ROOT_CA_FILE to LS_ROOT_CA for golinstor before 0.63.0, which reads
# the CA only as PEM content. Once golinstor >= 0.63.0 is the floor, drop this
# wrapper and let the systemd drop-in set LS_ROOT_CA_FILE directly.
if [ -n "${LS_ROOT_CA_FILE:-}" ] && [ -f "${LS_ROOT_CA_FILE}" ]; then
    LS_ROOT_CA="$(<"${LS_ROOT_CA_FILE}")"
    export LS_ROOT_CA
fi
exec /usr/sbin/linstor-gateway server "$@"
