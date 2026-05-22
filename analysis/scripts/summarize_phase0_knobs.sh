#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${repo_root}/scripts/python_common.sh"
python_bin="$(aurora_geopm_python)" || {
    echo "No usable Python found. Load a newer Python module or set AURORA_GEOPM_PYTHON." >&2
    exit 1
}

exec "${python_bin}" "${repo_root}/analysis/scripts/summarize_phase0_knobs.py" "$@"
