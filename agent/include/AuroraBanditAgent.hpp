// AuroraBanditAgent.hpp
//
// Public class declaration for the unified Aurora GEOPM agent.
// Contract: agent/SKELETON.md
// Spec:     docs/agent-design.md
// Priors:   analysis/agent_suggestions.md

#pragma once

#include <cstdint>
#include <functional>
#include <map>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "geopm/Agent.hpp"
#include "geopm/PlatformIO.hpp"
#include "geopm/PlatformTopo.hpp"

namespace aurora_bandit {

class FeatureExtractor;
class ActionGrid;
class LinUCB;
class MinControlGuard;

// One batched control write: PIO batch index + identity + last value.
// Pattern lifted from power_tree_agent.cpp.
struct BatchControl {
    int batch_idx = -1;
    int domain_type = GEOPM_DOMAIN_INVALID;
    int domain_idx = -1;
    std::string name;
    double last_setting = NAN;
    bool   readback_failed = false;   // set true if write-readback check failed
};

class AuroraBanditAgent : public geopm::Agent {
public:
    // ----- Policy fields (must match policy_names() order) -----
    enum policy_e {
        M_POLICY_POWER_CAP_WATTS,        // 0 = no cap; >0 = informational normalizer
        M_POLICY_RUNTIME_SLACK,          // ε in runtime ≤ (1+ε)·baseline
        M_POLICY_PERF_ENERGY_BIAS,       // Lagrangian weight (0=energy, 1=perf)
        M_POLICY_UCB_ALPHA,              // LinUCB exploration constant
        M_POLICY_LOG_DECISIONS,          // 0/1 — emit per-tick decision in trace
        M_NUM_POLICY
    };

    // ----- Sample fields aggregated up the tree (telemetry only in v1) -----
    enum sample_e {
        M_SAMPLE_NODE_COUNT,
        M_SAMPLE_BOARD_POWER_W,
        M_SAMPLE_LAST_ARM_IDX,
        M_SAMPLE_LAST_REWARD,
        M_SAMPLE_RUNTIME_SLACK_USED,     // (elapsed - baseline) / baseline
        M_NUM_SAMPLE
    };

    // ----- Per-tick trace columns (geopm-trace CSV) -----
    enum trace_e {
        M_TRACE_ARM_IDX,
        M_TRACE_UCB_SCORE,
        M_TRACE_BOARD_POWER_W,
        M_TRACE_CPU_FREQ_HZ,
        M_TRACE_GPU_FREQ_HZ,
        M_TRACE_ENERGY_DELTA_J,
        M_TRACE_RUNTIME_DELTA_S,
        M_NUM_TRACE
    };

    AuroraBanditAgent();
    AuroraBanditAgent(geopm::PlatformIO &platform_io,
                      const geopm::PlatformTopo &platform_topo,
                      double period_sec);
    virtual ~AuroraBanditAgent();

    // ----- GEOPM plugin identity -----
    static std::string plugin_name();
    static std::unique_ptr<geopm::Agent> make_plugin();
    static std::vector<std::string> policy_names();
    static std::vector<std::string> sample_names();

    // ----- Agent overrides -----
    void init(int level, const std::vector<int> &fan_in, bool is_level_root) override;
    void validate_policy(std::vector<double> &policy) const override;

    void split_policy(const std::vector<double> &in_policy,
                      std::vector<std::vector<double>> &out_policy) override;
    bool do_send_policy() const override;
    void aggregate_sample(const std::vector<std::vector<double>> &in_sample,
                          std::vector<double> &out_sample) override;
    bool do_send_sample() const override;

    void adjust_platform(const std::vector<double> &in_policy) override;
    bool do_write_batch() const override;
    void sample_platform(std::vector<double> &out_sample) override;
    void wait() override;

    std::vector<std::pair<std::string, std::string>> report_header() const override;
    std::vector<std::pair<std::string, std::string>> report_host() const override;
    std::map<uint64_t, std::vector<std::pair<std::string, std::string>>>
        report_region() const override;

    std::vector<std::string> trace_names() const override;
    std::vector<std::function<std::string(double)>> trace_formats() const override;
    void trace_values(std::vector<double> &values) override;

    void enforce_policy(const std::vector<double> &policy) const override;

private:
    // ----- Helpers -----
    void apply_arm(int arm_idx);
    double compute_reward();
    void log(const std::string &msg) const;
    bool should_log(uint64_t count) const;
    bool safety_tripwire_active() const;

    geopm::PlatformIO        &m_platform_io;
    const geopm::PlatformTopo &m_platform_topo;
    double                    m_period;

    // Tree state
    int                       m_level = -1;
    bool                      m_is_level_root = false;
    int                       m_num_children = 0;
    bool                      m_do_send_policy = true;
    bool                      m_do_send_sample = true;
    bool                      m_do_write_batch = false;

    // Policy snapshot
    std::vector<double>       m_last_policy;
    std::vector<double>       m_last_sample;

    // Components
    std::unique_ptr<FeatureExtractor> m_features;
    std::unique_ptr<ActionGrid>       m_actions;
    std::unique_ptr<LinUCB>           m_bandit;
    std::unique_ptr<MinControlGuard>  m_min_guard;

    // Live control writes: one BatchControl per (control name × instance).
    std::vector<BatchControl> m_controls;

    // Per-tick decision state
    std::vector<double>       m_last_x;            // feature vector (size d)
    int                       m_last_arm_idx = -1;
    double                    m_last_ucb_score = NAN;
    double                    m_baseline_energy_J = NAN;
    double                    m_baseline_runtime_s = NAN;
    double                    m_elapsed_s = 0.0;
    double                    m_last_reward = NAN;
    double                    m_last_board_power_w = NAN;
    bool                      m_safety_tripped = false;

    // Debug
    bool                      m_verbose = false;
    bool                      m_controls_enabled = true;
    int                       m_log_stride = 50;
    uint64_t                  m_tick_count = 0;
};

} // namespace aurora_bandit
