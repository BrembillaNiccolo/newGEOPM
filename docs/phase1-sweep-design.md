# Phase 1 — Knob characterization sweep design

Goal: produce a per-epoch CSV dataset mapping `(benchmark, knob_setting) → (energy, runtime, signals)` so we can (a) identify which signals reliably detect each workload class and (b) rank the controls that actually move the Pareto frontier per class.

This is the input to the unified-agent design in Phase 2.

## Sweep strategy

For each benchmark, two passes:

1. **1-D sweeps** (always-on baseline): vary one control at a time; hold the others at hardware default.
2. **Joint 4-D Latin-hypercube sweep** (~30 samples): explore interactions between the four knobs most relevant to that workload class.

The 1-D pass gives clean per-knob curves. The Latin-hypercube samples interactions cheaply (full grid is too expensive: 6 levels × 4 knobs = 1296 cells per benchmark).

## Knob grid (default values; per-benchmark refinements in each `experiments/phase1/<bench>/sweep.yaml`)

Knob list reflects what's actually writable on Aurora per `docs/signals_and_controls/geopm_research_strict_controls (1).md`.

| Knob | Levels | Notes |
|------|--------|-------|
| `CPU_FREQUENCY_MAX_CONTROL` | 6: {min_avail, +20%, +40%, +60%, +80%, max_avail} of (max_avail − min_avail) | sticker + base also added if not on grid |
| `CPU_UNCORE_FREQUENCY_MAX_CONTROL` | 5: same fractions of uncore min..max | swept separately — gates memory bandwidth |
| `CPU_POWER_LIMIT_CONTROL` | 5: {60, 70, 80, 90, 100}% of `CPU_POWER_LIMIT_DEFAULT` | RAPL PL1 per package |
| `DRAM_POWER_LIMIT_CONTROL` | 5: {60, 70, 80, 90, 100}% of read-out default | **Confirmed writable on Xeon Max.** Per package. |
| `GPU_CORE_FREQUENCY_MAX_CONTROL` | 6: same as CPU freq scheme, per-tile | applied to all 12 tiles (6 cards × 2). **Primary GPU lever — there is no writable GPU power cap.** |
| `LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL` | 3: {0.0, 0.5, 1.0} | read back to confirm write took — silently refused in some configs |
| `BOARD_POWER_LIMIT_CONTROL` | 5: {60, 70, 80, 90, 100}% of read-out default | **Whole-node PL1.** Sweep only once per benchmark (long run with logging) — this is the headline cap. Likely needs systemd service / root; verify. |

**Note: no GPU power-cap knob is swept** — neither `GPU_POWER_LIMIT_CONTROL` nor `DRM::HWMON::POWER1_MAX` is writable on Aurora. To create an "indirect GPU cap", the agent in Phase 2 will lean on `BOARD_POWER_LIMIT_CONTROL` + `CPU_POWER_LIMIT_CONTROL` + `DRAM_POWER_LIMIT_CONTROL` to leave the GPU a specific fraction of the board budget; this multidimensional response is what the Latin-hypercube pass below characterizes.

`SST::COREPRIORITY:*` is also writable on Aurora and could form a comm-class sweep, but skip in Phase 1 v1 — its joint interaction with the other knobs is large and Phase 1 should establish single-knob effects first.

## Per-benchmark parameters

| Benchmark | Class | Nodes | Repeats | Notes |
|-----------|-------|-------|---------|-------|
| mixbench-SYCL | GPU compute | 1 | 3 | run the full AI sweep inside the benchmark; treat each AI bucket as a separate sub-experiment |
| oneMKL DGEMM (GPU) | GPU compute | 1 | 3 | large enough M=N=K to saturate one tile (~16k) and to use full card (~32k) — separate runs |
| Intel HPL (CPU) | CPU compute | 1 | 3 | problem size tuned to ~70% memory footprint of HBM-only mode |
| STREAM HBM-only | Memory | 1 | 3 | bind to HBM via `numactl --membind=<hbm_node>` |
| STREAM flat | Memory | 1 | 3 | bind to DDR via `numactl --membind=<ddr_node>` |
| BabelStream (GPU Triad) | Memory | 1 | 3 | per-tile run + full-card run |
| OSU `osu_alltoall` | Comm | 4, 8 | 3 each | sweep message sizes 1B..8MB; record at each size |
| OSU `osu_allreduce` | Comm | 4, 8 | 3 each | same |
| HPCG | Mixed | 4 | 3 | reference problem size |
| Quicksilver | Comm (imbalanced) | 8 | 3 | Coral2 input deck |

Total Phase 1 cells (1-D pass only): ~10 benchmarks × ~5 knobs × ~5 levels × 3 repeats ≈ 750 runs. Latin-hypercube pass adds ~10 × 30 × 3 = 900 runs. Plan for ~1600-2000 node-hours per node-class.

## Always-on instrumentation

Every run, regardless of which knob is being swept:

- **Agent**: `monitor` (or `frequency_map` when sweeping freq knobs that monitor can't write — TBD)
- **Sampling**: full PIO trace at 20 ms via `--geopm-trace`
- **Report**: `--geopm-report=report.yaml` for per-region aggregates
- **Always-logged signals**: see `docs/geopm-aurora.md` "Signals to log every run" list

## Output schema

One CSV per run. Filename: `experiments/phase1/<bench>/runs/<knob>_<level>_<repeat>.csv`.

Columns (one row per epoch, ~50/sec at 20 ms):

```
time_s, epoch, region_hash, region_hint,
cpu_power_pkg0_W, cpu_power_pkg1_W, cpu_energy_pkg0_J, cpu_energy_pkg1_J,
cpu_freq_avg_Hz, cpu_uncore_freq_pkg0_Hz, cpu_uncore_freq_pkg1_Hz,
cpu_ipc_avg, cpu_aperf_sum, cpu_mperf_sum,
dram_power_pkg0_W, dram_power_pkg1_W, dram_energy_pkg0_J, dram_energy_pkg1_J,
gpu0_card_power_W, gpu0_card_energy_J, gpu0_card_util,
gpu0_tile0_power_W, gpu0_tile0_energy_J, gpu0_tile0_freq_Hz, gpu0_tile0_activity, gpu0_tile0_throttle_bits,
gpu0_tile1_*, gpu1_*, ..., gpu5_*,
cpu_pkg_temp_max_C, gpu_core_temp_max_C
```

(Repeat the per-card/per-tile block for 6 cards × 2 tiles = 12 tiles.)

Per-run sidecar JSON: `meta.json` with — benchmark name, problem size, knob values written, hostname, GEOPM version, oneAPI version, Cray MPICH version, allocation queue, timestamp.

## Power & energy attribution model

Two views, both reported:

1. **Component sum** (preferred for agent reward): `E = Σ_pkg CPU_ENERGY + Σ_pkg DRAM_ENERGY + Σ_card GPU_ENERGY`. Excludes NIC, fans, PSU losses.
2. **Whole-node** (when available): if PDU-level or BMC node power is exposed, log it as a separate column for sanity-checking the component sum.

For the 3000 W cap in Phase 3, work in component sum throughout — that's what GEOPM can both measure and control.

## Statistical reporting

- Per cell: median + IQR over 3 repeats.
- Outlier rule: discard a repeat if its time-to-solution differs from the median by >2× IQR (likely interference). Re-run.
- Pareto-frontier computation: for each benchmark, compute non-dominated set in (energy, runtime) plane across all knob settings → emit `analysis/pareto/<bench>.csv`.

## Phase 1 report (deliverable)

`analysis/phase1-report.md` must contain:

- **Per workload class** (4 sections):
  - Signal detector: which 2-3 signals threshold-classify this class with low false-positive rate (validate on out-of-class benchmarks)
  - Ranked knobs by ΔE / Δt impact
  - Pareto-frontier table (the seed for Phase 2 agent action arms)
- **Cross-class confusion matrix** for the detector
- **Open knobs**: which controls turned out to have no measurable effect (drop from Phase 2)
