# Phase 3 — Power-cap evaluation (3000 W headline scenario)

Goal: under a **user-chosen per-node cap** (3000 W is our headline scenario; the framework runs at any value), measure how much of the uncapped time-to-solution our unified agent recovers vs the stock `power_governor` baseline, how much energy it saves when no cap is binding, and what those savings imply economically at Aurora scale.

**Two user-tunable knobs** (set per run, not hard-coded):
- `power_cap_watts` — `BOARD_POWER_LIMIT_CONTROL` value in W. Headline = 3000 W (~60-65 % of Aurora's ~4.5-5 kW peak: 2× Xeon Max ≈ 700 W + 6× PVC ≈ 3600 W + DRAM/network/misc).
- `runtime_slack` — max tolerated slowdown ε ∈ [0, ∞). Headline = 0.05 (5 %). Lower = "energy savings only when free"; higher = "energy-first, accept perf loss".

For the headline, run cross-product over a small grid of (cap, slack); plots in `analysis/phase3-report.md` are faceted by both. See "Cap & slack sweep" below.

## Why 3000 W (headline)

Picks the regime where:
- Hardware autonomy alone (RAPL + `BOARD_POWER_LIMIT_CONTROL`) starts to leave wins on the table — at default caps, hardware just runs full speed and there's no opportunity for the software policy.
- Deep enough that knob choices matter, but not so deep that everything throttles uniformly (~1500 W per node would likely flatten all approaches).

Per-class headroom calibration in `analysis/phase3-report.md` includes whether 3000 W is in the interesting regime for each benchmark, or if it's already pinning at floor frequencies.

## Cap & slack sweep (parameterized headline experiment)

Headline reports one cell (cap=3000 W, slack=5 %), but the full sweep should cover at least:

| Dim | Values | Rationale |
|-----|--------|-----------|
| `power_cap_watts` | {`default`, 4500, 3000, 2250} W | uncapped, mild, headline, deep |
| `runtime_slack` | {0.00, 0.05, 0.20} | strict, headline, energy-first |

Total = 4 × 3 = 12 cap-slack cells per benchmark; multiply by 3 conditions × 3 repeats. Cut the grid down per benchmark if walltime is tight — the headline cell `(3000, 0.05)` is the must-have; the rest help characterize the Pareto frontier across operating points.

The 2250 W deep-cap row is provisional — keep it only if Phase 1 establishes that the agent has interesting headroom that far down (otherwise all conditions collapse to "everything throttled").

## Cap mechanism (revised after Aurora signal/control dump)

There is no writable GPU power cap on Aurora (see `docs/geopm-aurora.md` "headline result"). The 3000 W cap is enforced as follows:

1. **`BOARD_POWER_LIMIT_CONTROL = 3000 W`** — set at job launch (likely requires GEOPM systemd service; verify via Q open-questions Q11). This is the hard ceiling — hardware throttles whatever component is over its share to keep total ≤ 3000 W.
2. The agent (or `power_governor` baseline) operates *within* that ceiling by writing per-component caps (`CPU_POWER_LIMIT_CONTROL`, `DRAM_POWER_LIMIT_CONTROL`) and per-tile GPU freq caps (`GPU_CORE_FREQUENCY_MAX_CONTROL`). These bias **how** the 3000 W gets split among CPU vs DRAM vs GPU, without raising the board total.
3. Neither the agent nor any baseline writes to `BOARD_POWER_LIMIT_CONTROL` mid-run — that's a policy setting, not an action.

## Four conditions per benchmark (per cap-slack cell)

The fourth condition (`uncapped_bandit`) validates the **always-on energy saving** regime — agent harvests free energy savings even without a binding cap.

| # | Label | Board cap | Below-board policy |
|---|-------|-----------|---------------------|
| 1 | `uncapped` | Default (~4500-5000 W; verify Q12) | None. Hardware autonomy only. Reference for TTS / energy. |
| 2 | `uncapped_bandit` | Default (no binding cap) | Our `aurora_bandit` running with `policy.runtime_slack` from the cell. **Validates always-on energy saving**: does the agent save energy even when the cap isn't binding? Compared against condition 1 for energy reduction at matched TTS-within-slack. |
| 3 | `cap_governor` | `${power_cap_watts}` via `BOARD_POWER_LIMIT_CONTROL` | `power_governor` agent: sets `CPU_POWER_LIMIT` to a fraction of TDP, splits evenly across sockets. No DRAM cap, no GPU freq cap — relies on hardware autonomy + board-level enforcement for GPU. **Cap-compliance baseline-of-record.** |
| 4 | `cap_bandit` | `${power_cap_watts}` via `BOARD_POWER_LIMIT_CONTROL` | Our `aurora_bandit` agent: writes `CPU_POWER_LIMIT_CONTROL`, `DRAM_POWER_LIMIT_CONTROL`, `CPU_FREQUENCY_MAX_CONTROL`, `CPU_UNCORE_FREQUENCY_MAX_CONTROL`, `GPU_CORE_FREQUENCY_MAX_CONTROL` per arm. Operates within `${power_cap_watts}` and respects `runtime_slack` as the action-filter constraint. |

Note: condition 2 doesn't need to be run for every (cap, slack) cell — only for each `slack` value (cap is irrelevant when not binding). Cuts the matrix.

Optional fourth: `cap_uncapped_baseline` — set `BOARD_POWER_LIMIT_CONTROL` to its default (effectively non-binding) but run `power_governor` and `aurora_bandit` anyway, to sanity-check that running with the cap-write path active isn't itself perturbing measurements.

### Per-component starting biases (initial conditions for `cap_bandit`)

Since the agent learns online, give it a sensible starting arm per workload class. Provisional initial-arm splits (Phase 1 Pareto will refine):

- **Static fair start**: `cpu_pl1 = 250 W` per package, `dram_pl1 = 75 W` per package, GPU freq at default (lets BOARD cap throttle GPU as needed). Net of CPU+DRAM caps: ~2350 W stays available to the GPUs collectively.
- **GPU-heavy start** (for GPU-bound workloads): `cpu_pl1 = 175 W` per package, `dram_pl1 = 50 W` per package, GPU freq at default. Net ~2600 W to GPUs.

Both biases are just initial arms — the bandit refines them based on observed reward. Report results under both biases so the comparison vs `power_governor` is apples-to-apples (`power_governor` is implicitly a static fair split).

## Benchmarks

Phase 3 should not simply rerun every Phase 1 base benchmark. Phase 1 ranks knobs on simple workloads; Phase 3 proves whether the custom agent works on held-out validation workloads and selected anchors.

| Benchmark | Phase 3 role |
|-----------|--------------|
| `stream` and/or `babelstream` | retain one memory anchor if Phase 1 predicts the biggest energy savings there |
| `dgemm-gpu` and/or `hpl-cpu` | compute anchors for headline cap response; use HPL only after `cpu-dgemm` has characterized CPU knobs |
| `mixbench` | optional GPU arithmetic-intensity validation after pure GPU compute/memory behavior is understood |
| OSU `osu_allreduce` / `osu_alltoall` | communication anchor for cap and slack response |
| `hpcg` | mixed proxy validation; tests whether the agent can combine memory and communication policies |
| `quicksilver` | communication-imbalance validation; expected to be relevant against `power_balancer` |
| **GROMACS (SYCL)** | first production MD app. Local: `benchmarks/gromacs/`. Inputs: `gmxbench-3.0/d.dppc` (1-node), `d.poly-ch2` (multi-node). |
| **LAMMPS (Kokkos/SYCL)** | second production MD app after GROMACS. Local: `benchmarks/lammps/`. Inputs: `bench/in.rhodo` (1-node), `bench/in.lj` (multi-node). |

Node counts should be chosen per validation workload, not copied blindly from Phase 1.

## Metrics

Per (benchmark, condition, repeat):

| Metric | Definition |
|--------|------------|
| TTS | wall time to completion (s) |
| Energy | Σ component energy over run (J) |
| EDP | Energy × TTS (J·s) |
| TTS recovery | `(TTS_cap_bandit − TTS_uncapped) / (TTS_cap_governor − TTS_uncapped)`; lower is better (1.0 = matches governor, <1 = better, 0 = full recovery). **Cap-compliance metric.** |
| Free-savings ratio | `(E_uncapped − E_uncapped_bandit) / E_uncapped`; higher is better. **Always-on energy-saving metric** — how much energy the bandit saves with no cap binding. Validates condition 2 vs 1. |
| TTS overhead (uncapped) | `(TTS_uncapped_bandit − TTS_uncapped) / TTS_uncapped`; must be ≤ `policy.runtime_slack`. Sanity check: if free-savings ratio is high but TTS overhead exceeds slack, the constraint is being violated and λ tuning is wrong. |
| Throttle time | Σ time `GPU_CORE_THROTTLE_REASONS` non-zero across tiles |
| Cap-utilization | mean(node_power) / 3000 W — wasted headroom indicator |
| Per-component split | (CPU energy, DRAM energy, GPU energy) / total — where the budget actually went |
| Electricity saved | `(E_baseline − E_agent) / 3.6e6` kWh, optionally multiplied by facility PUE |
| Cost avoided | `electricity_saved_kWh × electricity_price_per_kWh` |

Statistics: 3 repeats per cell, median + IQR.

## Economic framing

The final paper can frame the work as performance recovery plus operational savings:

- **Capped performance**: how much faster jobs run under the same per-node power cap with the custom agent than with stock GEOPM/hardware behavior.
- **Always-on savings**: how much energy is saved when the cap is not binding while respecting the user's runtime slack.
- **System-scale money saved**: extrapolate measured kWh savings to Aurora-scale node-hours using an explicit electricity price and PUE assumption.

Keep the cost model transparent and separate from measured control results. Report the formula and assumptions so readers can substitute their own electricity price or facility PUE.

## Hypothesis (to evaluate, not assume)

**Cap-compliance hypothesis**: At the headline cell (cap = 3000 W, slack = 5 %), `aurora_bandit` recovers ≥ X % of uncapped TTS vs `power_governor`'s baseline.

**Always-on saving hypothesis** (NEW, condition 2 vs 1): At slack = 5 %, `aurora_bandit` running with no binding cap saves ≥ Y % of total energy vs hardware autonomy, with TTS overhead ≤ slack. Provisional targets per class: memory ≥15 %, comm ≥10 %, GPU compute ≥5 %, CPU compute ≥5 %. Higher slack should unlock more savings monotonically.

X to be set once Phase 1 establishes per-class Pareto slopes. Concrete provisional targets for cap-compliance (subject to revision):

| Class | Target TTS recovery @ (3000 W, 5 %) |
|-------|---------------------------------------|
| GPU compute | ≥40 % |
| CPU compute | ≥30 % |
| Memory | ≥60 % (expect biggest win — uncore freq + CPU freq decoupling) |
| Comm | ≥50 % (slack power redistribution) |

For other (cap, slack) cells: report the same metric and check whether the headline trend holds. At deep cap + tight slack, expect the bandit's advantage to shrink (hardware autonomy dominates); at mild cap + loose slack, expect biggest wins (more headroom to exploit).

If we **don't** hit these, the result is still useful: it bounds what software policy can do beyond hardware autonomy in the deep-cap regime, and motivates a follow-up federated/multi-node bandit.

## Deliverable: `analysis/phase3-report.md`

Must contain:

- Headline plot: per-benchmark bar chart of TTS under (uncapped, cap_governor, cap_bandit).
- Per-class summary: median TTS recovery + IQR.
- Per-component energy split bar charts → shows whether bandit "spent the budget" differently.
- Economic projection table: measured kWh saved per workload, assumed electricity price/PUE, and projected cost avoided at selected node-hour scales.
- Failure analysis: where `aurora_bandit` ≤ `power_governor`, what happened (action trace + signal trace excerpts).
- Decision: does the bandit warrant scaling up (more nodes, federated) or is a different algorithm needed?

## Decisions still open (resolve at phase start)

- Final cap × slack grid: prune which of the 12 cells from the sweep to run vs skip based on Phase 1 Pareto data.
- Whether to also run `power_balancer` as a third baseline (currently treated as covered by `power_governor` for single-node — would matter at multi-node).
- Whether `runtime_slack` should be tuned per class as well as per job (e.g. comm-bound class tolerates more slack since MPI waits are already perf-neutral).
