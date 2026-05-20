# Quicksilver

**Class**: Comm-bound, load-imbalanced (Monte Carlo neutron transport). ECP proxy.

**Why**: load imbalance creates uneven `MPI_Wait` slack — perfect target for slack-aware agents. The textbook `power_balancer` benchmark; our `aurora_bandit` should match or beat it.

## Source

Upstream: https://github.com/LLNL/Quicksilver

**Local**: `src/` (pinned commit in `VERSION.txt`: `eb68bb8`).

## Build

```bash
module load oneapi/release cray-mpich
cd benchmarks/quicksilver/src/src
# Choose Makefile target — Intel CPU build:
make CXX=CC OPENMP_FLAGS="-qopenmp" MPI_HOME=$CRAY_MPICH_DIR
```

Binary: `qs`.

(SYCL/PVC port of Quicksilver exists in some forks but is not upstream — stick to CPU build for v1.)

## Run (8-node default for load imbalance to show)

```bash
export OMP_NUM_THREADS=<phys cores per rank>
mpiexec -n 64 ./qs -i Examples/CORAL2_Benchmark/CORAL2_P1.inp
```

CORAL2 inputs intentionally trigger load imbalance; use those, not the trivially balanced examples.

## Expected runtime

5-30 minutes depending on input deck.

## Validation criterion

Quicksilver prints a "Final tracks/sec" figure and a hash. Verify the hash against the input deck's published value (in the input directory).

## GEOPM hypothesis

- **`power_balancer` agent** baseline: should already do well here (it's designed for this).
- **`aurora_bandit`**: per-rank slack detection (via per-rank `MSR::APERF/MPERF` divergence) → deprioritize ranks observed waiting → either drop their freq or borrow their power budget. Should match `power_balancer` on absolute power but additionally exploit GPU knobs (which `power_balancer` doesn't touch).
- Expected detector signal: high variance in IPC across ranks within a node.

## Sweep config

See `experiments/phase1/quicksilver/sweep.yaml` (written in Phase 1).
