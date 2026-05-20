# experiments/

Sweep configurations and raw run logs. **No source code here.**

## Layout (planned)

```
experiments/
├── phase1/
│   ├── <bench>/
│   │   ├── sweep.yaml          # knob grid for this benchmark
│   │   ├── HPL.dat / hpcg.dat  # if benchmark has an input file
│   │   ├── runs/
│   │   │   └── <knob>_<level>_<repeat>/   # one dir per cell
│   │   │       ├── trace.csv               # PIO trace at 20 ms
│   │   │       ├── report.yaml             # geopm-report
│   │   │       ├── stdout.log
│   │   │       └── meta.json               # benchmark args, env, timestamps
│   │   └── README.md                       # what was swept, link to analysis
│   └── ...
└── phase3/
    └── <bench>/
        └── <condition>_<repeat>/
            ├── trace.csv
            ├── report.yaml
            ├── stdout.log
            └── meta.json
```

Conditions in Phase 3: `uncapped`, `cap_governor_fair`, `cap_governor_gpuheavy`, `cap_bandit_fair`, `cap_bandit_gpuheavy`.

## Conventions

- **Reproducibility**: every `meta.json` records — GEOPM version, oneAPI version, Cray MPICH version, allocation queue, node IDs, git commit of benchmark source, exact knob values written, hostname, UTC timestamp.
- **Naming**: snake_case for directories; knob names match GEOPM PIO spelling.
- **Logs are append-only** during sweeps — never edit raw run output. Re-run if a row is bad.
- **Outlier rule**: a repeat is discarded if its TTS deviates from the median by >2× IQR. Mark in `meta.json: {"discarded": true, "reason": "..."}`.
- **Storage**: `runs/` directories are big (~MB each at 20 ms trace). Compress or move to scratch when a benchmark is fully analyzed; keep `report.yaml` + `meta.json` in repo.
- **Schema**: full column list in `docs/phase1-sweep-design.md` "Output schema" section. Match exactly.

## How to add a new benchmark

1. Add `benchmarks/<bench>/README.md` with build recipe (Phase 0).
2. Create `experiments/phase1/<bench>/sweep.yaml` defining knob grid (Phase 1).
3. Use the standard launcher from `scripts/` (Phase 1).
