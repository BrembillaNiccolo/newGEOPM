# benchmarks/

Per-benchmark build recipes and run notes. **Phase 0 deliverable: README per subdir, no source / no builds.** Builds happen on Aurora in Phase 1.

## Conventions

- Each subdir = one benchmark; subdir name matches benchmark short name.
- Each subdir has a `README.md` with: source URL, module loads, build invocation, expected runtime, validation criterion.
- Source is vendored under `<bench>/src/` when the benchmark depends on external source downloaded in Phase 0. Pinned version recorded in `<bench>/VERSION.txt` (git commit or tarball release).
- Exceptions: `dgemm-gpu/` and `cpu-dgemm/` may use vendor-shipped oneMKL binaries/samples; `mpi-idle-wait/` and `gpu-bursty-idle/` are small local synthetics whose source can be added in Phase 1 if needed.
- Per-benchmark sweep config lives in `experiments/phase1/<bench>/sweep.yaml`, **not here** (separation of "how to build" from "how to sweep").
- To transfer to Aurora: `rsync -a benchmarks/ <aurora-user>@<login>:<project-dir>/AuroraGeopm/benchmarks/` (or use Globus for big projects).

## Required env for every benchmark run

```bash
export ZES_ENABLE_SYSMAN=1            # all GPU LevelZero signals require this
module load oneapi/release
module load cray-mpich
module load geopm/<version-from-Q7>   # see docs/open-questions.md
```

## Standard launch wrapper (Phase 1)

```bash
geopmlaunch mpiexec \
    --geopm-agent=monitor \
    --geopm-report=$RUNDIR/report.yaml \
    --geopm-trace=$RUNDIR/trace.csv \
    --geopm-period=0.020 \
    -- <ranks/affinity> <bench binary> <bench args>
```

(In Phase 1 the `--geopm-agent` is replaced by `frequency_map` or stays `monitor` depending on the knob being swept; in Phase 2/3 it becomes `aurora_bandit`.)

## Benchmark suite status

Phase 1 base-suite recommendations live in [`../docs/benchmark-suite-recommendations.md`](../docs/benchmark-suite-recommendations.md). A `DELETE.md` file in a benchmark folder means "deferred from the reduced Phase 1 base campaign", not "remove from git".

For an easier run-order view, use [`by-phase/`](by-phase/), which groups benchmarks into Phase 1 base characterization, Phase 2 agent development, and Phase 3 validation/paper workloads.

## Characterization benchmarks and end-to-end apps

| Subdir | Phase | Class | First-pass status | Source | Local |
|--------|-------|-------|-------------------|--------|-------|
| `stream/` | 1 | Memory (CPU HBM/DDR) | Core | https://www.cs.virginia.edu/stream/ | `src/stream.c` |
| `babelstream/` | 1 | Memory (GPU) | Core | https://github.com/UoB-HPC/BabelStream | `src/` @ 57637d5 |
| `dgemm-gpu/` | 1 | GPU compute | Core | oneMKL (Aurora module) | none — vendor-shipped |
| `cpu-dgemm/` | 1 | CPU compute | Core | oneMKL BLAS sample or vendor benchmark | none yet |
| `osu/` | 1 | Comm | Core, focus `osu_allreduce` first | https://mvapich.cse.ohio-state.edu/benchmarks/ | `src/osu-micro-benchmarks-7.4/` |
| `mpi-idle-wait/` | 1 | Comm slack synthetic | Core detector/debug helper | local synthetic | none yet |
| `gpu-bursty-idle/` | 1 | GPU burst/idle synthetic | Core detector/debug helper | local synthetic | none yet |
| `hpcg/` | after Phase 1 | Mixed (memory + comm) | Deferred; see `DELETE.md` | Intel HPCG (Aurora module) + reference HPCG backup | `src/` @ 114602d |
| `gromacs/` | after Phase 2 | End-to-end MD (GPU+comm) | Deferred; see `DELETE.md`; first production app later | https://ftp.gromacs.org/gromacs/ | `src/gromacs-2025.0/` + `inputs/gmxbench-3.0/` |
| `mixbench/` | after Phase 1 | GPU compute (sweeps AI) | Deferred; see `DELETE.md` | https://github.com/ekondis/mixbench | `src/` @ 32edeca |
| `hpl-cpu/` | after Phase 1 | CPU compute | Deferred; see `DELETE.md` | oneMKL MP_LINPACK (Aurora) + Netlib HPL backup | `src/hpl-2.3/` |
| `quicksilver/` | after Phase 2 | Comm (imbalanced) | Deferred; see `DELETE.md` | https://github.com/LLNL/Quicksilver | `src/` @ eb68bb8 |
| `lammps/` | after GROMACS | End-to-end MD (GPU+comm) | Deferred; see `DELETE.md` | https://download.lammps.org/ | `src/lammps-22Jul2025/` + in-tree `bench/` |
