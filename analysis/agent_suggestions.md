# Agent design suggestions — derived from Phase 0 results

This document translates the Phase 0 response curves (see `analysis/results.md`) into concrete recommendations for the Phase 2 unified `geopm::Agent` plugin: which knobs to expose as bandit arms, which to keep as fixed setup, what context features to learn over, and per-class default policies for warm-start.

The Phase 0 sweep covers 7 benches × 10 knobs × 60 reps. The numbers cited below are best-safe energy reductions (`worst_dt < +5%`) extracted from `analysis/phase0_by_control.csv`.

---

## 1. Recommended arm set for the bandit

Six arms total. Three primary levers + two complementary GPU levers + one whole-node cap for cap-compliance mode.

| arm | knob | levels | role | rationale |
|---|---|---|---|---|
| **A1** | `CPU_FREQUENCY_MAX_CONTROL` | `{1.0, 1.6, 2.0, 2.5, 3.5}` GHz | biggest single energy lever | wins on 5/7 benches (up to −68% energy at +0.3% runtime); catastrophic on 2 → context-gated |
| **A2** | `CPU_UNCORE_FREQUENCY_MAX_CONTROL` | `{0.8, 1.6, 2.3}` GHz | secondary CPU lever | best knob on cpu-dgemm (−16%); harmful only on uncore-traffic benches (stream, osu) |
| **A3** | `GPU_CORE_FREQUENCY_MAX_CONTROL` | `{0.4, 0.8, 1.2, 1.6}` GHz | only GPU energy lever (no GPU PL on Aurora) | up to −28% on bursty-idle, −10 to −15% on every GPU-cold bench; harmful only when GPU is hot |
| **A4** | `LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL` | `{0.0, 0.5, 1.0}` | soft GPU bias | similar shape to A3 at lower magnitude — useful when A3's hard cap would be too aggressive |
| **A5** | `CPU_POWER_LIMIT_CONTROL` | `{50%, 70%, 100%}` of `CPU_POWER_LIMIT_DEFAULT` | smooth CPU cap | USEFUL_LINEAR on 4 benches; coexists with A1 (PL1 is the cap, A1 is the ceiling) |
| **A6** | `BOARD_POWER_LIMIT_CONTROL` | `{2000, 3000, 4500}` W | cap-compliance mode only | **does not arm during always-on mode**; only the user-supplied power cap is set when the user provides one |

**Dropped:** `DRAM_POWER_LIMIT_CONTROL`, `*_POWER_TIME_WINDOW_CONTROL`. Neither shows >3% energy headroom on more than one bench; not worth bandit arm overhead. Keep as fixed-default values.

**Floor knobs:** `CPU_FREQUENCY_MIN_CONTROL`, `CPU_UNCORE_FREQUENCY_MIN_CONTROL`, `GPU_CORE_FREQUENCY_MIN_CONTROL` are **mandatory mode-setup writes** (not bandit arms). The agent drops each to its absolute floor on workload entry so the corresponding MAX arms can actually bind below the driver default. This is the bug Phase 0 v1 hit and that the verify probe (`results/8509922/`) characterized; without it every MAX write below the existing MIN is silently clamped.

---

## 2. Context features (the "x" in LinUCB x·θ)

The arm choice depends on the workload class. Phase 0 shows the four classes are cleanly separated by these signals — all of them are already in the GEOPM PIO stream at the agent's 20 ms tick:

| feature | source signal | what it captures |
|---|---|---|
| `gpu_active_fraction` | mean over recent window of `GPU_UTILIZATION` across all 12 tiles | high → GPU-active class; low → GPU-cold |
| `gpu_compute_vs_mem` | ratio of `GPU_CORE_ACTIVITY` to `GPU_UNCORE_ACTIVITY` | high → GPU compute-bound; low → GPU memory-bound |
| `cpu_busy_fraction` | derived from `CPU_FREQUENCY_STATUS` vs `CPU_FREQUENCY_MAX_CONTROL` ratio and `CPU_POWER` headroom | high → CPU-active; low → CPU-cold |
| `mem_bw_fraction` | `DRAM_POWER` / `DRAM_POWER_LIMIT_DEFAULT` ratio over recent window | high → memory streaming |
| `comm_fraction` | (1 − `cpu_busy_fraction`) when also `gpu_active_fraction` low and no MPI region annotation → likely comm spin-wait | identifies osu/mpi-idle patterns |
| `board_power_headroom` | `board_power_cap − BOARD_POWER` (only when cap is set) | how much budget is left under user cap |
| `runtime_slack_remaining` | `(1+ε)·baseline_runtime − elapsed` | how much the agent can still spend on slowdown |

Optional one-hot from the user-provided benchmark hint (if available) — collapses cold-start time but the LinUCB should converge from the continuous features alone within ~5–10 application phases.

---

## 3. Per-class warm-start policy (Phase 1 → 2 transfer)

The Phase 0 verdict matrix gives a strong prior. Use it to initialize each arm's θ vector so the agent doesn't have to relearn from zero per workload. The pattern: on each class, set the safe-best arm's level as the initial policy and let the bandit explore from there.

| class | detection rule | warm-start arms |
|---|---|---|
| **GPU compute-bound** | `gpu_active_fraction > 0.7` AND `gpu_compute_vs_mem > 1.5` | A1=2.0 GHz, A2=1.6 GHz, A3=**MAX**, A4=1.0, A5=70%, A6=user cap |
| **GPU mem-bound** | `gpu_active_fraction > 0.7` AND `gpu_compute_vs_mem < 0.7` | A1=1.6 GHz, A2=1.6 GHz, A3=**MAX**, A4=0.5, A5=70%, A6=user cap |
| **CPU compute-bound** | `cpu_busy_fraction > 0.8` AND `gpu_active_fraction < 0.2` | A1=**MAX**, A2=**1.2 GHz** (the big win), A3=0.4 GHz, A4=0.25, A5=**default**, A6=user cap |
| **HBM memory-bound** | `mem_bw_fraction > 0.6` AND `cpu_busy_fraction > 0.5` | A1=**1.0 GHz**, A2=**MAX** (do not cap), A3=0.4 GHz, A4=0.0, A5=default, A6=user cap |
| **Comm/wait-dominated** | `cpu_busy_fraction < 0.4` AND `gpu_active_fraction < 0.2` | A1=1.0 GHz, A2=0.8 GHz, A3=0.4 GHz, A4=0.0, A5=50%, A6=user cap |
| **Comm collective (osu-like)** | `comm_fraction > 0.5` AND `cpu_busy_fraction > 0.3` | A1=**MAX** (do not touch), A2=**MAX**, A3=0.4 GHz, A4=0.0, A5=**default**, A6=user cap |
| **Bursty (gpu-bursty-idle-like)** | high variance in `gpu_active_fraction` over 1 s window | A1=1.6 GHz, A2=1.6 GHz, A3=0.4 GHz between bursts → MAX during bursts (state machine), A4=0.0, A5=70%, A6=user cap |

The last two rows are the agent's biggest value-add: alltoall and bursty workloads where static caps are unsafe but a context-aware agent can apply per-phase policy.

---

## 4. Always-on mode vs cap-compliance mode

The unified agent supports both per the project's two value propositions. Branch on whether the user passed a power cap on the command line.

### Always-on (no cap set)
- A6 is fixed at the default (no board cap).
- Reward: `−ΔEnergy` subject to `runtime ≤ (1+ε)·baseline_runtime`.
- Explore A1–A5; conservative ε defaults (0.05 → 5%) give the curves above on every bench except osu/cpu-dgemm where the bandit should converge to A1=MAX, A2=MAX (the safe-default arms).

### Cap-compliance (user-supplied cap, e.g. 3000 W headline scenario)
- A6 is **fixed at user_cap** for the run; bandit does NOT explore the board cap.
- The agent's job is allocation: how to split the cap budget across CPU / GPU / uncore via A1–A5 so runtime is minimized.
- Reward: `−runtime` subject to `BOARD_POWER ≤ user_cap`.
- At 3000 W on Aurora (idle floor ~2300 W, so 3000 W binds during work), the bandit should still prefer:
  - GPU-cold work → A3 hard cap (preserves GPU headroom for when work resumes)
  - GPU-hot work → A1 / A2 caps (preserves GPU budget)
  - Comm phases → all-MAX (let the cap throttle naturally)

---

## 5. Safety rails (regardless of arm choice)

Three hard rules the agent must enforce before any arm decision lands:

1. **MIN_CONTROL drop on workload start.** For every MAX arm (A1, A2, A3), write the corresponding `_MIN_CONTROL` to its absolute floor (CPU 0.8 GHz, UNCORE 0.8 GHz, GPU 0.2 GHz). Restore on exit. Without this, half the arm space is silently inaccessible.
2. **Write-readback assertion.** After every `geopmwrite`, read the same signal back. If `|readback − requested| / requested > 5%`, mark the arm unusable for the rest of the run and log to the diagnostic trace. Phase 0 caught the `LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL` "silently refused" failure mode this way once.
3. **Runtime slack tripwire.** If `elapsed / projected_baseline > 1 + ε - safety_margin` (safety_margin = 0.02), force all arms to MAX and freeze exploration for the rest of the run. The bandit's slowdown budget is one-shot per job.

---

## 6. Phase 2 implementation skeleton

```cpp
// agent/unified_agent.cpp (sketch)
class UnifiedAgent : public geopm::Agent {
    LinUCBPolicy policy_;
    SafetyMonitor safety_;
    MinControlGuard min_guard_;  // drops *_MIN_CONTROL on init, restores on exit

    void init(...) override {
        min_guard_.drop_all();   // mandatory before any MAX arm
        policy_.warm_start_from_priors("/etc/geopm-aurora/phase0_priors.json");
    }

    void adjust_platform(...) override {
        auto ctx = build_context();          // §2 features
        auto arms = policy_.select(ctx);     // 6-arm LinUCB
        safety_.assert_safe(arms);           // §5 rules
        write_controls(arms);
    }

    void sample_platform(...) override {
        auto reward = compute_reward();      // §4 mode-dependent
        policy_.update(last_ctx_, last_arms_, reward);
    }
};
```

`/etc/geopm-aurora/phase0_priors.json` ships the per-class warm-start θ vectors from §3, generated by:

```bash
/usr/bin/python3.10 analysis/scripts/generate_phase2_priors.py \
    --by-control analysis/phase0_by_control.csv \
    --out /etc/geopm-aurora/phase0_priors.json
```

(That script is Phase 2 work, not yet written.)

---

## 7. Validation plan for Phase 3

Two end-to-end MD apps (GROMACS-SYCL, LAMMPS-Kokkos/SYCL) under three conditions on N = 32 nodes:

1. **uncapped baseline** — no power management, current Aurora default.
2. **cap_governor_fair @ 3000 W** — stock GEOPM `power_governor` agent with equal split.
3. **cap_bandit @ 3000 W** — our unified agent.

Success criteria:
- For (2) vs (1): GROMACS ns/day drops by X%.
- For (3) vs (1): GROMACS ns/day drops by less than X (i.e. the bandit recovers some).
- For (3) vs (2): bandit beats the static governor on every bench's tts under the same cap.

Energy comparison: at iso-runtime (the unsteered case), the bandit should also save 10–25% energy via always-on mode on the comm/idle phases that GROMACS' update loop has.

---

## Reference: Phase 0 best-safe knob per bench (one-shot lookup)

| bench | best safe knob | dE / dt |
|---|---|---|
| stream | `CPU_FREQUENCY_MAX_CONTROL @ 1.0 GHz` | −68.1% / +0.3% |
| mpi-idle-wait | `CPU_FREQUENCY_MAX_CONTROL @ 1.0 GHz` | −64.0% / +0.2% |
| gpu-bursty-idle | `BOARD_POWER_LIMIT_CONTROL @ 2000 W` | −51.5% / +0.1% |
| babelstream | `CPU_FREQUENCY_MAX_CONTROL @ 1.0 GHz` | −42.2% / +0.3% |
| dgemm-gpu | `CPU_FREQUENCY_MAX_CONTROL @ 1.0 GHz` | −34.2% / +0.2% |
| cpu-dgemm | `CPU_UNCORE_FREQUENCY_MAX_CONTROL @ 0.8 GHz` | −16.3% / −0.3% |
| osu | (no safe knob — pure comm) | — |
