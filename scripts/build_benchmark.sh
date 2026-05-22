#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/build_benchmark.sh <benchmark|all>

Build a benchmark from benchmarks/registry.json.

Environment:
  CC        C compiler for local C benchmarks (default: icx if available, else gcc)
  CFLAGS   C flags for local C benchmarks (default: -O3 -std=c11 -march=native)
  CXX       C++ compiler for local benchmarks (default: g++)
  CXXFLAGS  C++ flags for local benchmarks (default: -O3 -std=c++17 -march=native)
  MPICXX    MPI C++ compiler (default: mpicxx)
  MPICXXFLAGS MPI C++ flags (default: -O3 -std=c++17)
  SYCL_CXX  SYCL compiler (default: icpx)
  SYCL_CXXFLAGS SYCL C++ flags (default: -O3 -std=c++17 -fsycl)
  STREAM_ARRAY_SIZE Elements for STREAM build (default: 10000000)
  STREAM_NTIMES STREAM iterations (default: 10)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -ne 1 ]]; then
    usage
    exit $([[ $# -eq 1 ]] && echo 0 || echo 2)
fi

bench="$1"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"
source "${repo_root}/scripts/python_common.sh"
python_bin="$(aurora_geopm_python)" || {
    echo "No usable Python found. Load a newer Python module or set AURORA_GEOPM_PYTHON." >&2
    exit 1
}

"${python_bin}" - "$bench" <<'PY'
import json
import os
import subprocess
import sys
from shutil import which
from pathlib import Path

requested = sys.argv[1]
registry = json.loads(Path("benchmarks/registry.json").read_text())

def pick(*names):
    for name in names:
        if name and which(name):
            return which(name)
    return names[-1]

def build_one(bench, entry):
    fmt = {
        "cc": os.environ.get("CC") or pick("icx", "gcc", "cc"),
        "cflags": os.environ.get("CFLAGS", "-O3 -std=c11 -march=native"),
        "cxx": os.environ.get("CXX") or pick("icpx", "g++", "c++"),
        "cxxflags": os.environ.get("CXXFLAGS", "-O3 -std=c++17 -march=native"),
        "mpicxx": os.environ.get("MPICXX") or pick("mpicxx", "CC", "mpic++"),
        "mpicxxflags": os.environ.get("MPICXXFLAGS", "-O3 -std=c++17"),
        "sycl_cxx": os.environ.get("SYCL_CXX") or pick("icpx", "dpcpp"),
        "sycl_cxxflags": os.environ.get("SYCL_CXXFLAGS", "-O3 -std=c++17 -fsycl"),
        "stream_array_size": os.environ.get("STREAM_ARRAY_SIZE", "10000000"),
        "stream_ntimes": os.environ.get("STREAM_NTIMES", "10"),
    }
    command = entry["build"]["command"].format(**fmt)

    binary = entry.get("binary", "")
    if binary and not binary.startswith("${"):
        Path(binary).parent.mkdir(parents=True, exist_ok=True)

    print(f"[build] {bench}: {command}")
    subprocess.run(command, shell=True, check=True, executable="/bin/bash")

if requested == "all":
    failures = []
    for bench, entry in registry["benchmarks"].items():
        try:
            build_one(bench, entry)
        except Exception as exc:
            failures.append((bench, str(exc)))
            print(f"[build:failed] {bench}: {exc}", file=sys.stderr)
    if failures:
        print("[build] failures:", file=sys.stderr)
        for bench, error in failures:
            print(f"  {bench}: {error}", file=sys.stderr)
        raise SystemExit(1)
else:
    try:
        entry = registry["benchmarks"][requested]
    except KeyError:
        known = ", ".join(sorted(registry["benchmarks"]))
        raise SystemExit(f"Unknown benchmark {requested!r}. Known: {known}")
    build_one(requested, entry)
PY
