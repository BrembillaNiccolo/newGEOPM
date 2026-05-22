# AuroraGeopm

GEOPM-based energy-efficiency research for the Aurora supercomputer (ALCF). Targets the 3000 W per-node power-cap regime with a custom `geopm::Agent` plugin that learns online (contextual bandit / RL) from per-workload-class characterization data.

## Quick links

- Full research plan: `/home/nbrembilla/.claude/plans/ethereal-discovering-treehouse.md`
- GEOPM signal/control cheat-sheet for Aurora: [`docs/geopm-aurora.md`](docs/geopm-aurora.md)
- Phase 1 sweep design: [`docs/phase1-sweep-design.md`](docs/phase1-sweep-design.md)
- Benchmark suite recommendations: [`docs/benchmark-suite-recommendations.md`](docs/benchmark-suite-recommendations.md)
- Agent design: [`docs/agent-design.md`](docs/agent-design.md)
- 3000 W cap experimental design: [`docs/phase3-cap-design.md`](docs/phase3-cap-design.md)
- Open questions (verify on Aurora): [`docs/open-questions.md`](docs/open-questions.md)
- Glossary: [`docs/glossary.md`](docs/glossary.md)

## Status

Phase 0 now has a first runnable path in addition to the design docs:

- `benchmarks/cpu-dgemm/src/cpu_dgemm.cpp` implements the first simple benchmark.
- `benchmarks/registry.json` describes benchmark build/run commands.
- `experiments/phase1/*/sweep.json` lists the first useful GEOPM knobs per workload class.
- `scripts/run_phase0_sweep.sh` runs a benchmark cell and can optionally apply GEOPM controls.
- `analysis/scripts/summarize_phase0_knobs.sh` writes the useful-knob CSVs.

See [`docs/phase0-knob-discovery.md`](docs/phase0-knob-discovery.md) for commands.
