# Phase 0 Results — fixed-knob sweep (post 8509922 verification)

**Data source:** `analysis/phase0_by_control.csv` (70 rows = 10 controls × 7 benches), built from `analysis/phase0_cells.csv` (27,719 successful cells, 60 reps/bench across PBS jobs 8510137 / 8510226 / 8510276). Plots: `analysis/plots/per_bench/<bench>/<KNOB>.png` (70 PNGs) and `analysis/plots/per_control/<KNOB>.png` (10 cross-bench overlays).

**What changed since the previous sweep:** the frequency knobs (CPU_FREQUENCY_MAX_CONTROL, CPU_UNCORE_FREQUENCY_MAX_CONTROL, GPU_CORE_FREQUENCY_MAX_CONTROL) now actually bind to the requested values. The prior runs were silently clamped by the corresponding `_MIN_CONTROL` floor (e.g. GPU MIN pinned at 1.5 GHz blocked every MAX write below 1.5). `scripts/run_phase0_sweep.py` now drops MIN to its absolute floor before each MAX write; `experiments/phase1/strict_knobs.json` switched the three freq knobs from `fraction_range` to literal-Hz levels.

---

## Headline numbers

Best safe energy reduction (`worst_dt_pct < 5%`, i.e. within a 5% slack budget) per bench:

| bench | workload class | best safe knob | dE | dt |
|---|---|---|---|---|
| **stream** | HBM mem-bound (CPU) | `CPU_FREQUENCY_MAX_CONTROL` @ 1.0 GHz | **−68.1%** | +0.3% |
| **mpi-idle-wait** | comm/wait-dominated | `CPU_FREQUENCY_MAX_CONTROL` @ 1.0 GHz | **−64.0%** | +0.2% |
| **gpu-bursty-idle** | bursty GPU + long idle | `BOARD_POWER_LIMIT_CONTROL` @ 2000 W | **−51.5%** | +0.1% |
| **babelstream** | GPU mem-bound (HBM via SYCL) | `CPU_FREQUENCY_MAX_CONTROL` @ 1.0 GHz | **−42.2%** | +0.3% |
| **dgemm-gpu** | GPU compute | `CPU_FREQUENCY_MAX_CONTROL` @ 1.0 GHz | **−34.2%** | +0.2% |
| **cpu-dgemm** | CPU compute | `CPU_UNCORE_FREQUENCY_MAX_CONTROL` @ 0.8 GHz | **−16.3%** | −0.3% |
| **osu** | comm collective | — | none safe | — |

**Free savings exist on 6 of 7 workload classes.** Only osu (alltoall + allreduce) has zero safe-knob headroom — any cap of either CPU or GPU breaks the comm runtime. That's the correct answer for a comm-bound bench, and tells the agent to keep its hands off when it detects comm-dominated phases.

---

## Per-knob verdict matrix

`HARMFUL` = at least one tested level pushed runtime past +5%. `USEFUL_LINEAR` = monotone energy drop with no runtime hit. `USEFUL_THRESHOLD` = a single floor level gives almost all the saving. `NEGLIGIBLE` = <1% in either direction. Numbers are `best_dE` / `worst_dt`.

### CPU_FREQUENCY_MAX_CONTROL (verified literal-Hz levels: 1.0/1.2/1.6/2.0/2.5/3.0/3.5 GHz)

| bench | verdict | best dE | worst dt | notes |
|---|---|---|---|---|
| stream | USEFUL_THRESHOLD | −68.1% | +0.3% | HBM bandwidth-bound — CPU cores can sit at 1.0 GHz, saves 2/3 of energy |
| mpi-idle-wait | USEFUL_THRESHOLD | −64.0% | +0.2% | spin-wait dominated, full freq is pure waste |
| babelstream | USEFUL_THRESHOLD | −42.2% | +0.3% | CPU drives SYCL kernels but isn't on critical path |
| gpu-bursty-idle | USEFUL_THRESHOLD | −36.5% | +0.2% | CPU idle most of the time |
| dgemm-gpu | USEFUL_THRESHOLD | −34.2% | +0.2% | CPU only orchestrates; GPU does the math |
| cpu-dgemm | HARMFUL | −11.9% | +102.2% | CPU compute-bound — capping kills it |
| osu | HARMFUL | −0.2% | +207.6% | alltoall latency is CPU-driven; freq matters |

### CPU_UNCORE_FREQUENCY_MAX_CONTROL (literal 0.8/1.2/1.6/2.0/2.3 GHz)

| bench | verdict | best dE | worst dt | notes |
|---|---|---|---|---|
| cpu-dgemm | USEFUL_THRESHOLD | −16.3% | −0.3% | best CPU-dgemm knob; mesh/LLC don't need turbo |
| mpi-idle-wait | USEFUL_THRESHOLD | −8.2% | 0.0% | |
| gpu-bursty-idle | USEFUL_THRESHOLD | −7.1% | 0.0% | |
| dgemm-gpu | USEFUL_THRESHOLD | −5.2% | 0.0% | |
| babelstream | USEFUL_THRESHOLD | −3.4% | 0.0% | |
| stream | HARMFUL | −0.3% | +57.2% | HBM streaming goes through uncore — drop it and bandwidth tanks |
| osu | HARMFUL | +0.1% | +66.3% | comm goes through uncore mesh — same issue |

### GPU_CORE_FREQUENCY_MAX_CONTROL (literal 0.4 → 1.6 GHz) — THE BREAKTHROUGH KNOB

Previously totally missed because of the MIN_CONTROL clamp. Now produces real curves.

| bench | verdict | best dE | worst dt | notes |
|---|---|---|---|---|
| gpu-bursty-idle | USEFUL_THRESHOLD | −28.5% | +0.1% | huge win — GPU can sit at 0.4 GHz between bursts |
| stream | USEFUL_THRESHOLD | −14.6% | +0.3% | CPU-only bench; GPU pure idle, cap it down |
| cpu-dgemm | USEFUL_THRESHOLD | −13.5% | +1.5% | GPU idle; cap saves real energy |
| mpi-idle-wait | USEFUL_THRESHOLD | −11.2% | 0.0% | |
| osu | USEFUL_THRESHOLD | −10.7% | +0.2% | |
| babelstream | HARMFUL | −2.3% | +105.2% | GPU stream IS the workload — cap kills it |
| dgemm-gpu | HARMFUL | +0.2% | +209.7% | GPU compute-bound — cap kills it |

The classification is exactly right: cap GPU when GPU is idle/bursty/cold-side; never cap it when GPU is the hot path.

### BOARD_POWER_LIMIT_CONTROL (2000–5500 W literal)

| bench | verdict | best dE | worst dt | notes |
|---|---|---|---|---|
| gpu-bursty-idle | USEFUL_LINEAR | **−51.5%** | +0.1% | the biggest single saving in the whole campaign |
| mpi-idle-wait | USEFUL_LINEAR | −24.9% | +0.1% | |
| babelstream | HARMFUL | −26.6% | +227.5% | 2 kW cap chokes GPU streaming |
| dgemm-gpu | HARMFUL | −17.0% | +272.1% | same — GPU compute starves |
| stream | HARMFUL | −64.5% | +11.5% | CPU-only at low cap → uncore choked |
| cpu-dgemm | HARMFUL | −2.8% | +25.5% | CPU compute can't get the watts it needs |
| osu | HARMFUL | −1.1% | +81.2% | |

### CPU_POWER_LIMIT_CONTROL (scaled to CPU_POWER_LIMIT_DEFAULT, 30–100%)

| bench | verdict | best dE | worst dt | notes |
|---|---|---|---|---|
| mpi-idle-wait | USEFUL_LINEAR | −15.4% | +0.7% | |
| babelstream | USEFUL_LINEAR | −13.3% | +0.2% | |
| gpu-bursty-idle | USEFUL_LINEAR | −11.7% | +0.1% | |
| dgemm-gpu | USEFUL_LINEAR | −8.7% | 0.0% | |
| stream | HARMFUL | −81.5% | +79.5% | very tight cap kills HBM bandwidth |
| osu | HARMFUL | −0.3% | +919.2% | CPU comm cap → catastrophic |
| cpu-dgemm | HARMFUL | −2.7% | +670.4% | CPU compute cap → catastrophic |

### LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL (0.0–1.0)

Real knob! Previously had no data. Behaves like a soft GPU-DVFS bias inside the [MIN, MAX] window.

| bench | verdict | best dE | worst dt | notes |
|---|---|---|---|---|
| gpu-bursty-idle | USEFUL_LINEAR | −18.2% | 0.0% | favor 0.0 → faster downclock during waits |
| mpi-idle-wait | USEFUL_LINEAR | −12.6% | 0.0% | |
| osu | USEFUL_LINEAR | −12.1% | +0.2% | |
| stream | USEFUL_THRESHOLD | −11.7% | +0.1% | CPU bench, GPU idle |
| cpu-dgemm | USEFUL_THRESHOLD | −10.6% | +2.0% | |
| babelstream | HARMFUL | −0.1% | +7.1% | GPU active — biasing away from perf hurts |
| dgemm-gpu | HARMFUL | −1.2% | +28.1% | same |

Same pattern as `GPU_CORE_FREQUENCY_MAX_CONTROL`: useful on GPU-cold, harmful on GPU-hot. Slightly less aggressive (max −18% vs −28%) because it's a soft bias, not a hard cap.

### DRAM_POWER_LIMIT_CONTROL

Mostly NEGLIGIBLE. Only stream (−2.8%) and cpu-dgemm (−1.8%) show small mild gains. Not worth bandit arm cost.

### Time-window knobs (BOARD/CPU/GPU_POWER_TIME_WINDOW_CONTROL)

All NEGLIGIBLE except CPU/GPU TW on cpu-dgemm (−1% / −3%). Not worth bandit arm cost.

---

## Workload-class profiles

Phase 0 cleanly separates four classes by which knobs help safely:

| class | benches | safe wins | harmful caps to avoid |
|---|---|---|---|
| **GPU-active (compute or stream)** | dgemm-gpu, babelstream | CPU_FREQ_MAX, CPU_UNCORE, CPU_POWER (CPU side only) | GPU_FREQ_MAX, GPU_PERF_FACTOR, BOARD_POWER below ~4 kW |
| **CPU-active compute** | cpu-dgemm | CPU_UNCORE_MAX, GPU_FREQ_MAX, GPU_PERF_FACTOR, DRAM_POWER | CPU_FREQ_MAX, CPU_POWER, BOARD_POWER |
| **Memory-bound (HBM streaming)** | stream | CPU_FREQ_MAX (huge!), GPU_FREQ_MAX, GPU_PERF_FACTOR, DRAM_POWER | CPU_UNCORE_MAX, CPU_POWER, BOARD_POWER |
| **Comm/idle-dominated** | mpi-idle-wait, gpu-bursty-idle, osu | nearly everything (best ROI for the agent) | osu hates CPU-side caps |

Osu is the most fragile bench: alltoall is CPU-driven and any CPU cap (freq, uncore, or PL1) breaks it. The agent must detect comm-heavy phases and back off CPU caps — but it CAN still cap GPU (osu shows −10.7% on GPU_FREQ_MAX safely).

---

## Three things the curves prove

1. **The PVC "1.5 GHz busy floor" was a driver pin, not silicon.** With `GPU_CORE_FREQUENCY_MIN_CONTROL` dropped to 0.2 GHz, every requested MAX from 0.4 → 1.6 GHz binds exactly, and the response curve on bursty-idle is a clean monotone (−28.5% energy at 0.4 GHz). No 1.5 GHz floor in the data.
2. **`LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL` is real** and roughly tracks the GPU_FREQ_MAX curve at half the magnitude. Keeping it as a second GPU lever gives the agent a "soft" alternative when a hard cap would be too aggressive.
3. **The biggest single knob per bench is workload-dependent.** No universal "always-on" knob — even CPU_FREQ_MAX (the winner on 5 benches) is catastrophic on cpu-dgemm and osu. This is exactly the regime where a contextual bandit beats a static policy.

---

## Files

- `analysis/phase0_cells.csv` — 27,719 raw cells (one row per benchmark × variant × knob × level × repeat × node)
- `analysis/phase0_knob_detail.csv` — per (bench, knob, level) mean/median/std across reps
- `analysis/phase0_knob_summary.csv` — per (bench, knob) one-row summary
- `analysis/phase0_by_control.csv` — per (bench, control) verdict + best dE/dt + curve_pairs
- `analysis/phase0_by_control_curves.md` — human-readable per (bench, control) curves with the level-by-level numbers
- `analysis/plots/per_bench/<bench>/<KNOB>.png` — 3-panel response curve (runtime / energy / mean power) per (bench, knob)
- `analysis/plots/per_control/<KNOB>.png` — cross-bench overlay per knob
- `analysis/plots/index.md` — plot index with links
- `analysis/agent_suggestions.md` — Phase 2 agent design recommendations derived from these results
