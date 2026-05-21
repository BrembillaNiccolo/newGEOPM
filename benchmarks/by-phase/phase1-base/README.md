# Phase 1 base benchmarks

Phase 1 uses simple, controlled workloads to answer one question: **which GEOPM knobs are useful for each workload class?**

Do not use this phase to claim the final agent works. The output should be per-class knob rankings, signal detectors, and Pareto points for Phase 2.

| Benchmark | Workload class | Main knobs to study | Notes |
| --- | --- | --- | --- |
| [`cpu-dgemm`](../../cpu-dgemm/) | CPU compute | `CPU_FREQUENCY_MAX_CONTROL`, `CPU_POWER_LIMIT_CONTROL` | Cheap CPU compute anchor before HPL. |
| [`stream`](../../stream/) | CPU memory | `CPU_FREQUENCY_MAX_CONTROL`, `CPU_UNCORE_FREQUENCY_MAX_CONTROL`, `DRAM_POWER_LIMIT_CONTROL` | Run HBM-only and flat/DDR variants. |
| [`dgemm-gpu`](../../dgemm-gpu/) | GPU compute | `GPU_CORE_FREQUENCY_MAX_CONTROL`, board/CPU/DRAM budget split | Clean PVC compute anchor. |
| [`babelstream`](../../babelstream/) | GPU memory | `GPU_CORE_FREQUENCY_MAX_CONTROL`, GPU activity/power signals | GPU memory-bound mirror of STREAM. |
| [`osu`](../../osu/) | MPI communication | `CPU_FREQUENCY_MAX_CONTROL`, possibly SST later | Start with `osu_allreduce`; add `osu_alltoall` if time allows. |
| [`mpi-idle-wait`](../../mpi-idle-wait/) | Synthetic communication slack | `CPU_FREQUENCY_MAX_CONTROL` | Isolates wait-phase throttling before noisy MPI apps. |
| [`gpu-bursty-idle`](../../gpu-bursty-idle/) | GPU burst/idle | `GPU_CORE_FREQUENCY_MAX_CONTROL` | Tests always-on savings during GPU idle gaps. |

Expected deliverables:

- Per-class knob ranking by energy/runtime impact.
- Signal detector candidates for each workload class.
- Pareto points to seed the Phase 2 action grid.
- List of knobs to drop because they do not move the frontier.
