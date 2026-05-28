#!/usr/bin/env bash
# Submit scripts/submit_phase0_all.pbs REPEATS times in sequence.
# Each PBS submission is the 7-node debug-scaling parallel run (one bench per node).
# Each submission's cells land in experiments/phase1/<bench>/runs/<PBS_JOBID>/...
# After all REPEATS finish, the summarizer averages across the N PBS_JOBIDs.
#
# Default: REPEATS=5 full strict-knob sweeps on all 7 benches.
# At ~40 min wall per submission and 5 submissions, expect ~3.5 h total.
#
# Usage:
#   ./scripts/submit_phase0_all_repeat.sh
#   REPEATS=3 ./scripts/submit_phase0_all_repeat.sh
#   WALLTIME=00:45:00 VARIANT=smoke_15s ./scripts/submit_phase0_all_repeat.sh
#   APPLY_CONTROLS=0 ./scripts/submit_phase0_all_repeat.sh        # dry / read-only
#
# Env overrides:

set -euo pipefail

: "${REPEATS:=10}"
: "${QUEUE:=debug-scaling}"
: "${ACCOUNT:=UIC-HPC}"
: "${WALLTIME:=01:00:00}"
: "${SELECT:=7}"
: "${VARIANT:=all_tiles_15s}"   # GPU benches use all 12 tiles; CPU/MPI benches use the smoke_15s alias
: "${APPLY_CONTROLS:=1}"
: "${GEOPM_MONITOR:=1}"
: "${GEOPM_PERIOD:=0.05}"
: "${MAX_CELLS:=}"
: "${BENCH_LIST:=}"           # empty -> use submit_phase0_all.pbs default (all 7 benches)
: "${POLL_SECONDS:=30}"
: "${PBS_SCRIPT:=scripts/submit_phase0_all.pbs}"
: "${DRY_RUN:=0}"   # 1 = print the qsub command(s) without submitting

echo "Repeating ${REPEATS} submissions of ${PBS_SCRIPT}"
echo "Settings:"
echo "  QUEUE=${QUEUE}  ACCOUNT=${ACCOUNT}  WALLTIME=${WALLTIME}  SELECT=${SELECT}"
echo "  VARIANT=${VARIANT}  APPLY_CONTROLS=${APPLY_CONTROLS}  GEOPM_MONITOR=${GEOPM_MONITOR}"
echo "  GEOPM_PERIOD=${GEOPM_PERIOD}  MAX_CELLS=${MAX_CELLS:-<unset>}  BENCH_LIST=${BENCH_LIST:-<default>}"
echo "  POLL_SECONDS=${POLL_SECONDS}"
echo

if ! command -v qsub >/dev/null 2>&1; then
    echo "ERROR: qsub not on PATH. Run from an Aurora login node." >&2
    exit 1
fi

# Build the -v list once (same for every iteration)
VARS="VARIANT=${VARIANT},APPLY_CONTROLS=${APPLY_CONTROLS},GEOPM_MONITOR=${GEOPM_MONITOR},GEOPM_PERIOD=${GEOPM_PERIOD}"
[[ -n "${MAX_CELLS}" ]] && VARS+=",MAX_CELLS=${MAX_CELLS}"
[[ -n "${BENCH_LIST}" ]] && VARS+=",BENCH_LIST=${BENCH_LIST}"

JOBIDS=()
for i in $(seq 1 "${REPEATS}"); do
    echo "=========================================="
    echo "[$(date +%H:%M:%S)] iteration ${i}/${REPEATS}: submitting"
    echo "=========================================="

    QSUB_CMD=(qsub -q "${QUEUE}" -A "${ACCOUNT}" -l walltime="${WALLTIME}" -l select="${SELECT}" -v "${VARS}" "${PBS_SCRIPT}")
    if [[ "${DRY_RUN}" == "1" ]]; then
        printf '  [DRY_RUN] would run:'; printf ' %q' "${QSUB_CMD[@]}"; echo
        JOBIDS+=("DRY_RUN_${i}")
        continue
    fi
    JOBID=$("${QSUB_CMD[@]}")
    echo "  jobid: ${JOBID}"
    JOBIDS+=("${JOBID}")

    # Poll qstat until job leaves the queue
    while qstat "${JOBID}" >/dev/null 2>&1; do
        STATE=$(qstat "${JOBID}" 2>/dev/null | awk 'NR>=3 && $1 ~ /^[0-9]/ {print $5; exit}')
        printf '  [%s] iter %d/%d  %s  state=%s\n' "$(date +%H:%M:%S)" "${i}" "${REPEATS}" "${JOBID}" "${STATE:-?}"
        sleep "${POLL_SECONDS}"
    done
    echo "  [$(date +%H:%M:%S)] iteration ${i} done"
    echo
done

echo "=========================================="
echo "All ${REPEATS} submissions finished."
echo "=========================================="
for i in "${!JOBIDS[@]}"; do
    printf '  iter %d  ->  %s  ->  results/%s/\n' "$((i+1))" "${JOBIDS[$i]}" "${JOBIDS[$i]}"
done

echo
echo "Aggregate everything (mean/median/std across all ${REPEATS} runs):"
echo "  ./analysis/scripts/summarize_phase0_knobs.sh \\"
echo "      experiments/phase1/cpu-dgemm/runs \\"
echo "      experiments/phase1/stream/runs \\"
echo "      experiments/phase1/dgemm-gpu/runs \\"
echo "      experiments/phase1/babelstream/runs \\"
echo "      experiments/phase1/osu/runs \\"
echo "      experiments/phase1/mpi-idle-wait/runs \\"
echo "      experiments/phase1/gpu-bursty-idle/runs"
