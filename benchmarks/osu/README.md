# OSU Micro-Benchmarks — `osu_alltoall` + `osu_allreduce`

**Class**: Comm-bound (MPI / Slingshot-11).

**Why**: clean collective signal with knobs (message size, rank count) to vary intensity. Large-message alltoall is the textbook GEOPM slack-power target — cores spinning in `MPI_Wait` can be slowed without TTS penalty.

## Source

Upstream: https://mvapich.cse.ohio-state.edu/benchmarks/

**Local**: `src/osu-micro-benchmarks-7.4/` (release recorded in `VERSION.txt`).

## Build

```bash
module load oneapi/release cray-mpich
cd benchmarks/osu/src/osu-micro-benchmarks-7.4
./configure CC=cc CXX=CC \
            --enable-cuda=no --enable-rocm=no --enable-sycl=no
make -j
```

Binaries land under `c/mpi/collective/osu_alltoall` and `osu_allreduce`.

(Note: SYCL build of OSU benchmarks would let us also test host-staged GPU collectives; skip for v1.)

## Run (multi-node, default 4 nodes × 8 ranks per node = 32 ranks)

```bash
export ZES_ENABLE_SYSMAN=1
mpiexec -n 32 ./osu_alltoall -m 1:8388608    # sweep msg sizes 1 B to 8 MB
mpiexec -n 32 ./osu_allreduce -m 1:8388608
```

For Phase 1, also run with 8 nodes × 8 = 64 ranks to see scaling effects.

## Expected runtime

Seconds per message size; minutes total per sweep.

## Validation criterion

OSU reports latency (µs) and/or bandwidth (MB/s) per message size. Sanity:

- Small-message latency on Slingshot-11: ~1-2 µs.
- Large-message alltoall bandwidth: scales with rank count; expect a few GB/s per rank pair at saturation.

Fail if latency >10 µs at small messages (indicates wrong fabric or bad rank placement).

## GEOPM hypothesis

- **`CPU_FREQUENCY_MAX_CONTROL` low** during collectives: 20%+ energy savings on comm phases, with little or no TTS hit (cores are waiting anyway).
- The challenge is *detecting the comm phase*: `REGION_HINT == network` if app sets it; otherwise use IPC drop + high `MSR::APERF/MPERF` divergence.
- `power_balancer` already does some of this; we should beat it on imbalanced collectives.

## Sweep config

See `experiments/phase1/osu/sweep.yaml` (written in Phase 1). Two binaries × {4, 8} nodes × knob grid.
