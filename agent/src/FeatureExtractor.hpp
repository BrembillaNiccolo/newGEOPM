// FeatureExtractor.hpp
//
// Pushes PIO signals at agent init and assembles the d=11 feature vector
// described in docs/agent-design.md §State. Implements the signal-name
// fallback chain (CPU_POWER → MSR aliases, etc.) so the agent degrades
// cleanly on stacks where a signal is missing.

#pragma once

#include <cmath>
#include <cstddef>
#include <string>
#include <vector>

#include "geopm/PlatformIO.hpp"
#include "geopm/PlatformTopo.hpp"

namespace aurora_bandit {

struct BatchSignal {
    int batch_idx = -1;
    int domain_type = GEOPM_DOMAIN_INVALID;
    int domain_idx = -1;
    std::string name;
    double value = NAN;
};

class FeatureExtractor {
public:
    // Indices into the feature vector returned by extract().
    enum feat_e {
        F_BOARD_POWER_FRAC,        // BOARD_POWER / power_cap_watts (or 1.0 if unset)
        F_GPU_ACTIVITY_AVG,        // mean GPU_CORE_ACTIVITY across tiles
        F_GPU_POWER_FRAC,          // sum GPU_POWER / sum GPU_POWER_LIMIT_DEFAULT
        F_GPU_FREQ_NORMALIZED,     // mean GPU_CORE_FREQUENCY_STATUS / max-avail
        F_CPU_POWER_FRAC,          // sum CPU_POWER / sum CPU_POWER_LIMIT_DEFAULT
        F_CPU_FREQ_NORMALIZED,     // mean CPU_FREQUENCY_STATUS / max
        F_UNCORE_FREQ_NORMALIZED,  // mean CPU_UNCORE_FREQUENCY_STATUS / max
        F_DRAM_POWER_FRAC,         // DRAM_POWER / DRAM_POWER_LIMIT_DEFAULT
        F_GPU_ACTIVITY_VARIANCE,   // detects bursty class
        F_MPI_WAIT_FRAC,           // 1 - cpu_busy_fraction proxy
        F_THROTTLE_BITSET,         // 0/1 if any tile reports THERMAL throttle
        N_FEATURES
    };

    FeatureExtractor(geopm::PlatformIO &platform_io,
                     const geopm::PlatformTopo &platform_topo);

    // Push signals onto the PIO batch. Must be called from agent init().
    void push_signals();

    // Sample latest batch values; build and return the feature vector.
    // power_cap_watts is from policy.power_cap_watts; 0 means use board default.
    std::vector<double> extract(double power_cap_watts);

    // For reporting
    int n_signals() const;
    int n_features() const { return N_FEATURES; }

    // Raw access for the agent's reward computation.
    double last_board_power_w() const { return m_last_board_power; }
    double last_board_energy_j() const { return m_last_board_energy; }

private:
    void push_first_signal_group(const std::vector<std::string> &candidate_names,
                                 std::vector<BatchSignal> &out);
    void push_all_signals(const std::string &name, int domain_type,
                          std::vector<BatchSignal> &out);
    void sample_group(std::vector<BatchSignal> &group);
    double sum(const std::vector<BatchSignal> &g) const;
    double mean(const std::vector<BatchSignal> &g, double fallback) const;
    double variance(const std::vector<BatchSignal> &g) const;

    geopm::PlatformIO         &m_pio;
    const geopm::PlatformTopo &m_topo;

    // Signal groups (each group is multi-instance across its native domain).
    std::vector<BatchSignal> m_board_power;
    std::vector<BatchSignal> m_board_energy;
    std::vector<BatchSignal> m_gpu_activity;
    std::vector<BatchSignal> m_gpu_power;
    std::vector<BatchSignal> m_gpu_freq;
    std::vector<BatchSignal> m_cpu_power;
    std::vector<BatchSignal> m_cpu_freq;
    std::vector<BatchSignal> m_uncore_freq;
    std::vector<BatchSignal> m_dram_power;
    std::vector<BatchSignal> m_gpu_throttle;

    // Defaults (read once during push_signals()).
    double m_gpu_power_limit_default = NAN;
    double m_cpu_power_limit_default = NAN;
    double m_dram_power_limit_default = NAN;
    double m_gpu_freq_max_avail = NAN;
    double m_cpu_freq_max_avail = NAN;
    double m_uncore_freq_max_avail = NAN;

    // Cache for reward computation.
    double m_last_board_power = NAN;
    double m_last_board_energy = NAN;
};

} // namespace aurora_bandit
