# benchmarks/

Per-benchmark build recipes and run notes. **Phase 0 deliverable: README per subdir, no source / no builds.** Builds happen on Aurora in Phase 1.

## Conventions

- Each subdir = one benchmark; subdir name matches benchmark short name.
- Each subdir has a `README.md` with: source URL, module loads, build invocation, expected runtime, validation criterion.
- Source IS vendored under `<bench>/src/` (downloaded Phase 0). Pinned version recorded in `<bench>/VERSION.txt` (git commit or tarball release).
- Exception: `dgemm-gpu/` has no `src/` — the benchmark is the vendor-shipped binary in `$MKLROOT/benchmarks/gemm` on Aurora.
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

## The 8 characterization benchmarks (Phase 1) + 2 end-to-end apps (Phase 3)

| Subdir | Phase | Class | Source | Local |
|--------|-------|-------|--------|-------|
| `mixbench/` | 1 | GPU compute (sweeps AI) | https://github.com/ekondis/mixbench | `src/` @ 32edeca |
| `dgemm-gpu/` | 1 | GPU compute | oneMKL (Aurora module) | none — vendor-shipped |
| `hpl-cpu/` | 1 | CPU compute | oneMKL MP_LINPACK (Aurora) + Netlib HPL backup | `src/hpl-2.3/` |
| `stream/` | 1 | Memory (CPU HBM/DDR) | https://www.cs.virginia.edu/stream/ | `src/stream.c` |
| `babelstream/` | 1 | Memory (GPU) | https://github.com/UoB-HPC/BabelStream | `src/` @ 57637d5 |
| `osu/` | 1 | Comm | https://mvapich.cse.ohio-state.edu/benchmarks/ | `src/osu-micro-benchmarks-7.4/` |
| `hpcg/` | 1 | Mixed (memory + comm) | Intel HPCG (Aurora module) + reference HPCG backup | `src/` @ 114602d |
| `quicksilver/` | 1 | Comm (imbalanced) | https://github.com/LLNL/Quicksilver | `src/` @ eb68bb8 |
| `gromacs/` | 3 | End-to-end MD (GPU+comm) | https://ftp.gromacs.org/gromacs/ | `src/gromacs-2025.0/` + `inputs/gmxbench-3.0/` |
| `lammps/` | 3 | End-to-end MD (GPU+comm) | https://download.lammps.org/ | `src/lammps-22Jul2025/` + in-tree `bench/` |
