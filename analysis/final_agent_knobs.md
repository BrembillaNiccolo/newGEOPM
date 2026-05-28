# Final agent knob inventory — what's in, what's out, what might be next

The agent's knob set after Phase 0 + Phase 1.5 (a/b/c/d). Written at the end of Phase 1.5 when all 5 interaction-test blocks landed.

Sources:
- `analysis/results.md` — Phase 0 single-knob sweep results
- `analysis/phase1_5/results.md` — Phase 1.5 block-by-block findings
- `analysis/prod_45s/results.md` — prod-vs-scaling comparison
- `agent/src/action_grid_default.json` — the actual arm grid the agent ships with

---

## The knobs the agent actually writes (5 control levers + 3 mandatory floor drops)

### Bandit-controlled (per-arm choices)

| # | Knob | Range | Used by arms | Why |
|---|---|---|---|---|
| 1 | `CPU_FREQUENCY_MAX_CONTROL` | 1.0–3.5 GHz (literal Hz) | A1, A2, A3, A4, A5, A7 | **Biggest CPU energy lever.** Phase 0 showed −68 % on stream, −64 % on mpi-idle-wait at 1.0 GHz. The fundamental DVFS knob for CPU. |
| 2 | `CPU_UNCORE_FREQUENCY_MAX_CONTROL` | 0.8–2.3 GHz | A1, A2, A3, A4, A5, A7 | **Memory mesh / LLC frequency.** Critical because dropping it on HBM-streaming benches breaks bandwidth (+57 % runtime on stream when UNCORE alone is capped), but dropping it on CPU-compute benches saves 16 %. The agent needs the *independent* axis from CPU_FREQ to express e.g. "fast cores + slow mesh" (A3) vs "slow cores + fast mesh" (A1). |
| 3 | `GPU_CORE_FREQUENCY_MAX_CONTROL` | 0.4–1.6 GHz | A1, A2, A3, A4, A5, A7 | **Only writable GPU energy lever on Aurora** (`GPU_POWER_LIMIT_CONTROL` isn't writable). Once we fixed the MIN-clamping bug, it gives −28 % on bursty-idle and similar savings on every GPU-cold workload. |
| 4 | `LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL` | 0.0–1.0 | A1, A2, A3, A4, A5, A7 | **Soft GPU bias.** Phase 1.5 Block D proved it's NOT redundant with #3 — flips energy by 6–22 % at fixed GPU_FREQ. Counter-intuitively PF=1.0 (compute bias) saves more when GPU is capped low (it finishes the tiny GPU work faster → more deep idle), but PF=1.0 *hurts* dgemm-gpu at GPU=MAX. Independent axis. |
| 5 | `CPU_POWER_LIMIT_CONTROL` | 105 W (only) | A7 only | **One distinguishing knob for the most-aggressive arm.** Phase 1.5 Block E showed PL=175 W is redundant with CPU=1.0 GHz on 5/6 benches — dropped from A4. Kept on A7 at 105 W (untested but more aggressive) so A7 isn't a duplicate of A4. |

### Mandatory floor drops (not bandit choices — fixed setup writes)

| Knob | Floor written | Why |
|---|---|---|
| `CPU_FREQUENCY_MIN_CONTROL` | 0.8 GHz | Otherwise MAX writes below the existing MIN get silently clamped (verified bug from Phase 0 v1). |
| `CPU_UNCORE_FREQUENCY_MIN_CONTROL` | 0.8 GHz | Same. |
| `GPU_CORE_FREQUENCY_MIN_CONTROL` | 0.2 GHz | This was the Phase 0 v1 disaster — PVC's MIN ships pinned at 1.5 GHz which silently ate every cap below 1.5. |

Restored to originals on agent exit via `~MinControlGuard()`.

### Read-only (informational features, not actuated)

| Knob | Why the agent only reads it |
|---|---|
| `BOARD_POWER_LIMIT_CONTROL` | Set by the **launch script** per `policy.power_cap_watts`. Agent reads `BOARD_POWER` as a feature for the LinUCB context. Writing it from inside the agent is forbidden — that's a policy-level setting. |
| `BOARD_POWER`, `CPU_POWER`, `GPU_POWER`, `DRAM_POWER`, `BOARD_ENERGY`, `*_FREQUENCY_STATUS`, `GPU_CORE_ACTIVITY`, `*_THROTTLE_REASONS` | All used by `FeatureExtractor` to build the 11-D context vector. |

---

## Knobs we tested and explicitly dropped

| Knob | Why dropped |
|---|---|
| `DRAM_POWER_LIMIT_CONTROL` | NEGLIGIBLE on 5/7 benches (Phase 0). Only stream/cpu-dgemm show 1–3 % — not worth the bandit arm cost. |
| `BOARD_POWER_TIME_WINDOW_CONTROL` | NEGLIGIBLE on all 7 benches (Phase 0). Smoothing window doesn't change cap value. |
| `CPU_POWER_TIME_WINDOW_CONTROL` | NEGLIGIBLE on 6/7; cpu-dgemm shows 1 % — not worth keeping. |
| `GPU_POWER_TIME_WINDOW_CONTROL` | NEGLIGIBLE on 6/7. |
| `CPU_POWER_LIMIT_CONTROL` *in arm A4* | Phase 1.5 Block E proved it's redundant with CPU_FREQ when CPU is already at 1.0 GHz, AND it catastrophically interacts with cpu-dgemm. |

---

## Knobs that exist on Aurora but we never tested — potentially useful

Looking at `docs/signals_and_controls/` and the verified writable list:

| Knob | Reason it might be worth a Phase 1.6 / Phase 2 follow-up | Why not now |
|---|---|---|
| `CPU_FREQUENCY_MIN_CONTROL` *as a bandit arm* | Could prevent wake-up latency on bursty workloads — "during the comm phase, force CPU MIN=2.0 GHz so the first compute kernel doesn't pay a P-state ramp penalty". | Not an energy lever directly — it's a **safety hint** for latency-critical phases. Better as a hook than a bandit arm. |
| `GPU_CORE_FREQUENCY_MIN_CONTROL` *as a bandit arm* | Same logic for GPU: hold GPU MIN high during a kernel-launch barrier on gpu-bursty-idle so the first kernel doesn't slow-clock-start. | Same: hook material, not arm. |
| `GPU_POWER_LIMIT_CONTROL` | The "right" GPU energy lever — direct power cap rather than frequency cap. | **Not writable on Aurora.** Verified in 8509922. The OS/driver returns an error on write. We use GPU_FREQ_MAX as the substitute. |
| `LEVELZERO::GPU_MEM_FREQUENCY_MAX_CONTROL` (if exposed) | Could decouple HBM bandwidth from compute frequency on PVC. Would matter on babelstream where memory is the bottleneck even though it's GPU-bound. | Not verified writable on this stack. Worth a `geopmwrite` probe before designing any sweep. |
| `MSR::POWER_CTL:C1E_ENABLE` / C-state config | Could give the agent control over CPU deep-sleep entry — bigger savings on long idle periods than DVFS. | Phase 0 didn't include any C-state knobs because they require root in many configs. ALCF policy unclear. |
| `CPU_POWER_LIMIT_CONTROL` *at non-tested levels* (e.g. 250 W, "soft" caps) | Phase 0/1.5 only tested 105 W, 175 W and a few %TDP variants. There may be a sweet spot at 200–250 W that binds under load but doesn't crush cpu-dgemm. | Untested. Worth a small focused sweep. |
| `MSR::PERF_BIAS:PERFORMANCE_ENERGY_BIAS` (IA32_ENERGY_PERF_BIAS) | Soft analog of GPU's PERFORMANCE_FACTOR but for CPU side. Would be the CPU dual of A4/A5's PF=1.0 setting. | Documented but not in the GEOPM verified-writable inventory. Probe before designing an arm. |

---

## The summary table

| Category | Count | Knobs |
|---|---|---|
| **Bandit arm dimensions** | 5 | CPU_FREQ_MAX, CPU_UNCORE_MAX, GPU_FREQ_MAX, GPU_PERF_FACTOR, CPU_POWER_LIMIT (A7 only) |
| **Mandatory setup writes** | 3 | CPU/UNCORE/GPU `_MIN_CONTROL` to floor |
| **Read-only context features** | ~12 signals | BOARD/CPU/GPU/DRAM POWER + ENERGY + FREQUENCY_STATUS + activity + throttle reasons |
| **Tested and dropped** | 4 | DRAM_PL, 3 × TIME_WINDOW |
| **Worth future investigation** | 4–6 | MIN_CONTROL as state-machine hint, intermediate CPU_PL values, MSR PERF_BIAS, MEM_FREQ if exposed |

---

## Why this set is *probably* enough for Phase 2

- **Empirically validated**: 21,645 cells across 4 PBS jobs prove each of the 5 chosen knobs moves either energy or runtime by >5 % on at least one workload class.
- **Orthogonal**: Phase 1.5 Block D proved PF and GPU_FREQ are independent. Block E proved CPU_PL is redundant *only* when stacked on CPU_FREQ=1.0 — A7's lone PL=105 W keeps the cap-compliance regime hedged.
- **Tractable for LinUCB**: 8 arms × 5 knobs = ~16-dim joint action space, fits the d=11 feature vector well below the curse-of-dimensionality threshold.
- **Recoverable**: anything we missed surfaces as worse-than-expected reward, which the bandit's online update absorbs without policy disruption.

The honest answer on "are we done?" is: for **always-on energy saving on the 4 main classes** (mem-bound, compute-bound CPU, compute-bound GPU, comm/idle), yes. For **cap-compliance at tight BOARD caps** (3 kW, the headline scenario), there's one remaining open question — whether intermediate CPU_PL values (200–250 W) provide a useful "soft cap" arm. Worth one Phase 1.6 sweep if cap-compliance becomes the priority before Phase 3.
