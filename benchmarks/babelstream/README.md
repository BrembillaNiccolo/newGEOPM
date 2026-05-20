# BabelStream (SYCL, GPU Triad)

**Class**: Memory-bound (GPU). The HBM2e-bandwidth saturation benchmark for PVC.

**Why**: GPU mirror of CPU STREAM. Used to validate GPU memory-bound detection and the GPU freq cap response on bandwidth-bound code.

## Source

Upstream: https://github.com/UoB-HPC/BabelStream

**Local**: `src/` (pinned commit in `VERSION.txt`: `57637d5`).

SYCL backend target.

## Build

```bash
module load oneapi/release cmake
cd benchmarks/babelstream/src
mkdir build && cd build
cmake -DMODEL=sycl2020 \
      -DSYCL_COMPILER=ONEAPI-ICPX \
      -DCMAKE_BUILD_TYPE=Release \
      ..
make -j
```

Binary: `sycl2020-stream`.

## Run (single tile)

```bash
export ZES_ENABLE_SYSMAN=1
ZE_AFFINITY_MASK=0.0 ./sycl2020-stream -s 268435456    # ~2 GB per array → ~6 GB total
```

## Run (whole card)

```bash
ZE_AFFINITY_MASK=0 ./sycl2020-stream -s 536870912
```

## Expected runtime

<1 minute per run.

## Validation criterion

BabelStream reports Triad bandwidth. Sanity:

- Per-tile: ~1.4-1.6 TB/s.
- Whole card: ~2.8-3.2 TB/s.

Fail if <70% of these.

## GEOPM hypothesis

- `LEVELZERO::GPU_CORE_FREQUENCY_MAX_CONTROL` reduction: 10-15% energy savings at <3% bandwidth loss.
- GPU uncore freq matters but has no write path; observe correlation.
- `GPU_CORE_PERFORMANCE_FACTOR` may help if set to 0 (mem-biased) — but write may be silently refused (Q from `docs/open-questions.md`).
- Expected detector signals: high `GPU_CORE_ACTIVITY` AND low `GPU_CORE_FREQUENCY_STATUS` relative to max-avail (memory stalls).

## Sweep config

See `experiments/phase1/babelstream/sweep.yaml` (written in Phase 1).
