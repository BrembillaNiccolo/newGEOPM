# GEOPM controls — tier classification & what actually moves the needle

Source: re-read of `docs/signals_and_controls/geopm_controls_described (1).md` (165 lines, all controls on the system) and `geopm_research_strict_controls (1).md` (35 strict candidates), cross-referenced with measured response from the 1435-cell campaign aggregated by `analysis/scripts/summarize_by_control.py` → `analysis/phase0_by_control.csv`.

> **Bottom line**: of 35 strict controls, only **7 belong in the bandit's per-decision action space**. The other 28 split into "redundant alias", "mode/setup knob", "floor guard", "specialist (SST)", or "bookkeeping (TIME_WINDOW)". This file justifies that split with the empirical data.

---

## 1. The classification (with evidence)

### 🥇 Tier 1 — direct power/DVFS levers (bandit per-decision arms)

These change *what the hardware actually does*. They map cleanly onto a "more power → more performance → more energy" curve that the bandit can learn over.

| Control | Domain | Unit | What it changes | Verdict from data |
|---|---|---|---|---|
| `BOARD_POWER_LIMIT_CONTROL` | board | W | Whole-node PL1 cap | **1 USEFUL_LINEAR + 1 USEFUL_THRESHOLD + 5 HARMFUL** — the highest-magnitude knob, **workload-dependent** |
| `CPU_POWER_LIMIT_CONTROL` | package | W | RAPL package PL1 | **4 USEFUL_LINEAR + 3 HARMFUL** — the "free CPU on GPU bench" knob |
| `DRAM_POWER_LIMIT_CONTROL` | package | W | DRAM/HBM RAPL cap | 5 NEGLIGIBLE + 1 USEFUL_MILD + 1 USEFUL_THRESHOLD — small absolute impact (DRAM ~1% of node) |
| `CPU_FREQUENCY_MAX_CONTROL` | core | Hz | CPU DVFS ceiling | **NO_DATA (7/7)** — was in old `strict_knobs.json` but `fraction_range` cells never produced output |
| `CPU_UNCORE_FREQUENCY_MAX_CONTROL` | package | Hz | Uncore (mesh/LLC/IMC) DVFS | NO_DATA — never reached cell stage in prior sweeps |
| `GPU_CORE_FREQUENCY_MAX_CONTROL` | gpu_chip | Hz | GPU DVFS ceiling | NO_DATA — same |
| `LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL` | gpu_chip | 0-1 | PVC perf/power bias | NO_DATA — same |

→ **3 of 7 Tier-1 controls have characterization data; 4 are untested**. The new `strict_knobs.json` fills the gap with 5-level response-curve sweeps.

### 🥈 Tier 2 — secondary effects (probe-and-confirm, NOT bandit arms)

These change *how* power is enforced, not *how much* power is delivered. Empirically sub-1 %.

| Control | What it changes | Verdict from data |
|---|---|---|
| `BOARD_POWER_TIME_WINDOW_CONTROL` | PL1 averaging window | 6 NEGLIGIBLE + 1 USEFUL_LINEAR — basically noise |
| `CPU_POWER_TIME_WINDOW_CONTROL` | same on CPU | 5 NEGLIGIBLE + 1 FLAT + 1 THRESHOLD |
| `DRAM_POWER_TIME_WINDOW_CONTROL` | same on DRAM | 5 NEG + 1 LINEAR + 1 HARMFUL (one outlier) |
| `GPU_POWER_TIME_WINDOW_CONTROL` | same on GPU | 5 NEG + 1 FLAT + 1 THRESHOLD |

→ Kept in the new `strict_knobs.json` at 2 levels each (half/double) **only to confirm** they remain near-zero on the new curve sweeps. After confirmation: drop entirely.

### 🟢 Mode knobs — set once at session start (NOT bandit arms)

Changing these mid-run invalidates other knobs' state. They're configuration parameters that determine which Tier-1 knobs are even effective.

| Control | Role |
|---|---|
| `CPU_FREQUENCY_GOVERNOR_CONTROL` | Picks the kernel cpufreq governor. We use `performance`. Setting to `userspace` activates `CPU_FREQUENCY_DESIRED_CONTROL`. Setting to `powersave` ≈ clamps to MIN_AVAIL. |
| `SST::COREPRIORITY_ENABLE:ENABLE` | Master switch for Intel SST-CP. **All 12 `SST::COREPRIORITY:N:*` knobs are no-ops unless this is enabled first.** |
| `SST::TURBO_ENABLE:ENABLE` | Master switch for Intel SST-TF. Enabling auto-enables SST-CP. |

→ Configure in the PBS script header / job-start hook. Not in the bandit action set.

### 🟢 Floor knobs — safety guards (one-shot, NOT bandit arms)

These set a *minimum* — they only bind when the governor would otherwise clock down. Useful as one-time "don't let the GPU drop below 0.5×max" guards, not per-decision arms.

| Control | When useful |
|---|---|
| `CPU_FREQUENCY_MIN_CONTROL` | Pin CPU above some floor during MPI wait phases |
| `CPU_UNCORE_FREQUENCY_MIN_CONTROL` | Keep memory bandwidth available during GPU-only phases |
| `GPU_CORE_FREQUENCY_MIN_CONTROL` | Prevent GPU dropping into deep idle states during bursty kernels |

→ Configure once based on workload class (set when bandit picks an arm that needs the floor), not swept per-decision.

### 🔮 SST specialist family — dedicated campaign (NOT in current bandit)

| Control group | Why deferred |
|---|---|
| `SST::COREPRIORITY:ASSOCIATION` | Assigns each core to a priority bucket (0..3). Only useful when ranks have *asymmetric* compute loads. |
| `SST::COREPRIORITY:0..3:FREQUENCY_MAX` (4 knobs) | Per-bucket frequency caps. Bandit value depends on rank-skew classification. |
| `SST::COREPRIORITY:0..3:FREQUENCY_MIN` (4) | Per-bucket frequency floors. |
| `SST::COREPRIORITY:0..3:PRIORITY` (4) | Per-bucket power-share priorities. |

→ Our 7-bench suite has no rank-imbalanced workload (all are uniformly-loaded MPI or single-process). A dedicated SST campaign with `mpi-idle-wait --skew-rank 0` and quicksilver would unlock these. **Phase 3 work, not Phase 2.**

### ❌ Truly drop — redundant or never-effective

| Control | Why drop |
|---|---|
| `POWERCAP::CPU_POWER_LIMIT` | Same MSR as `CPU_POWER_LIMIT_CONTROL`. **Confirmed identical** in our data — see CPU_POWER_LIMIT 4-LIN-3-HARM vs POWERCAP::CPU 4-LIN-3-HARM (exact same verdict pattern). |
| `POWERCAP::DRAM_POWER_LIMIT` | Same MSR as `DRAM_POWER_LIMIT_CONTROL`. Confirmed identical. |
| `POWERCAP::CPU_TIME_WINDOW` | Same MSR as `CPU_POWER_TIME_WINDOW_CONTROL`. Confirmed. |
| `POWERCAP::DRAM_TIME_WINDOW` | Same MSR as `DRAM_POWER_TIME_WINDOW_CONTROL`. Confirmed. |
| `CPU_FREQUENCY_DESIRED_CONTROL` | Only effective under `userspace` governor; we run `performance` → all writes were no-ops. If you switch governor, *then* it becomes useful. |

→ 5 controls dropped with **zero information loss**. Halves the redundant search space.

---

## 2. Tally — 35 strict controls partitioned

| Bucket | Count | Examples |
|---|---:|---|
| **Tier 1** (bandit arms) | **7** | BOARD_PWR_LIMIT, CPU_PWR_LIMIT, DRAM_PWR_LIMIT, CPU_FREQ_MAX, CPU_UNCORE_FREQ_MAX, GPU_FREQ_MAX, GPU_PERF_FACTOR |
| **Tier 2** (probe only) | 3 | BOARD/CPU/GPU_PWR_TIME_WINDOW (DRAM dropped as redundant of CPU) |
| **Mode knobs** (one-shot) | 3 | GOVERNOR, SST_CP_ENABLE, SST_TF_ENABLE |
| **Floor knobs** (one-shot) | 3 | CPU_FREQ_MIN, CPU_UNCORE_FREQ_MIN, GPU_FREQ_MIN |
| **SST specialist** (later) | 13 | COREPRIORITY:ASSOCIATION + 4×{MAX, MIN, PRIORITY} |
| **Drop entirely** (redundant/blocked) | 5 | POWERCAP::* (4) + FREQ_DESIRED (1) |
| **CHECK** total | **34** | (DRAM_POWER_TIME_WINDOW lives in either Tier 2 or "drop" — pragmatic choice; 1 control of ambiguity) |

---

## 3. What we ACTUALLY know from the existing data

The previous campaign produced cells for **only 7 of the 35 strict controls** (after deduping POWERCAP aliases). Here's what each one taught us:

### Strong response (workload-conditional)

#### `BOARD_POWER_LIMIT_CONTROL` — the headline knob
- 7 benches × 5 levels = 35 cells
- 5/7 verdicts: HARMFUL (cap broke runtime budget on compute-bound)
- 1/7 USEFUL_LINEAR + 1/7 USEFUL_THRESHOLD on time-bounded workloads (`gpu-bursty-idle`, `mpi-idle-wait` — saw −74 % energy at lit_2000W)
- **Mechanism**: directly limits aggregate node power. Effect depends entirely on whether the bench's runtime is compute-bound (cap → throttle → +runtime) or time-bounded (cap → less power, same time → −energy linearly).
- **Bandit guidance**: classify workload first; expand the 5 → 7 levels to map the curve more finely (done in new `strict_knobs.json`: 5000/4000/3000/2500/2000 W).

#### `CPU_POWER_LIMIT_CONTROL` — the "free CPU savings on GPU bench" knob
- 7 × 3 levels = 21 cells
- 4/7 USEFUL_LINEAR (GPU-bound + idle/wait benches → CPU isn't the bottleneck)
- 3/7 HARMFUL (CPU-bound benches → throttle hurts)
- **Mechanism**: clamps CPU socket power. On GPU benches the CPU is mostly idle driving kernels, so −power is free; on CPU benches, work depends linearly on power.
- **Bandit guidance**: use only when `cpu_power_fraction < 0.5` (CPU isn't fully loaded). New strict_knobs.json adds tdp_100 and tdp_40 endpoints.

### Weak response (low priority)

#### `DRAM_POWER_LIMIT_CONTROL`
- 7 × 3 levels = 21 cells
- 5/7 NEGLIGIBLE, 1 MILD, 1 THRESHOLD
- DRAM is ~1 % of node power (~38 W of 3800 W). Even halving it saves ~0.5 %.
- **Bandit guidance**: deprioritize but keep — useful as a tiebreaker arm.

### No data (the gap)

#### `CPU_FREQUENCY_MAX_CONTROL`, `CPU_UNCORE_FREQUENCY_MAX_CONTROL`, `GPU_CORE_FREQUENCY_MAX_CONTROL`, `LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL`
- **All 4 produced NO_DATA verdicts (7 benches × 0 cells each)**.
- These were in the previous `strict_knobs.json` with `fraction_range` levels but every cell failed silently — probably the `MIN_AVAIL/MAX_AVAIL` signal reads didn't resolve at write time, or the resulting frequency wasn't acceptable to the hardware.
- **This is the biggest characterization gap**. Frequency knobs are THE primary DVFS levers; without them the bandit is missing its most controllable arm.

### Confirmed bookkeeping (TIME_WINDOW family)

#### `*_POWER_TIME_WINDOW_CONTROL` (4 controls × 2 levels each = 8 measurements per bench)
- 5–6 of 7 benches: NEGLIGIBLE per control
- Span of ΔE across half/double levels: 0.1–0.5 % typical
- **Confirms your intuition**: changing the averaging window doesn't change the cap value or the work being done. The slight effect (when present) is transient response under load variation.

---

## 4. The new `experiments/phase1/strict_knobs.json` (already written)

- **10 controls** = **7 Tier 1** (5-level response curves) + **3 Tier 2** (2-level confirmation)
- **51 cells per (bench, variant, repeat)** vs 118 in the old set (−57 %)
- **~17 min wall** per bench at 20 s/cell vs ~40 min before
- Removes: 5 POWERCAP aliases, 12 SST specialist, 1 CPU_FREQUENCY_DESIRED, 3 floor knobs, 1 governor, 1 SST master switch

### Why fewer knobs is better than the old "include everything"

| Metric | Old (35 knobs, ~118 cells) | New (10 knobs, ~51 cells) |
|---|---:|---:|
| Cells per bench-repeat | 118 | 51 |
| Wall per bench (1 repeat) | ~40 min | ~17 min |
| Wall for 7 benches × 5 repeats | ~24 h | ~10 h |
| Useful insight per cell | low (lots of negligible/redundant) | high (every cell on a response curve) |
| Coverage of Tier-1 frequency knobs | 0/4 (all NO_DATA) | 4/4 (5 levels each) |
| Coverage of POWERCAP duplicates | 4 redundant | 0 |
| Coverage of SST specialist | 12 noisy | 0 (deferred to Phase 3) |

---

## 5. What to run next

```bash
# Validate new strict_knobs.json on one bench (single PBS, ~25 min)
qsub -q debug -A UIC-HPC -l walltime=00:30:00 \
     -v BENCH=dgemm-gpu,VARIANT=all_tiles_15s,APPLY_CONTROLS=1,GEOPM_MONITOR=1 \
     scripts/submit_phase0.pbs

# Reduce the new data (per-control curves)
./analysis/scripts/summarize_phase0_knobs.sh experiments/phase1/*/runs    # writes phase0_*.csv
/usr/bin/python3.10 analysis/scripts/summarize_by_control.py              # writes by_control_*.csv, curves.md

# After all 7 benches × N repeats, the per-control verdict matrix will tell you
# which of the 7 Tier-1 knobs are USEFUL_LINEAR (bandit-friendly), USEFUL_THRESHOLD
# (use only one specific level), HARMFUL (workload-dependent), or NEGLIGIBLE (drop).
```

---

## 6. Files in this report set

- **`analysis/controls_classification.md`** ← this file
- `analysis/phase0_by_control_curves.md` — per-bench response-curve tables (one row per (bench, control))
- `analysis/phase0_by_control.csv` — machine-readable, 84 rows
- `analysis/scripts/summarize_by_control.py` — the aggregator (re-run after every new sweep)
- `experiments/phase1/strict_knobs.json` — the new curated 10-control sweep config
- See also: `analysis/knobs_for_agent.md`, `analysis/knobs_universal.md`, `analysis/knobs_per_workload.md`, `analysis/knobs_to_avoid.md` (Phase-1 reports built from the *old* sweep)

---

## 7. Open questions for the next sweep

1. **Do the 4 frequency knobs actually work?** The previous sweep produced 0 cells for any of them — was that a signal-resolution bug (MIN_AVAIL/MAX_AVAIL not available at write time) or do `fraction_range` writes get rejected by Aurora? Smoke-test the new sweep on cpu-dgemm to find out.
2. **Does `GPU_CORE_FREQUENCY_MAX` give the "free GPU savings on CPU bench" mirror?** Hypothesis: yes — clamping GPU freq during cpu-dgemm should drop the 14 kJ of idle GPU energy with no runtime cost.
3. **Is `GPU_PERFORMANCE_FACTOR` an axis distinct from `GPU_FREQ_MAX`?** Or just a synonym? Sweep both and compare response curves on babelstream (memory-bound) where the bias should differ.
4. **What's the right `BOARD_POWER_LIMIT_CONTROL` granularity?** The 6-level sweep (default + 5000/4000/3000/2500/2000) should reveal whether the response is linear, piecewise, or threshold-shaped on each bench.
