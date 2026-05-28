# Universal knobs — what works across all workload classes

`(knob, level)` cells ranked by how many of the 7 workload classes they help (effectiveness=`useful`), tie-broken by safety (`n_too_slow`) then by median energy savings. Source: `analysis/phase0_combo_ranking.csv`.

> **Interpretation**: a knob in this list is a candidate for the agent's *default* policy (write whenever no better action is known). A knob NOT in this list is workload-conditional — see `knobs_per_workload.md`.

---

## Top 12 — always-safe, useful in ≥4 of 7 benches

These never produce a `too_slow` cell anywhere in the matrix. They're the agent's safest action set.

| Rank | Knob | Level | Benches useful | Median ΔE on those | Worst Δt anywhere |
|---:|---|---|---:|---:|---:|
| 1 | `POWERCAP::DRAM_TIME_WINDOW` | `readback_double` | **6/7** | −0.39 % | +0.3 % |
| 2 | `BOARD_POWER_LIMIT_CONTROL` | `lit_4000W` | 5/7 | −1.42 % | +3.0 % |
| 3 | `CPU_POWER_TIME_WINDOW_CONTROL` | `readback_double` | 5/7 | −0.80 % | +0.2 % |
| 4 | `POWERCAP::DRAM_POWER_LIMIT` | `readback_75pct` | 5/7 | −0.60 % | +1.4 % |
| 5 | `BOARD_POWER_TIME_WINDOW_CONTROL` | `readback_double` | 5/7 | −0.50 % | +1.9 % |
| 6 | `BOARD_POWER_TIME_WINDOW_CONTROL` | `readback_half` | 5/7 | −0.49 % | +0.0 % |
| 7 | `CPU_POWER_TIME_WINDOW_CONTROL` | `readback_half` | 5/7 | −0.34 % | +0.2 % |
| 8 | `POWERCAP::DRAM_TIME_WINDOW` | `readback_half` | 5/7 | −0.31 % | +0.5 % |
| 9 | `POWERCAP::DRAM_POWER_LIMIT` | `readback_90pct` | 4/7 | −0.36 % | +0.4 % |
| 10 | `POWERCAP::DRAM_POWER_LIMIT` | `readback_60pct` | 4/7 | −0.29 % | +0.4 % |
| 11 | `POWERCAP::CPU_TIME_WINDOW` | `readback_double` | 4/7 | −0.11 % | +3.6 % |
| 12 | `DRAM_POWER_LIMIT_CONTROL` | `readback_60pct` | 4/7 | −0.02 % | +0.7 % |

**Pattern**: every single knob in this list is either
- a **time-window** knob (changes how the PL1 averaging window is measured, doesn't actually change the budget) — 7 of 12, OR
- a **DRAM cap** (DRAM is ~1 % of node power, so even aggressive caps barely move anything) — 4 of 12, OR
- the **most-lenient board cap** (lit_4000W is non-binding for most benches).

Mechanism: these knobs are "low energy, low risk" — small magnitude wins that compound when run continuously. **The agent should write some Class A knob roughly always, switching levels per workload.**

---

## Workload-conditional with high upside (useful in 4–5 of 7 but with some too_slow)

| Rank | Knob | Level | Useful | Slow | Best ΔE | Worst Δt | Workload class that breaks it |
|---:|---|---|---:|---:|---:|---:|---|
| 13 | `BOARD_POWER_LIMIT_CONTROL` | `lit_3500W` | 5/7 | **1** | −17.9 % | +18.9 % | dgemm-gpu (12 saturated tiles can't share 3.5 kW) |
| 14 | `BOARD_POWER_LIMIT_CONTROL` | `lit_2500W` | 4/7 | **2** | −27.2 % | +107.3 % | cpu-dgemm, dgemm-gpu, babelstream |
| 15 | `BOARD_POWER_LIMIT_CONTROL` | `lit_3000W` | 4/7 | **2** | −27.5 % | +44.0 % | dgemm-gpu, babelstream |
| 16 | `CPU_POWER_LIMIT_CONTROL` | `tdp_60pct` | 4/7 | **3** | −3.6 % | +190.7 % | cpu-dgemm, osu, stream (CPU-bound benches) |
| 17 | `POWERCAP::CPU_POWER_LIMIT` | `readback_60pct` | 4/7 | **3** | −2.8 % | +187.3 % | same as #16 (it's an alias) |

These knobs need **a workload classifier** before they're safe. The agent can only write them when it's confident the current workload tolerates the cap.

---

## Narrow but spectacular (useful in 2/7, huge effect)

| Knob | Level | Useful | Best ΔE | Worst Δt | When to use |
|---|---|---:|---:|---:|---|
| `BOARD_POWER_LIMIT_CONTROL` | `lit_2000W` | 2/7 | **−73.9 %** | +376.3 % | **Only** time-bounded workloads (mpi-idle-wait, gpu-bursty-idle). Catastrophe everywhere else. |

This is the highest-magnitude single cell in the whole campaign. It's also the most dangerous. The agent's reward function must heavily penalize the `too_slow` outcome to make it learn the right context.

---

## Knobs with no useful cells anywhere (drop from agent)

The strict set has 35 controls; 29 appeared in our scoring table (others had effectiveness `runtime_ok_no_energy_win` everywhere). These contribute nothing measurable:

- `CPU_FREQUENCY_DESIRED_CONTROL` (any level) — needs userspace governor; our system uses performance
- `CPU_FREQUENCY_GOVERNOR_CONTROL` (any level) — toggle, not a per-decision arm
- All `SST::COREPRIORITY:*` priority levels — sub-noise impact, complex semantics
- `GPU_POWER_TIME_WINDOW_CONTROL` `readback_half` — only useful on 1 bench, marginal effect

---

## Practical decision tree (one-screen agent logic)

```
context = read_context()  # gpu_compute_activity_mean12, cpu_power_fraction, ...

# Always-on policy: pick ONE Class A action per decision interval
class_A_arms = [1, 2, ..., 12]   # the always-safe list above
default_arm = bandit_choose(class_A_arms, context)
apply(default_arm)

# Augment with Class B/C if context allows
if context.is_time_bounded():           # gpu_compute_activity < 0.3 AND cpu_power_fraction < 0.5
    apply(BOARD_POWER_LIMIT_CONTROL=lit_2000W)   # arm 18, -74% ΔE
elif context.is_gpu_bound():            # gpu_compute_activity > 0.7
    apply(CPU_POWER_LIMIT_CONTROL=tdp_60pct)     # arm 16, -3.6% ΔE
elif context.is_cpu_memory_bound():     # cpu_power_fraction > 0.5 AND dram_fraction > 0.6
    apply(BOARD_POWER_LIMIT_CONTROL=lit_2500W)   # arm 15, -26% ΔE
elif context.is_comm_bound():           # high time-in-MPI
    apply(BOARD_POWER_LIMIT_CONTROL=lit_3500W)   # arm 13, -1.2% ΔE
# else: stick with Class A default
```

Bandit's job is to *refine* these rules from data; the rules above are reasonable priors.

---

## What's NOT in this list that we still need

This characterization didn't cover three potentially-universal knobs:

1. **`GPU_CORE_FREQUENCY_MAX_CONTROL`** — would likely be universal-useful on GPU-bound benches (analogous to CPU_POWER_LIMIT being universal on CPU benches). Untested.
2. **`CPU_FREQUENCY_MAX_CONTROL`** — direct CPU DVFS. The CPU_POWER_LIMIT_CONTROL is an indirect proxy; the direct freq knob might be more controllable.
3. **`CPU_UNCORE_FREQUENCY_MAX_CONTROL`** — would likely be the memory-bandwidth dual of CPU_POWER cap.

A focused 3-knob × 7-bench × 5-level sweep would add ~3 candidates to this list and likely promote one or two to "Class A always-safe".
