# Phase 3 validation and paper benchmarks

Phase 3 evaluates the custom GEOPM agent against stock behavior. These benchmarks should be treated as validation workloads, not as the original knob-discovery set.

Primary questions:

- How much time-to-solution is recovered under the same power cap?
- How much energy is saved when no cap is binding?
- What electricity cost could be avoided on an Aurora-scale system?

| Benchmark | Validation role | Notes |
| --- | --- | --- |
| [`hpcg`](../../hpcg/) | Mixed proxy validation | Tests memory plus communication phase behavior. |
| [`hpl-cpu`](../../hpl-cpu/) | CPU compute headline | Use after `cpu-dgemm` has characterized CPU knobs. |
| [`mixbench`](../../mixbench/) | GPU arithmetic-intensity validation | Tests behavior between pure GPU memory and pure GPU compute regimes. |
| [`quicksilver`](../../quicksilver/) | Communication imbalance validation | Good comparison point for slack-aware behavior. |
| [`gromacs`](../../gromacs/) | First production application | Best first real MD app for GPU plus MPI behavior. |
| [`lammps`](../../lammps/) | Second production application | Generality test after GROMACS. |

Optional anchors from Phase 1 can be rerun here if needed for clean headline plots:

- [`stream`](../../stream/) or [`babelstream`](../../babelstream/) for memory savings.
- [`dgemm-gpu`](../../dgemm-gpu/) for GPU compute cap response.
- [`osu`](../../osu/) for controlled communication response.

Paper-facing metrics:

- TTS recovery under cap.
- Energy saved at equal or bounded runtime.
- EDP improvement.
- Cap utilization.
- Per-component energy split.
- kWh saved and projected cost avoided using explicit electricity price, PUE, and node-hour assumptions.
