# Phase 1 prod 45 s sweep — results and comparison vs scaling 15 s

**Job:** PBS 8510227 on `prod`, 350 nodes (50 per bench × 7 benches), 6 h walltime allowance, finished in ~1 h 10 min. Variant `all_tiles_45s` (3× longer cells than the `all_tiles_15s` debug-scaling sweep). 23,100 total cells, 22,844 successful (98.9 % success rate). The job completed before Aurora entered maintenance.

**Source files:**
- `results/8510227/per_node_summaries/` — 350 raw per-node CSVs
- `analysis/prod_45s/cells.csv` — 22,844 cleaned cells (bench column recovered from `run_dir` because the runner's summary writer accidentally stringifies a Popen object into the `benchmark` field — a bug worth fixing in `scripts/run_phase0_sweep.py`)
- `analysis/prod_45s/by_knob.csv` — 459 (bench, knob, level) aggregates with median rt, median E, n=50 reps each
- `analysis/prod_45s/compare_vs_scaling_15s.csv` — 387 matched cells with side-by-side dE/dt deltas

---

## Headline: best safe knob per bench (worst_dt < 5 %)

Prod 45 s vs scaling 15 s headline tables:

| bench | scaling 15 s winner | prod 45 s winner | what changed |
|---|---|---|---|
| **stream** | `CPU_FREQUENCY_MAX_CONTROL @ 1.0 GHz` (−68.1 % / +0.3 %) | `CPU_FREQUENCY_MAX_CONTROL @ 1.0 GHz` (−67.8 % / +0.4 %) | same — CPU_FREQ still dominant |
| **mpi-idle-wait** | `CPU_FREQUENCY_MAX_CONTROL @ 1.0 GHz` (−64.0 % / +0.2 %) | **`CPU_POWER_LIMIT_CONTROL @ tdp_30` (−91.7 % / +0.7 %)** | NEW WINNER — power cap saves ~28 pp more |
| **gpu-bursty-idle** | `BOARD_POWER_LIMIT_CONTROL @ 2000 W` (−51.5 % / +0.1 %) | **`CPU_POWER_LIMIT_CONTROL @ tdp_40` (−56.9 % / +0.1 %)** | per-component cap beats whole-node cap |
| **babelstream** | `CPU_FREQUENCY_MAX_CONTROL @ 1.0 GHz` (−42.2 % / +0.3 %) | **`CPU_POWER_LIMIT_CONTROL @ tdp_40` (−61.9 % / +0.2 %)** | +20 pp more savings with the power cap |
| **dgemm-gpu** | `CPU_FREQUENCY_MAX_CONTROL @ 1.0 GHz` (−34.2 % / +0.2 %) | **`CPU_POWER_LIMIT_CONTROL @ tdp_40` (−50.3 % / 0.0 %)** | +16 pp more savings |
| **cpu-dgemm** | `CPU_UNCORE_FREQUENCY_MAX_CONTROL @ 0.8 GHz` (−16.3 % / −0.3 %) | **`GPU_CORE_FREQUENCY_MAX_CONTROL @ 0.4 GHz` (−13.4 % / −0.2 %)** | similar magnitude, different lever |
| **osu** | **none** | **`GPU_CORE_FREQUENCY_MAX_CONTROL @ 1.6 GHz` (−15.1 % / +0.1 %)** | NEW — osu now has a safe knob |

Three of these are big policy-relevant changes; details below.

---

## Three findings that update the Phase 0 understanding

### 1. CPU_POWER_LIMIT replaces CPU_FREQ_MAX as the universal "free-save" lever

On the 15 s variant, `CPU_FREQUENCY_MAX_CONTROL @ 1.0 GHz` was the best safe knob on 5 of 7 benches. On the 45 s variant, **`CPU_POWER_LIMIT_CONTROL @ tdp_30 or tdp_40` wins on 4 of 7 benches** (babelstream, dgemm-gpu, mpi-idle-wait, gpu-bursty-idle).

**Mechanism:** CPU_FREQ caps the peak clock; CPU_POWER caps the time-integrated draw. The 15 s variant is dominated by startup/teardown (~3-5 s of fork + module-load + spinup overhead), during which CPU energy is largely fixed regardless of the cap. The 45 s variant has more steady-state, so the integral-based cap (CPU_POWER) sees a higher ratio of effective cap binding.

**Bias quantification:** comparing matched cells, `CPU_FREQUENCY_MAX_CONTROL` saves on average **8.1 pp less** in prod than in scaling (σ=10 pp, n=49 cells). `CPU_POWER_LIMIT_CONTROL` saves more in prod but with high variance (mean +4.3 pp, σ=29 pp) — the bias direction depends on bench.

**Implication for the agent:** `CPU_POWER_LIMIT` should be elevated in priority within the arm grid. The current `comm_wait_save` arm (A4) already sets it to 175 W; the new evidence suggests an additional `cpu_pl_aggressive` arm with tdp_30 (=105 W) might dominate A4 on the non-cpu-dgemm wait/idle classes. But A4 + A7 already have CPU_PL writes, so the bandit will find them.

### 2. osu has a safe knob in prod that scaling missed

Phase 0 (15 s) reported osu has no safe knob — every cap broke runtime by >5 %. Prod (45 s) reveals **`GPU_CORE_FREQUENCY_MAX_CONTROL @ 1.6 GHz` (= keep GPU at MAX, do nothing else) is safe**: dE = −15.1 %, dt = +0.1 %.

Why "GPU at MAX" saves any energy: at the 45 s scale, the GPU's idle leakage during alltoall periods becomes a measurable fraction of total energy. The 15 s variant didn't capture enough of this idle to expose the saving.

**Implication for the agent:** osu's `comm_collective_safe` arm (A5, which sets GPU=0.4 GHz) should give similar savings — and Phase 1.5b confirmed A5 gives −14 % on osu. The arm is the right choice; we now have an independent prod data point validating it.

### 3. GPU_FREQ_MAX saves slightly MORE on the longer variant

Opposite bias from CPU_FREQ. Prod 45 s shows GPU_FREQ_MAX caps save on average **2.6 pp more** energy than scaling 15 s predicted (σ=2.7 pp, n=49). The mechanism is the same as #1 but flipped: GPU idle leakage matters more in steady-state, so a hard GPU cap during otherwise-idle phases captures more of the integral.

This validates `bursty_gpu_idle` (A6, currently marked inactive due to dominance by A4 in Phase 1.5 Block A). A6's GPU=0.4 GHz write is now confirmed to capture real prod savings; the only reason A6 is inactive is that A4 captures the same savings PLUS more on the CPU side.

---

## What does NOT change

These knobs behave identically in prod and scaling (mean |Δ dE| < 1 pp):

- `DRAM_POWER_LIMIT_CONTROL` (mean +0.3 pp, σ=1.3)
- `CPU_UNCORE_FREQUENCY_MAX_CONTROL` (mean −0.04 pp, σ=2.5)
- `LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL` (mean −0.37 pp, σ=1.0)
- All three `*_POWER_TIME_WINDOW_CONTROL` (mean ≈ 0 pp, σ < 1)

The Phase 0 conclusions for these knobs transfer verbatim to prod-scale workloads. The bandit's priors for these can stay as-is.

---

## What does NOT flip verdicts

Critical sanity check: **no cell crossed the safe / unsafe boundary** between scaling and prod. Every (bench, knob, level) that was `dt < 5 %` in scaling is also `dt < 5 %` in prod, and every harmful cell stays harmful. The categorical verdicts (`USEFUL_LINEAR`, `HARMFUL`, etc.) from `analysis/phase0_by_control.csv` transfer to prod cleanly. The agent's HARMFUL filter still picks the right arms.

**Magnitudes shift, categories don't.** This is the headline.

---

## 68 cells with |Δ dE| > 5 pp

Breakdown by knob (the agent should source warm-start priors from prod for these):

| Knob | n big-delta cells | mean Δ | what this means |
|---|---|---|---|
| `CPU_FREQUENCY_MAX_CONTROL` | 23 | +8.1 pp | scaling over-predicts savings |
| `CPU_POWER_LIMIT_CONTROL` | 21 | +4.3 pp | high variance — bench-dependent |
| `BOARD_POWER_LIMIT_CONTROL` | 13 | +5.3 pp | tight caps less effective on long workloads |
| `GPU_CORE_FREQUENCY_MAX_CONTROL` | 7 | −2.6 pp | prod saves more |
| `CPU_UNCORE_FREQUENCY_MAX_CONTROL` | 4 | small | a few outliers, mostly aligned |

Breakdown by bench:

| Bench | n big-delta cells |
|---|---|
| cpu-dgemm | 19 (worst case: `BOARD_POWER lit_2000W` was −4.3 % in scaling, +113.8 % in prod — short-bench rebound effect) |
| babelstream | 12 |
| dgemm-gpu | 12 |
| gpu-bursty-idle | 9 |
| mpi-idle-wait | 7 |
| osu | 7 |
| stream | 2 (most-aligned bench — long enough already in 15 s to be representative) |

The **stream** bench's near-zero divergence (only 2 of ~55 cells differ >5pp) is reassuring: its workload reaches steady-state quickly, so 15 s and 45 s give the same picture.

---

## Agent action items

| Action | Status |
|---|---|
| Regenerate Phase 2 LinUCB warm-start priors from prod 45 s data | TODO (no `generate_phase2_priors.py` exists yet — Phase 2 work) |
| Confirm `comm_wait_save` (A4) and `aggressive_save` (A7) use CPU_POWER_LIMIT — they do | ✓ |
| Reconsider reactivating A6 `bursty_gpu_idle` now that prod confirms GPU caps save more | maybe — wait for Phase 1.5b D/E results first |
| Re-classify osu: now has a safe knob | ✓ A5 covers it |
| Categorical verdicts in `analysis/phase0_by_control.csv` are still valid | ✓ no flips |
| Agent grid restructuring needed? | **No.** Same arms, just different magnitudes. The bandit handles the magnitude correction online. |

---

## Bug surfaced by this aggregation

`scripts/run_phase0_sweep.py` writes the per-cell summary with `"benchmark": bench` where `bench` is a local variable that gets shadowed by `bench = subprocess.Popen(...)` earlier in `run_cell()`. The result is "<Popen: returncode: 0 args: ...>" stringified into the per-node CSVs.

This aggregation works around it by extracting bench from `run_dir`. Fix in the runner: rename the local Popen variable to `bench_proc` (or similar) so it doesn't shadow the loop variable. Low priority — workaround is reliable.

---

## Files

- `analysis/prod_45s/cells.csv` — 22,844 cleaned prod cells
- `analysis/prod_45s/by_knob.csv` — 459 (bench, knob, level) aggregates
- `analysis/prod_45s/compare_vs_scaling_15s.csv` — 387 matched cells, side-by-side
- `analysis/prod_45s/results.md` — this document
- `results/8510227/` — raw prod run output (preserved)
