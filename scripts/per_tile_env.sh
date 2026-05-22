#!/usr/bin/env bash
# Pin each MPI rank to a specific PVC tile via ZE_AFFINITY_MASK.
# Use as: mpiexec -n 12 -ppn 12 scripts/per_tile_env.sh <bench> <args>
#
# Aurora node = 6 PVC cards x 2 tiles = 12 tiles total.
# Mapping (12 ranks per node): rank N -> card (N/2), tile (N%2)
#   rank 0  -> 0.0   rank 1  -> 0.1   rank 2  -> 1.0   rank 3  -> 1.1
#   rank 4  -> 2.0   rank 5  -> 2.1   rank 6  -> 3.0   rank 7  -> 3.1
#   rank 8  -> 4.0   rank 9  -> 4.1   rank 10 -> 5.0   rank 11 -> 5.1
#
# Each rank's SYCL default_selector will see exactly its one tile, so benches
# written with `sycl::queue(sycl::default_selector_v)` work unchanged.

set -euo pipefail

# PALS exposes the local rank as PALS_LOCAL_RANKID; legacy MPICH/Hydra uses PMI_LOCAL_RANK.
RANK="${PALS_LOCAL_RANKID:-${PMI_LOCAL_RANK:-0}}"

CARD=$(( RANK / 2 ))
TILE=$(( RANK % 2 ))

export ZE_AFFINITY_MASK="${CARD}.${TILE}"
: "${ZES_ENABLE_SYSMAN:=1}"
export ZES_ENABLE_SYSMAN

# Optional: log placement on rank 0 only so meta is human-readable
if [[ "${RANK}" == "0" ]]; then
    echo "[per_tile_env] rank=${RANK} ZE_AFFINITY_MASK=${ZE_AFFINITY_MASK} cmd: $*" >&2
fi

exec "$@"
