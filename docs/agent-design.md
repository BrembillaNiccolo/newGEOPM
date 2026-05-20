# Unified GEOPM agent — design

A native C++ `geopm::Agent` plugin that detects workload class from PIO signals and picks (CPU freq, CPU uncore freq, GPU freq, optional power caps) from a Pareto-optimal action grid using **contextual LinUCB**, warm-started from Phase 1 sweep data.

This document is the spec; implementation is Phase 2. Reread Phase 1 results before implementing — they will refine the feature/action choices below.

## Two operating regimes — same agent, same code

| Regime | When | What the agent does |
|--------|------|---------------------|
| **Always-on energy saving** | `BOARD_POWER_LIMIT_CONTROL` at default (no binding cap) | Harvest free energy savings. Memory-bound code → cut CPU freq; comm-bound code → cut CPU freq during MPI waits; GPU-idle bursts → cut GPU freq. Constrained by `policy.runtime_slack`: only takes savings the user authorized as acceptable. |
| **Cap-compliance** | `BOARD_POWER_LIMIT_CONTROL` set below default | Allocate the cap across CPU / DRAM / GPU to recover TTS vs `power_governor`. Same reward function; the cap just makes the action-filter constraint tighter. |

The agent does NOT branch between regimes — they fall out of the same reward function and action filter automatically. The user signals which regime they care about by choosing `policy.power_cap_watts` (default = no cap) and `policy.runtime_slack` (0 = strict, large = aggressive).

---

## Plugin shape

Class `AuroraBanditAgent : public geopm::Agent` registered via the standard plugin factory entry point. Loaded by setting `GEOPM_PLUGIN_PATH=$PWD/agent/build/` and `--geopm-agent=aurora_bandit` at `geopmlaunch`.

Hierarchical role:

- **Leaf** (per-node): runs control loop; reads PIO, writes controls.
- **Tree/root**: aggregate node-level rewards for telemetry only; no cross-node policy in v1 (keep tractable).

Control loop period: **20 ms** (matches `ffnet` / `gpu_activity`; below this, contextual statistics are too noisy for LinUCB updates).

Policy schema (JSON, mirroring stock agents). **All values are user-supplied per job — none are hard-coded in the agent.**

```json
{
  "power_cap_watts": 3000,        // BOARD_POWER_LIMIT_CONTROL value set at job launch.
                                  //   The agent does NOT write this; it's used as a normalizer
                                  //   in the state vector and as a hint for action filtering.
                                  //   Pass the same value to geopmlaunch / the launch script
                                  //   that actually writes BOARD_POWER_LIMIT_CONTROL.
  "runtime_slack": 0.05,          // ε in "runtime ≤ (1+ε)·baseline". User sets per job.
                                  //   0.0 = no slowdown allowed (only free energy savings);
                                  //   0.05 = 5% slowdown tolerated; large values = energy-first.
  "perf_energy_bias": 0.5,        // 0=energy, 1=perf; Lagrangian weight (separate lever from
                                  //   runtime_slack — bias picks the trade-off curve;
                                  //   slack is the hard constraint).
  "ucb_alpha": 1.0,               // LinUCB exploration constant.
  "warm_start_path": "/path/to/phase1_seed.json",
  "action_grid_path": "/path/to/action_grid.json",
  "log_decisions": true
}
```

Per-run JSON files live in `experiments/phase3/<bench>/policy_<cap>W_<slack>pct.json`.

---

## State (feature vector)

Per control-loop tick, build feature vector `x_t ∈ R^d` from PIO. Drawn from Phase 1 signal-detector results; current best guesses (refine after Phase 1):

| Feature | Source | Why |
|---------|--------|-----|
| Board power frac | `BOARD_POWER` / `policy.power_cap_watts` | **headline**: how close to the node cap we are (uses the policy value, not the live readback, so the metric is stable across cap settings) |
| GPU activity avg | `GPU_CORE_ACTIVITY` averaged across 12 tiles | distinguishes GPU-busy vs GPU-idle |
| GPU power frac | (Σ `GPU_CORE_POWER`) / Σ `GPU_POWER_LIMIT_DEFAULT` | how saturated PVCs are |
| GPU freq normalized | mean `GPU_CORE_FREQUENCY_STATUS` / `GPU_CORE_FREQUENCY_MAX_AVAIL` | low + high `GPU_CORE_ACTIVITY` ⇒ memory-stalled GPU |
| CPU power frac | (Σ `CPU_POWER`) / Σ `CPU_POWER_LIMIT_DEFAULT` | how saturated CPUs are |
| CPU IPC | Δ`CPU_INSTRUCTIONS_RETIRED` / Δ`CPU_CYCLES_THREAD` | compute vs stall (requires `geopmwrite -e` to enable fixed counter once) |
| DRAM BW proxy | `DRAM_POWER` / `CPU_CYCLES_REFERENCE` (normalized) | memory traffic intensity |
| DRAM throttle | `MSR::DRAM_PERF_STATUS:THROTTLE_TIME` rate | memory cap binding? |
| MPI-wait frac | epoch-region time spent in regions with `REGION_HINT` ∈ {network, sync} (or per-tick `MSR::APERF/MPERF` divergence as proxy) | comm slack opportunity |
| GPU throttle bits | bitwise-OR of `LEVELZERO::GPU_CORE_THROTTLE_REASONS` + per-reason `DRM::THROTTLE_REASON_{PL1,PL2,THERMAL}` across tiles | inform Pareto choice; ignore RATL/VR_TDC/PROCHOT |
| Uncore-freq normalized | `CPU_UNCORE_FREQUENCY_STATUS` / `CPU_FREQUENCY_MAX_AVAIL` | what uncore is doing right now |

Feature standardization (zero-mean, unit-variance) from Phase 1 sweep statistics, saved in `warm_start_path`.

Optional: append polynomial / interaction features if LinUCB underfits (decide after first runs).

---

## Action space (arms)

A **small discrete set** (~16-32 arms) of (CPU freq cap, CPU uncore freq cap, GPU freq cap per tile, CPU power limit, DRAM power limit) tuples, drawn from the Pareto-optimal points discovered in Phase 1. Rationale: continuous control is overkill, and small discrete arm sets make LinUCB tractable.

**Critical constraint from `docs/geopm-aurora.md`**: there is **no writable GPU power cap** on Aurora. The agent shapes GPU energy spend in two ways instead:

- **Direct**: `GPU_CORE_FREQUENCY_MAX_CONTROL` per tile (12 tiles per node).
- **Indirect via budget allocation**: with `BOARD_POWER_LIMIT_CONTROL = 3000 W` enforced, every watt the agent gives to CPU+DRAM (by raising their per-component PL1) is a watt taken away from the GPU's effective ceiling, and vice versa.

So the arm tuple is:

```
(cpu_freq_max, cpu_uncore_freq_max, gpu_freq_max,
 cpu_pl1, dram_pl1)   # board cap is fixed by policy, not by the agent
```

Provisional arm categories (Phase 1 Pareto data will replace these):

| Arm class | When useful |
|-----------|-------------|
| `all_max` | unknown / first-tick; sets every knob to `*_MAX_AVAIL` |
| `gpu_starve` | GPU compute-bound + tight cap: lower `gpu_freq_max` so GPU runs cooler; redirect saved budget by raising `cpu_pl1` only if CPU has work |
| `cpu_starve_gpu_feed` | GPU compute-bound + tight cap: drop `cpu_pl1` and `cpu_freq_max` to floor so the GPU gets max share of the BOARD budget |
| `cpu_freq_low_uncore_high` | memory-bound: drop `cpu_freq_max` but keep `cpu_uncore_freq_max` high (uncore gates HBM bandwidth) |
| `cpu_freq_low_all` | comm-bound: drop `cpu_freq_max` during MPI slack; uncore can also drop a notch |
| `dram_save` | low memory pressure: tighten `dram_pl1` to free budget for compute |
| `aggressive_save` | deep cap regime; all knobs near floor |

Action grid lives in `action_grid_path` JSON so it can be updated without recompiling the agent.

---

## Reward

Per epoch (`geopm_prof_epoch` boundary, or fixed time window if no epoch):

```
energy_epoch = Σ_components ΔENERGY  (CPU + DRAM + GPU)
runtime_epoch = Δtime
ips_epoch = Δinstructions / runtime_epoch    # if available
```

Two reward formulations supported via `perf_energy_bias`:

1. **Lagrangian** (default):
   `r = -energy_epoch - λ · max(0, runtime_epoch - (1+ε)·baseline_runtime)`
   with `λ` adapted online (slow integrator) so the slack constraint holds in expectation. Here ε = `policy.runtime_slack`.

2. **Energy-per-instruction** (when IPS is meaningful):
   `r = -energy_epoch / max(ips_epoch, ε)`

`baseline_runtime` per workload class comes from the Phase 1 default-knob runs.

**Always-on saving falls out naturally**: when the BOARD cap is non-binding, the reward `-energy_epoch` still rewards arms that consume less power. The slack constraint `runtime ≤ (1+ε)·baseline` is what prevents the agent from over-throttling and trashing performance. If the user sets `runtime_slack = 0`, the agent will only take arms with zero expected perf cost — free savings only. If they set `runtime_slack = 0.20`, the agent will trade up to 20 % perf for energy even uncapped.

---

## Algorithm: contextual LinUCB

For each arm `a`, maintain:

- `A_a ∈ R^{d×d}` (ridge-regression covariance), init `λI`
- `b_a ∈ R^d` (response vector), init `0`

At each tick:

- `θ_a = A_a^{-1} b_a`
- UCB score: `s_a = θ_a^T x_t + α · sqrt(x_t^T A_a^{-1} x_t)`
- Pick `a* = argmax_a s_a` (with action-filter step: drop arms that would violate the slack constraint in expectation)
- After reward `r` lands at next epoch:
  - `A_{a*} += x_t x_t^T`
  - `b_{a*} += r · x_t`

`α` annealed from policy value over the first ~10 minutes of runtime, then frozen.

### Warm-start from Phase 1

The Phase 1 dataset is an offline observational dataset of `(x, a, r)` tuples (different policy: each row is whatever knob was being swept). To warm-start LinUCB without on-policy bias:

1. **Inverse propensity weighting**: estimate `π_0(a|x)` (the sweep selected `a` uniformly within each 1-D sweep — known) and reweight.
2. Solve the per-arm ridge regression on the reweighted data to get initial `(A_a, b_a)`.
3. Save to `warm_start_path` JSON.

Result: agent starts on-policy with informed `θ_a` rather than zero — avoids the cold-start regret cost.

### Fallback / safety

- If an arm would request a control outside `*_MIN/MAX_AVAIL`, clamp and log.
- If GPU throttle reasons report `THERMAL`, force `all_max` arm temporarily (let hardware autonomy take over).
- If throttle reasons report `RATL`, `VR_TDC`, or `PROCHOT`, don't react — hardware is already protecting itself; reacting can drive runaway oscillation.
- If write-readback shows a control didn't take (e.g. `LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL` silently refused), mark that knob unusable for the rest of the run.
- **Never write `BOARD_POWER_LIMIT_CONTROL`** from inside the agent — that's a policy-level setting written by the launch script per `policy.power_cap_watts`, not an action arm. The agent operates within whatever BOARD cap was set at job launch.
- The launch script must verify `geopmread BOARD_POWER_LIMIT_CONTROL board 0` after writing it; if write was refused (no systemd service), abort the run rather than silently running uncapped.

---

## Comparison baselines (Phase 2 acceptance)

Run the same benchmark set under each and report energy + runtime:

- `monitor` (no actuation; defines ceiling)
- `power_governor` (default node power)
- `power_balancer` (epoch-aware)
- `frequency_map` (uniform low / high; spot checks)
- `ffnet` (NN baseline if Aurora NN paths available)
- `gpu_activity` (GPU-only baseline)
- `aurora_bandit` (us)

Phase 2 ships when `aurora_bandit` ≥ `monitor` on energy at <(1+ε) runtime, beats `power_governor` at the same `CPU_POWER_LIMIT` setting on at least 5 of 8 benchmarks, and matches `gpu_activity` on GPU-bound workloads.

---

## Build & install

- Headers: GEOPM module on Aurora provides `<geopm/Agent.hpp>`.
- Build: out-of-source CMake in `agent/build/`. Link `-lgeopmd` (and `-lgeopm` if using IO outside the agent).
- Install: copy `.so` to a directory in `GEOPM_PLUGIN_PATH`.
- Smoke test: load with `geopmagent -a aurora_bandit -p '{}'`; should print agent metadata without segfault.

---

## RL upgrade path (if LinUCB plateaus)

- **Step 1**: contextual Q-learning with same features/actions; replaces per-arm linear model with tabular or small NN.
- **Step 2**: Thompson sampling instead of UCB if exploration is too greedy.
- **Step 3**: only consider continuous-action policies (DDPG / SAC) once the discrete-action agent is solidly beating baselines — the engineering cost of a continuous policy inside a 20 ms control loop is high.

Each step needs a separate offline replay validation against the Phase 1 dataset before going on-Aurora.

---

## Open design decisions (decide before Phase 2 starts)

- Whether to use `EPOCH` boundaries or a fixed 100-ms reward window. Epochs are clean but require app cooperation; not all 8 benchmarks call `geopm_prof_epoch`.
- Whether to share LinUCB statistics across nodes (federated bandit) — likely v2.
- Whether to expose `perf_energy_bias` as a per-region policy override.
