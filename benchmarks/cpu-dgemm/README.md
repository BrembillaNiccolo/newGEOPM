# CPU DGEMM

**Class**: CPU compute.

**Why**: a small CPU compute anchor before running expensive HPL. This benchmark should provide a clean view of CPU package power, CPU frequency sensitivity, and AVX-heavy compute behavior without the long runtime and input tuning burden of full LINPACK.

## Source

Preferred source: the oneMKL BLAS DGEMM sample or any vendor-shipped CPU BLAS benchmark available in the Aurora oneAPI module.

If no suitable benchmark binary is available, write a minimal local driver that calls `cblas_dgemm` repeatedly on large square matrices and records wall time plus GFLOP/s. Keep the source small and record the exact oneMKL version in each run's `meta.json`.

## Build

Use the Aurora oneAPI module and link against MKL:

```bash
module load oneapi/release

icx -O3 -qopenmp cpu_dgemm.cpp \
    -qmkl \
    -o cpu_dgemm
```

If using a shipped oneMKL sample, record the sample path and module version instead of vendoring a copy.

## Run

```bash
export OMP_NUM_THREADS=<physical cores per socket or node>
export OMP_PROC_BIND=close
export OMP_PLACES=cores

./cpu_dgemm --m 32768 --n 32768 --k 32768 --iters 10
```

Tune matrix size so the run lasts at least 30 seconds and does not fit in cache. Use HBM binding when testing HBM-mode behavior:

```bash
numactl --membind=<hbm_node> -- ./cpu_dgemm --m 32768 --n 32768 --k 32768 --iters 10
```

## Expected runtime

30-180 seconds per cell after matrix size tuning.

## Validation criterion

Report GFLOP/s and verify that output is numerically sane, either by checking a small sampled residual or by comparing against a known checksum for deterministic inputs. Throughput should be stable across repeats and high enough to drive CPU package power near the expected compute regime.

## GEOPM hypothesis

- `CPU_FREQUENCY_MAX_CONTROL` and `CPU_POWER_LIMIT_CONTROL` should be the dominant knobs.
- `CPU_UNCORE_FREQUENCY_MAX_CONTROL` should matter less than it does for STREAM.
- This benchmark should replace `hpl-cpu/` in the Phase 1 base campaign, then HPL can return later as a CPU headline validation case.

## Sweep config

See `experiments/phase1/cpu-dgemm/sweep.yaml` once Phase 1 configs are written.
