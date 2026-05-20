# Glossary

| Term | Meaning |
|------|---------|
| **Aurora** | ALCF exascale supercomputer at Argonne. Intel Xeon Max CPUs + Intel Data Center GPU Max GPUs. |
| **GEOPM** | Global Extensible Open Power Manager. Intel-led runtime for power/perf control on HPC nodes. https://geopm.github.io |
| **`geopm::Agent`** | C++ plugin interface for custom GEOPM control policies. |
| **PIO** | GEOPM's Platform IO layer. Signals (read) and controls (write) flow through it. |
| **IOGroup** | A GEOPM plugin that exposes a set of signals/controls from one source (MSR, LevelZero, sysfs, etc.). |
| **PVC** | Ponte Vecchio. Intel Data Center GPU Max. 2 compute tiles per card. |
| **SPR / SPR-HBM** | Sapphire Rapids / Sapphire Rapids with HBM (Xeon Max). |
| **HBM** | High-Bandwidth Memory. On Xeon Max, ~64 GB per socket; can run HBM-only or flat (HBM+DDR). |
| **Tile** (PVC) | One of two compute slices per PVC card. Many GEOPM signals are per-tile (`gpu_chip` domain). |
| **Domain** (GEOPM) | Granularity at which a signal/control is exposed: board, package, cpu, core, gpu, gpu_chip, memory. |
| **RAPL** | Running Average Power Limit. Intel's MSR-based power-cap mechanism (PL1, PL2). |
| **PL1** | RAPL long-term power limit (sustained). The "thermal" cap. |
| **PL2** | RAPL short-term power limit (boost). |
| **DVFS** | Dynamic Voltage and Frequency Scaling. |
| **HWP** | Hardware-controlled P-states. Intel's autonomous core-freq governor. GEOPM's `CPU_FREQUENCY_*_CONTROL` writes the HWP min/max bounds. |
| **Uncore** | Non-core parts of the CPU package: mesh, L3, memory controllers. Has its own frequency knob (`CPU_UNCORE_FREQUENCY_*_CONTROL`) that gates memory bandwidth. |
| **Epoch** | A GEOPM region boundary; created by `geopm_prof_epoch()` calls inside the app. Used by agents like `power_balancer` for periodic decisions. |
| **Region** | A user-tagged code section in GEOPM (`geopm_prof_region` + `geopm_prof_enter`/`exit`). |
| **REGION_HINT** | Semantic tag attached to a region: compute, memory, network, sync, etc. Used by agents to switch policy by phase. |
| **TTS** | Time to solution. |
| **EDP** | Energy-Delay Product (J·s). Lower = better. |
| **IPS / IPC** | Instructions per second / per cycle. |
| **AVX-512** | 512-bit SIMD vector instructions. Heavy on CPU power. |
| **AMX** | Advanced Matrix Extensions. SPR feature for tile-based matrix ops; Xeon Max lacks AMX-FP64. |
| **XMX / XVE** | PVC's matrix and vector engines respectively. |
| **Slingshot-11** | Cray's HPC interconnect. Aurora's network fabric. |
| **Cray MPICH** | The Aurora-default MPI implementation. |
| **oneAPI / Level Zero / SYCL** | Intel's GPU programming stack. Level Zero is the low-level runtime; SYCL is the C++ programming model. |
| **xpu-smi** | Intel's PVC monitoring CLI (analogous to `nvidia-smi`). Not part of GEOPM but available on Aurora. |
| **SST-CP / SST-PP / SST-TF / SST-BF** | Intel Speed Select Technology variants: Core Priority / Performance Profile / Turbo Frequency / Base Frequency. |
| **LinUCB** | Linear Upper-Confidence-Bound algorithm. Classical contextual-bandit policy. |
| **IPS estimator** | Inverse Propensity Score; offline reweighting technique to debias contextual-bandit warm-start from observational data. |
| **Pareto frontier** | Non-dominated set in (energy, runtime) space — points where you can't improve one without worsening the other. |
| **ECP** | Exascale Computing Project (US DOE). Source of standard "proxy apps" (HPCG, AMG, Quicksilver, Nekbone, ...) used as realistic mini-benchmarks. |
