# Knob blacklist — combos the agent must NEVER write blindly

Cells where `effectiveness=too_slow` (runtime exceeded the +5 % budget). Source: `analysis/phase0_knob_detail.csv`.

> **For the C++ agent**: these `(knob, level, workload_class)` tuples should be **hard-forbidden** in the bandit's action space until/unless the user opts into a higher runtime-slack budget. The reward function should also penalize *exploration* of these arms in the wrong context.

---

## The 5 most-dangerous cells in the whole campaign

| Rank | Bench | Knob | Level | Δt | ΔE | Why |
|---:|---|---|---|---:|---:|---|
| 1 | **osu** | `BOARD_POWER_LIMIT_CONTROL` | `lit_2000W` | **+376 %** | +313 % | Tight cap throttles CPUs → ranks fall behind in spin-wait → allreduce blocks forever |
| 2 | **cpu-dgemm** | `BOARD_POWER_LIMIT_CONTROL` | `lit_2000W` | +287 % | +189 % | CPU-bound work fully throttled by board cap |
| 3 | **dgemm-gpu** | `BOARD_POWER_LIMIT_CONTROL` | `lit_2000W` | +275 % | +102 % | 12 saturated tiles can't fit in 2 kW budget |
| 4 | **babelstream** | `BOARD_POWER_LIMIT_CONTROL` | `lit_2000W` | +225 % | +63 % | Same — 12 HBM streams need budget |
| 5 | **cpu-dgemm** | `CPU_POWER_LIMIT_CONTROL` | `tdp_60pct` | +191 % | +216 % | Direct CPU throttle on CPU-bound bench |

The **single most dangerous knob** is `BOARD_POWER_LIMIT_CONTROL=lit_2000W` — 4 of the top-5 worst cells. It's also the **highest-reward** knob in the right context (−74 % energy on time-bounded). Bandit's classification problem in a nutshell.

---

## Per-workload blacklist

### cpu-dgemm (CPU compute) — forbid these
| Knob | Level | Δt | ΔE |
|---|---|---:|---:|
| `BOARD_POWER_LIMIT_CONTROL` | `lit_2000W` | +287 % | +189 % |
| `CPU_POWER_LIMIT_CONTROL` | `tdp_60pct` | +191 % | +216 % |
| `POWERCAP::CPU_POWER_LIMIT` | `readback_60pct` | +187 % | +154 % |
| `CPU_POWER_LIMIT_CONTROL` | `tdp_75pct` | +58 % | +72 % |
| `POWERCAP::CPU_POWER_LIMIT` | `readback_75pct` | +55 % | +62 % |
| `CPU_POWER_LIMIT_CONTROL` | `tdp_90pct` | +11 % | +9 % |
| `POWERCAP::CPU_POWER_LIMIT` | `readback_90pct` | +9 % | +7 % |
| `DRAM_POWER_TIME_WINDOW_CONTROL` | `readback_half` | +6 % | +0 % |

**Rule**: never reduce CPU power on a CPU-bound bench. Sounds obvious; the agent learns it the hard way otherwise.

### dgemm-gpu (GPU compute, 12-tile) — forbid these
| Knob | Level | Δt | ΔE |
|---|---|---:|---:|
| `BOARD_POWER_LIMIT_CONTROL` | `lit_2000W` | +275 % | +102 % |
| `BOARD_POWER_LIMIT_CONTROL` | `lit_2500W` | +90 % | +3 % |
| `BOARD_POWER_LIMIT_CONTROL` | `lit_3000W` | +44 % | −19 % (good energy, bad runtime) |
| `BOARD_POWER_LIMIT_CONTROL` | `lit_3500W` | +19 % | −14 % (good energy, bad runtime) |

**Rule**: 12 saturated PVC tiles need ≥4000 W. Any board cap below that hurts runtime. The lit_3000W/lit_3500W rows are interesting — energy goes down but runtime exceeds the 5 % slack. Re-classifies to `useful` if user picks slack ε≥0.5.

### babelstream (GPU memory, 12-tile) — forbid these
| Knob | Level | Δt | ΔE |
|---|---|---:|---:|
| `BOARD_POWER_LIMIT_CONTROL` | `lit_2000W` | +225 % | +63 % |
| `BOARD_POWER_LIMIT_CONTROL` | `lit_2500W` | +107 % | −0 % |
| `BOARD_POWER_LIMIT_CONTROL` | `lit_3000W` | +42 % | −27 % |

**Rule**: even memory-bound GPU workloads need ≥3500 W board budget.

### osu (MPI communication) — forbid these
| Knob | Level | Δt | ΔE |
|---|---|---:|---:|
| `BOARD_POWER_LIMIT_CONTROL` | `lit_2000W` | **+376 %** | **+313 %** |
| `CPU_POWER_LIMIT_CONTROL` | `tdp_60pct` | +72 % | +70 % |
| `POWERCAP::CPU_POWER_LIMIT` | `readback_60pct` | +70 % | +67 % |
| `POWERCAP::CPU_POWER_LIMIT` | `readback_75pct` | +17 % | +16 % |
| `CPU_POWER_LIMIT_CONTROL` | `tdp_75pct` | +16 % | +15 % |

**Rule**: MPI collectives are super-sensitive to CPU throttling. Spin-wait amplifies any slowdown.

### stream (CPU memory) — forbid these
| Knob | Level | Δt | ΔE |
|---|---|---:|---:|
| `CPU_POWER_LIMIT_CONTROL` | `tdp_60pct` | +72 % | −100 % (data error) |
| `POWERCAP::CPU_POWER_LIMIT` | `readback_60pct` | +72 % | −100 % |
| `BOARD_POWER_LIMIT_CONTROL` | `lit_2000W` | +23 % | −100 % |
| `POWERCAP::CPU_POWER_LIMIT` | `readback_75pct` | +13 % | −47 % |
| `CPU_POWER_LIMIT_CONTROL` | `tdp_75pct` | +13 % | −56 % |
| `BOARD_POWER_LIMIT_CONTROL` | `lit_2500W` | +0.8 % | −26 % ⚠️ borderline — actually USEFUL with our slack=0.05 |

⚠️ Caveat: stream's `−100 %` ΔE rows are a measurement artifact (sidecar caught no energy data because the bench crashed or the trace cleanup was incomplete). The runtime regressions are real; the energy "savings" aren't trustworthy. Treat all stream rows here as runtime-blacklist regardless.

### dgemm-gpu — *also* never write
| Knob | Level | Δt |
|---|---|---:|
| `POWERCAP::CPU_POWER_LIMIT` | `readback_75pct` | +0.5 % (not too_slow, but useless) |

(Already covered in the dgemm-gpu rejection list above.)

### mpi-idle-wait (MPI slack) — nothing blacklisted
Every knob tested is useful. The deterministic-loop structure is cap-resilient.

### gpu-bursty-idle (GPU bursty) — nothing blacklisted
Same reason. Aggressive caps welcome.

---

## "Universal don't" — never write under any workload, any time

| Knob | Level | Why |
|---|---|---|
| `BOARD_POWER_LIMIT_CONTROL` | `lit_2000W` | **High variance: −74 % to +376 % runtime**. Use ONLY when context features confirm time-bounded workload (gpu_compute_activity<0.3 AND cpu_power_fraction<0.5). |
| `CPU_POWER_LIMIT_CONTROL` | `tdp_60pct` | Same logic: lethal on CPU-bound, free on GPU-bound. **Don't write without checking `cpu_power_fraction`.** |
| `POWERCAP::CPU_POWER_LIMIT` | `readback_60pct` | Alias of above; same risk. |

These are the bandit's "explore carefully" arms — write them only when the workload classifier has ≥80 % confidence the workload is the right kind.

---

## What the agent should learn from this list

1. **A blacklist isn't a fixed table** — every entry here is contextual. The "right" answer depends on workload class + slack budget. The bandit must learn the (context → arm) mapping; this list seeds the priors.

2. **The most-rewarding arms are also the most-punishing**. `BOARD_POWER_LIMIT_CONTROL=lit_2000W` is the single highest-magnitude action (in *both* directions). High-variance arms are exactly the ones bandits gain most from learning about — but the early exploration is expensive.

3. **Reward function design**: the agent's reward should be heavily asymmetric. A +5 % runtime hit is much worse than a −5 % energy win is good, because runtime regressions compound (longer run = more energy too). Use something like
   `reward = -ΔE / baseline_energy - 10 × max(0, Δt/baseline_runtime - ε)`
   to make the runtime-slack violation cliff explicit.

4. **The osu lit_2000W cell at +376 % runtime** is a useful data point for the bandit: it's the worst possible outcome of the worst possible arm-context combo. Whatever exploration policy you use, make sure the bandit can't trip into that cell more than once.
