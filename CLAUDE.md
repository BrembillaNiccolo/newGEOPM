# AuroraGeopm

Research project: build a unified GEOPM agent (eventually contextual-bandit / online-RL) that runs HPC jobs on **Aurora** (ALCF) more energy-efficiently than autonomous hardware behavior.

Two complementary value propositions, **both targeted by the same agent**:
1. **Always-on energy saving** — even when no power cap is set, the agent detects workloads that don't need full power (memory-bound, comm-bound, GPU-idle bursts) and applies energy-saving knobs within the user's `runtime_slack` budget. Free savings = the agent claims them.
2. **Cap-compliance** — under **a user-defined per-node power cap** (3000 W is our headline scenario; the framework supports any value), the agent recovers more time-to-solution than hardware autonomy alone by allocating the budget intelligently across CPU / DRAM / GPU.

Per-node hardware reference: 2× Intel Xeon Max (Sapphire Rapids HBM) + 6× Intel Data Center GPU Max "Ponte Vecchio" (PVC), 2 tiles each.

**Two user-tunable knobs frame every experiment** (set per-job, not learned by the agent):
- **Power cap** — the `BOARD_POWER_LIMIT_CONTROL` value (W) for the run. Default scenario 3000 W; anything from near-floor (~1500 W) to default (~4500-5000 W) is valid.
- **Runtime slack tolerance** — max allowed slowdown vs uncapped baseline, expressed as a fraction ε. The agent's reward is constrained `runtime ≤ (1+ε)·baseline_runtime`. Default 0.05 (5 %), but the user can pick anything from 0 (no slowdown allowed; energy savings only when free) to large (aggressive energy-first).

**Key cap mechanism on Aurora**: there's no writable GPU power cap. Whatever cap is chosen is enforced via `BOARD_POWER_LIMIT_CONTROL` (whole-node PL1); the agent shapes how that budget gets split via `CPU_POWER_LIMIT_CONTROL`, `DRAM_POWER_LIMIT_CONTROL`, and `GPU_CORE_FREQUENCY_MAX_CONTROL`. See [`docs/geopm-aurora.md`](docs/geopm-aurora.md) — the verified signal/control inventory lives in [`docs/signals_and_controls/`](docs/signals_and_controls/).

## Phases

| Phase | What | When | Status |
|-------|------|------|--------|
| 0 | Repo scaffolding + design docs (no Aurora needed) | Now, Aurora maintenance window | **active** |
| 1 | Knob characterization sweeps on all 4 workload classes | When Aurora returns | pending |
| 2 | Unified C++ `geopm::Agent` plugin (LinUCB warm-started from Phase 1) | After Phase 1 | pending |
| 3 | 3000 W cap evaluation: stock `power_governor` vs unified agent | After Phase 2 | pending |

Full plan: `/home/nbrembilla/.claude/plans/ethereal-discovering-treehouse.md`.

## Directory orientation

- `docs/` — design docs (sweep design, agent architecture, cap design), GEOPM-on-Aurora cheat-sheet, open questions, glossary
- `benchmarks/` — per-benchmark build recipes (READMEs only in Phase 0; no source until Aurora)
- `experiments/` — sweep configs and run logs (filled in Phase 1)
- `agent/` — C++ `geopm::Agent` plugin sources (Phase 2)
- `analysis/` — per-phase reports + plotting code
- `scripts/` — PBS/qsub templates + `geopmlaunch` wrappers (Phase 1)

Each subdirectory has its own `CLAUDE.md` with scoped conventions.

## Golden-path commands (Aurora, once available)

Always set before running anything that reads GPU telemetry:

```bash
export ZES_ENABLE_SYSMAN=1
```

Discover what's actually exposed on the node:

```bash
geopmread --info-all | less     # all signals + controls + domains
geopmread CPU_POWER package 0   # spot-check one
geopmwrite --info-all           # writable controls only
```

Launch a benchmark under a GEOPM agent:

```bash
geopmlaunch mpiexec \
    --geopm-agent=monitor \
    --geopm-report=report.yaml \
    --geopm-trace=trace.csv \
    --geopm-period=0.020 \
    -- <ranks args> <benchmark binary> <args>
```

(Phase 2 swaps `monitor` → our custom agent via `GEOPM_PLUGIN_PATH`.)

## Workload classes & benchmark suite

Phase 1 (characterization):

1. GPU compute → **mixbench-SYCL**, **oneMKL DGEMM (GPU)**
2. CPU compute → **Intel HPL (CPU)**
3. Memory → **STREAM (HBM-only + flat)**, **BabelStream (GPU Triad)**
4. Comm → **OSU `osu_alltoall` + `osu_allreduce`**
5. Mixed validation → **HPCG**, **Quicksilver**

Phase 3 (end-to-end MD apps): **GROMACS-SYCL** + **LAMMPS-Kokkos/SYCL**.

## Conventions

- All energy numbers in joules (J), power in watts (W), frequency in Hz (not GHz) — match GEOPM units.
- Per-tile attribution: PVC has 2 tiles per card. Tile-domain signals use `gpu_chip`; card-domain uses `gpu`.
- Treat memory as a separate domain from CPU package (`DRAM_POWER` is its own RAPL zone).
- Phase 0 produces **no executable code**. Only .md scaffolding.
