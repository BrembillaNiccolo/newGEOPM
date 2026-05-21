# MPI idle/wait synthetic

**Class**: Communication slack / wait-phase detector.

**Why**: OSU collectives are useful, but a synthetic wait benchmark makes it easier to test one specific claim: CPU frequency can be reduced during MPI wait or barrier-like phases without hurting time to solution.

## Source

Local source should be a tiny MPI program added in Phase 1 if needed. The program should alternate between a configurable compute phase and a communication or wait phase.

Recommended loop:

1. Do fixed CPU work for `compute_ms`.
2. Enter `MPI_Barrier`, `MPI_Allreduce`, or a deliberate rank-skewed wait phase.
3. Repeat for `iterations`.
4. Print total runtime and per-phase timing.

## Build

```bash
module load oneapi/release cray-mpich

mpicxx -O3 -qopenmp mpi_idle_wait.cpp -o mpi_idle_wait
```

## Run

Balanced wait case:

```bash
mpiexec -n 32 ./mpi_idle_wait \
    --compute-ms 20 \
    --wait-ms 20 \
    --iterations 500 \
    --mode barrier
```

Rank-skewed case:

```bash
mpiexec -n 32 ./mpi_idle_wait \
    --compute-ms 20 \
    --wait-ms 80 \
    --skew-rank 0 \
    --iterations 500 \
    --mode allreduce
```

Wrap with `geopmlaunch` for sweeps once the basic timing looks stable.

## Expected runtime

1-5 minutes, depending on iteration count and wait duration.

## Validation criterion

The benchmark should report clear compute and wait phase timing. Repeats should have low variance in total runtime. If reducing CPU frequency during wait phases changes total runtime materially, the wait detector or phase construction is suspect.

## GEOPM hypothesis

- Lowering `CPU_FREQUENCY_MAX_CONTROL` during wait-heavy regions should reduce energy with little or no TTS penalty.
- The useful detector signals are low IPC, APERF/MPERF divergence, and region or phase timing if the synthetic benchmark is GEOPM-instrumented.
- This benchmark should de-risk OSU and Quicksilver by proving the slack-control path on a simple workload first.

## Sweep config

See `experiments/phase1/mpi-idle-wait/sweep.yaml` once Phase 1 configs are written.
