# GROMACS (SYCL)

**Class**: End-to-end molecular dynamics (Phase 3 only). Mixed GPU compute (PME + nonbonded kernels) + MPI communication (domain decomposition + PME reduce-scatter). Realistic validation that the unified agent works on production HPC apps, not just microbenchmarks.

**Why**: production MD code, runs on PVC via SYCL, well-known performance characteristics, large user base — results are credible and reproducible by others.

## Source

Upstream: https://manual.gromacs.org / https://ftp.gromacs.org/gromacs/

**Local**: `src/gromacs-2025.0/` (release in `VERSION.txt`).

Prefer the **Aurora-installed module** if available (`module load gromacs`); use the vendored source only if the module is missing or for a specific patch.

## Build (on Aurora, from local source)

GROMACS with SYCL/Level Zero target for PVC:

```bash
module load oneapi/release cray-mpich cmake

cd benchmarks/gromacs/src/gromacs-2025.0
mkdir build && cd build
cmake .. \
    -DGMX_GPU=SYCL \
    -DGMX_SYCL=DPCPP \
    -DGMX_FFT_LIBRARY=mkl \
    -DGMX_MPI=ON \
    -DCMAKE_C_COMPILER=mpicc \
    -DCMAKE_CXX_COMPILER=mpicxx \
    -DCMAKE_BUILD_TYPE=Release \
    -DGMX_GPU_NB_CLUSTER_SIZE=8 \
    -DCMAKE_INSTALL_PREFIX=$PWD/install
make -j 32
make install
source $PWD/install/bin/GMXRC
```

Resulting `gmx_mpi` binary.

Confirm SYCL target list: `gmx_mpi --version | grep -i sycl`.

## Benchmark inputs

`inputs/gmxbench-3.0/` contains four systems (small → large):

| System | Atoms | Use |
|--------|-------|-----|
| `d.villin` | ~12 K | small protein; smoke test |
| `d.lzm` | ~25 K | lysozyme in water; classic single-node test |
| `d.dppc` | ~120 K | DPPC lipid bilayer; medium |
| `d.poly-ch2` | ~600 K | polymer; large, multi-node scaling test |

For Phase 3 use `d.dppc` (1-node baseline) and `d.poly-ch2` (4-node scaling). All come pre-generated with `topol.tpr` files.

## Run (single-node, dppc system)

```bash
export ZES_ENABLE_SYSMAN=1
source $GMX_INSTALL/bin/GMXRC
cd inputs/gmxbench-3.0/d.dppc

mpiexec -n 12 gmx_mpi mdrun \
    -s topol.tpr \
    -nsteps 50000 \
    -ntomp 8 \
    -nb gpu -pme gpu -bonded gpu \
    -noconfout -nstlist 100
```

(12 ranks = 2 ranks per GPU card × 6 cards. Adjust if you want 1 rank per tile = 12 ranks total but `-nb gpu` per-tile.)

## Expected runtime

5-15 minutes per run at 50000 steps on a single Aurora node.

## Validation criterion

GROMACS prints `Performance: <ns/day>` at the end. Sanity:

- d.dppc on one Aurora node should hit ~50-100 ns/day with SYCL + 6 PVCs (subject to GROMACS version perf changes).
- The run must complete normally (no `Fatal error` lines in `md.log`).

For energy-conservation check across knob settings, monitor `mdrun -e energy.edr` then `gmx energy -f energy.edr` — total energy drift should be class-typical (~1e-5 / step).

## GEOPM hypothesis

- **GPU compute phase** (nonbonded + PME spread/gather): GPU power cap is primary, freq cap secondary.
- **MPI phase** (domain decomp halo + PME reduce-scatter): CPU freq can drop without TTS penalty; classic slack opportunity.
- **CPU bonded phase** (small fraction with `-bonded cpu`): CPU freq matters.
- The unified agent should beat both static caps and `gpu_activity` here because of the multi-phase character.

## Sweep config

See `experiments/phase3/gromacs/sweep.yaml` (written in Phase 3).
