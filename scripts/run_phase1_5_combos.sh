#!/usr/bin/env bash
# Thin wrapper around scripts/run_phase1_5_combos.py — same idiom as
# scripts/run_phase0_sweep.sh: picks an Aurora-compatible Python and exec's
# the runner with all args forwarded.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${repo_root}/scripts/python_common.sh"
python_bin="$(aurora_geopm_python)" || {
    echo "No usable Python found. Load a newer Python module or set AURORA_GEOPM_PYTHON." >&2
    exit 1
}

exec "${python_bin}" "${repo_root}/scripts/run_phase1_5_combos.py" "$@"
