# Phase 1.5b — fill in the missing interaction blocks

Phase 1.5 (PBS job 8510402) hit walltime after completing only Block A (agent arm validation). Per-cell time turned out to be ~50 s, not the ~20 s estimated in `docs/phase1_5-combo-design.md`, so a 1-h `debug-scaling` slot held only ~28 cells per node out of 136 planned.

Phase 1.5b runs **only Blocks B / C / D / E** (26 combos) with the corrected walltime estimate. See `analysis/phase1_5/results.md` for what we already have and what's still missing.

---

## What gets tested (26 combos × 7 benches)

| Block | Cells | Question |
|---|---|---|
| **B** CPU × GPU 3×3 | 9 | Does combined ΔE = ΔE(CPU) + ΔE(GPU)? Most universal interaction. |
| **C** CPU × UNCORE 3×3 | 9 | Validates stream's `memory_bound_save` and cpu-dgemm's `cpu_compute_uncore_save` arm designs. |
| **D** GPU × PERF_FACTOR 2×2 | 4 | Redundancy: does PERF_FACTOR add anything when GPU is already capped? |
| **E** CPU × CPU_PL 2×2 | 4 | Redundancy: does CPU_POWER_LIMIT add anything when CPU_FREQ_MAX is already capped? |

Block A is **not re-run** — we have 80 reps per (bench, arm) from 8510402 already.

---

## Execution plan — single 210-node debug-scaling job

`prod` is not available. The chosen plan fits a single 1-h `debug-scaling` slot.

```bash
qsub -l select=210 \
     -v "NODES_PER_BENCH=30,REPEATS=2,COMBO_BLOCKS=B:C:D:E" \
     scripts/submit_phase1_5.pbs
```

**Note** the COMBO_BLOCKS uses `:` not `,` as separator. PBS `-v` parses commas as variable boundaries, so `COMBO_BLOCKS=B,C,D,E` would silently break ("C=" undefined). The runner accepts both `:` and `,`.

| Setting | Value |
|---|---|
| Queue | `debug-scaling` |
| Walltime | `01:00:00` (PBS-script default) |
| Nodes | **210** (= 7 benches × 30 nodes/bench) |
| Combos | 26 (Blocks B + C + D + E; Block A already done in 8510402) |
| In-process reps | 2 |
| Per-node cells | 26 × 2 = 52 |
| Per-node walltime | 52 × 50 s ≈ **43 min** — fits 1 h with 17 min margin |
| Reps per (bench, combo) | 2 (in-process) × 30 (nodes) = **60** (matches Phase 0 density) |
| Total cells | 7 × 52 × 30 = 10,920 |

---

## Required runner change

`scripts/run_phase1_5_combos.py` needs to honor `--combo-blocks "B,C,D,E"` so we can skip Block A. One-line addition to the combo-iteration loop:

```python
# After loading combos_doc:
if args.combo_blocks:
    wanted = {b.strip() for b in args.combo_blocks.split(",")}
    combos_doc["combos"] = [c for c in combos_doc["combos"]
                            if c.get("_block","").split("_")[0] in wanted]
```

Add `--combo-blocks` to `argparse` and `submit_phase1_5.pbs` (forward via `-v COMBO_BLOCKS=...` → environment → the `SWEEP=(...)` array).

Both changes are in this commit.

---

## Analysis after results land

Existing aggregation scripts work as-is:

```bash
bash analysis/scripts/summarize_phase0_knobs.sh experiments/phase1_5/*/runs/
# Or use the same loop from this campaign's results.md:
/usr/bin/python3.10 <<'PYEOF'
# (paste the by-bench delta-energy script from analysis/phase1_5/results.md)
PYEOF
```

NEW script needed: `analysis/scripts/additivity_check.py` — computes:
- For each (bench, combo) in Block B: `measured_dE` vs `phase0_dE(CPU) + phase0_dE(GPU)`. Histogram the residual. If centered at 0 with σ < 5% → additivity holds; agent priors are fine as-is.
- For each (bench, combo) in Block D: `D_gpu0.4_pf0` vs `D_gpu0.4_pf1`. If |diff| < 3% → PERF_FACTOR is redundant when GPU is capped; drop it from arms with GPU_FREQ < 1.0 GHz.
- For each (bench, combo) in Block E: same redundancy test for CPU_POWER_LIMIT.

Decision feeds back into `agent/src/action_grid_default.json` for the next iteration.

---

## What changes in the agent based on Phase 1.5b outcomes

| Outcome on Block B (CPU × GPU) | Agent action |
|---|---|
| additivity holds | keep current arm grid; warm-start priors are safe as sum of Phase 0 single-knob effects |
| significant negative interaction (combined less than sum) | shrink arm grid: drop low-CPU+low-GPU corners; bandit can still find them via interpolation |
| significant positive interaction (combined more than sum) | add Pareto-dominant corners as new arms; expand grid |

| Outcome on Block D (GPU × PERF_F) | Agent action |
|---|---|
| PERF_F redundant when GPU capped | drop PERF_FACTOR from A1/A4/A5/A6/A7 (kept only in A2 where GPU=MAX) |
| PERF_F adds 3-10% energy beyond GPU cap | keep current per-arm PERF_F settings |
| PERF_F dominant lever (>GPU cap) | replace GPU_FREQ_MAX with PERF_FACTOR in arm controls |

| Outcome on Block E (CPU × CPU_PL) | Agent action |
|---|---|
| CPU_PL redundant when CPU_FREQ_MAX capped | drop CPU_POWER_LIMIT from A4/A7 |
| CPU_PL adds 3-10% energy beyond CPU_FREQ cap | keep current settings |
| CPU_PL dominant lever | restructure A4 as a CPU_PL-only arm |

---

## What happened with the timing estimate

The original `docs/phase1_5-combo-design.md` predicted ~20 s per cell. Reality from 8510402 was ~50 s. Breakdown of the extra time:

- Bench runtime (`all_tiles_15s`): 15 s — as expected
- Combo writes (3 floors + 4-7 arm writes × ~50 instances avg): ~10 s — under-estimated
- Restore writes (same shape): ~10 s — under-estimated
- Sidecar boot + sample + teardown: ~5 s
- Per-cell mkdir, meta.json write, trace parse: ~5 s
- Synchronous geopmread before each write: ~5 s

Aurora's `geopmwrite` fork overhead is the dominant cost (each `geopmwrite` is its own subprocess; we issue ~150 of them per cell). The Phase 0 sweep used the same runner but issued fewer writes per cell (1 knob = ~100 instance writes; combos issue 4-7 × 100 = 400-700 writes).

**Mitigation for Phase 1.5b**: nothing required — the 50 s per cell is real and we just budget for it.

**Phase 2 implication**: the C++ agent uses GEOPM's batch IO (`m_platform_io.adjust` + `write_batch`) which is one fork per tick, not one per knob × instance. The agent will not hit this overhead. Phase 1.5b confirms the python runner is the bottleneck, not the hardware writes themselves.

---

## Submit

```bash
cd /home/nic_br/GEOPM_Argonne_start/newGEOPM
qsub -l select=210 \
     -v "NODES_PER_BENCH=30,REPEATS=2,COMBO_BLOCKS=B:C:D:E" \
     scripts/submit_phase1_5.pbs
```

When results land, run the same aggregation snippet from `analysis/phase1_5/results.md` against `results/phase1_5_<NEW_JOBID>/per_node_summaries/` and append to `analysis/phase1_5/cells.csv` / `by_combo.csv`. The additivity check script (`analysis/scripts/additivity_check.py`) is the new analysis deliverable after this run.
