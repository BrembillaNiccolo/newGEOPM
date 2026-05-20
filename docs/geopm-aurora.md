# GEOPM on Aurora — signal & control cheat-sheet

**Source of truth**: this doc is derived from the actual Aurora `geopmread/geopmwrite --info` output captured in `docs/signals_and_controls/geopm_research_strict_*.md` (the curated research-relevant subset) and `geopm_*_described.md` (full lists). When in doubt, reread those.

Hardware: Aurora node = 2× Intel Xeon Max (Sapphire Rapids HBM, SPR-HBM) + 6× Intel Data Center GPU Max (Ponte Vecchio, "PVC"); each PVC has 2 tiles.

Required environment: `export ZES_ENABLE_SYSMAN=1` (or all LevelZero GPU signals return errors).

---

## The headline result: how power capping actually works on Aurora

There is **no writable GPU power cap** in our GEOPM build. Neither `GPU_POWER_LIMIT_CONTROL` (LevelZero) nor `DRM::HWMON::POWER1_MAX` (sysfs) appears in the writable-controls list. We have `GPU_POWER_TIME_WINDOW_CONTROL` (the cap's time window) but not the cap value itself.

**Instead, the 3000 W per-node cap is enforced indirectly via the following layered controls**:

1. **`BOARD_POWER_LIMIT_CONTROL`** (board domain, watts) — direct PL1 limit on whole-node power. Alias: `MSR::PLATFORM_POWER_LIMIT:PL1_POWER_LIMIT`. **This is our primary cap.** Set it to 3000 W and hardware will enforce it.
2. **`CPU_POWER_LIMIT_CONTROL`** (package, watts) — RAPL PL1 per CPU socket. Bounds the CPU's share.
3. **`DRAM_POWER_LIMIT_CONTROL`** (package, watts) — RAPL DRAM zone limit per socket. Bounds the DRAM share (HBM exposed through this).
4. **What's left of the board budget after CPU + DRAM enforced caps becomes the GPU's effective ceiling**, throttled by hardware autonomy. The agent additionally throttles GPUs explicitly via `GPU_CORE_FREQUENCY_MAX_CONTROL` per tile.

This is the central design fact that drives everything in the agent: **we choose how the 3000 W budget gets split among CPU / DRAM / GPU by setting per-component caps and freqs, not by capping the GPU directly.**

---

## Stock GEOPM agents (upstream, not Aurora-specific)

| Agent | Loop | Targets | Policy |
|-------|------|---------|--------|
| `monitor` | 200 ms | observation only | — |
| `power_governor` | 5 ms | CPU package power cap, per node, split evenly across sockets | `CPU_POWER_LIMIT` (W) |
| `power_balancer` | 5 ms | CPU power cap, shifts slack between nodes per epoch | `CPU_POWER_LIMIT` (W) |
| `frequency_map` | 2 ms | per-region CPU freq + optional uncore + optional GPU freq | `FREQ_CPU_DEFAULT`, `FREQ_GPU_DEFAULT`, `FREQ_CPU_UNCORE` + per-hash overrides |
| `ffnet` | 20 ms | per-domain NN classifier picks energy-efficient frequency | `PERF_ENERGY_BIAS` ∈ [0,1] + NN weight paths |
| `gpu_activity` | 20 ms | scales GPU core freq Fe..Fmax by `GPU_CORE_ACTIVITY` | `GPU_PHI` ∈ [0,1] |

None of the stock agents touches `BOARD_POWER_LIMIT_CONTROL`. Our `aurora_bandit` will.

---

## Writable controls (the agent's action surface)

### Board-level (the headline)

| Control | Unit | Domain | Notes |
|---------|------|--------|-------|
| `BOARD_POWER_LIMIT_CONTROL` | W | board | **Whole-node PL1.** Alias: `MSR::PLATFORM_POWER_LIMIT:PL1_POWER_LIMIT`. Direct 3000 W cap target. |
| `BOARD_POWER_TIME_WINDOW_CONTROL` | s | board | Averaging window for the board cap. |

### CPU

| Control | Unit | Domain | Notes |
|---------|------|--------|-------|
| `CPU_POWER_LIMIT_CONTROL` | W | package | RAPL PL1 per socket. Alias: `MSR::PKG_POWER_LIMIT:PL1_POWER_LIMIT`. Also aliased as `POWERCAP::CPU_POWER_LIMIT` (sysfs path). |
| `CPU_POWER_TIME_WINDOW_CONTROL` | s | package | PL1 averaging window. |
| `CPU_FREQUENCY_MAX_CONTROL` | Hz | core | HWP ceiling. Alias: `MSR::PERF_CTL:FREQ`. **Primary core-freq knob.** |
| `CPU_FREQUENCY_MIN_CONTROL` | Hz | cpu | sysfs `CPUFREQ::SCALING_MIN_FREQ`. |
| `CPU_FREQUENCY_DESIRED_CONTROL` | Hz | cpu | userspace-governor hint. |
| `CPU_FREQUENCY_GOVERNOR_CONTROL` | enum | cpu | 0=perf, 1=powersave, 2=ondemand, 3=conservative, 4=userspace, 5=schedutil. |
| `CPU_UNCORE_FREQUENCY_MAX_CONTROL` | Hz | package | Alias: `MSR::UNCORE_RATIO_LIMIT:MAX_RATIO`. **Gates memory bandwidth — keep HIGH for memory-bound workloads.** |
| `CPU_UNCORE_FREQUENCY_MIN_CONTROL` | Hz | package | Alias: `MSR::UNCORE_RATIO_LIMIT:MIN_RATIO`. |

### DRAM (HBM exposed via this domain)

| Control | Unit | Domain | Notes |
|---------|------|--------|-------|
| `DRAM_POWER_LIMIT_CONTROL` | W | package | **Writable on Xeon Max** (confirmed). Alias: `MSR::DRAM_POWER_LIMIT:POWER_LIMIT`. Also `POWERCAP::DRAM_POWER_LIMIT` (sysfs). |
| `DRAM_POWER_TIME_WINDOW_CONTROL` | s | package | |

### GPU (PVC, per-tile = `gpu_chip` domain)

| Control | Unit | Domain | Notes |
|---------|------|--------|-------|
| `GPU_CORE_FREQUENCY_MAX_CONTROL` | Hz | gpu_chip | RPS max per tile. Alias of `DRM::RPS_MAX_FREQ`. **Primary GPU lever** (since power cap isn't writable). |
| `GPU_CORE_FREQUENCY_MIN_CONTROL` | Hz | gpu_chip | RPS min per tile. Alias of `DRM::RPS_MIN_FREQ`. Useful to *force* tiles to stay at a low band. |
| `LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL` | 0..1 | — | Mem-vs-compute bias. Always read back — write may be silently refused. |
| `GPU_POWER_TIME_WINDOW_CONTROL` | s | gpu | The averaging window for `DRM::HWMON::POWER1_MAX`. **Note: the cap value itself is NOT writable in our build, only the time window.** |

### Intel SST (Speed Select) — confirmed available on Aurora

| Control | Unit | Domain | Notes |
|---------|------|--------|-------|
| `SST::COREPRIORITY_ENABLE:ENABLE` | bool | package | Enable SST-CP. |
| `SST::TURBO_ENABLE:ENABLE` | bool | package | Enable SST-TF (also enables SST-CP). |
| `SST::COREPRIORITY:ASSOCIATION` | int | core | Map a core to a priority level 0..3. |
| `SST::COREPRIORITY:{0..3}:FREQUENCY_MAX` | Hz | package | Per-level max freq. |
| `SST::COREPRIORITY:{0..3}:FREQUENCY_MIN` | Hz | package | Per-level min freq. |
| `SST::COREPRIORITY:{0..3}:PRIORITY` | 0..1 | package | Lower value = larger share of surplus power. |

**Use case**: deprioritize cores observed waiting in MPI by raising their `PRIORITY` value (less surplus power), freeing budget for busy cores or for GPUs (via the BOARD cap).

---

## Read-only signals (telemetry into the agent's state vector)

### Board

| Signal | Unit | Notes |
|--------|------|-------|
| `BOARD_POWER` | W | Average over 40 ms / 8 control loop iterations. Alias: `MSR::PLATFORM_ENERGY_STATUS:ENERGY` rate-of-change. |
| `BOARD_ENERGY` | J | U32 cumulative counter — handle rollover. |

### CPU

| Signal | Unit | Domain | Notes |
|--------|------|--------|-------|
| `CPU_POWER` | W | package | 40 ms avg. Derived from `CPU_ENERGY`. |
| `CPU_ENERGY` | J | package | Rolls over; see `CPU_MAX_ENERGY_RANGE`. |
| `CPU_MAX_ENERGY_RANGE` | J | package | Rollover value. |
| `CPU_POWER_LIMIT_DEFAULT` | W | package | TDP. Anchors "% of PL1" sweep levels. |
| `CPU_POWER_MAX_AVAIL` / `MIN_AVAIL` | W | package | Hardware bounds. |
| `CPU_FREQUENCY_STATUS` | Hz | cpu | Current operating freq. |
| `CPU_FREQUENCY_MAX_AVAIL` / `MIN_AVAIL` | Hz | package / cpu | Bounds. |
| `CPU_FREQUENCY_STICKER` | Hz | cpu | Base frequency. |
| `CPU_FREQUENCY_STEP` | Hz | cpu | Quantum for sweeps. |
| `CPU_UNCORE_FREQUENCY_STATUS` | Hz | package | Current uncore freq. |
| `CPU_CYCLES_THREAD` | count | cpu | `MSR::APERF:ACNT`. |
| `CPU_CYCLES_REFERENCE` | count | cpu | `MSR::MPERF:MCNT`. |
| `CPU_INSTRUCTIONS_RETIRED` | count | cpu | `MSR::FIXED_CTR0:INST_RETIRED_ANY`. **Requires `geopmwrite -e` to enable the fixed counter once per session.** |
| `CPU_PACKAGE_TEMPERATURE` | °C | package | Derived from PROCHOT + thermal status MSR. |
| `CPU_CORE_TEMPERATURE` | °C | core | Same source per-core. |

### DRAM (HBM)

| Signal | Unit | Domain | Notes |
|--------|------|--------|-------|
| `DRAM_POWER` | W | package | 40 ms avg. |
| `DRAM_ENERGY` | J | package | Rolls over. |
| `MSR::DRAM_PERF_STATUS:THROTTLE_TIME` | s | memory | Time throttled below requested freq due to DRAM PL1. **Key throttle telemetry.** |

### GPU (per-card, `gpu` domain)

| Signal | Unit | Notes |
|--------|------|-------|
| `GPU_POWER` | W | 40 ms avg, derived from `LEVELZERO::GPU_ENERGY`. |
| `GPU_ENERGY` | J | Card-level energy counter. |
| `GPU_POWER_LIMIT_CONTROL` | W | **READ-ONLY in our build** — the value of the cap (whoever set it: hardware default or systemd). Useful for the agent's state vector. |
| `GPU_POWER_LIMIT_DEFAULT` | W | TDP. |
| `LEVELZERO::GPU_POWER_LIMIT_MAX_AVAIL` | W | Hardware ceiling. |
| `GPU_UTILIZATION` | 0..1 | Utilization of all engines. (LevelZero logical engines may share hardware → signal range may be <1.) |

### GPU (per-tile, `gpu_chip` domain)

| Signal | Unit | Notes |
|--------|------|-------|
| `GPU_CORE_POWER` | W | Per-tile, 40 ms avg. |
| `GPU_CORE_ENERGY` | J | Per-tile cumulative. |
| `GPU_CHIP_ENERGY` | J | Tile-level energy counter (alternate). |
| `GPU_CORE_FREQUENCY_STATUS` | Hz | Latest cached freq. |
| `GPU_CORE_FREQUENCY_MAX_AVAIL` / `MIN_AVAIL` | Hz | Tile bounds. |
| `GPU_CORE_FREQUENCY_STEP` | Hz | |
| `GPU_CORE_ACTIVITY` (alias `LEVELZERO::GPU_CORE_UTILIZATION`) | 0..1 | Utilization of EUs. |
| `GPU_UNCORE_ACTIVITY` (alias `LEVELZERO::GPU_UNCORE_UTILIZATION`) | 0..1 | Utilization of copy engines. |
| `LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR` | 0..1 | Current value of the bias. |
| `LEVELZERO::GPU_CORE_TEMPERATURE_MAXIMUM` | °C | Max across compute sensors. |
| `LEVELZERO::GPU_MEMORY_TEMPERATURE_MAXIMUM` | °C | Max across memory sensors. |

### GPU throttle reasons — well-exposed, granular

All per-tile (`gpu_chip`):

| Signal | What it means |
|--------|----------------|
| `DRM::THROTTLE_REASON_STATUS` | Throttled for any reason (rollup). |
| `DRM::THROTTLE_REASON_PL1` | Average-power cap. |
| `DRM::THROTTLE_REASON_PL2` | Burst-power cap. |
| `DRM::THROTTLE_REASON_PL4` | Current cap. |
| `DRM::THROTTLE_REASON_THERMAL` | Thermal. |
| `DRM::THROTTLE_REASON_PROCHOT` | External PROCHOT signal. |
| `DRM::THROTTLE_REASON_RATL` | Reliability Average Temperature Limit. |
| `DRM::THROTTLE_REASON_VR_TDC` | Voltage regulator current limit. |
| `LEVELZERO::GPU_CORE_THROTTLE_REASONS` | LevelZero-side bitmask (see oneAPI Sysman spec). |

The agent should treat PL1/PL2/THERMAL as actionable (back off freq); RATL/VR_TDC/PROCHOT as "hardware is already protecting itself — don't fight it".

### SST (mirrors of the writable controls)

`SST::COREPRIORITY_ENABLE:ENABLE`, `SST::TURBO_ENABLE:ENABLE`, `SST::COREPRIORITY:ASSOCIATION` — all readable to confirm what the agent wrote actually took effect.

### Time

`TIME` — seconds since profiling start. Use for derived rates (Δenergy / Δtime).

---

## Resolved questions (vs `docs/open-questions.md`)

| Q | Status |
|---|--------|
| Q1: `DRAM_POWER_LIMIT_CONTROL` writable on Xeon Max? | **YES, writable.** Resolved by signals/controls dump. |
| Q2: HBM-specific RAPL zones? | **No separate HBM zone**; HBM exposed through standard `DRAM_*`. (Re-verify with `ls /sys/class/powercap/` if doubt.) |
| Q3: `DRM::HWMON::POWER1_MAX` (GPU per-card power cap) writable by users? | **NOT in the strict writable controls list at all.** Use indirect strategy (BOARD + CPU + DRAM caps; GPU freq cap on top). |
| Q4: Which IOGroup wins for aliased signals? | Aliases are documented per row in `described.md` (e.g. `BOARD_POWER` → `MSR::PLATFORM_ENERGY_STATUS:ENERGY`). |
| Q5: `REGION_RUNTIME` / `EPOCH_RUNTIME` as PIO signals? | **NOT in the strict signal list.** Derive from `TIME` + region boundaries inside the agent. |
| Q6: SST-CP enabled in BIOS? | **YES — full SST-CP control set is exposed and writable.** |

---

## Still open (must verify on Aurora before Phase 1 launches)

These the dumps cannot tell us — they are runtime / permission / numerical questions:

- **`BOARD_POWER_LIMIT_CONTROL` write permissions for ordinary users?** Almost certainly needs the GEOPM systemd service. Confirm with a `geopmwrite` attempt.
- **Default values** of `CPU_POWER_LIMIT_DEFAULT`, `GPU_POWER_LIMIT_DEFAULT`, `CPU_FREQUENCY_MAX_AVAIL`, `GPU_CORE_FREQUENCY_MAX_AVAIL`, `CPU_FREQUENCY_STEP`, `GPU_CORE_FREQUENCY_STEP` — anchor all sweep grids.
- **What is the default `BOARD_POWER_LIMIT_CONTROL`?** (Expect ~4500-5000 W. Determines headroom calibration in Phase 3.)
- **Does `CPU_INSTRUCTIONS_RETIRED` require `geopmwrite -e` once before reading?** Documented yes; verify behavior.
- **Does `LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL` actually take writes** on PVC, or silently refuse?
- **Domain enumeration**: how many `board`, `package`, `gpu`, `gpu_chip`, `core`, `cpu` instances exposed on a node? (Expect 1 board, 2 packages, 6 gpus, 12 gpu_chips, ~104 cores, ~208 cpus.)
- **GEOPM build version** installed on Aurora — pin our agent against it.

---

## References

- **Primary source on Aurora**: `docs/signals_and_controls/` — the actual signal & control dumps from this Aurora install.
- LevelZero IOGroup: https://geopm.github.io/geopm_pio_levelzero.7.html
- MSR IOGroup: https://geopm.github.io/geopm_pio_msr.7.html
- Sysfs IOGroup: https://geopm.github.io/geopm_pio_sysfs.7.html
- SST IOGroup: https://geopm.github.io/geopm_pio_sst.7.html
- POWERCAP IOGroup: see `POWERCAP::*` entries in the local dumps.
- High-level aliases: https://geopm.github.io/geopm_pio.7.html
- Source tree: https://github.com/geopm/geopm/tree/dev/libgeopmd/src
- ALCF Aurora docs: https://docs.alcf.anl.gov/aurora/
- xpu-smi: https://docs.alcf.anl.gov/aurora/performance-tools/xpu-smi/
