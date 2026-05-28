# Phase 1.5 — knob combination sweep

Phase 0 measured each Tier-1 knob in isolation (one knob varied per cell; all others at default). The unified agent (`AuroraBanditAgent`) picks **arm tuples** that set multiple knobs at once. Two questions Phase 0 cannot answer:

1. **Are the savings additive?** Phase 0 says `CPU_FREQUENCY_MAX=1.0 GHz` saves −68 % energy on stream, `GPU_CORE_FREQUENCY_MAX=0.4 GHz` saves −14.6 %. If both knobs at once save −80 % we're additive. If they save only −70 % the agent's warm-start priors are wrong about that arm.
2. **Is the agent's default arm grid Pareto-optimal?** The 8 default arms in `agent/src/action_grid_default.json` were designed from single-knob priors. Some combinations might dominate them; some arms might be dominated by other combinations and should be dropped from the grid.

Phase 1.5 answers both by running a small, focused combination sweep before Phase 2 implementation work begins.

---

## What gets tested (34 combos × 7 benches × 4 reps × 20 nodes ≈ 19 k cells)

Five blocks, each answering a specific question. Block A validates the agent's arm grid as-is; blocks B–E test pair interactions for the four most-likely-to-matter knob pairs from Phase 0.

### Block A — agent arm validation (8 combos / bench)

Run each of the 8 arms hardcoded in `ActionGrid::load_default()` exactly as the agent will issue them. Confirms the predicted energy/runtime per arm per bench, and produces the baseline Pareto curve the bandit will be initialized against.

| Arm | Knob settings |
|---|---|
| `all_max` | (no writes — all knobs at hardware MAX) |
| `memory_bound_save` | CPU=1.0 GHz, UNCORE=2.3 GHz, GPU=0.4 GHz, PERF_F=0.0 |
| `gpu_compute_max` | CPU=2.0 GHz, UNCORE=1.6 GHz, GPU=1.6 GHz, PERF_F=1.0 |
| `cpu_compute_uncore_save` | CPU=3.5 GHz, UNCORE=1.2 GHz, GPU=0.4 GHz, PERF_F=0.25 |
| `comm_wait_save` | CPU=1.0 GHz, UNCORE=0.8 GHz, GPU=0.4 GHz, PERF_F=0.0, CPU_PL=175 W |
| `comm_collective_safe` | CPU=3.5 GHz, UNCORE=2.3 GHz, GPU=0.4 GHz, PERF_F=0.0 |
| `bursty_gpu_idle` | CPU=1.6 GHz, UNCORE=1.6 GHz, GPU=0.4 GHz, PERF_F=0.0 |
| `aggressive_save` | CPU=1.0 GHz, UNCORE=0.8 GHz, GPU=0.4 GHz, PERF_F=0.0, CPU_PL=105 W |

### Block B — CPU × GPU interaction grid (9 combos / bench)

`CPU_FREQUENCY_MAX_CONTROL ∈ {1.0, 2.0, 3.5} GHz × GPU_CORE_FREQUENCY_MAX_CONTROL ∈ {0.4, 1.0, 1.6} GHz` — full 3×3 grid. The most universally informative interaction: every workload class has a CPU-vs-GPU tradeoff. Answers: is the predicted combined energy saving (Phase 0 single-knob sum) actually achieved when both knobs are pulled at once?

### Block C — CPU × UNCORE interaction grid (9 combos / bench)

`CPU_FREQUENCY_MAX_CONTROL ∈ {1.0, 2.0, 3.5} GHz × CPU_UNCORE_FREQUENCY_MAX_CONTROL ∈ {0.8, 1.6, 2.3} GHz` — full 3×3 grid. The second most informative pair. Phase 0 showed:
- **stream** has CPU_FREQ_MAX USEFUL (−68 % energy) but CPU_UNCORE_MAX HARMFUL (+57 % runtime). The agent's `memory_bound_save` arm sets CPU=1.0 GHz AND UNCORE=2.3 GHz to dodge the uncore harm — does that combination actually deliver the energy savings without the runtime hit, or does the low CPU still drag uncore demand down?
- **cpu-dgemm** has the reverse: CPU_FREQ HARMFUL (+102 %), CPU_UNCORE USEFUL (−16 %). The agent's `cpu_compute_uncore_save` arm sets CPU=MAX, UNCORE=1.2 GHz. Does it work?

This grid validates both arm designs in one pass.

### Block D — GPU × PERF_FACTOR redundancy check (4 combos / bench)

`GPU_CORE_FREQUENCY_MAX_CONTROL ∈ {0.4, 1.6} GHz × LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL ∈ {0.0, 1.0}` — 2×2 corners. Both are GPU energy levers; Phase 0 showed they have similar response shape at different magnitudes. Question: when GPU_FREQ_MAX is already low, does PERF_FACTOR still do anything? If `D_gpu0.4_pf0` ≈ `D_gpu0.4_pf1` then PERF_FACTOR is redundant when the freq is capped — and the agent can drop the PERF_FACTOR axis from arms that already set a low GPU cap.

### Block E — CPU × CPU_POWER_LIMIT redundancy check (4 combos / bench)

`CPU_FREQUENCY_MAX_CONTROL ∈ {1.0, 3.5} GHz × CPU_POWER_LIMIT_CONTROL ∈ {default, 175 W}` — 2×2 corners. Same redundancy question for the CPU side. Phase 0 showed both knobs are USEFUL_LINEAR on the same benches with similar dE; if they overlap, the agent should pick one not both.

### Excluded from this phase
- 3-way interactions (would need 3³ = 27 cells per triple, blowing the cell budget). Schedule Phase 1.6 if any pair fails additivity.
- DRAM_POWER, BOARD_TIME_WINDOW, CPU_POWER_TIME_WINDOW — Phase 0 said NEGLIGIBLE on 6/7 benches.
- BOARD_POWER cap-compliance split: belongs in Phase 3 (`docs/phase3-cap-design.md`).
- Per-bench combo sets: same 34 combos run on every bench, even when Phase 0 said a combo will be catastrophic. Confirming catastrophic combos remain catastrophic is part of validating the agent's HARMFUL filter.

---

## Output

Same per-cell shape as Phase 0:
```
experiments/phase1_5/<bench>/runs/<JOBID>_n<rank>/<combo_label>__r<repeat>/
  ├── meta.json          # combo definition + apply log
  ├── metrics.json       # runtime, energy, board power
  ├── stdout.log
  ├── geopmsession_trace.csv-<host>
  └── geopmsession_report.yaml
```

Aggregate analysis script (`analysis/scripts/summarize_combo_results.py`, written after results land) produces:

1. **Per-bench Pareto plot**: each combo as a (runtime, energy) point. Highlight the 8 agent arms; flag any combo that dominates an agent arm.
2. **Additivity check**: compute `predicted_dE(combo) = Σ_knob phase0_dE(knob, level)` and `measured_dE(combo)`. Histogram `measured − predicted` per bench. If centered at 0 with small spread → additivity holds. If skewed → interactions matter and the agent priors need to use combo data.
3. **Updated arm-grid recommendation**: list of dominated arms to drop and any newly-Pareto combos to add.

---

## Cost / schedule

- Cells per bench per node: 34 combos × 4 reps = 136 cells
- Per-cell wall: bench runtime (~15 s for `all_tiles_15s`) + combo write/restore + sidecar boot/teardown ≈ 20 s
- Per-node walltime: 136 × 20 s ≈ 45 min — fits 1 h `debug-scaling` slot with 15 min margin
- Per (bench, combo) reps: 4 (in-process) × 20 (nodes per bench) = **80 reps**, more than Phase 0's 60
- Total cells per PBS job: 34 × 4 × 20 × 7 = 19,040
- Single submission produces enough samples for tight per-combo IQR

Knobs to dial up/down:
- `qsub -v REPEATS=2 …` → ~25 min/node, 40 reps/(bench, combo). Use for first-pass exploration.
- `qsub -v REPEATS=6 …` → ~70 min/node, 120 reps/(bench, combo). Need to bump walltime past 1 h (move to `prod` queue, walltime 02:00).
- `qsub -v BENCH_LIST=stream,gpu-bursty-idle …` → restrict to specific benches, scales NODES_PER_BENCH up automatically.

---

## How to run

```bash
# Submit (default settings: 140 nodes, 1 h walltime, all_tiles_15s variant)
qsub scripts/submit_phase1_5.pbs

# Submit with overrides
qsub -v REPEATS=5,VARIANT=all_tiles_15s scripts/submit_phase1_5.pbs

# Sequential repeats (3 jobs × the above for more statistics)
REPEATS=5 ./scripts/submit_phase1_5_repeat.sh   # if needed; v1 ships only the single-shot
```

Aggregate after results land:
```bash
bash analysis/scripts/summarize_phase1_5.sh experiments/phase1_5/*/runs/
/usr/bin/python3.10 analysis/scripts/pareto_combo.py
```

---

## Decision gate after Phase 1.5

Two possible outcomes:

### Outcome A: additivity holds (`|measured − predicted| < 5 %` on >80 % of combos per bench)

- The agent's default arm grid is validated. Proceed to Phase 2 implementation with the current `action_grid_default.json`.
- Warm-start priors for LinUCB can be derived from Phase 0 single-knob data via the simple sum-of-effects model — no need for a more sophisticated factorial model.

### Outcome B: significant interactions exist

- Generate updated priors directly from combo cells (one `(A_a, b_a)` per arm using only that arm's observed `(x, r)` pairs).
- Possibly expand arm grid based on Pareto plot — add dominating combos found in Block B.
- Possibly schedule Phase 1.6: 3-way interactions for the surprising pairs only.

Either way, the result feeds directly into `analysis/scripts/generate_phase2_priors.py` (Phase 2 work, not yet written) which produces the JSON consumed by `LinUCB::warm_start_from_json()`.

---

## Why not test all combinations?

Full factorial over the 5 useful knobs at 3 levels each = 3⁵ = 243 combos per bench × 7 benches × 10 reps × 20 nodes = ~340 k cells. About 35 h on debug-scaling. Not worth it before we know whether additivity holds.

The 17-combo design tests **just enough** to answer the additivity question. If it fails, the next phase is targeted (focus on the failing pair); if it succeeds, we can build the agent and validate end-to-end in Phase 2/3 instead of doing more sweeps.
