# Open questions — verify on Aurora before relying on these

These come from gaps in the public GEOPM documentation. **Resolve each as the first task of Phase 1**, on a single interactive node, before launching any sweeps. Each question lists the verification command and what to do based on the result.

---

## Q1. Is `DRAM_POWER_LIMIT_CONTROL` writable on Xeon Max?

**Verify**:
```bash
geopmwrite --info DRAM_POWER_LIMIT_CONTROL
geopmwrite DRAM_POWER_LIMIT_CONTROL memory 0 100   # try a safe value
geopmread DRAM_POWER_LIMIT_CONTROL memory 0        # read back
```

**Outcome**:
- Writable → add a 5-level sweep to Phase 1 sweep design (`docs/phase1-sweep-design.md`).
- Not writable → drop from agent action grid; don't waste sweep time.

## Q2. Are HBM-specific RAPL zones exposed beyond the standard DRAM domain?

**Verify**:
```bash
geopmread --info-all | grep -i hbm
geopmread --info-all | grep -i dram
# Also check sysfs powercap directly:
ls /sys/class/powercap/
```

**Outcome**:
- Separate HBM zone → log it as a distinct feature in the agent's state vector.
- Standard DRAM only → `DRAM_POWER` includes HBM; document this in `docs/geopm-aurora.md`.

## Q3. Is `DRM::HWMON::POWER1_MAX` (GPU per-card power cap) writable by ordinary users?

**Verify**:
```bash
geopmwrite --info DRM::HWMON::POWER1_MAX
geopmwrite DRM::HWMON::POWER1_MAX gpu 0 250   # set first card to 250W
geopmread DRM::HWMON::POWER1_MAX gpu 0
```

**Outcome**:
- Writable to user → straightforward.
- Requires root / GEOPM systemd service → request access from ALCF support; flag as scheduling constraint for Phase 1 sweep runs and Phase 3 cap experiments.

## Q4. Which IOGroup wins for aliased signals (e.g. `GPU_ENERGY` — LevelZero vs DRM-sysfs)?

**Verify**:
```bash
geopmread --info GPU_ENERGY
# Look for "Provided by: LEVELZERO" or "Provided by: DRM"
geopmread --info GPU_POWER
```

**Outcome**: document the actual provider in `docs/geopm-aurora.md` and in the agent's feature documentation — different providers have different sampling latencies.

## Q5. Do `REGION_RUNTIME` / `EPOCH_RUNTIME` / `REGION_COUNT` exist as PIO signals on the installed version?

**Verify**:
```bash
geopmread --info REGION_RUNTIME 2>&1 | head
geopmread --info EPOCH_RUNTIME 2>&1 | head
geopmread --info REGION_COUNT 2>&1 | head
```

**Outcome**:
- Present → use directly in agent state.
- Absent → derive in the agent from `REGION_HASH` + `TIME` deltas; document the derivation in `docs/agent-design.md`.

## Q6. Is SST-CP enabled in BIOS?

**Verify**:
```bash
geopmread --info SST::COREPRIORITY_ENABLE 2>&1 | head
geopmread SST::COREPRIORITY_ENABLE package 0
```

**Outcome**:
- Enabled → consider adding SST-CP arms (deprioritize MPI-waiting cores) to action grid for comm-bound class.
- Disabled → drop SST from scope; revisit if BIOS change negotiable with ALCF.

## Q7. GEOPM version installed on Aurora?

**Verify**:
```bash
module avail geopm
module load geopm/<version>
geopmread --version
geopmagent --help | head
```

**Outcome**: pin our agent against this version's headers; record version in `docs/geopm-aurora.md` and `docs/agent-design.md`.

## Q8. Are all 6 PVCs visible from a single MPI rank, or are they partitioned per rank?

**Verify**:
```bash
geopmread --info-all | grep -c "gpu="     # how many gpu domains
geopmread --info-all | grep -c "gpu_chip="  # how many tile domains (should be 2× gpu)
```

**Outcome**: shapes how the agent counts cards/tiles when computing aggregate features. Document in `docs/agent-design.md`.

## Q9. What is `CPU_POWER_LIMIT_DEFAULT` on Aurora Xeon Max?

**Verify**:
```bash
geopmread CPU_POWER_LIMIT_DEFAULT package 0
geopmread CPU_POWER_LIMIT_DEFAULT package 1
geopmread MSR::PKG_POWER_INFO:THERMAL_SPEC_POWER package 0
```

**Outcome**: anchors all "% of PL1" sweep levels in Phase 1.

## Q10. What is `GPU_POWER_LIMIT_DEFAULT` per PVC?

**Verify**:
```bash
for i in 0 1 2 3 4 5; do
  geopmread GPU_POWER_LIMIT_DEFAULT gpu $i
  geopmread GPU_POWER_LIMIT_MAX_AVAIL gpu $i
done
```

**Outcome**: anchors GPU cap sweep + Phase 3 budget split.

---

## Resolution log

Append a row each time a question is resolved:

| Date | Q# | Resolution | Doc updated |
|------|----|-----------|-------------|
| 2026-05-20 | Q1 | `DRAM_POWER_LIMIT_CONTROL` is writable on Xeon Max (confirmed via `docs/signals_and_controls/geopm_research_strict_controls (1).md`). Added to Phase 1 sweep. | `geopm-aurora.md`, `phase1-sweep-design.md` |
| 2026-05-20 | Q3 | No writable GPU power cap exists in this Aurora build — neither `GPU_POWER_LIMIT_CONTROL` (LevelZero) nor `DRM::HWMON::POWER1_MAX` (sysfs) appear in writable controls. Strategy switched to indirect GPU capping via `BOARD_POWER_LIMIT_CONTROL` + `CPU_POWER_LIMIT_CONTROL` + `DRAM_POWER_LIMIT_CONTROL` + `GPU_CORE_FREQUENCY_MAX_CONTROL`. | `geopm-aurora.md`, `agent-design.md`, `phase1-sweep-design.md`, `phase3-cap-design.md` |
| 2026-05-20 | Q5 | `REGION_RUNTIME` / `EPOCH_RUNTIME` / `REGION_COUNT` are NOT in the strict signal list. Derive from `TIME` + region boundaries inside the agent. | `geopm-aurora.md`, `agent-design.md` |
| 2026-05-20 | Q6 | SST-CP is enabled and fully exposed (4 priority levels with per-level freq min/max/priority writable). Deferred to Phase 1 v2 (single-knob effects first). | `geopm-aurora.md`, `phase1-sweep-design.md` |

## New questions raised by the signals/controls dump

| Q# | Question | How to verify |
|----|----------|--------------|
| Q11 | Does writing `BOARD_POWER_LIMIT_CONTROL` require root / GEOPM systemd service? | `geopmwrite BOARD_POWER_LIMIT_CONTROL board 0 4000` from a normal interactive job; observe success vs permission error. |
| Q12 | What is the **default** value of `BOARD_POWER_LIMIT_CONTROL` on Aurora? Anchors 3000 W cap as a fraction of total node TDP. | `geopmread BOARD_POWER_LIMIT_CONTROL board 0` before any agent runs. |
| Q13 | Does `CPU_INSTRUCTIONS_RETIRED` require `geopmwrite -e` once before reading? Documented yes; verify behavior. | `geopmread CPU_INSTRUCTIONS_RETIRED cpu 0` — if 0/NaN, run `geopmwrite -e` and re-read. |
| Q14 | Does `LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL` actually take writes on Aurora's PVC driver? | Write 0.0 and 1.0; read back. If readback doesn't change, mark unusable. |
| Q15 | Domain enumeration on a node: how many `board`, `package`, `gpu`, `gpu_chip`, `core`, `cpu` instances? | `geopmread --domain board` etc. Expect 1/2/6/12/~104/~208. |
