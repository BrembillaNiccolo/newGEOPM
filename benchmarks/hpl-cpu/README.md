# Intel HPL (CPU, LINPACK)

**Class**: CPU compute. Saturates AVX-512 FMA on all Xeon Max cores; drives package power to PL1/PL2.

**Why**: clean AVX-512 single-app signal; clearest CPU-class Pareto curve.

## Source

Intel MKL ships MP_LINPACK on Aurora (preferred):

```bash
module load oneapi/release
ls $MKLROOT/benchmarks/mp_linpack
```

Binary: `xhpl_intel64_dynamic` (or similar).

**Local Netlib HPL backup**: `src/hpl-2.3/` (release recorded in `VERSION.txt`). Use only if the MKL binary is unavailable.

## Build

No build needed if the module's binary is used. To build Netlib HPL from local source linked against MKL:

```bash
module load oneapi/release cray-mpich
cd benchmarks/hpl-cpu/src/hpl-2.3
# Copy and edit Make.<arch>: set CC=cc, MPdir=$CRAY_MPICH_DIR, LAlib uses MKL
make arch=Aurora
```

## HPL.dat (problem size)

Tune `N` so the matrix consumes ~70% of HBM-only memory on the node:

- 2× Xeon Max with 64 GB HBM/socket = 128 GB HBM total
- 70% = ~90 GB → `N ≈ sqrt(90e9 / 8) ≈ 106000` for FP64

Record the exact `HPL.dat` in `experiments/phase1/hpl-cpu/HPL.dat`.

Block size `NB` = 224 or 384 are typical sweet spots for SPR; experiment.

## Run (single-node)

```bash
module load oneapi/release cray-mpich
export OMP_NUM_THREADS=1
export I_MPI_PIN_DOMAIN=core
mpiexec -n <ranks> ./xhpl_intel64_dynamic   # HPL.dat in cwd
```

For HBM-only mode: configure node memory mode in BIOS or via `numactl --membind=<hbm_nodes>`.

## Expected runtime

20-60 minutes at N≈100k on one Aurora node.

## Validation criterion

HPL self-reports GFLOPS + a residual check. Residual must be `||Ax-b|| / (eps*||A||*||x||*N) < O(1)` (HPL prints "PASSED"). Performance: should approach published Xeon Max HPL numbers (lower than HPL-MxP/GPU runs, since HPL is FP64).

## GEOPM hypothesis

- `CPU_FREQUENCY_MAX_CONTROL` reduction is dominant; ~8-12% energy saving at <3% perf loss near base frequency.
- `CPU_UNCORE_FREQUENCY_MAX_CONTROL` should stay HIGH — uncore gates inter-core data movement.
- `CPU_POWER_LIMIT_CONTROL` reduction works similarly (RAPL throttles frequency to hit cap).

## Sweep config

See `experiments/phase1/hpl-cpu/sweep.yaml` (written in Phase 1).
