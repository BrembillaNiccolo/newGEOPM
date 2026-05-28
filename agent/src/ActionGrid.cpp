// ActionGrid.cpp
// Default arm set encodes the Phase 0 per-class winners from
// analysis/agent_suggestions.md §3. JSON loader is a stub for v1; the
// production loader will use a real JSON library (rapidjson or nlohmann).

#include "ActionGrid.hpp"

#include <cstddef>
#include <fstream>
#include <sstream>

namespace aurora_bandit {

// Aurora Xeon Max + PVC verified-binding levels (results/8509922/knob_verification.txt).
// Comments cite the per-class best-safe knob from analysis/results.md headline table.
void ActionGrid::load_default() {
    m_arms.clear();
    m_arms.reserve(8);

    // Arm 0: hardware default — every freq cap at hardware MAX, no power cap.
    // Used as cold-start and as fallback when safety tripwire fires.
    m_arms.push_back({"all_max", {}, "unknown"});

    // Arm 1: HBM streaming / memory-bound (winner on stream).
    //  CPU=1.0 GHz, UNCORE=2.3 GHz (keep uncore high — memory mesh),
    //  GPU=0.4 GHz (idle).  Phase 0: stream -68% energy at +0.3% runtime.
    m_arms.push_back({"memory_bound_save", {
        {"CPU_FREQUENCY_MAX_CONTROL",         1.0e9},
        {"CPU_UNCORE_FREQUENCY_MAX_CONTROL",  2.3e9},
        {"GPU_CORE_FREQUENCY_MAX_CONTROL",    0.4e9},
        {"LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL", 0.0},
    }, "memory_bound"});

    // Arm 2: GPU compute-bound (winner-shape for dgemm-gpu/babelstream).
    //  CPU=MAX (3.5 GHz), UNCORE=MAX (2.3 GHz), GPU=MAX, PERF_F=0.0.
    //  Phase 1.5 update: was CPU=2.0/UNCORE=1.6 GHz; that hurt dgemm-gpu by
    //  +27% runtime because GPU benches still need CPU at MAX for kernel
    //  dispatch over MPI.
    //  Phase 1.5c update: PERF_FACTOR was 1.0; flipped to 0.0. Block D
    //  showed PF=1 at GPU=MAX HURTS dgemm-gpu by +14% energy and +21%
    //  runtime — PF=0 (memory-bias) feeds the compute units instead of
    //  starving them. With PF=0 + everything at MAX, A2 is now nearly
    //  identical to A0 (only the explicit PF setting differs); kept for
    //  traceability and as a contextual hedge.
    m_arms.push_back({"gpu_compute_max", {
        {"CPU_FREQUENCY_MAX_CONTROL",         3.5e9},
        {"CPU_UNCORE_FREQUENCY_MAX_CONTROL",  2.3e9},
        {"GPU_CORE_FREQUENCY_MAX_CONTROL",    1.6e9},
        {"LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL", 0.0},
    }, "gpu_compute"});

    // Arm 3: CPU compute-bound (winner on cpu-dgemm).
    //  CPU=MAX, UNCORE=1.2 GHz (the big win, -16%), GPU/PERF_F = idle.
    m_arms.push_back({"cpu_compute_uncore_save", {
        {"CPU_FREQUENCY_MAX_CONTROL",         3.5e9},
        {"CPU_UNCORE_FREQUENCY_MAX_CONTROL",  1.2e9},
        {"GPU_CORE_FREQUENCY_MAX_CONTROL",    0.4e9},
        {"LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL", 0.25},
    }, "cpu_compute"});

    // Arm 4: comm/wait-dominated (winner on mpi-idle-wait).
    //  CPU=1.0 GHz, UNCORE=0.8 GHz, GPU=0.4 GHz.
    //  Phase 1.5c: PERF_FACTOR was 0.0; flipped to 1.0. Block D showed
    //  PF=1 at GPU=0.4 saves 19% MORE energy on mpi-idle-wait — PF=1 keeps
    //  the small amount of GPU work at high clock so it finishes faster.
    //  Phase 1.5d: CPU_POWER_LIMIT_CONTROL=175W was dropped. Block E showed
    //  CPU_PL is redundant with CPU_FREQ=1.0 GHz on 5/6 benches (|diff|
    //  ≤ 1.7%) and CATASTROPHIC on cpu-dgemm (+338% energy). Removing it
    //  simplifies the arm and eliminates the cpu-dgemm risk.
    m_arms.push_back({"comm_wait_save", {
        {"CPU_FREQUENCY_MAX_CONTROL",         1.0e9},
        {"CPU_UNCORE_FREQUENCY_MAX_CONTROL",  0.8e9},
        {"GPU_CORE_FREQUENCY_MAX_CONTROL",    0.4e9},
        {"LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL", 1.0},
    }, "comm_wait"});

    // Arm 5: comm collective (osu-like) — CPU must stay MAX; GPU can cap.
    //  Phase 0: GPU_FREQ_MAX safely yields -10.7% on osu; CPU caps are
    //  catastrophic (+919% runtime). DON'T touch CPU.
    //  Phase 1.5 UPGRADE: this arm is the UNIVERSAL SAFE SAVE — gives -13 to
    //  -28% energy on 5 of 7 benches (stream, cpu-dgemm, gpu-bursty-idle,
    //  mpi-idle-wait, osu) at <5% runtime cost. Only fails on babelstream/
    //  dgemm-gpu where all non-baseline arms fail. The agent should use this
    //  as the cold-start default in always-on mode; A0 (all_max) only as the
    //  safety fallback when the runtime tripwire fires.
    //  Phase 1.5c: PERF_FACTOR was 0.0; flipped to 1.0. Block D shows PF=1
    //  at GPU=0.4 saves 9% more on osu and 16% more on stream — both this
    //  arm's targets.
    m_arms.push_back({"comm_collective_safe", {
        {"CPU_FREQUENCY_MAX_CONTROL",         3.5e9},
        {"CPU_UNCORE_FREQUENCY_MAX_CONTROL",  2.3e9},
        {"GPU_CORE_FREQUENCY_MAX_CONTROL",    0.4e9},
        {"LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL", 1.0},
    }, "comm_collective"});

    // Arm 6: bursty GPU + idle gaps.
    //  Phase 1.5 status: DOMINATED. On gpu-bursty-idle A6 gave −43% energy vs
    //  A4's −53%; on mpi-idle-wait −45% vs A4's −70%. Keep the entry in the
    //  C++ grid for traceability but mark inactive — LinUCB will see it but
    //  the agent's select() should skip arms whose class_hint=="_inactive".
    //  Reactivate after Phase 1.5b Block C/D/E data lands and we know whether
    //  the bursty-detection feature would prefer A6 in some workload regime
    //  that we haven't sampled yet.
    m_arms.push_back({"bursty_gpu_idle", {
        {"CPU_FREQUENCY_MAX_CONTROL",         1.6e9},
        {"CPU_UNCORE_FREQUENCY_MAX_CONTROL",  1.6e9},
        {"GPU_CORE_FREQUENCY_MAX_CONTROL",    0.4e9},
        {"LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL", 0.0},
    }, "_inactive"});

    // Arm 7: aggressive_save — deep cap regime; all knobs near floor.
    //  Use only when policy.runtime_slack is large or under tight power cap.
    //  Phase 1.5b: the (CPU=1.0 + UNCORE=0.8) combination is a compound
    //  bottleneck — cpu-dgemm sees +76% runtime vs the +38% predicted from
    //  single-knob priors. The AuroraBanditAgent::adjust filter penalizes
    //  this arm (same as A4) when cpu_power_frac > 0.5.
    //  Phase 1.5c: PERF_FACTOR was 0.0; flipped to 1.0 (same Block D rationale).
    //  Phase 1.5d: CPU_POWER_LIMIT=105W kept. Block E only tested PL=175W
    //  redundancy. PL=105W (30% TDP) is more aggressive and may still bind
    //  even at CPU=1.0 GHz — keep until directly tested. The PL=105W also
    //  distinguishes A7 from A4 (which has no PL write after Phase 1.5d).
    m_arms.push_back({"aggressive_save", {
        {"CPU_FREQUENCY_MAX_CONTROL",         1.0e9},
        {"CPU_UNCORE_FREQUENCY_MAX_CONTROL",  0.8e9},
        {"GPU_CORE_FREQUENCY_MAX_CONTROL",    0.4e9},
        {"LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL", 1.0},
        {"CPU_POWER_LIMIT_CONTROL",           105.0},  // ≈30% of default 350 W
    }, "aggressive"});
}

bool ActionGrid::load(const std::string &path) {
    if (path.empty()) {
        load_default();
        return true;
    }

    // TODO(phase2): parse JSON via rapidjson / nlohmann::json.
    // For v1 skeleton: refuse, fall back to default. The default grid is the
    // Phase 0 winners and is the right shipping default anyway.
    std::ifstream f(path);
    if (!f.good()) {
        load_default();
        return false;
    }

    load_default();
    return false;  // signals to caller "JSON parsing not implemented yet"
}

const std::vector<ControlWrite> &ActionGrid::resolve(int arm_idx) const {
    if (arm_idx < 0 || static_cast<size_t>(arm_idx) >= m_arms.size()) {
        return m_empty;
    }
    return m_arms[static_cast<size_t>(arm_idx)].controls;
}

int ActionGrid::find(const std::string &name) const {
    for (size_t i = 0; i < m_arms.size(); ++i) {
        if (m_arms[i].name == name) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

} // namespace aurora_bandit
