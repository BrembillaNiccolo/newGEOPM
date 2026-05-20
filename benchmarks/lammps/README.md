# LAMMPS (Kokkos / SYCL)

**Class**: End-to-end molecular dynamics (Phase 3 only). Mixed GPU compute + MPI communication. Companion to GROMACS — different code, different performance profile, both production MD.

**Why**: a second production MD app validates that the unified agent generalizes beyond a single codebase. LAMMPS's Kokkos backend gives us a SYCL path for PVC.

## Source

Upstream: https://www.lammps.org / https://download.lammps.org/

**Local**: `src/lammps-22Jul2025/` (release in `VERSION.txt`).

Prefer the **Aurora-installed module** if available (`module load lammps`); use the vendored source only if the module is missing.

## Build (on Aurora, from local source, Kokkos+SYCL for PVC)

```bash
module load oneapi/release cray-mpich cmake

cd benchmarks/lammps/src/lammps-22Jul2025
mkdir build && cd build
cmake ../cmake \
    -DPKG_KOKKOS=ON \
    -DKokkos_ENABLE_SYCL=ON \
    -DKokkos_ARCH_INTEL_PVC=ON \
    -DPKG_MOLECULE=ON -DPKG_KSPACE=ON -DPKG_RIGID=ON \
    -DBUILD_MPI=ON \
    -DCMAKE_CXX_COMPILER=mpicxx \
    -DCMAKE_C_COMPILER=mpicc \
    -DCMAKE_BUILD_TYPE=Release
make -j 32
```

Binary: `lmp` (with Kokkos package).

Verify SYCL: `./lmp -h | grep -i kokkos` and `./lmp -h | grep -i sycl`.

## Benchmark inputs

In-tree at `src/lammps-22Jul2025/bench/`:

| Input | System | Use |
|-------|--------|-----|
| `in.lj` | Lennard-Jones liquid | classic perf benchmark |
| `in.eam` | metallic EAM | Class 1 (GPU compute) heavy |
| `in.chain` | bead-spring polymer | Class 4 (comm-heavy) |
| `in.chute` | granular | small smoke test |
| `in.rhodo` | rhodopsin membrane | realistic biomolecular |

For Phase 3, use `in.rhodo` (single-node realistic) and `in.lj` scaled up (multi-node).

## Run (single-node, rhodopsin)

```bash
export ZES_ENABLE_SYSMAN=1
cd benchmarks/lammps/src/lammps-22Jul2025/bench

mpiexec -n 12 ../build/lmp \
    -k on g 6 \
    -sf kk \
    -pk kokkos newton on neigh half \
    -in in.rhodo \
    -var x 4 -var y 4 -var z 4
```

(`-k on g 6` = Kokkos on 6 GPUs; `-sf kk` = use Kokkos versions of styles; `-var x/y/z` scales the box.)

## Run (multi-node Lennard-Jones, 4 nodes)

```bash
mpiexec -n 48 ../build/lmp \
    -k on g 6 -sf kk -pk kokkos newton on \
    -in in.lj \
    -var x 8 -var y 8 -var z 8
```

## Expected runtime

5-20 minutes per run at default step counts. Scale `-var x/y/z` to control box size.

## Validation criterion

LAMMPS prints performance at end:

```
Performance: <tau/ns ns/day>
Loop time of <X> on <N> procs for <steps> steps with <natoms> atoms
```

Sanity:
- `in.rhodo` on one Aurora node with Kokkos+SYCL: ~10-30 ns/day class (varies with build flags).
- Run must finish with no `ERROR:` lines.

## GEOPM hypothesis

- **EAM / LJ kernels**: GPU compute-bound → GPU power cap dominates.
- **PPPM (long-range electrostatics in `in.rhodo`)**: comm-bound FFTs → CPU freq drop during comm phases helps.
- **Bonded compute (rhodopsin)**: smaller GPU phase, more CPU work — CPU freq matters more.
- Expected: unified agent wins over `gpu_activity` because of the comm phase, and over `power_governor` because of the GPU phase.

## Sweep config

See `experiments/phase3/lammps/sweep.yaml` (written in Phase 3).
