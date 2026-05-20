# oneMKL DGEMM (GPU)

**Class**: GPU compute. The canonical compute-bound kernel; vendor-tuned, near-TDP per tile.

**Why**: cleanest Pareto frontier benchmark for the GPU power cap. Use this to anchor the GPU-class Pareto curve.

## Source

**No local source.** This benchmark is the vendor-shipped oneMKL GEMM binary on Aurora:

```bash
module load oneapi/release
ls $MKLROOT/benchmarks      # look for gemm / onemkl_gemm_benchmark
```

If the Aurora module turns out not to carry the benchmark binary at sweep time, fall back to building the oneMKL GEMM example from https://github.com/oneapi-src/oneMKL — but skip vendoring it until that's confirmed needed.

## Build (only if vendor binary is missing)

```bash
module load oneapi/release
git clone https://github.com/oneapi-src/oneMKL
cd oneMKL
mkdir build && cd build
cmake -DCMAKE_CXX_COMPILER=icpx \
      -DENABLE_MKLGPU_BACKEND=ON \
      -DENABLE_LEVEL_ZERO=ON \
      ..
make -j
# Use the gemm_usm sample / benchmark
```

## Run (single tile)

```bash
export ZES_ENABLE_SYSMAN=1
ZE_AFFINITY_MASK=0.0 ./onemkl_gemm_benchmark --M 16384 --N 16384 --K 16384 --dtype double --iters 20
```

## Run (whole card)

```bash
export ZES_ENABLE_SYSMAN=1
ZE_AFFINITY_MASK=0 ./onemkl_gemm_benchmark --M 32768 --N 32768 --K 32768 --dtype double --iters 20
```

(Tune M=N=K up until memory limits; record final size in meta.json.)

## Expected runtime

~10-60 s per iteration count, depending on M=N=K and tile vs card.

## Validation criterion

DGEMM throughput should approach published PVC peak (~45+ TF/s FP64 per tile). Fail if <70% of peak.

## GEOPM hypothesis

- GPU per-card `DRM::HWMON::POWER1_MAX` reduction of ~15% trades ~5-8% perf — clearest Pareto curve.
- `LEVELZERO::GPU_CORE_FREQUENCY_MAX_CONTROL` should track power cap response closely.
- `GPU_CORE_PERFORMANCE_FACTOR` should sit near 1.0 (compute regime).

## Sweep config

See `experiments/phase1/dgemm-gpu/sweep.yaml` (written in Phase 1).
