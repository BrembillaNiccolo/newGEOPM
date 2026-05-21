# Benchmarks by phase

This folder groups the benchmark suite by research phase without moving the benchmark source folders. The canonical benchmark recipes still live directly under `benchmarks/<bench>/`.

Use this index to decide what to run:

| Phase folder | Purpose |
| --- | --- |
| [`phase1-base/`](phase1-base/) | Simple base workloads used to learn which GEOPM knobs matter for each workload class. |
| [`phase2-agent-development/`](phase2-agent-development/) | Benchmarks used while building and debugging the custom GEOPM agent. |
| [`phase3-validation-paper/`](phase3-validation-paper/) | Held-out proxy and real workloads used to evaluate speed under caps, energy savings, and projected cost savings. |

Rule of thumb: Phase 1 chooses knobs; Phase 2 builds the agent; Phase 3 proves whether the agent is useful.
