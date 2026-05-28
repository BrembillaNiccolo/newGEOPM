# Agent skeleton — implementation contract

This document specifies the layout, class boundaries, and per-file responsibilities of the Phase 2 `AuroraBanditAgent` plugin. It is the contract the actual code in `agent/src/` must satisfy.

Three inputs converge in this design:

1. **`docs/agent-design.md`** — the high-level spec (regimes, feature vector, action space, reward, LinUCB algorithm).
2. **`analysis/results.md` + `analysis/agent_suggestions.md`** — Phase 0 empirics: which knobs are USEFUL_LINEAR / USEFUL_THRESHOLD / HARMFUL per workload class, with the verified literal-Hz levels and `min_control` requirements.
3. **`~/GEOPM_Argonne_start/aurora_geopm_job/src/power_tree_agent.cpp`** — a working single-file reference Agent (1085 LoC) that demonstrates: plugin registration, `__attribute__((constructor))` factory hook, batch signal/control push, tree vs leaf split, REGION_HINT handling, env-flag debug, and the `BatchSignal` / `BatchControl` struct pattern.

The skeleton borrows the reference's plumbing (push_first_signal_group, push_all_controls, sample/adjust batch IO) and replaces its "static GPU/CPU power split" decision with a LinUCB arm selection driven by Phase 0 priors.

---

## File layout

```
agent/
├── SKELETON.md                         # THIS FILE
├── CMakeLists.txt                      # build
├── include/
│   └── AuroraBanditAgent.hpp           # public class declaration
├── src/
│   ├── AuroraBanditAgent.cpp           # main: init/sample/adjust loop + plugin reg
│   ├── ActionGrid.hpp / .cpp           # discrete arm tuples; JSON load
│   ├── FeatureExtractor.hpp / .cpp     # PIO batch → R^d feature vector
│   ├── LinUCB.hpp / .cpp               # contextual bandit core (A_a, b_a updates)
│   └── MinControlGuard.hpp / .cpp      # drops *_MIN_CONTROL on init, restores on exit
└── tests/                              # gtest unit tests (later)
```

Single shared object: `libgeopmagent_aurora_bandit.so.2.2.0` (the `.2.2.0` suffix is required by GEOPM's plugin loader — symlinks are ignored).

---

## Class boundaries

### `AuroraBanditAgent : public geopm::Agent`

The only class GEOPM knows about. Mirrors the reference's structure:

| Override | Where the work lives |
|---|---|
| `init(level, fan_in, is_level_root)` | Builds `FeatureExtractor`, `ActionGrid`, `LinUCB`, `MinControlGuard`. Drops MIN_CONTROL floors. Loads warm-start from `policy.warm_start_path`. |
| `validate_policy(policy)` | Fills defaults (`power_cap_watts=0` → no cap; `runtime_slack=0.05`; `ucb_alpha=1.0`; etc.). Validates ranges. |
| `sample_platform(out_sample)` | LEAF only. Calls `FeatureExtractor::extract()` → `x_t`. Stores `x_t` for use in the next `adjust_platform`. Also computes `reward_t` against the *previous* action and feeds `LinUCB::update(x_{t-1}, a_{t-1}, r_t)`. |
| `adjust_platform(in_policy)` | LEAF only. Calls `LinUCB::select(x_t)` → arm index. Resolves arm to a control vector via `ActionGrid::resolve(arm_idx)`. Applies writes via `apply_arm()` (with per-write readback assertion). |
| `aggregate_sample(children, out_sample)` | TREE only. Aggregates per-node rewards/utilization for telemetry. No cross-node policy in v1. |
| `split_policy(in_policy, out_policy)` | TREE only. Pass-through in v1 (every node gets the same policy). |
| `report_header()` / `report_host()` | Dump agent metadata + last decisions for the geopm-report YAML. |
| `trace_names()` / `trace_values()` | Per-tick: arm_idx, ucb_score, energy_delta, runtime_delta, cap_headroom — written to the geopm-trace CSV for offline analysis. |

The class owns:
- `std::unique_ptr<FeatureExtractor> m_features`
- `std::unique_ptr<ActionGrid>      m_actions`
- `std::unique_ptr<LinUCB>          m_bandit`
- `std::unique_ptr<MinControlGuard> m_min_guard`
- A `BatchControl` table mirroring the active arm — one entry per (control, domain, instance).
- Per-tick state: `m_last_x`, `m_last_arm`, `m_last_reward_time`, `m_energy_baseline_J`, `m_runtime_baseline_s`.

### `MinControlGuard`

Encapsulates the Phase 0 fix: drop CPU_FREQUENCY_MIN_CONTROL / CPU_UNCORE_FREQUENCY_MIN_CONTROL / GPU_CORE_FREQUENCY_MIN_CONTROL to their absolute floors on workload entry so MAX writes can bind below the driver default. Originals are restored in the dtor.

Hardcoded floors (from `experiments/phase1/strict_knobs.json`, verified by `results/8509922/knob_verification.txt`):
- CPU core MIN floor: 0.8 GHz
- CPU uncore MIN floor: 0.8 GHz
- GPU core MIN floor: 0.2 GHz

Drop happens once at `init()`; restore once at agent destruction. Failures are logged but non-fatal (the agent still works, just with the MAX arms partially blocked — same as Phase 0 v1).

### `ActionGrid`

A discrete set of arm tuples. Each arm = a partial setting of `(CPU_FREQUENCY_MAX, CPU_UNCORE_FREQUENCY_MAX, GPU_CORE_FREQUENCY_MAX, GPU_PERFORMANCE_FACTOR, CPU_POWER_LIMIT)`. Unspecified knobs in an arm are left at their previous value.

Loaded from `policy.action_grid_path` JSON. Default grid lives in `agent/src/action_grid_default.json` (shipped with the .so install) and reflects the Phase 0 winners. Schema:

```json
{
  "arms": [
    {
      "name": "all_max",
      "controls": {}
    },
    {
      "name": "memory_bound_save",
      "controls": {
        "CPU_FREQUENCY_MAX_CONTROL":  1.0e9,
        "CPU_UNCORE_FREQUENCY_MAX_CONTROL": 2.3e9,
        "GPU_CORE_FREQUENCY_MAX_CONTROL": 0.4e9
      }
    },
    ...
  ]
}
```

`ActionGrid::resolve(arm_idx)` returns a `std::vector<ControlWrite>` that the agent then applies through its `BatchControl` table.

### `FeatureExtractor`

Pushes a fixed set of PIO signals at agent init, samples them per tick, and builds the 11-dimensional feature vector specified in `docs/agent-design.md` §State. Implements the signal-name fallback chain from `power_tree_agent.cpp::push_first_signal_group` so the agent works on Aurora (Stack B) and degrades cleanly on stacks where a signal is missing.

Standardization (μ, σ per feature) is loaded from `policy.warm_start_path` and applied each tick before features are handed to LinUCB.

### `LinUCB`

Contextual bandit. Per arm a: `(A_a ∈ R^{d×d}, b_a ∈ R^d)`, init `A_a = λI`, `b_a = 0`.

- `select(x_t)` → `argmax_a (θ_a^T x_t + α · sqrt(x_t^T A_a^{-1} x_t))`, with action-filter step that drops arms previously shown to violate the slack constraint.
- `update(x, a, r)` → `A_a += xx^T; b_a += r·x`.
- `warm_start_from_json(path)` loads pre-fit `(A_a, b_a)` from Phase 0 priors via the inverse-propensity-weighted ridge regression described in `docs/agent-design.md` §"Warm-start from Phase 1".

For v1 keep the math in `<Eigen>` (header-only, already needed by ML deps). If Eigen is unavailable on Aurora, fall back to a tiny in-tree dense linear solver (Cholesky, ~50 LoC).

---

## Lifecycle

```
geopmlaunch
  └─ controller process
       ├─ dlopen(libgeopmagent_aurora_bandit.so.2.2.0)
       │     └─ __attribute__((constructor)) registers plugin
       ├─ agent_factory().make_plugin("aurora_bandit") → AuroraBanditAgent()
       └─ for each compute node:
            init(level=0, ..., is_level_root=true)
              ├─ MinControlGuard::drop_all()          ← MANDATORY (Phase 0 fix)
              ├─ FeatureExtractor::push_signals()
              ├─ ActionGrid::load(policy.action_grid_path)
              ├─ LinUCB::warm_start_from_json(policy.warm_start_path)
              └─ push controls (one BatchControl per arm × instance)
            loop until app exits:
              sample_platform(out_sample):
                x_t = FeatureExtractor::extract()
                r_t = compute_reward(prev_arm_outcome)
                LinUCB::update(x_{t-1}, a_{t-1}, r_t)
              adjust_platform(in_policy):
                a_t = LinUCB::select(x_t)
                writes = ActionGrid::resolve(a_t)
                apply_arm(writes)          ← BatchControl::adjust + write-readback
              wait(period)
            destructor:
              MinControlGuard::restore_all()
```

The LEAF role does all the work. Tree-level roles aggregate per-node metrics for telemetry only.

---

## Safety rails (must be implemented before plugin ships)

These match `agent_suggestions.md` §5:

1. **MIN_CONTROL drop on init** — `MinControlGuard` does this unconditionally. Without it, ~half the GPU_FREQ_MAX action space is silently inaccessible (Phase 0 v1 bug).
2. **Write-readback assertion** — every `m_platform_io.adjust(...)` followed (on the next tick) by a `sample()` of the same control. If `|readback − requested| / requested > 0.05`, the control is marked unusable for the rest of the run; arms that depend on it are filtered.
3. **Runtime slack tripwire** — every N ticks, project `elapsed × (baseline_runtime / progress_indicator)`. If the projection exceeds `(1 + ε − 0.02) × baseline_runtime`, force `all_max` for the rest of the run and freeze LinUCB exploration. The slack budget is one-shot per job.
4. **Throttle awareness** — if `LEVELZERO::GPU_CORE_THROTTLE_REASONS` reports THERMAL, fall back to `all_max` for that tick. RATL / VR_TDC / PROCHOT are ignored (hardware-autonomous; reacting causes oscillation).
5. **Never write `BOARD_POWER_LIMIT_CONTROL`** from inside the agent. That's set by the launch script per `policy.power_cap_watts`. The agent reads it only as a normalizer.

---

## Two-regime behavior — no branching

The agent does NOT have separate "always-on" and "cap-compliance" code paths. The user picks the regime via `policy.power_cap_watts`:

- **= 0 (or unset)** → no board cap, agent harvests free energy via slack budget.
- **> 0** → launch script wrote `BOARD_POWER_LIMIT_CONTROL = power_cap_watts`. Agent reads BOARD_POWER as a feature; action filter naturally drops arms that would exceed the cap.

Same reward function (`r = −energy − λ·max(0, runtime − (1+ε)·baseline)`) covers both regimes — the cap just makes the runtime constraint bite earlier.

---

## Build

```bash
cd agent
mkdir -p build && cd build
cmake -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CXX_COMPILER=mpicxx \
      -DGEOPM_PREFIX=$GEOPM_ROOT \
      ..
make -j
```

Produces `bin/libgeopmagent_aurora_bandit.so.2.2.0`. Install by copying into a directory on `GEOPM_PLUGIN_PATH`.

Smoke test on a login node:
```bash
GEOPM_PLUGIN_PATH=$PWD/bin geopmagent -a aurora_bandit -p '{}'
# Should print the agent's policy_names() and sample_names() without segfault.
```

Smoke test on an allocated compute node:
```bash
geopmlaunch mpiexec \
  --geopm-agent=aurora_bandit \
  --geopm-policy=experiments/phase3/policy_default.json \
  --geopm-report=report.yaml \
  --geopm-trace=trace.csv \
  --geopm-period=0.020 \
  -- <ranks> <bench>
```

---

## What's NOT in the skeleton (Phase 2 follow-ups)

- Warm-start training: `analysis/scripts/generate_phase2_priors.py` — converts `phase0_cells.csv` into `(A_a, b_a)` JSON via IPS-weighted ridge regression. Skeleton accepts the file but ships with an empty-prior fallback.
- Action-filter feasibility checks beyond "previously violated slack" — the simple version drops arms whose Phase 0 verdict on the *currently inferred class* was HARMFUL.
- Per-region overrides via `geopm_prof_epoch` — v1 uses a fixed 100 ms reward window.
- Federated bandit across nodes — v1 keeps statistics local per leaf.
- Continuous-action policies (DDPG / SAC) — only if discrete LinUCB plateaus.

---

## Mapping reference → skeleton

| Reference (`power_tree_agent.cpp`) | Our skeleton |
|---|---|
| `BatchSignal` / `BatchControl` structs | reused verbatim in `AuroraBanditAgent.hpp` |
| `push_first_signal_group()` / `push_all_signals()` | reused inside `FeatureExtractor::push_signals()` |
| `init()`, `validate_policy()`, etc. | same overrides; different internals |
| Static GPU/CPU split via `gpu_frac = util_gain · util − mpi_penalty · stall` | replaced by `LinUCB::select()` over `ActionGrid` |
| Single arm "split node budget" | discrete arm set from Phase 0 |
| `m_assigned_node_power` policy plumbing | kept as `policy.power_cap_watts` feature, not actuated |
| `__attribute__((constructor)) static void *_agent_load()` | same registration pattern, plugin name `aurora_bandit` |
| Env-flag debug (`POWER_TREE_VERBOSE` etc.) | `AURORA_BANDIT_VERBOSE`, `AURORA_BANDIT_LOG_STRIDE`, `AURORA_BANDIT_ENABLE_CONTROLS` |
