#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${repo_root}/scripts/python_common.sh"

# Load Aurora python module if available (gives us python3.10/3.12 so the
# analyzer's modern type hints parse). Safe no-op on systems without `module`.
: "${AURORA_PYTHON_MODULE:=python/3.12.12}"
if type module >/dev/null 2>&1; then
    [[ -d /soft/modulefiles ]] && module use /soft/modulefiles >/dev/null 2>&1 || true
    module load "${AURORA_PYTHON_MODULE}" >/dev/null 2>&1 || true
    hash -r
fi

python_bin="$(aurora_geopm_python)" || {
    echo "No usable Python found. Load a newer Python module or set AURORA_GEOPM_PYTHON." >&2
    exit 1
}

exec "${python_bin}" "${repo_root}/analysis/scripts/summarize_phase0_knobs.py" "$@"
