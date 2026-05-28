# Agent action set — 18 (knob, level) combos for Phase 2

**This is the curated knob shortlist** for the unified GEOPM agent. Built from `analysis/phase0_combo_ranking.csv` (29 candidates) by dropping POWERCAP::* aliases (confirmed-duplicate) and capping at 18 actions to keep the bandit's state space tractable.

> **Total**: 6 unique GEOPM controls × 1–4 selected levels each = **18 actions** (well under the 15–30 budget). Plus 1 implicit "noop" arm → **19-arm bandit**.

---

## The shortlist (sorted by safety class)

### Class A — always-safe (write at any time, no workload classification needed)
**12 actions.** No bench in our matrix saw `too_slow` for these levels. Median energy win is small (≤1 %) but consistent. These should form the agent's **default policy** when in doubt.

| # | Knob | Level | Useful in | Med ΔE | Worst Δt | Notes |
|---|---|---|---:|---:|---:|---|
| 1 | `BOARD_POWER_TIME_WINDOW_CONTROL` | `readback_double` | 5/7 | −0.50 % | +1.9 % | Widen board PL1 averaging window |
| 2 | `BOARD_POWER_TIME_WINDOW_CONTROL` | `readback_half` | 5/7 | −0.49 % | +0.0 % | Tighten board PL1 window |
| 3 | `CPU_POWER_TIME_WINDOW_CONTROL` | `readback_double` | 5/7 | −0.80 % | +0.2 % | Widen RAPL PL1 window |
| 4 | `CPU_POWER_TIME_WINDOW_CONTROL` | `readback_half` | 5/7 | −0.34 % | +0.2 % | Tighten RAPL PL1 window |
| 5 | `DRAM_POWER_TIME_WINDOW_CONTROL` | `readback_double` | 3/7 | −1.28 % | +0.4 % | Widen DRAM PL1 window |
| 6 | `DRAM_POWER_TIME_WINDOW_CONTROL` | `readback_half` | 2/7 | −0.95 % | +0.7 % | Tighten DRAM PL1 window |
| 7 | `GPU_POWER_TIME_WINDOW_CONTROL` | `readback_double` | 1/7 | −5.12 % | +0.4 % | Widen GPU PL1 window |
| 8 | `BOARD_POWER_LIMIT_CONTROL` | `lit_4000W` | 5/7 | −1.42 % | +3.0 % | Lenient board cap; non-binding most workloads |
| 9 | `DRAM_POWER_LIMIT_CONTROL` | `readback_60pct` | 4/7 | −0.02 % | +0.7 % | DRAM ~1 % of node power; tiny but free |
| 10 | `DRAM_POWER_LIMIT_CONTROL` | `readback_75pct` | 2/7 | −0.22 % | +2.3 % | Less aggressive DRAM cap |
| 11 | `DRAM_POWER_LIMIT_CONTROL` | `readback_90pct` | 2/7 | −0.29 % | +0.9 % | Light DRAM nudge |
| 12 | *(noop arm — always-safe baseline)* | — | 7/7 | 0 | 0 | The agent's fallback |

### Class B — workload-conditional (write only after classifying the workload)
**5 actions.** Big upside on the right workload class, runtime-violation risk on the wrong one. These are the bandit's "swing" arms; **context features must classify workload first**.

| # | Knob | Level | Useful in | Best ΔE | Worst Δt | When safe / dangerous |
|---|---|---|---:|---:|---:|---|
| 13 | `BOARD_POWER_LIMIT_CONTROL` | `lit_3500W` | 5/7 | **−17.9 %** | +18.9 % | Safe everywhere except dgemm-gpu when fully loaded |
| 14 | `BOARD_POWER_LIMIT_CONTROL` | `lit_3000W` (**headline cap**) | 4/7 | **−27.5 %** | +44.0 % | Safe on CPU/comm/timed; **forbidden on GPU-bound** (dgemm-gpu, babelstream) |
| 15 | `BOARD_POWER_LIMIT_CONTROL` | `lit_2500W` | 4/7 | **−27.2 %** | +107.3 % | Safe on stream/idle/comm; **forbidden on all compute** |
| 16 | `CPU_POWER_LIMIT_CONTROL` | `tdp_60pct` | 4/7 | −100 %† | +191 % | Safe on **GPU-bound** (CPU idle) + **MPI wait**; **forbidden on CPU-bound** |
| 17 | `CPU_POWER_LIMIT_CONTROL` | `tdp_75pct` | 2/7 | −56.2 %† | +58.2 % | Same shape as tdp_60pct but milder |

† Class B ΔE include some stream cells where bench finished before sidecar sampled — actual savings smaller than shown; runtime regressions are real.

### Class C — high-reward / narrow-scope (only on time-bounded workloads)
**1 action.** Spectacular wins on workloads with fixed-time loops, catastrophic elsewhere.

| # | Knob | Level | Useful in | Best ΔE | Worst Δt | Trigger |
|---|---|---|---:|---:|---:|---|
| 18 | `BOARD_POWER_LIMIT_CONTROL` | `lit_2000W` | 2/7 | **−73.9 %** | +376 % | **Only** when context features show `gpu_compute_activity < 0.3` AND `cpu_utilization < 0.5` (i.e., idle/wait/comm workload) |

---

## Cross-action notes

### Knobs explicitly DROPPED from this shortlist
The full strict set has 35 controls; we keep 6 unique. Reasons for dropping:

| Knob | Why dropped |
|---|---|
| `POWERCAP::CPU_POWER_LIMIT`, `POWERCAP::DRAM_POWER_LIMIT`, `POWERCAP::CPU_TIME_WINDOW`, `POWERCAP::DRAM_TIME_WINDOW` | Empirically identical to their CPU/DRAM_POWER_LIMIT_CONTROL siblings — confirmed in our data (every alias cell mirrors the GEOPM-native one within noise). Halves action space. |
| `CPU_FREQUENCY_DESIRED_CONTROL` | Only effective under `userspace` governor; our system runs `performance` by default → all cells were no-ops. |
| `CPU_FREQUENCY_GOVERNOR_CONTROL` | Switching governor invalidates other frequency settings; treat as a one-time mode, not a bandit arm. |
| All `SST::COREPRIORITY:*` (12 controls) | Sub-1 % effect in our data; complex semantics (4 priority levels × 3 fields); defer to Phase 3 or a dedicated SST experiment. |
| `SST::TURBO_ENABLE`, `SST::COREPRIORITY_ENABLE` | Boolean enables; toggle once at session start rather than per-decision. |
| `CPU_FREQUENCY_MIN_CONTROL`, `CPU_UNCORE_FREQUENCY_MIN_CONTROL`, `GPU_CORE_FREQUENCY_MIN_CONTROL` | "Raise the floor" knobs — useful as one-shot safety guards, not as bandit arms. |

### Knobs we STILL NEED to characterize before Phase 2
Not enough data in this campaign:
- **`CPU_FREQUENCY_MAX_CONTROL`** — primary CPU DVFS lever; only ran at default in the all_tiles_15s sweep.
- **`GPU_CORE_FREQUENCY_MAX_CONTROL`** — primary GPU lever on Aurora (since GPU power cap isn't writable). Critical for cap-compliance.
- **`CPU_UNCORE_FREQUENCY_MAX_CONTROL`** — should be the memory-bandwidth dual.

**Recommended next campaign**: a focused 3-knob sweep on the same 7 benches, ~15 cells per bench, ~1.5 h total.

---

## What context features the bandit needs to pick Class B/C arms

The agent must classify the current workload before reaching for Class B/C arms. Features from signals we already capture:

| Feature | Source signal | What it discriminates |
|---|---|---|
| `gpu_compute_activity_mean12` | mean of `GPU_CORE_ACTIVITY gpu_chip 0..11` | GPU-bound vs GPU-idle |
| `gpu_compute_activity_spread` | max − min of per-tile activity | balanced vs imbalanced GPU use |
| `cpu_power_fraction` | `CPU_POWER / CPU_POWER_LIMIT_DEFAULT` | CPU-bound vs CPU-idle |
| `dram_power_fraction` | `DRAM_POWER / DRAM_POWER_MAX_AVAIL` | memory-bound vs memory-light |
| `runtime_slack_budget ε` | user input (`runtime_slack` in sweep.json) | tolerance for runtime regression |
| `comm_fraction` (future) | from GEOPM region hooks | comm-bound vs compute-bound |

Decision logic (proposed simple rules; bandit can override after enough data):

```
if gpu_compute_activity_mean12 < 0.3 and cpu_power_fraction < 0.5:
    # idle / time-bounded — Class C is safe
    candidate_arms = [12, 13, 14, 15, 16, 17, 18]
elif gpu_compute_activity_mean12 > 0.7:
    # GPU-bound — clamp CPU is free; don't touch board cap below 4000W
    candidate_arms = [12, 13, 16, 17]   # plus Class A
elif cpu_power_fraction > 0.7:
    # CPU-bound — DRAM & board-3000W OK; don't clamp CPU
    candidate_arms = [12, 13, 14]       # plus Class A
else:
    # mixed / unclassified — Class A only
    candidate_arms = [12, 13]           # plus Class A
```

---

## C++ agent integration sketch

```cpp
// Constants derived from this report (Phase 1 outputs):
constexpr std::array<KnobLevel, 18> kArmSet = {
    // Class A (always-safe, indices 0..11)
    {"BOARD_POWER_TIME_WINDOW_CONTROL", "readback_double", 0.5, /*board*/  4, ...},
    {"BOARD_POWER_TIME_WINDOW_CONTROL", "readback_half",   2.0, ...},
    {"CPU_POWER_TIME_WINDOW_CONTROL",   "readback_double", 0.5, ...},
    ...
    // Class B (workload-conditional, 12..16)
    {"BOARD_POWER_LIMIT_CONTROL",       "lit_3500W",       3500.0, ...},
    {"BOARD_POWER_LIMIT_CONTROL",       "lit_3000W",       3000.0, ...},
    ...
    // Class C (high-reward narrow, 17)
    {"BOARD_POWER_LIMIT_CONTROL",       "lit_2000W",       2000.0, ...},
};
// LinUCB picks among candidate_arms[context]. Reward = -ΔE if Δt within ε, else heavy penalty.
```

---

## Files in this report set
- **`analysis/knobs_for_agent.md`** ← this file: the shortlist
- `analysis/knobs_per_workload.md`: per-workload-class top knobs (what to use *for each bench type*)
- `analysis/knobs_universal.md`: cross-bench winners (what works *everywhere*)
- `analysis/knobs_to_avoid.md`: explicit blacklist with worst-case data
- `analysis/phase1-report.md`: the full characterization narrative
- `analysis/phase0_combo_ranking.csv`: the raw 29-row scoring table
