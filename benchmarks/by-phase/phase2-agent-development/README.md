# Phase 2 agent-development benchmarks

Phase 2 builds and debugs the custom GEOPM agent using Phase 1 results. Use a small subset of Phase 1 benchmarks first, then add one mixed workload when the control loop is stable.

| Benchmark | Use in Phase 2 | Notes |
| --- | --- | --- |
| [`cpu-dgemm`](../../cpu-dgemm/) | CPU compute smoke test | Confirms CPU controls, readback, and reward calculation. |
| [`stream`](../../stream/) | CPU memory policy test | Checks that low core frequency plus high uncore is selected when appropriate. |
| [`dgemm-gpu`](../../dgemm-gpu/) | GPU compute policy test | Confirms GPU frequency and board-budget behavior. |
| [`babelstream`](../../babelstream/) | GPU memory policy test | Checks GPU memory-bound classification. |
| [`mpi-idle-wait`](../../mpi-idle-wait/) | Communication slack debug | Safest place to test wait-phase CPU throttling. |
| [`gpu-bursty-idle`](../../gpu-bursty-idle/) | Always-on GPU savings debug | Tests frequency restoration around GPU bursts. |
| [`hpcg`](../../hpcg/) | First mixed proxy test | Add only after simple workload policies are stable. |

Phase 2 acceptance should focus on correctness and safety:

- Agent loads and writes only allowed controls.
- Controls are clamped to available min/max values.
- Runtime slack is respected on simple workloads.
- Decision logs explain which arm was chosen and why.
- No benchmark is used yet as the final paper result.
