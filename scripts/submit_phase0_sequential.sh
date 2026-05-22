#!/usr/bin/env bash
# Submit Phase-0 smoke jobs one at a time, waiting for each to leave the queue
# before submitting the next. Use when the queue allows only one job at a time.
#
# Usage:
#   ./scripts/submit_phase0_sequential.sh                                       # all 7 benches
#   ./scripts/submit_phase0_sequential.sh cpu-dgemm stream                      # only these
#   KNOB=CPU_FREQUENCY_MAX_CONTROL ./scripts/submit_phase0_sequential.sh        # different knob
#   KNOB= APPLY_CONTROLS=1 ./scripts/submit_phase0_sequential.sh                # full sweep (all knobs)
#   WALLTIME=00:30:00 ./scripts/submit_phase0_sequential.sh                     # longer cells
#   POLL_SECONDS=30 ./scripts/submit_phase0_sequential.sh                       # check qstat less often
#
# Env overrides (defaults below):

set -euo pipefail

: "${QUEUE:=debug}"
: "${ACCOUNT:=UIC-HPC}"
: "${WALLTIME:=00:05:00}"
: "${VARIANT:=all_tiles_15s}"   # GPU benches use all 12 tiles; CPU/MPI benches see this as a smoke_15s alias
: "${APPLY_CONTROLS:=1}"
: "${GEOPM_MONITOR:=1}"
: "${KNOB:=BOARD_POWER_LIMIT_CONTROL}"   # set KNOB= (empty) to sweep ALL strict knobs
: "${LEVEL:=}"                            # single-level filter, e.g. lit_3000W
: "${MAX_CELLS:=}"
: "${POLL_SECONDS:=15}"
: "${PBS_SCRIPT:=scripts/submit_phase0.pbs}"

DEFAULT_BENCHES=(cpu-dgemm stream dgemm-gpu babelstream osu mpi-idle-wait gpu-bursty-idle)
if (( $# > 0 )); then
    BENCHES=("$@")
else
    BENCHES=("${DEFAULT_BENCHES[@]}")
fi

echo "Sequentially submitting ${#BENCHES[@]} job(s):"
printf '  %s\n' "${BENCHES[@]}"
echo "Settings:"
echo "  QUEUE=${QUEUE}  ACCOUNT=${ACCOUNT}  WALLTIME=${WALLTIME}  VARIANT=${VARIANT}"
echo "  APPLY_CONTROLS=${APPLY_CONTROLS}  GEOPM_MONITOR=${GEOPM_MONITOR}"
echo "  KNOB=${KNOB:-<all>}  LEVEL=${LEVEL:-<all>}  MAX_CELLS=${MAX_CELLS:-<unset>}"
echo "  POLL_SECONDS=${POLL_SECONDS}  PBS_SCRIPT=${PBS_SCRIPT}"
echo

if ! command -v qsub >/dev/null 2>&1; then
    echo "ERROR: qsub not on PATH. Run this from an Aurora login node." >&2
    exit 1
fi

JOBIDS=()
for B in "${BENCHES[@]}"; do
    echo "[$(date +%H:%M:%S)] submitting ${B}"

    # Build -v list (no spaces, no nested quotes -- avoids shell parsing bugs)
    VARS="BENCH=${B},VARIANT=${VARIANT},APPLY_CONTROLS=${APPLY_CONTROLS},GEOPM_MONITOR=${GEOPM_MONITOR}"
    [[ -n "${KNOB}" ]]      && VARS+=",KNOB=${KNOB}"
    [[ -n "${LEVEL}" ]]     && VARS+=",LEVEL=${LEVEL}"
    [[ -n "${MAX_CELLS}" ]] && VARS+=",MAX_CELLS=${MAX_CELLS}"

    JOBID=$(qsub -q "${QUEUE}" -A "${ACCOUNT}" -l walltime="${WALLTIME}" -v "${VARS}" "${PBS_SCRIPT}")
    echo "  jobid: ${JOBID}"
    JOBIDS+=("${JOBID}")

    # Poll qstat until the job is no longer known (i.e., it finished or was cancelled)
    while qstat "${JOBID}" >/dev/null 2>&1; do
        STATE=$(qstat "${JOBID}" 2>/dev/null | awk 'NR>=3 && $1 ~ /^[0-9]/ {print $5; exit}')
        QUEUE_NOW=$(qstat "${JOBID}" 2>/dev/null | awk 'NR>=3 && $1 ~ /^[0-9]/ {print $6; exit}')
        printf '  [%s] %s (%s) state=%s queue=%s\n' "$(date +%H:%M:%S)" "${B}" "${JOBID}" "${STATE:-?}" "${QUEUE_NOW:-?}"
        sleep "${POLL_SECONDS}"
    done
    echo "  [$(date +%H:%M:%S)] ${B} (${JOBID}) finished"
    echo
done

echo "=========================================="
echo "All ${#BENCHES[@]} job(s) submitted and finished."
echo "=========================================="
for i in "${!BENCHES[@]}"; do
    printf '  %-18s  %s  ->  results/%s/\n' "${BENCHES[$i]}" "${JOBIDS[$i]}" "${JOBIDS[$i]}"
done
echo
echo "Aggregate everything:"
echo "  ./analysis/scripts/summarize_phase0_knobs.sh experiments/phase1/*/runs"
