# scripts/

PBS/qsub submission templates + `geopmlaunch` wrappers. **Empty until Phase 1.**

## Planned contents

| Script | Purpose |
|--------|---------|
| `submit_phase1.sh` | submit a single (benchmark, knob, level, repeat) cell as a PBS job |
| `submit_phase1_sweep.sh` | enumerate all cells from `experiments/phase1/<bench>/sweep.yaml` and submit each |
| `run_under_geopm.sh` | the actual in-job script: sets env, calls `geopmlaunch`, copies outputs |
| `aurora_pbs_template.sh` | header (queue, walltime, nodes, project) for ALCF PBS jobs |
| `submit_phase3.sh` | same shape, but iterates conditions (uncapped, cap_governor, cap_bandit) per bench |
| `verify_open_questions.sh` | runs the verification commands from `docs/open-questions.md` end-to-end |

## Conventions

- All scripts assume they're run from repo root.
- Use `$PROJECT_ROOT` / `$RUN_ROOT` env vars (defaulted from `pwd`) — never hardcode paths.
- Output goes under `experiments/phase{1,3}/<bench>/runs/<cell_id>/`.
- Cell ID format: `<knob>_<level>_<repeat>` for Phase 1; `<condition>_<repeat>` for Phase 3.
- Log resolved env (`env > meta.env`) per run for reproducibility.
- Scripts must be idempotent: re-running a cell wipes that cell's `runs/` dir before re-submitting.

## ALCF PBS template (sketch — fill in once allocation details are known)

```bash
#PBS -A <PROJECT>
#PBS -q <QUEUE>
#PBS -l select=<NODES>:system=aurora
#PBS -l walltime=01:00:00
#PBS -l filesystems=home:flare
#PBS -j oe
#PBS -N geopm-sweep

cd $PBS_O_WORKDIR
export ZES_ENABLE_SYSMAN=1
module load oneapi/release cray-mpich geopm/<version>

bash scripts/run_under_geopm.sh "$BENCH" "$KNOB" "$LEVEL" "$REPEAT"
```

## Submitter pattern

The `submit_phase1_sweep.sh` script should produce one PBS submission per cell rather than one job for all — easier to re-run failed cells and avoids one bad cell killing a long job. Use PBS array jobs if the queue supports them.
