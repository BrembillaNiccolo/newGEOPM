# agent/

Native C++ `geopm::Agent` plugin sources. **Empty until Phase 2.** Full design in `docs/agent-design.md`.

## Planned layout

```
agent/
├── CMakeLists.txt
├── include/
│   └── AuroraBanditAgent.hpp
├── src/
│   ├── AuroraBanditAgent.cpp        # main agent class
│   ├── LinUCB.cpp                   # bandit core
│   ├── FeatureExtractor.cpp         # PIO signals → feature vector
│   ├── ActionGrid.cpp               # arms (control tuples)
│   └── PluginRegister.cpp           # geopm plugin factory entry point
├── tests/                           # unit tests (gtest)
└── build/                           # out-of-source build dir (gitignored)
```

## Build (when Phase 2 begins)

```bash
module load oneapi/release cmake
module load geopm/<version>            # Q7 from docs/open-questions.md

cd agent
mkdir -p build && cd build
cmake -DCMAKE_CXX_COMPILER=icpx \
      -DCMAKE_BUILD_TYPE=Release \
      -DGEOPM_PREFIX=$GEOPM_ROOT \
      ..
make -j
```

Produces `libaurora_bandit_agent.so`.

## Install / load

```bash
export GEOPM_PLUGIN_PATH=$PWD/agent/build
geopmagent -a aurora_bandit -p '{}'   # smoke test: prints agent metadata
```

Then in `geopmlaunch`:

```bash
geopmlaunch mpiexec \
    --geopm-agent=aurora_bandit \
    --geopm-policy=policy.json \
    --geopm-report=report.yaml \
    --geopm-trace=trace.csv \
    --geopm-period=0.020 \
    -- <ranks> <bench>
```

## Conventions

- C++17 minimum (GEOPM headers).
- Link `-lgeopmd`; `-lgeopm` if doing PIO outside the agent loop.
- No raw MSR writes — go through `PlatformIO`.
- Read controls back after write (some controls like `GPU_CORE_PERFORMANCE_FACTOR_CONTROL` silently refuse).
- Bound check every control write against `*_MIN_AVAIL` / `*_MAX_AVAIL`.
- Log every decision in trace mode (`policy.log_decisions = true`) so failure analysis in `analysis/phase3-report.md` is possible.

## Debug tips

- `GEOPM_DEBUG_ATTACH=1` lets you attach gdb to the controller process.
- `GEOPM_TRACE=trace.csv` works even without `--geopm-trace` if exporting from inside the agent.
- Most-common failure: forgot `ZES_ENABLE_SYSMAN=1` — all GPU signals return errors silently.
- Plugin not picked up: check `GEOPM_PLUGIN_PATH` includes the directory containing the `.so`, and that `dlopen` succeeds (run `LD_DEBUG=libs geopmagent ...`).
