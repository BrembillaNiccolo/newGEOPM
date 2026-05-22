# Phase 0 knob-discovery implementation

This is the first runnable path before the custom GEOPM agent exists. It has three pieces:

1. Build a benchmark from `benchmarks/registry.json`.
2. Run cells from `experiments/phase1/<bench>/sweep.json`.
3. Summarize per-workload useful knobs into CSV files under `analysis/`.

The first implemented benchmark is `cpu-dgemm`, a small local CPU-compute anchor. The same runner is used for every Phase 1 benchmark once its binary exists.

## Build the first benchmark

```bash
cd newGEOPM
./scripts/build_benchmark.sh cpu-dgemm
```

To build every Phase 1 base benchmark implementation:

```bash
./scripts/build_benchmark.sh all
```

The Phase 0 local implementations are intentionally small:

- `cpu-dgemm`: blocked CPU DGEMM.
- `stream`: CPU Triad.
- `dgemm-gpu`: simple SYCL DGEMM used as a GPU-compute pipeline test.
- `babelstream`: simple SYCL Triad used as a GPU-memory pipeline test.
- `osu`: small MPI collective timing stand-in for OSU allreduce/alltoall.
- `mpi-idle-wait`: MPI wait/slack synthetic.
- `gpu-bursty-idle`: SYCL burst/gap synthetic.

The official/vendor benchmark sources can replace these later by editing `benchmarks/registry.json`; the runner and CSV analysis do not need to change.

The script prefers `AURORA_GEOPM_PYTHON`, then `python3.12`, `python3.11`, `python3.10`, `python3.9`, and finally `python3`. On Aurora, load a newer Python module first if the default is old:

```bash
module load python
```

## Local plumbing smoke test

This checks that the benchmark runs and that the experiment directory layout is correct. It does not write GEOPM controls.

```bash
./scripts/run_phase0_sweep.sh cpu-dgemm \
    --variant smoke \
    --knob CPU_FREQUENCY_MAX_CONTROL \
    --level default \
    --repeat 0 \
    --clean
```

Each benchmark also has a `smoke` variant. On login nodes, the GPU smoke variants use `ONEAPI_DEVICE_SELECTOR=opencl:cpu` so the plumbing can be checked without a GPU allocation. The real GPU variants use Level Zero GPU selection.

## Aurora GEOPM control test

Use this after the benchmark smoke test passes on a compute node. `--apply-controls` writes the selected GEOPM control and restores the original value after the run. `--geopm-monitor` adds GEOPM report and trace files.

```bash
export ZES_ENABLE_SYSMAN=1

./scripts/run_phase0_sweep.sh cpu-dgemm \
    --variant phase0 \
    --knob CPU_FREQUENCY_MAX_CONTROL \
    --level range_80 \
    --repeat 0 \
    --apply-controls \
    --geopm-monitor \
    --clean
```

## Run all Phase 0 cells for one benchmark

```bash
./scripts/run_phase0_sweep.sh cpu-dgemm --variant phase0 --apply-controls --geopm-monitor --clean
```

## Summarize useful knobs

```bash
./analysis/scripts/summarize_phase0_knobs.sh experiments/phase1/cpu-dgemm/runs
```

Outputs:

- `analysis/phase0_knob_summary.csv`: one row per workload type and benchmark, with useful knobs listed.
- `analysis/phase0_knob_detail.csv`: per-knob/per-level median runtime and energy comparison.

Energy ranking becomes real once the run has GEOPM trace/report energy metrics. Local runs without `--apply-controls` are marked `control_not_applied`.
