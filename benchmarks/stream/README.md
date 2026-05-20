# STREAM (Triad)

**Class**: Memory-bound (CPU). The reference HBM-bandwidth benchmark.

**Why**: the canonical GEOPM win — reducing core freq saves package energy with minimal bandwidth loss, *as long as* uncore freq stays high. We run in both HBM-only and flat (HBM+DDR) modes.

## Source

Upstream: https://www.cs.virginia.edu/stream/

Single C file: `stream.c`.

**Local**: `src/stream.c` (SHA-256 in `VERSION.txt`).

## Build (on Aurora)

```bash
module load oneapi/release
cd benchmarks/stream/src
icx -O3 -qopenmp -DSTREAM_ARRAY_SIZE=400000000 -DNTIMES=20 -o stream stream.c
```

Tune `STREAM_ARRAY_SIZE` so 3 × 8 × size > 4× LLC (avoid cache fit) AND fits in HBM (`<` ~110 GB for HBM-only on Aurora). 4e8 elements = 9.6 GB total → safe.

## Run (HBM-only)

```bash
module load oneapi/release
export OMP_NUM_THREADS=<phys cores per socket>
export OMP_PROC_BIND=close
export OMP_PLACES=cores
numactl --membind=<hbm_node> -- ./stream
```

(HBM NUMA node ID depends on Xeon Max memory mode; see ALCF docs.)

## Run (flat — DDR)

```bash
numactl --membind=<ddr_node> -- ./stream
```

## Expected runtime

A few seconds per iteration; ~minute total at NTIMES=20.

## Validation criterion

STREAM reports best/avg Triad bandwidth. Sanity check:

- HBM-only: expect ~1.0-1.2 TB/s per socket → ~2.0-2.4 TB/s aggregated.
- Flat (DDR): ~200-300 GB/s per socket.

Fail if HBM <500 GB/s (likely fell to DDR by mistake — check `numactl --hardware` and binding).

## GEOPM hypothesis

The textbook GEOPM win:

- **`CPU_FREQUENCY_MAX_CONTROL` low** (e.g. 1.5 GHz): <5% bandwidth loss, 20-30% package energy savings.
- **`CPU_UNCORE_FREQUENCY_MAX_CONTROL` must stay HIGH**: it gates the mesh & memory controllers.
- `DRAM_POWER` is sizable (HBM ≠ free); track separately.
- Expected detector signals: low IPC, high DRAM bandwidth proxy, low GPU activity.

## Sweep config

See `experiments/phase1/stream/sweep.yaml` (written in Phase 1). Two variants per knob: HBM-only and flat.
