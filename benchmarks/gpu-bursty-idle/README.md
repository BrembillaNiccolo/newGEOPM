# GPU bursty idle synthetic

**Class**: GPU burst / idle behavior.

**Why**: the always-on energy-saving claim depends on recognizing periods where the GPU does not need full frequency. Saturated kernels like DGEMM and BabelStream are necessary, but they do not test idle gaps between GPU bursts.

## Source

Local source should be a small SYCL program added in Phase 1 if needed. It should launch repeated GPU kernels separated by configurable idle, CPU, or MPI phases.

Recommended loop:

1. Launch a GPU kernel sized to run for `kernel_ms`.
2. Synchronize.
3. Spend `gap_ms` in CPU work, MPI wait, or sleep.
4. Repeat for `iterations`.
5. Print total runtime and kernel/gap timing.

## Build

```bash
module load oneapi/release

icpx -O3 -fsycl -fsycl-targets=spir64_gen \
    gpu_bursty_idle.cpp \
    -o gpu_bursty_idle
```

Adjust target flags to match the Aurora oneAPI module guidance at run time.

## Run

Single tile:

```bash
export ZES_ENABLE_SYSMAN=1
ZE_AFFINITY_MASK=0.0 ./gpu_bursty_idle \
    --kernel-ms 20 \
    --gap-ms 80 \
    --iterations 500 \
    --gap-mode sleep
```

Whole card:

```bash
ZE_AFFINITY_MASK=0 ./gpu_bursty_idle \
    --kernel-ms 20 \
    --gap-ms 80 \
    --iterations 500 \
    --gap-mode cpu
```

## Expected runtime

1-5 minutes, depending on burst and gap settings.

## Validation criterion

Trace data should show alternating high and low `GPU_CORE_ACTIVITY`. Runtime should remain stable across repeats. During idle gaps, `GPU_CORE_ACTIVITY` should drop enough that a GPU frequency cap can be tested without confusing it with a saturated-kernel slowdown.

## GEOPM hypothesis

- The agent should lower `GPU_CORE_FREQUENCY_MAX_CONTROL` during idle or low-activity gaps and restore it before sustained GPU work.
- Useful detector signals include `GPU_CORE_ACTIVITY`, `GPU_CORE_FREQUENCY_STATUS`, `GPU_POWER`, and GPU throttle bits.
- This benchmark directly tests always-on savings that are not visible in always-saturated GPU kernels.

## Sweep config

See `experiments/phase1/gpu-bursty-idle/sweep.yaml` once Phase 1 configs are written.
