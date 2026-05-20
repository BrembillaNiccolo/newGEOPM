# mixbench (SYCL)

**Class**: GPU compute (sweeps arithmetic intensity from memory-bound to compute-bound).

**Why**: a single run characterizes the full PVC roofline. The high-AI buckets give the cleanest GPU-saturated power signature; the low-AI buckets double-check our memory-bound detection.

## Source

Upstream: https://github.com/ekondis/mixbench

**Local**: `src/` (pinned commit in `VERSION.txt`: `32edeca`).

Target: `mixbench-sycl`. Some PVC driver versions may need a small Level Zero patch — try clean build first; if it fails, search issues for the driver version reported by `clinfo`.

## Build (on Aurora)

```bash
module load oneapi/release
module load cmake

cd benchmarks/mixbench/src/mixbench-sycl
mkdir build && cd build
cmake -DCMAKE_CXX_COMPILER=icpx \
      -DCMAKE_BUILD_TYPE=Release \
      -DSYCL_TARGET=intel_gpu_pvc \
      ..
make -j
```

Resulting binary: `mixbench-sycl`. Record git commit in `phase1/mixbench/meta.json`.

## Run (single-node, single-tile)

```bash
export ZES_ENABLE_SYSMAN=1
ZE_AFFINITY_MASK=0.0 ./mixbench-sycl   # tile 0 of card 0
```

Add `geopmlaunch` wrapper from `benchmarks/CLAUDE.md` for sweeps.

## Run (single-card, both tiles)

```bash
export ZES_ENABLE_SYSMAN=1
ZE_AFFINITY_MASK=0 ./mixbench-sycl
```

## Expected runtime

~30-90 s per AI sweep, single tile, default array size. The mixbench output sweeps a range of operations-per-byte automatically.

## Validation criterion

Output reports GFLOPS and GB/s at each AI step. Sanity check:

- High-AI compute peak should approach published PVC FP32/FP64 numbers (~22 TF FP64 per tile).
- Low-AI bandwidth peak should approach ~1.6 TB/s HBM2e per tile.

Fail-fast: if either peak is <50% of published, something's wrong (likely affinity or driver).

## GEOPM hypothesis (Phase 1 will measure)

- **High-AI regime**: GPU per-tile freq cap and per-card power cap dominate. CPU DVFS irrelevant.
- **Low-AI regime**: GPU freq cap still helps modestly; uncore freq matters more.
- Expected per-class signal: `GPU_CORE_ACTIVITY` ~1.0 at high AI; `GPU_CORE_PERFORMANCE_FACTOR` reading and `GPU_CORE_THROTTLE_REASONS` worth logging.

## Sweep config

See `experiments/phase1/mixbench/sweep.yaml` (written in Phase 1).
