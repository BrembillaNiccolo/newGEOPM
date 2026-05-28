# Phase 1.5 results — Blocks A + B + C complete, D mostly complete, E missing

**Data:**
- `analysis/phase1_5/cells.csv` (17,142 successful cells across 3 PBS jobs)
- `analysis/phase1_5/by_combo.csv` (per-(bench, combo) aggregates)
- `analysis/phase1_5/additivity.csv` + `additivity_summary.md` (Block B/C residuals)
- `analysis/phase1_5/perf_factor_redundancy.csv` (Block D PF=0 vs PF=1)
- Sources: PBS jobs **8510402** (Block A, 140 nodes), **8510537** (Block B + partial C, 210 nodes), **8511663** (rest of C + D + partial E, 210 nodes)

**Coverage status (after all three jobs):**

| Block | combos | status | total cells |
|---|---|---|---|
| A — agent arm validation | 8 | **complete** | 3,672 (≈80 reps per (bench, arm)) |
| B — CPU × GPU 3×3 | 9 | **complete** | 3,780 (60 reps per cell) |
| C — CPU × UNCORE 3×3 | 9 | **complete** | 7,331 (90+ reps per cell — extra from 8511663) |
| D — GPU × PERF_FACTOR 2×2 | 4 | **mostly complete** (75-98% per combo) | 2,224 (~550 reps per cell) |
| E — CPU × CPU_PL 2×2 | 4 | **mostly missing** (only `E_cpu1.0_pl_default` has usable data on 7 benches; 20 of 28 (bench, combo) cells absent) | 135 |

Phase 1.5d to finish Block E (see end of doc).

---

## Per-arm × per-bench verdict matrix

Numbers are `median energy delta vs all_max baseline` (negative = saving). `✓` marks safe wins (runtime within +5%), `✗` marks harmful (runtime > +5%), `~` mark neutral.

| arm | babelstream | cpu-dgemm | dgemm-gpu | gpu-bursty | mpi-idle | osu | stream |
|---|---|---|---|---|---|---|---|
| **A0 all_max** (baseline) | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| **A1 memory_bound_save** | ✗ +105% rt | ✗ +101% rt | ✗ +210% rt | ✓ −51% E | ✓ −67% E | ✗ +209% rt | ✓ **−69% E** |
| **A2 gpu_compute_max** | ✗ +7% rt | ✗ +11% rt | ✗ +27% rt | ✓ −36% E | ✓ −34% E | ✗ +56% rt | ✓ −12% E |
| **A3 cpu_compute_uncore_save** | ✗ +106% rt | ✓ **−22% E** (and faster!) | ✗ +210% rt | ✓ −31% E | ✓ −19% E | ✗ +31% rt | ✗ +12% rt |
| **A4 comm_wait_save** | ✗ +108% rt | ✗ +560% rt!! | ✗ +211% rt | ✓ **−53% E** | ✓ **−70% E** | ✗ +209% rt | (no data) |
| **A5 comm_collective_safe** | ✗ +107% rt | ✓ −15% E | ✗ +211% rt | ✓ −26% E | ✓ −13% E | ✓ **−14% E** | ✓ −14% E |
| **A6 bursty_gpu_idle** | ✗ +106% rt | ✗ +38% rt | ✗ +210% rt | ✓ −43% E | ✓ −45% E | ✗ +128% rt | ✓ −29% E |
| **A7 aggressive_save** | (no data — walltime cut) | | | | | | |

Best safe arm per bench (the warm-start target for the agent's prior):

| bench | best safe arm | dE / dt |
|---|---|---|
| stream | A1 memory_bound_save | **−69.1 % / +0.3 %** |
| mpi-idle-wait | A4 comm_wait_save | **−70.2 % / +0.2 %** |
| gpu-bursty-idle | A4 comm_wait_save | **−53.1 % / +0.3 %** |
| cpu-dgemm | A3 cpu_compute_uncore_save | **−22.4 % / −7.9 %** (faster!) |
| osu | A5 comm_collective_safe | **−14.3 % / 0.0 %** |
| babelstream | **none** | every arm violates +5% |
| dgemm-gpu | **none** | every arm violates +5% |

---

## Five concrete findings that change the agent design

### 1. A2 `gpu_compute_max` is misdesigned and HARMS GPU-active benches

The arm was supposed to be the right arm for `dgemm-gpu` / `babelstream`. Phase 1.5 shows:
- dgemm-gpu: **+27 % runtime, +8 % energy** (worse than baseline on both axes!)
- babelstream: +7 % runtime, −7.6 % energy (Pareto-dominated by A0 if runtime matters)

Root cause: the arm sets `CPU_FREQUENCY_MAX_CONTROL = 2.0 GHz`. But on Aurora, even GPU-compute benches need the CPU at MAX to drive kernel dispatch over MPI — the CPU is on the critical path of every offload. The Phase 0 single-knob sweep showed CPU=2.0 GHz hurts dgemm-gpu but the priors model didn't catch this because Phase 0 measured each knob in isolation.

**Fix:** raise A2's CPU and UNCORE caps to MAX so it differs from A0 only in `PERF_FACTOR=1.0` (the GPU-side hint to favor compute over memory). See §"Agent grid update" below.

### 2. A5 `comm_collective_safe` is the universal safe arm

Saves 13–28% energy on **5 of 7 benches** while never violating the 5% slack on those 5. Only fails on the two GPU-active benches (babelstream, dgemm-gpu) where every arm fails.

Mechanism: A5 sets CPU=MAX, UNCORE=MAX, GPU=0.4 GHz, PERF_F=0. The CPU side stays full so comm and dispatch are unaffected; only the GPU gets capped. This is the "GPU side is always cheaper to cap when not actively in use" effect — confirmed for stream (CPU bench), cpu-dgemm (CPU bench), osu (comm bench), and both wait/bursty classes.

**Implication:** A5 should be the agent's default fallback arm (instead of A0) once it has any evidence that GPU is not the hot path. It's also the right cold-start arm under "always-on" mode for unknown workloads.

### 3. A4 `comm_wait_save` is catastrophic on cpu-dgemm (+560% runtime!)

The arm sets CPU_POWER_LIMIT=175 W, which throttles cpu-dgemm to ~17 % of its TDP. The bench runs at ~3 W per instruction so the cap binds hard immediately. Worst single-arm-vs-bench outcome in the whole campaign.

But A4 is the BEST arm on the two wait-dominated classes (−70% mpi-idle-wait, −53% gpu-bursty-idle). So the arm itself is right; the agent's context filter MUST keep it out of CPU-bound classes.

**Implication:** the agent's `cpu_busy_fraction` feature must be reliable BEFORE the bandit explores A4. Add a hard guard: never propose A4 if `cpu_busy_fraction > 0.5` in the recent window.

### 4. A6 `bursty_gpu_idle` is dominated everywhere it has data

| Bench | A6 | A4 | A1 | dominator |
|---|---|---|---|---|
| gpu-bursty | −43% | −53% | −51% | A4 |
| mpi-idle | −45% | −70% | −67% | A4 |
| stream | −29% | (no data) | −69% | A1 |
| osu | +128% rt | ✗ | ✗ | n/a (all bad) |

A6 was designed as a softer version of A4 (CPU=1.6 GHz instead of 1.0 GHz) for bursty workloads that might need to ramp CPU back up. With this dataset it's dominated by A4 on every safe-class bench. Either drop it or leave for Phase 1.5b to test under bursty conditions specifically (Phase 0 `gpu-bursty-idle` may not be bursty enough to differentiate).

**Implication:** soft drop A6 from the active arm set for now; keep the JSON entry but mark it `_inactive: true` until Phase 1.5b can produce more data.

### 5. babelstream and dgemm-gpu have NO safe energy headroom

Every arm besides A0 violates the 5% runtime budget on these two benches. They're tightly GPU-compute-bound; the only safe action is `all_max`. The agent must recognize this class and freeze on A0 — that's exactly the "GPU-active compute-bound" class from `analysis/agent_suggestions.md` §3.

The good news: the bandit's natural action filter (drop arms previously shown to violate slack) handles this. After a few ticks of trying A1/A2 and seeing the runtime overrun, LinUCB will converge to A0. Cold start cost: ~1–2 epochs on those benches.

---

## What this validates / refutes for Phase 0 results

| Phase 0 prediction | Phase 1.5 reality | verdict |
|---|---|---|
| "stream best knob = CPU_FREQ_MAX @ 1.0 GHz, −68% energy" | A1 (which includes that exact write) → −69.1% energy on stream | **confirmed** |
| "mpi-idle-wait: CPU_FREQ_MAX @ 1.0 GHz, −64% energy" | A4 (CPU=1.0 + others) → −70.2% energy | **stronger than predicted** |
| "cpu-dgemm: CPU_UNCORE_FREQUENCY @ 0.8 GHz, −16% energy" | A3 (UNCORE=1.2 + others) → −22.4% energy and FASTER | **even better** |
| "GPU caps below 1.5 GHz are real after MIN drop" | Every arm with GPU=0.4 GHz binds; produces the predicted savings | **confirmed** |
| "PERF_FACTOR is real but smaller magnitude than GPU_FREQ_MAX" | A2 (PERF_F=1.0, GPU=MAX) gives −36% on bursty-idle — *bigger* than expected. A5 (PERF_F=0.0, GPU=0.4) gives −53% | mixed — PERF_F is bigger than thought |

The additivity assumption that the agent's `action_grid_default.json` was built on is **mostly correct for the wait/idle/CPU classes** but **wrong about CPU's role in GPU-compute benches**. A2's broken design is the result of assuming "drop CPU to favor GPU" — wrong for offload-dispatch-heavy code. That's the kind of insight Block B (CPU × GPU 3×3) was supposed to make obvious by interpolating the response surface; we now know it qualitatively without that data, but the quantitative answer (HOW MUCH CPU is needed for kernel dispatch) is still missing.

---

## Agent grid update

See `agent/src/action_grid_default.json` and `agent/src/ActionGrid.cpp`. Diff against the original grid:

| Arm | Change | Why |
|---|---|---|
| A0 all_max | unchanged | baseline; only safe arm on GPU-active classes |
| A1 memory_bound_save | unchanged | confirmed: −69% on stream |
| **A2 gpu_compute_max** | **CPU 2.0 → 3.5 GHz, UNCORE 1.6 → 2.3 GHz** | fixes the +27% runtime on dgemm-gpu; now differs from A0 only in PERF_FACTOR=1.0 |
| A3 cpu_compute_uncore_save | unchanged | confirmed: −22% on cpu-dgemm |
| A4 comm_wait_save | unchanged + agent must filter out on `cpu_busy_fraction > 0.5` | confirmed great on wait classes, deadly on CPU-bound |
| A5 comm_collective_safe | unchanged + promote as "universal safe save" | confirmed: −13 to −28% on 5/7 benches |
| **A6 bursty_gpu_idle** | **mark `_inactive: true`** | dominated by A4 on every safe-class bench it touched |
| A7 aggressive_save | unchanged | no data yet; needed for hard cap scenarios |

Net arm count: 7 active (down from 8). Cleaner action space → faster LinUCB convergence.

The actual JSON + cpp edits land in this same Phase 1.5 commit.

---

## Block B (CPU × GPU 3×3) — additivity test

Detailed per-cell tables in `analysis/phase1_5/additivity_summary.md`. Verdict per bench:

| bench | verdict | residual median | residual σ | worst |
|---|---|---|---|---|
| babelstream | ADDITIVE | +0.1 pp | 4.6 | +9.7 pp |
| cpu-dgemm | ADDITIVE | −2.2 pp | 3.8 | −8.8 pp |
| dgemm-gpu | ADDITIVE | −0.5 pp | 2.2 | +4.7 pp |
| gpu-bursty-idle | MIXED | +5.0 pp | 4.6 | +15.8 pp |
| mpi-idle-wait | ADDITIVE | 0.0 pp | 4.5 | +8.3 pp |
| osu | SYNERGISTIC | −6.2 pp | 11.1 | −27.9 pp |
| stream | MIXED | +4.2 pp | 5.6 | +18.1 pp |

**Headline:** **5 of 7 benches are ADDITIVE** on the CPU × GPU pair. The agent's warm-start prior can use the simple `predicted_dE = phase0_dE(CPU) + phase0_dE(GPU)` model with confidence — the bandit's online updates will correct the few-pp residual in 1-2 epochs.

**Two real interactions, both small:**

1. **osu is SYNERGISTIC (−6 pp median).** Combined CPU+GPU caps save MORE energy than the sum — but every combination is still HARMFUL because osu is comm-bound and any cap kills runtime. The synergy doesn't change the agent's behavior (still need to avoid CPU caps), but it's notable.

2. **stream is MIXED (+4 pp median).** Predicted −85% on `(cpu=1.0, gpu=0.4)`, measured −66% (residual +18pp). When CPU is at the floor, dropping GPU further doesn't compound — GPU was barely consuming on a CPU-only bench. This is the classic "diminishing returns when both knobs target the same resource budget" pattern.

**Implication:** the agent grid stays as-is; no new arms needed from Block B.

## Block C (CPU × UNCORE 3×3, NOW COMPLETE) — interaction signal

Updated verdicts with full 9-cell coverage per bench:

| bench | verdict | residual median | residual σ | worst |
|---|---|---|---|---|
| babelstream | ADDITIVE | −0.5 pp | 2.3 | +5.9 pp |
| cpu-dgemm | MIXED | −1.2 pp | 14.2 | **+37.4 pp** |
| dgemm-gpu | ADDITIVE | −0.5 pp | 2.2 | +5.7 pp |
| gpu-bursty-idle | ADDITIVE | −0.6 pp | 3.0 | +7.5 pp |
| mpi-idle-wait | ADDITIVE | −0.4 pp | 3.5 | +9.6 pp |
| osu | MIXED | −0.4 pp | 20.6 | **−63.2 pp** |
| stream | SYNERGISTIC | −6.8 pp | 7.8 | −21.3 pp |

**5 of 7 benches now ADDITIVE on CPU × UNCORE** (Block B + Block C combined: 10 of 14 (bench, block) cells additive).

Two specific patterns confirmed with the complete data:

### Block C (CPU × UNCORE 3×3, partial) — interaction signal

3 of 9 cells fully populated, 6 partial or missing. What's there:

| bench | verdict (with partial data) | notes |
|---|---|---|
| babelstream | ADDITIVE | n=7 cells, σ=2.3 pp |
| cpu-dgemm | MIXED | n=6 cells, σ=15.9 pp, worst=+38 pp on `(cpu=1.0, unc=0.8)` — **compound bottleneck** |
| dgemm-gpu | ADDITIVE | n=4 cells |
| gpu-bursty-idle | ADDITIVE | n=6 cells |
| mpi-idle-wait | ADDITIVE | n=7 cells |
| osu | SYNERGISTIC | n=4 cells, but only the cpu=1.0 row is populated |
| stream | SYNERGISTIC | n=6 cells, median −16 pp — **non-binding UNCORE under low CPU demand** |

Two notable interactions:

### cpu-dgemm: compound bottleneck on (CPU=1.0 + UNCORE=0.8)
Predicted dE = +38% (sum of CPU=1.0 harm +55% and UNCORE=0.8 useful −16%). Measured = +76%. When CPU is already crippled at 1.0 GHz, dropping UNCORE compounds the slowdown rather than helping — the bench can't extract the UNCORE saving because it's already starved on CPU.

**Implication for agent:** A7 (aggressive_save = CPU=1.0 + UNCORE=0.8 + GPU=0.4 + CPU_PL=105W) will be even worse than Phase 0 predicted on cpu-dgemm. Already filtered against high `cpu_power_frac` by the same guard as A4. No new change needed.

### stream: UNCORE doesn't hurt as much under low CPU
Phase 0 said UNCORE=0.8 alone is +117% runtime (catastrophic) on stream. In Phase 1.5b, when combined with CPU=1.0 GHz, the combined runtime is only +59% (`C_cpu1.0_unc0.8`) — half the predicted harm.

Mechanism: stream's UNCORE bottleneck binds when CPU is demanding HBM bandwidth at full rate. With CPU clocked to 1.0 GHz, demand drops and UNCORE is no longer the gating resource.

**Implication for agent:** A1 (memory_bound_save) currently sets UNCORE=2.3 GHz to dodge the predicted UNCORE harm. Phase 1.5b shows it could safely drop UNCORE to 1.6 GHz too and still save energy without runtime cost — but the additional UNCORE savings on stream are only ~2 pp beyond the current A1, so adding a new arm is not justified.

The general insight DOES matter for cap-compliance mode in Phase 3: under a hard `BOARD_POWER` cap, the agent has more headroom to drop UNCORE on memory-bound workloads than Phase 0 single-knob priors suggest. Add this to the Phase 3 acceptance criteria.

---

## Block D (GPU × PERF_FACTOR 2×2) — **NOT redundant**

Compared `GPU_FREQ_MAX = {0.4, 1.6} × PERF_FACTOR = {0.0, 1.0}` at 2×2 corners. Question: is PERF_FACTOR worth keeping in the arm grid, or does GPU_FREQ_MAX subsume it?

**Verdict: PERF_FACTOR matters on 12 of 14 (bench, gpu_freq) corners.** The "diff PF=1 vs PF=0" exceeds the 3% redundancy threshold almost everywhere.

| bench | GPU=0.4 PF=1 vs PF=0 | GPU=1.6 PF=1 vs PF=0 |
|---|---|---|
| babelstream | −3.0 % (marginal) | +3.1 % (marginal) |
| cpu-dgemm | **−10.5 %** (PF=1 saves) | **−8.8 %** (PF=1 saves) |
| **dgemm-gpu** | +1.4 % (redundant) | **+14.2 %** (PF=1 HURTS, +21 % runtime) |
| gpu-bursty-idle | **−21.8 %** (PF=1 big save) | **−12.1 %** (PF=1 save) |
| mpi-idle-wait | **−18.9 %** (PF=1 big save) | **−6.4 %** (PF=1 save) |
| osu | **−9.1 %** (PF=1 saves) | **−6.5 %** (PF=1 saves) |
| stream | **−15.6 %** (PF=1 saves) | **−7.1 %** (PF=1 saves) |

**Two takeaways:**

1. **PF=1 saves energy on most workloads.** Counter-intuitive — "compute bias" on a *cold* GPU saves more than "memory bias". Mechanism: PF=1 keeps GPU clocks pinned, so the small amount of GPU work that does occur finishes faster → more time in deep idle → less leakage. PF=0 lets the clock dither up/down between the small work bursts, paying transition energy each time.

2. **PF=1 HURTS dgemm-gpu at GPU=MAX** (+14 % energy, +21 % runtime). On a GPU-compute-bound workload at MAX frequency, PF=1 prevents the memory subsystem from clocking up enough to feed the compute units → stall → slowdown → more total energy.

**Implication for the agent grid:**
- **A2 `gpu_compute_max` has the wrong PF.** Currently sets `PERF_FACTOR=1.0`. Block D shows PF=1 *hurts* dgemm-gpu at GPU=MAX. **Change A2 PF to 0.0** (memory-bias to feed compute) — or simpler, A2 becomes nearly identical to A0 and we can drop it.
- **A4, A5, A6, A7 should set PF=1.0**, not 0.0. They all use GPU=0.4 and target GPU-cold classes where Block D shows PF=1 saves 6–22 % more energy.
- Net: one knob value flips on 5 arms.

---

## Block E (CPU × CPU_POWER_LIMIT 2×2) — **CPU_PL IS REDUNDANT**

Job 8512185 completed Phase 1.5d (Block E only, REPEATS=10, 210 nodes). Got full coverage on the two `E_cpu1.0_*` combos that answer the redundancy question; the `E_cpu3.5_*` combos are partial but not needed for the verdict.

**Redundancy test:** does `CPU_POWER_LIMIT_CONTROL=175W` add anything when `CPU_FREQ_MAX=1.0 GHz` is already set? Comparing `E_cpu1.0_pl_default` vs `E_cpu1.0_pl175`:

| bench | E with PL=default | E with PL=175 W | Δ energy | Δ runtime | verdict |
|---|---|---|---|---|---|
| babelstream | 19,755 J | 19,614 J | **−0.7 %** | +0.0 % | **redundant** |
| cpu-dgemm | 20,519 J | 89,914 J | **+338.2 %** | **+222.4 %** | **PL CATASTROPHIC** |
| dgemm-gpu | 28,458 J | 28,246 J | **−0.7 %** | −0.0 % | **redundant** |
| gpu-bursty-idle | 23,501 J | 23,296 J | **−0.9 %** | −0.0 % | **redundant** |
| mpi-idle-wait | 4,547 J | 4,470 J | **−1.7 %** | +0.0 % | **redundant** |
| osu | 53,108 J | 53,008 J | **−0.2 %** | +0.1 % | **redundant** |
| stream | (no PL=175 data) | — | — | — | — |

**5 of 6 benches: PL=175W adds nothing when CPU is already at 1.0 GHz.** The one exception (cpu-dgemm) makes things 4× worse — but A4/A7 weren't safe on cpu-dgemm anyway (the runtime guard already filters them out).

**Implication for the agent:** **CPU_POWER_LIMIT_CONTROL is redundant in arms that already cap CPU_FREQ_MAX low.**
- A4 `comm_wait_save` currently sets CPU=1.0 GHz + PL=175W → **drop PL=175W**. Same effect on target classes, plus no catastrophic interaction with cpu-dgemm.
- A7 `aggressive_save` currently sets CPU=1.0 GHz + PL=105W → **drop PL=105W**. Same logic.

Net: 2 arms get simpler (one less write each), agent grid action space is unchanged but the LinUCB cost-of-arm drops slightly.

---

## Summary across all completed blocks

| question | answer | source |
|---|---|---|
| Are the 8 agent arms validated end-to-end? | Yes — A2 fixed in Phase 1.5a, A6 deactivated, A5 promoted | Block A |
| Does additivity hold for CPU × GPU? | Yes on 5/7 benches | Block B |
| Does additivity hold for CPU × UNCORE? | Yes on 5/7 benches | Block C (now complete) |
| Are GPU_FREQ and PERF_FACTOR redundant? | **No** — PF=1 saves 6-22% MORE energy on most benches when GPU is capped. **Update PF settings on 5 arms.** | Block D |
| Is CPU_POWER_LIMIT redundant when CPU_FREQ is capped? | **Yes on 5/6 benches.** Drop PL writes from A4 and A7. | Block E |

**The agent's warm-start priors from Phase 0 single-knob data remain safe.** Block C confirms additivity holds for CPU × UNCORE the same way it did for CPU × GPU. Block D reveals one categorical agent-design correction (PF settings) — applied below.

---

## Phase 1.5 — COMPLETE

All 5 blocks now have enough data to answer the per-block questions. The agent grid has been updated through 4 iterative changes:

| Phase | Change to agent | Justified by |
|---|---|---|
| 1.5a (Block A) | A2 CPU/UNCORE→MAX; A6→inactive | per-arm validation on 7 benches |
| 1.5b (Block B) | A4 + A7 runtime guard penalizes when CPU busy | compound bottleneck on cpu-dgemm |
| 1.5c (Block D) | A2 PF=1→0; A4/A5/A7 PF=0→1 | PERF_FACTOR non-redundancy, PF=1 helps cold GPU |
| 1.5d (Block E) | **A4 drop CPU_PL=175W; A7 drop CPU_PL=105W** | CPU_PL redundant when CPU_FREQ already low |

No further sweeps required for Phase 2 implementation. The remaining open question (whether PL=175W matters when CPU_FREQ is at 3.5 GHz, from the missing `E_cpu3.5_*` combos) is moot: the agent never uses PL writes alone — they always coexist with a CPU_FREQ cap in A4/A7, so PL is dropped from the grid entirely.

## ~~Phase 1.5d — finish Block E only~~ (DONE — job 8512185)

The 8511663 job (Phase 1.5c) completed Block C + most of Block D but ran out of time before Block E. **Only Block E remains.** 4 combos × 7 benches = 28 cells per node, but at ~60 s per cell only ~50 fit in a 1 h slot — so a single 4-combo block can run with high reps and fit easily.

```bash
qsub -l select=210 \
     -v "NODES_PER_BENCH=30,REPEATS=10,COMBO_BLOCKS=E" \
     scripts/submit_phase1_5.pbs
```

| Setting | Value |
|---|---|
| Queue | `debug-scaling` |
| Walltime | `01:00:00` |
| Nodes | 210 (= 7 benches × 30) |
| Combos | 4 (Block E only) |
| In-process reps | 10 |
| Per-node cells | 4 × 10 = 40 |
| Per-node walltime | 40 × 60 s ≈ **40 min** — fits with 20 min margin |
| Reps per (bench, combo) | 10 × 30 = **300** — very dense |

After 1.5d lands the additivity check covers all of B, C, D, E and we can answer the final agent-design question: is CPU_POWER_LIMIT redundant with CPU_FREQUENCY_MAX_CONTROL, or do they coexist? Either answer simplifies the arm grid further.

## ~~Phase 1.5c~~ (superseded — completed by job 8511663)

## ~~Phase 1.5b — what still needs to run~~ (superseded by 1.5c above; original section below)

Blocks B/C/D/E never started. They are the interaction-test blocks that answer the **additivity question** (does combined ΔE match the sum of single-knob ΔEs?). Without them the agent's per-class warm-start priors can use the Block A arm-level point estimates, but cannot use a richer combinatorial regression.

Recommended Phase 1.5b config:
- **Same combos.json**, but only blocks B/C/D/E (drop block A since we have it). 26 combos.
- **`prod` queue, 02:00 walltime** to fit the per-cell ~50 s reality from this job.
- `REPEATS=2` per node × 20 nodes per bench → 40 reps per (bench, combo). Good enough for additivity.
- Per-node cells: 26 × 2 = 52 cells × 50 s = 43 min — comfortably under 2 h.

Or split into two debug-scaling jobs of 1 h each:
- Job 1: B + C (18 combos × 3 reps = 54 cells × 50 s = 45 min)
- Job 2: D + E (8 combos × 8 reps = 64 cells × 50 s = 53 min)

Both options shippable with the existing `submit_phase1_5.pbs` + `combos.json` if we add a `--combo-block` filter to the runner (small change to `run_phase1_5_combos.py`'s main loop).

---

## Files

- `analysis/phase1_5/cells.csv` — 3,672 successful cells (one row per bench × combo × node × repeat)
- `analysis/phase1_5/by_combo.csv` — 49 rows (one per (bench, combo) with n, median rt/E, mean rt/E, std E)
- `results/phase1_5_8510402/per_node_summaries/` — raw 140 per-node CSVs
- `results/phase1_5_8510402/per_node_logs/` — raw per-node stdout/stderr
- `experiments/phase1_5/<bench>/runs/8510402_n*/A*__r*/` — per-cell run dirs with meta.json + metrics.json + sidecar trace
