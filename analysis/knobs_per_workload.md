# Per-workload best knobs

For each of the 7 workload classes, the ranked `(knob, level)` cells with effectiveness=`useful` (runtime within +5 %, energy reduced). Source: `analysis/phase0_knob_detail.csv`, n=5 PBS-job repeats per cell.

> **How to use this**: when the agent recognizes the workload class (via context features), it should pick from that class's top-5 with high prior probability. The Class B/C cells from `knobs_for_agent.md` are flagged ⭐.

---

## CPU compute — cpu-dgemm
*Baseline ≈ 10 s wall, 18.5 kJ board energy. Workload: blocked DGEMM, OMP, no MPI.*

| Rank | Knob | Level | ΔE | Δt | Class |
|---:|---|---|---:|---:|:---:|
| 1 | `BOARD_POWER_LIMIT_CONTROL` | `lit_3000W` | **−7.45 %** | −4.59 % | ⭐ B |
| 2 | `POWERCAP::DRAM_TIME_WINDOW` | `readback_double` | −6.29 % | −4.76 % | (A) |
| 3 | `GPU_POWER_TIME_WINDOW_CONTROL` | `readback_double` | −5.12 % | −5.25 % | A |
| 4 | `POWERCAP::DRAM_TIME_WINDOW` | `readback_half` | −4.74 % | −3.29 % | (A) |
| 5 | `CPU_POWER_TIME_WINDOW_CONTROL` | `readback_double` | −4.66 % | −4.55 % | A |
| 6 | `BOARD_POWER_TIME_WINDOW_CONTROL` | `readback_half` | −4.10 % | −0.61 % | A |
| 7 | `DRAM_POWER_LIMIT_CONTROL` | `readback_90pct` | −3.88 % | −2.81 % | A |
| 8 | `DRAM_POWER_TIME_WINDOW_CONTROL` | `readback_double` | −3.38 % | −2.63 % | A |
| 9 | `BOARD_POWER_LIMIT_CONTROL` | `lit_2500W` | −4.01 % | −1.79 % | ⭐ B |

**Mechanism**: CPU-bound DGEMM saturates the CPU but leaves DRAM and GPU underused. The "useful" knobs all reduce non-critical-path power: trim GPU idle wattage, widen RAPL windows (smoother sustained draw), lightly cap DRAM. The lit_3000W board cap works *because* it's above what cpu-dgemm naturally draws (~2.4 kW), so it acts as headroom-trimming, not throttling.

**Don't touch**: `CPU_POWER_LIMIT_CONTROL` at any reduced level (`tdp_90pct` already +10 % runtime; `tdp_60pct` +191 %), `BOARD_POWER_LIMIT_CONTROL=lit_2000W` (+287 % runtime), per knobs_to_avoid.md.

---

## CPU memory — stream
*Baseline ≈ 22 s wall, ~120 kJ board. Workload: STREAM Triad on DDR (no HBM binding in this variant).*

| Rank | Knob | Level | ΔE | Δt | Class |
|---:|---|---|---:|---:|:---:|
| 1 | `BOARD_POWER_LIMIT_CONTROL` | `lit_2500W` | **−26.39 %** | +0.77 % | ⭐ B |
| 2 | `DRAM_POWER_TIME_WINDOW_CONTROL` | `readback_half` | −3.28 % | −0.31 % | A |
| 3 | `BOARD_POWER_TIME_WINDOW_CONTROL` | `readback_double` | −2.30 % | −0.14 % | A |
| 4 | `BOARD_POWER_TIME_WINDOW_CONTROL` | `readback_half` | −2.18 % | −0.11 % | A |
| 5 | `DRAM_POWER_TIME_WINDOW_CONTROL` | `readback_double` | −1.28 % | −0.11 % | A |
| 6 | `POWERCAP::DRAM_POWER_LIMIT` | `readback_75pct` | −1.17 % | −0.09 % | (A) |
| 7 | `BOARD_POWER_LIMIT_CONTROL` | `lit_3500W` | −0.11 % | −0.10 % | ⭐ B |

**Mechanism**: STREAM is memory-bound. CPU just waits on DRAM, so capping CPU/board power gives "free" savings up to a threshold. The huge −26 % at lit_2500W is real — STREAM's CPU activity drops to ~50 % already; halving the board budget barely affects throughput. Below ~2000 W though, even memory access slows (memory controller throttles) and runtime balloons.

**Don't touch**: `CPU_POWER_LIMIT_CONTROL` tdp_60pct → +72 % runtime; `BOARD_POWER_LIMIT_CONTROL=lit_2000W` → +23 % runtime. Caveat: stream's energy data is unreliable under aggressive CPU caps (sidecar caught no signal in some cells).

---

## GPU compute — dgemm-gpu
*Baseline ≈ 14 s wall, 46.5 kJ board energy. Workload: 12 MPI ranks × naive SYCL DGEMM, one per PVC tile.*

| Rank | Knob | Level | ΔE | Δt | Class |
|---:|---|---|---:|---:|:---:|
| 1 | `CPU_POWER_LIMIT_CONTROL` | `tdp_60pct` | **−3.62 %** | −0.33 % | ⭐ B |
| 2 | `POWERCAP::CPU_POWER_LIMIT` | `readback_60pct` | −2.82 % | +0.47 % | (B) |
| 3 | `BOARD_POWER_LIMIT_CONTROL` | `lit_4000W` | −2.70 % | −0.16 % | A |
| 4 | `CPU_POWER_LIMIT_CONTROL` | `tdp_75pct` | −1.11 % | +0.07 % | (B) |
| 5 | `CPU_POWER_TIME_WINDOW_CONTROL` | `readback_double` | −0.86 % | −0.12 % | A |

**Mechanism**: **This is the "free CPU savings on GPU bench" hypothesis confirmed**. 12 PVC tiles do all the work; the 2 CPU sockets sit at ~500 W just driving the kernel launches. Clamping CPU to 60 % of TDP drops CPU power but doesn't slow the GPU at all → ~3.6 % whole-node energy saving for free. `BOARD_POWER_LIMIT_CONTROL=lit_4000W` is similarly non-binding (peak GPU draw is ~4.6 kW, so 4 kW cap trims only the burst).

**Don't touch**: any `BOARD_POWER_LIMIT_CONTROL` below 4000 W on this bench. lit_3500W +19 % runtime, lit_3000W +44 %, lit_2500W +89 %, lit_2000W +275 %. The 12 saturated tiles can't share a tight budget.

---

## GPU memory — babelstream
*Baseline ≈ 11 s wall, 22 kJ board energy. Workload: 12 MPI ranks × BabelStream Triad, one per PVC tile.*

| Rank | Knob | Level | ΔE | Δt | Class |
|---:|---|---|---:|---:|:---:|
| 1 | `BOARD_POWER_LIMIT_CONTROL` | `lit_3500W` | **−17.86 %** | +1.23 % | ⭐ B |
| 2 | `POWERCAP::CPU_POWER_LIMIT` | `readback_60pct` | −4.04 % | −0.71 % | (B) |
| 3 | `CPU_POWER_LIMIT_CONTROL` | `tdp_60pct` | −3.62 % | −1.04 % | ⭐ B |
| 4 | `BOARD_POWER_LIMIT_CONTROL` | `lit_4000W` | −2.09 % | −0.10 % | A |
| 5 | `CPU_POWER_LIMIT_CONTROL` | `tdp_75pct` | −1.70 % | −0.66 % | (B) |

**Mechanism**: GPU Triad is HBM-bandwidth-bound, not compute-bound. EUs stall waiting for memory; that idle time draws less power. lit_3500W board cap gives a big saving (−17.9 %) because the compute side isn't pushing peak power even at full load. CPU savings same as dgemm-gpu (CPU is essentially idle).

**Don't touch**: `BOARD_POWER_LIMIT_CONTROL` below 3500 W. lit_3000W +42 % runtime, lit_2500W +107 %, lit_2000W +225 %. Even memory-bound GPU work needs minimum board power.

---

## MPI communication — osu
*Baseline ≈ 16 s wall, 36 kJ board energy. Workload: 12 ranks intra-node allreduce, message range 1B–32 MiB.*

| Rank | Knob | Level | ΔE | Δt | Class |
|---:|---|---|---:|---:|:---:|
| 1 | `BOARD_POWER_LIMIT_CONTROL` | `lit_3500W` | **−1.19 %** | −1.00 % | ⭐ B |
| 2 | `DRAM_POWER_TIME_WINDOW_CONTROL` | `readback_double` | −1.26 % | −0.89 % | A |
| 3 | `DRAM_POWER_TIME_WINDOW_CONTROL` | `readback_half` | −0.95 % | −0.97 % | A |
| 4 | `BOARD_POWER_LIMIT_CONTROL` | `lit_4000W` | −0.53 % | −1.00 % | A |
| 5 | `BOARD_POWER_LIMIT_CONTROL` | `lit_3000W` | −0.29 % | −0.81 % | ⭐ B |
| 6 | `CPU_POWER_TIME_WINDOW_CONTROL` | `readback_half` | −0.34 % | −0.68 % | A |

**Mechanism**: OSU allreduce is wait-dominated; ranks spend most time in MPI barriers. CPU power is mostly burned in spin-wait, so anything that reduces CPU power without slowing the collective wins. The win sizes are small (~1 %) because the collective itself is short relative to all-to-all overhead.

**Don't touch**: `CPU_POWER_LIMIT_CONTROL` below `tdp_90pct` — slow CPUs delay the spin-wait completion (`tdp_60pct` +72 % runtime). `BOARD_POWER_LIMIT_CONTROL=lit_2000W` → +376 % runtime, the worst single cell in the matrix.

---

## MPI slack — mpi-idle-wait
*Baseline ≈ 7.5 s (deterministic loop), 14 kJ board energy. Workload: 12 ranks × (30 ms compute + 30 ms barrier-wait) × 250.*

| Rank | Knob | Level | ΔE | Δt | Class |
|---:|---|---|---:|---:|:---:|
| 1 | `BOARD_POWER_LIMIT_CONTROL` | `lit_2000W` | **−71.94 %** | +0.38 % | ⭐ C |
| 2 | `CPU_POWER_LIMIT_CONTROL` | `tdp_60pct` | −3.80 % | +0.04 % | ⭐ B |
| 3 | `POWERCAP::CPU_POWER_LIMIT` | `readback_60pct` | −2.99 % | +0.04 % | (B) |
| 4 | `BOARD_POWER_LIMIT_CONTROL` | `lit_2500W` | −0.73 % | −0.00 % | ⭐ B |
| 5 | `BOARD_POWER_LIMIT_CONTROL` | `lit_3500W` | −0.70 % | +0.00 % | ⭐ B |
| 6 | (every other strict knob also "useful") | — | small | ~0 | — |

**Mechanism**: time-bounded loop — runtime is set by `sleep(60 ms)` calls, NOT by hardware throttle. Any cap reduces *power*, time stays fixed, so energy = ∫P dt drops linearly with the cap. **This is the cleanest "always-on" win class in the matrix**. Every cell is useful; the bandit can be aggressive here.

**Don't touch**: nothing. Every knob tested gave a useful result. Free real estate.

---

## GPU bursty / idle — gpu-bursty-idle
*Baseline ≈ 15 s (deterministic loop), 30 kJ board energy. Workload: 12 ranks × (30 ms GPU kernel + 30 ms idle gap) × 250.*

| Rank | Knob | Level | ΔE | Δt | Class |
|---:|---|---|---:|---:|:---:|
| 1 | `BOARD_POWER_LIMIT_CONTROL` | `lit_2000W` | **−73.94 %** | +0.09 % | ⭐ C |
| 2 | `BOARD_POWER_LIMIT_CONTROL` | `lit_2500W` | **−27.19 %** | +0.03 % | ⭐ B |
| 3 | `BOARD_POWER_LIMIT_CONTROL` | `lit_3000W` | **−16.54 %** | +0.00 % | ⭐ B |
| 4 | `BOARD_POWER_LIMIT_CONTROL` | `lit_3500W` | −3.64 % | +0.00 % | ⭐ B |
| 5 | `POWERCAP::CPU_POWER_LIMIT` | `readback_60pct` | −3.61 % | +0.00 % | (B) |
| 6 | `CPU_POWER_LIMIT_CONTROL` | `tdp_60pct` | −3.25 % | +0.00 % | ⭐ B |

**Mechanism**: same as mpi-idle-wait — time-bounded. Plus the GPU has long idle stretches (gap-mode=sleep) where it draws idle wattage. Aggressive board caps shave that idle leakage without affecting the 30 ms kernel bursts (which complete in time regardless).

**Don't touch**: nothing rejected. This is the **best workload class for the agent to be aggressive** — everything tested helps, with the lit_2000W cell being the single highest-impact cell in the entire campaign.

---

## Cross-class observation

The **same `(knob, level)` pair** has dramatically different effects across workload classes:

| Knob | Level | cpu-dgemm | dgemm-gpu | gpu-bursty-idle | mpi-idle-wait |
|---|---|---|---|---|---|
| `BOARD_POWER_LIMIT_CONTROL` | `lit_2000W` | **+287 % Δt** | **+275 % Δt** | **−74 % ΔE** | **−72 % ΔE** |
| `CPU_POWER_LIMIT_CONTROL` | `tdp_60pct` | **+191 % Δt** | **−3.6 % ΔE** | **−3.3 % ΔE** | **−3.8 % ΔE** |
| `BOARD_POWER_LIMIT_CONTROL` | `lit_3000W` | −7.4 % ΔE | **+44 % Δt** | −17 % ΔE | −0.7 % ΔE |

This is the central justification for **context-aware** action selection. A bandit that doesn't classify workload before reaching for Class B/C will burn slack budget on cpu-dgemm while leaving free −74 % savings on the table for gpu-bursty-idle.
