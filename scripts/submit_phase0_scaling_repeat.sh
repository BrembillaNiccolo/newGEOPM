#!/usr/bin/env bash
# Submit scripts/submit_phase0_scaling.pbs REPEATS times sequentially.
# Each submission = 140 nodes on debug-scaling = 7 benches x 20 reps in parallel.
# REPEATS submissions in a row -> N x 20 reps per (bench, knob, level).
#
# Default REPEATS=3 -> 60 reps per bench. Use REPEATS=5 for 100 reps (matches
# the prod 350-node single-shot statistical resolution, but with the safety of
# multiple smaller jobs instead of one big one).
#
# Usage:
#   ./scripts/submit_phase0_scaling_repeat.sh
#   REPEATS=5 ./scripts/submit_phase0_scaling_repeat.sh
#   DRY_RUN=1 ./scripts/submit_phase0_scaling_repeat.sh         # preview
#   NODES_PER_BENCH=10 ./scripts/submit_phase0_scaling_repeat.sh # halve nodes
#   APPLY_CONTROLS=0 ./scripts/submit_phase0_scaling_repeat.sh   # baseline only
#
# Env overrides:

set -euo pipefail

: "${REPEATS:=3}"
: "${QUEUE:=debug-scaling}"
: "${ACCOUNT:=UIC-HPC}"
: "${WALLTIME:=01:00:00}"
: "${SELECT:=140}"            # 7 benches x 20 = 140
: "${VARIANT:=all_tiles_15s}"
: "${APPLY_CONTROLS:=1}"
: "${GEOPM_MONITOR:=1}"
: "${GEOPM_PERIOD:=0.05}"
: "${MAX_CELLS:=}"
: "${NODES_PER_BENCH:=20}"
: "${BENCH_LIST:=}"
: "${POLL_SECONDS:=30}"
: "${PBS_SCRIPT:=scripts/submit_phase0_scaling.pbs}"
: "${DRY_RUN:=0}"

echo "Repeating ${REPEATS} submissions of ${PBS_SCRIPT}"
echo "Settings:"
echo "  QUEUE=${QUEUE}  ACCOUNT=${ACCOUNT}  WALLTIME=${WALLTIME}  SELECT=${SELECT}"
echo "  VARIANT=${VARIANT}  APPLY_CONTROLS=${APPLY_CONTROLS}  GEOPM_MONITOR=${GEOPM_MONITOR}"
echo "  GEOPM_PERIOD=${GEOPM_PERIOD}  MAX_CELLS=${MAX_CELLS:-<unset>}"
echo "  NODES_PER_BENCH=${NODES_PER_BENCH}  BENCH_LIST=${BENCH_LIST:-<default>}"
echo "  POLL_SECONDS=${POLL_SECONDS}  DRY_RUN=${DRY_RUN}"
echo

if ! command -v qsub >/dev/null 2>&1; then
    echo "ERROR: qsub not on PATH. Run from an Aurora login node." >&2
    exit 1
fi

VARS="VARIANT=${VARIANT},APPLY_CONTROLS=${APPLY_CONTROLS},GEOPM_MONITOR=${GEOPM_MONITOR},GEOPM_PERIOD=${GEOPM_PERIOD},NODES_PER_BENCH=${NODES_PER_BENCH}"
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
    printf '  iter %d  ->  %s  ->  results/%s/\n' "$((i+1))" "${JOBIDS[$i]}" "${JOBIDS[$i]%%.*}"
done

echo
echo "Aggregate everything (mean/median/std across all reps):"
echo "  ./analysis/scripts/summarize_phase0_knobs.sh experiments/phase1/*/runs"
echo "  /usr/bin/python3.10 analysis/scripts/summarize_by_control.py"
echo "  /usr/bin/python3.10 analysis/scripts/plot_response_curves.py"
