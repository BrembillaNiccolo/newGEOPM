# Benchmark suite recommendations

This repo already has a strong benchmark plan, but the full suite is larger than the Phase 1 characterization campaign needs to be. Phase 1 should answer one narrow question: **for each workload class, which GEOPM knobs actually move energy and runtime?**

The recommendation is to keep all existing benchmark material, but split benchmarks into two groups:

- **Phase 1 base benchmarks**: simple, controlled workloads used to rank knobs by application class.
- **Later validation benchmarks**: mixed/proxy/real applications used after the custom GEOPM agent exists.

The runnable grouping lives in [`../benchmarks/by-phase/`](../benchmarks/by-phase/).

Deferred benchmarks are marked with `DELETE.md` in their folders to mean "exclude from the Phase 1 base campaign", not "remove from git".

## Phase 1 base suite

| Benchmark | Role | Why it stays in the first pass |
| --- | --- | --- |
| `stream/` | CPU memory-bound | Canonical CPU HBM/DDR bandwidth test. It should expose the expected GEOPM win: lower CPU frequency while keeping uncore high. |
| `babelstream/` | GPU memory-bound | GPU mirror of STREAM. It tests PVC bandwidth sensitivity to `GPU_CORE_FREQUENCY_MAX_CONTROL`. |
| `dgemm-gpu/` | GPU compute-bound | Clean vendor-tuned GPU compute anchor with high, stable PVC utilization. |
| `cpu-dgemm/` | CPU compute-bound | Smaller and cheaper CPU compute anchor before running full HPL. |
| `osu/` focused on `osu_allreduce` first | MPI communication-bound | Isolates collective communication slack with lower complexity than full application imbalance. Add `osu_alltoall` after `allreduce` if time allows. |
| `mpi-idle-wait/` | Synthetic communication slack | Confirms whether CPU throttling during wait phases is safe before testing more variable MPI workloads. |
| `gpu-bursty-idle/` | Synthetic GPU idle/burst behavior | Tests always-on energy savings during GPU idle gaps, which saturated kernels do not expose. |

Together these cover the base classes needed to choose knobs: CPU compute, CPU memory, GPU compute, GPU memory, MPI communication slack, and bursty idle behavior.

Phase 1 output should be a per-class knob ranking and Pareto table, not a claim that the final agent works on real applications.

## Later validation suite

| Benchmark | Later role | Why it moves after Phase 1 |
| --- | --- | --- |
| `hpcg/` | Mixed proxy validation | Useful once the agent can switch behavior across memory and communication phases. Too mixed for clean knob discovery. |
| `hpl-cpu/` | CPU headline validation | Good recognizable CPU compute result, but expensive compared with `cpu-dgemm/`. |
| `mixbench/` | GPU arithmetic-intensity validation | Useful to test detector behavior between pure GPU memory and pure GPU compute regimes. |
| `quicksilver/` | Communication imbalance validation | Good test for slack-aware policy after simple OSU and synthetic wait cases are understood. |
| `gromacs/` | First production application | Best first real app to show GPU compute plus MPI behavior under the custom agent. |
| `lammps/` | Second production application | Generality test after GROMACS, with a different MD code and performance profile. |

These later benchmarks should answer a different question: **how much time-to-solution is recovered under a cap, and how much energy does the custom GEOPM policy save versus stock behavior?**

## Paper framing

The technical metrics remain runtime, energy, EDP, cap utilization, and per-component energy split. The final paper should translate those into an operational result:

- How much performance is recovered when a job is power-capped.
- How much energy is saved when no cap is binding.
- How much electricity cost could be avoided on a system like Aurora by applying the policy at scale.

That cost claim should be computed from measured joules saved, assumed electricity price, facility PUE if available, and projected node-hours. Keep the cost model separate from the control-policy result so the science remains reproducible even if electricity prices change.
