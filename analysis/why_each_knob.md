# Why each knob matters (or doesn't) — knob-by-knob reasoning

For each of the 35 strict GEOPM controls, what it **physically does**, why it's **important or not** for the AuroraGeopm agent, and what the **data + hardware mechanism** tell us.

Format per knob:
- **What it does**: physical/MSR-level effect
- **Why it matters or not**: mechanism reasoning
- **Verdict**: tier + bandit role

---

## Group 1 — Power-limit knobs (RAPL / board PL1)

These directly set how many watts the hardware is allowed to draw. They're the most physically meaningful knobs because they cap *actual energy delivery*.

### `BOARD_POWER_LIMIT_CONTROL` (board, watts)
- **What it does**: writes the whole-node PL1 power-limit MSR. The motherboard enforces it by throttling CPUs and/or GPUs to keep the running average below the limit over `BOARD_POWER_TIME_WINDOW` seconds.
- **Why important**: this is the *single most impactful* knob in the system. Everything downstream (CPU/DRAM/GPU power) is bounded by it. Aurora's headline scenario (3000 W cap) is a direct write to this knob.
- **Data**: 5/7 benches HARMFUL at aggressive levels (cap binds → throttle → runtime explodes). 2/7 benches USEFUL_LINEAR for ANY cap (time-bounded workloads where cap reduces power but not work). **Highest variance of any knob in the matrix**: −74 % to +376 % runtime.
- **Verdict**: **Tier 1. Bandit's most important arm.** Needs a workload classifier to decide direction.

### `CPU_POWER_LIMIT_CONTROL` (package, watts)
- **What it does**: RAPL package PL1. Each CPU socket has its own; the OS enforces the cap by reducing frequency/voltage of cores in that socket.
- **Why important**: the *only* lever that can selectively starve the CPU without touching GPU. Critical for the "free CPU savings on GPU bench" finding (CPU is idle during GPU compute → clamping it saves 5–10 % node energy at zero perf cost).
- **Data**: 4/7 USEFUL_LINEAR (GPU + idle/wait benches), 3/7 HARMFUL (CPU-bound benches throttle hard). Dose-response is clean: tdp_90 → small effect, tdp_60 → big effect.
- **Verdict**: **Tier 1. Bandit's second-most-important arm.** Trivially context-gated by `cpu_power_fraction`.

### `DRAM_POWER_LIMIT_CONTROL` (package, watts)
- **What it does**: RAPL DRAM PL1. Caps the power the memory subsystem can draw. The IMC throttles memory channels under cap pressure.
- **Why important on paper**: would directly hit memory-bound benches.
- **Why NOT important in practice**: DRAM is ~1 % of Aurora node power (38 W of 3800 W during stream). Even halving the cap only saves ~0.5 % node energy. Plus on Aurora the HBM is in-package so it's already heavily power-managed.
- **Data**: 5/7 NEGLIGIBLE. Best result: −3.3 % ΔE on cpu-dgemm (a marginal win).
- **Verdict**: **Tier 1 by mechanism, deprioritize in practice.** Keep as tiebreaker arm; don't expect headline wins.

### `POWERCAP::CPU_POWER_LIMIT`, `POWERCAP::DRAM_POWER_LIMIT` (package, watts)
- **What they do**: write the same MSRs as `CPU_POWER_LIMIT_CONTROL` and `DRAM_POWER_LIMIT_CONTROL` respectively, via the Linux `/sys/class/powercap/` interface instead of GEOPM's native MSR access path.
- **Why they DON'T matter as separate knobs**: confirmed empirically — every POWERCAP cell mirrors its CPU/DRAM_POWER_LIMIT_CONTROL counterpart verdict-for-verdict. Same MSR, same hardware effect, two write paths.
- **Verdict**: **Drop entirely**. Zero info loss.

---

## Group 2 — Power-limit time-window knobs (averaging window)

You're right to flag these — they're mostly bookkeeping.

### `BOARD_POWER_TIME_WINDOW_CONTROL` (board, seconds)
- **What it does**: sets the time window τ over which the rolling-average power must stay below `BOARD_POWER_LIMIT`. **Does NOT change the cap value itself.**
- **Why it doesn't really matter**: physics — `∫P dt = E`, regardless of τ. If the cap is non-binding, τ is irrelevant. If the cap *is* binding, a wider window lets brief bursts go through (slight perf benefit during transients), a narrower window enforces more tightly.
- **Data**: 6/7 NEGLIGIBLE. One USEFUL_LINEAR row on cpu-dgemm (`+1.2 % ΔE / +1.9 % Δt` at rb_double; `−2.5 % ΔE / −0.6 % Δt` at rb_half) — basically noise.
- **Verdict**: **Tier 2 (probe-only). Drop after confirming.** Not a bandit arm.

### `CPU_POWER_TIME_WINDOW_CONTROL`, `DRAM_POWER_TIME_WINDOW_CONTROL`, `GPU_POWER_TIME_WINDOW_CONTROL`
- **Same story** as `BOARD_POWER_TIME_WINDOW_CONTROL`, applied to the respective per-package / per-card power limits.
- **Data**: all NEGLIGIBLE majority. Sub-1 % effects.
- **Verdict**: Tier 2 (probe), drop after confirming.

### `POWERCAP::CPU_TIME_WINDOW`, `POWERCAP::DRAM_TIME_WINDOW`
- Aliases of `CPU_POWER_TIME_WINDOW_CONTROL` / `DRAM_POWER_TIME_WINDOW_CONTROL`. **Drop.**

---

## Group 3 — Frequency MAX (DVFS ceilings)

The complementary lever to power limits: directly set the maximum operating frequency. The hardware's voltage regulator chooses the appropriate V at that f.

### `CPU_FREQUENCY_MAX_CONTROL` (core, Hz)
- **What it does**: writes `MSR::PERF_CTL:FREQ`. Each core's voltage/frequency negotiation is bounded above by this value.
- **Why important**: the **direct** counterpart to `CPU_POWER_LIMIT_CONTROL`. P ≈ C·V²·f, V ≈ k·f → P ≈ f³. So reducing f to 70 % drops P to ~0.34. Cleaner control surface than power-limit (no enforcement delay; cap is instantaneous).
- **Hypothesis**: should give USEFUL_LINEAR curves on every CPU-bound bench (clean energy/perf tradeoff) and NEGLIGIBLE on GPU benches (CPU not on critical path).
- **Data**: **NO_DATA — the cells never produced output in the previous sweep**. Probably a `fraction_range` resolution bug (MIN_AVAIL/MAX_AVAIL signals not readable at write time on Aurora). The new `strict_knobs.json` reattempts with 5 levels.
- **Verdict**: **Tier 1. Highest-priority knob to re-characterize.** Probably comparable in usefulness to `CPU_POWER_LIMIT_CONTROL` but with cleaner curves.

### `CPU_UNCORE_FREQUENCY_MAX_CONTROL` (package, Hz)
- **What it does**: writes `MSR::UNCORE_RATIO_LIMIT:MAX_RATIO`. Sets the max frequency of the mesh/ring interconnect, LLC, and IMC.
- **Why important**: governs memory-bandwidth-relevant components. STREAM is uncore-bound, not core-bound — clamping core frequency on STREAM does nothing if uncore is still maxed.
- **Hypothesis**: should be USEFUL_LINEAR on stream (the core-freq knob's dual for memory-bound work) and NEGLIGIBLE on compute-bound.
- **Data**: NO_DATA in previous sweep (same issue as CPU_FREQUENCY_MAX).
- **Verdict**: **Tier 1. Re-characterize.** Likely the memory-side dual of CPU_FREQ_MAX.

### `GPU_CORE_FREQUENCY_MAX_CONTROL` (gpu_chip, Hz)
- **What it does**: writes Intel `DRM::RPS_MAX_FREQ`. Sets the maximum GPU compute frequency requested by the driver.
- **Why critical**: Aurora's GPU power limit (`GPU_POWER_LIMIT_CONTROL`) is **NOT writable**. So this is the *only* lever for GPU power on Aurora. Without it, the agent has no GPU control authority at all.
- **Hypothesis**: should be the GPU dual of CPU_FREQ_MAX — USEFUL_LINEAR on GPU-bound benches, "free saving" on GPU-idle benches (cpu-dgemm, mpi-idle-wait).
- **Data**: NO_DATA (same bug).
- **Verdict**: **Tier 1. Most critical missing knob.** Without GPU frequency control, the agent's authority over the 65–80 % of node energy spent on GPUs is zero.

### `LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL` (gpu_chip, 0–1)
- **What it does**: Intel-specific GPU performance-vs-power bias. 0.0 → aggressive power saving (slower kernels, deeper sleep), 1.0 → max perf (run at boost ceiling).
- **Why interesting**: orthogonal to `GPU_CORE_FREQUENCY_MAX` — it changes the GPU's *governor preference*, not the ceiling. Could give finer-grained behavior.
- **Hypothesis**: 0.0 should help on memory-bound GPU work (babelstream) by lowering boost; 1.0 should help on compute-bound (dgemm-gpu) by reducing throttle hesitation.
- **Data**: NO_DATA.
- **Verdict**: **Tier 1. Re-characterize.** Likely a complementary lever to GPU_FREQ_MAX.

---

## Group 4 — Frequency MIN (DVFS floors)

These set the LOWER bound. They only bind when the governor would otherwise clock down (idle).

### `CPU_FREQUENCY_MIN_CONTROL`, `CPU_UNCORE_FREQUENCY_MIN_CONTROL`, `GPU_CORE_FREQUENCY_MIN_CONTROL`
- **What they do**: write the minimum-frequency MSRs. Force the hardware to never drop below the value, regardless of governor choice.
- **Why NOT a bandit arm**: don't change power directly. They only bind during idle phases — and if the workload is wait-dominated (mpi-idle-wait), the floor knob *prevents* the energy savings the bandit wants by keeping cores warm.
- **Why STILL useful**: as **safety guards** for latency-critical phases. Example: "during the kernel-launch barrier on gpu-bursty-idle, force GPU_FREQ_MIN=0.5×max so the first kernel doesn't pay a wake-up penalty."
- **Data**: not directly tested in this campaign.
- **Verdict**: **Mode/setup knob**, not bandit arm. Configure at workload-entry hook based on workload class.

---

## Group 5 — Frequency DESIRED & GOVERNOR

### `CPU_FREQUENCY_GOVERNOR_CONTROL` (cpu, 0–5)
- **What it does**: chooses the kernel cpufreq governor (0=performance, 1=powersave, 2=ondemand, 3=conservative, 4=userspace, 5=schedutil).
- **Why critical (sort of)**: governor determines which other knobs are even effective. Under `performance` (our default), `CPU_FREQUENCY_DESIRED_CONTROL` is a no-op. Under `userspace`, DESIRED becomes the primary lever.
- **Why NOT a bandit arm**: changing governor mid-run breaks the bandit's reward attribution (rewards collected under one governor don't transfer). It's a session-level mode.
- **Verdict**: **Mode knob. Set once in PBS header.**

### `CPU_FREQUENCY_DESIRED_CONTROL` (cpu, Hz)
- **What it does**: writes the userspace-governor target frequency. Only effective under `userspace` governor.
- **Why USELESS on our setup**: we run `performance`, so this knob is a guaranteed no-op (every write returns success but does nothing).
- **Data**: not even worth testing; would all be NEGLIGIBLE.
- **Verdict**: **Drop entirely** unless / until we switch to userspace governor (which would forfeit the perf governor's faster turbo response).

### `CPUFREQ::*` (CPUFREQ::CPU_GOVERNOR, CPUFREQ::SCALING_MAX_FREQ, etc.)
- Linux sysfs aliases of the above. **Same MSRs, different write path.** Drop as redundant.

---

## Group 6 — SST (Intel Speed Select Technology)

A specialized family for asymmetric workloads. All depend on `SST::COREPRIORITY_ENABLE:ENABLE` being set first.

### `SST::COREPRIORITY_ENABLE:ENABLE` (package, 0/1)
- **What it does**: master switch for SST-CP (Core Priority). Enables the per-bucket priority/frequency mechanisms.
- **Why important**: gates the 12 specialist knobs below. **Without this, those knobs do nothing.**
- **Verdict**: **Mode knob.** Enable in PBS header if running asymmetric workloads (quicksilver, skewed MPI).

### `SST::TURBO_ENABLE:ENABLE` (package, 0/1)
- **What it does**: master switch for SST-TF (Turbo Frequency). Enables per-bucket turbo bins.
- **Verdict**: **Mode knob.** Enabling auto-enables SST-CP.

### `SST::COREPRIORITY:ASSOCIATION` (core, 0–3)
- **What it does**: assigns each core to one of 4 priority buckets.
- **Why important** when running imbalanced workloads: high-priority cores get larger share of power budget; low-priority cores throttle to make room.
- **Why NOT in our scope yet**: all 7 benches in our suite are uniformly-loaded MPI or single-process. Bucketing them gains nothing.
- **Verdict**: **Specialist knob. Defer to Phase 3** with quicksilver / skewed `mpi-idle-wait --skew-rank 0`.

### `SST::COREPRIORITY:0..3:FREQUENCY_MAX` (4 knobs, package, Hz)
- **What they do**: per-bucket frequency ceiling. Bucket 0 cores get this max, bucket 1 a different max, etc.
- **Why important** for skewed work: lets you pin the "hot" rank to high freq while clamping idle ranks.
- **Verdict**: **Specialist. Phase 3.**

### `SST::COREPRIORITY:0..3:FREQUENCY_MIN` (4 knobs, package, Hz)
- Per-bucket frequency floor. **Specialist. Phase 3.**

### `SST::COREPRIORITY:0..3:PRIORITY` (4 knobs, package, 0–1)
- Per-bucket *proportional* share of surplus power. Lower = larger share.
- **Verdict**: **Specialist. Phase 3.**

---

## Summary — which knobs to actually wire into the agent

```
Agent bandit action space (Phase 2):                 [Tier 1]
  • BOARD_POWER_LIMIT_CONTROL          (6 levels)
  • CPU_POWER_LIMIT_CONTROL            (6 levels)
  • DRAM_POWER_LIMIT_CONTROL           (6 levels)    ← keep as tiebreaker
  • CPU_FREQUENCY_MAX_CONTROL          (6 levels)    ← critical re-test
  • CPU_UNCORE_FREQUENCY_MAX_CONTROL   (6 levels)
  • GPU_CORE_FREQUENCY_MAX_CONTROL     (6 levels)    ← most critical (no GPU power cap)
  • GPU_PERFORMANCE_FACTOR             (6 levels)

Probe-only (drop after confirming small effect):    [Tier 2]
  • {BOARD, CPU, GPU}_POWER_TIME_WINDOW_CONTROL

Setup at PBS header / job-start hook:               [Mode]
  • CPU_FREQUENCY_GOVERNOR_CONTROL
  • SST::COREPRIORITY_ENABLE / SST::TURBO_ENABLE

Per-arm safety hooks (one-shot, conditional):       [Floor]
  • CPU_FREQUENCY_MIN_CONTROL
  • CPU_UNCORE_FREQUENCY_MIN_CONTROL
  • GPU_CORE_FREQUENCY_MIN_CONTROL

Defer to Phase 3 (asymmetric workloads):             [SST specialist]
  • SST::COREPRIORITY:* (12 knobs)
  • SST::COREPRIORITY:ASSOCIATION

DROP entirely:
  • POWERCAP::CPU_POWER_LIMIT             ← MSR alias of CPU_POWER_LIMIT_CONTROL
  • POWERCAP::DRAM_POWER_LIMIT            ← MSR alias of DRAM_POWER_LIMIT_CONTROL
  • POWERCAP::CPU_TIME_WINDOW             ← MSR alias of CPU_POWER_TIME_WINDOW_CONTROL
  • POWERCAP::DRAM_TIME_WINDOW            ← MSR alias of DRAM_POWER_TIME_WINDOW_CONTROL
  • CPU_FREQUENCY_DESIRED_CONTROL         ← no-op under performance governor
  • CPUFREQ::* (4 sysfs aliases)          ← same MSRs as MSR:: variants
```

35 strict controls → **7 bandit arms** + **3 probes** + **3 mode** + **3 floor** + **13 specialist** + **9 drop** = 38. (The 3 over-count comes from including the 4 CPUFREQ::* aliases that weren't in the strict-controls 35-list but live in the larger 165-control universe; drop these too.)

**Net bandit action space: 7 knobs × ~6 levels each = ~40 (knob, level) actions**. With workload context, prune to ~20 candidate arms per decision via the rules in `knobs_for_agent.md` § "What context features the bandit needs".

---

## Cross-reference

- `analysis/controls_classification.md` — the same content in table form, with empirical verdict counts
- `analysis/phase0_by_control_curves.md` — measured response curves per (bench, control)
- `experiments/phase1/strict_knobs.json` — the new sweep config that fills the data gaps
- `analysis/knobs_for_agent.md` — the action set + context-feature decision rules for the C++ agent
