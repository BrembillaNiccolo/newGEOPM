# HPCG

**Class**: Mixed (memory-bound smoother + comm-bound halo exchange). Realistic sparse-solver proxy.

**Why**: validates the agent's phase-aware behavior — within one app, different regions need different policies. Aligned with the ECP / Top500 HPCG list.

## Source

Two options:

- **Reference HPCG**: https://www.hpcg-benchmark.org — **Local**: `src/` (pinned commit in `VERSION.txt`: `114602d`).
- **Intel-optimized HPCG**: ships in oneAPI MKL on Aurora (`$MKLROOT/benchmarks/hpcg`).

Prefer Intel HPCG for headline numbers; reference HPCG as a control.

## Build

```bash
# Reference HPCG
module load oneapi/release cray-mpich
cd benchmarks/hpcg/src
# Pick a setup file from setup/ matching the toolchain, or create one
./configure ONEAPI-MPI    # or hand-edit Make.* for cc/CC wrappers
make -j
```

Intel HPCG is pre-built — `./xhpcg_avx512`.

## hpcg.dat (problem size)

Default `104 104 104` is small. For Aurora characterization:

- Per-node local size `nx ny nz`: choose so per-rank memory ~5 GB (HBM-friendly). With 8 ranks/node and 64 GB HBM/socket: ~250³ per rank works.

Edit `hpcg.dat` accordingly.

## Run (4-node default)

```bash
export ZES_ENABLE_SYSMAN=1
mpiexec -n 32 ./xhpcg_avx512    # 4 nodes × 8 ranks
```

## Expected runtime

Reference HPCG runs the official 30-minute test by default; set `runtime_min = 60` in `hpcg.dat` for shorter sweeps (5-10 min).

## Validation criterion

HPCG self-reports GFLOPS and a verification score. Pass = "PASS" in the output file. Sanity: HPCG numbers are ~1% of HPL on the same hardware (it's memory-bound).

## GEOPM hypothesis

- Mixed signature: smoother phase = memory-bound, halo phase = comm-bound.
- Static knobs (one freq for everything) under-perform a phase-aware agent.
- `frequency_map` agent with per-region freq should beat `monitor`; `aurora_bandit` should match or beat `frequency_map` without manual region annotation.

## Sweep config

See `experiments/phase1/hpcg/sweep.yaml` (written in Phase 1).
