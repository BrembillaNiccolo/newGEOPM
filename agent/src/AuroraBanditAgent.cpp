// AuroraBanditAgent.cpp
//
// Main agent orchestration: init/sample/adjust loop.
// Contract: agent/SKELETON.md
// Spec:     docs/agent-design.md
// Priors:   analysis/agent_suggestions.md
//
// Plugin registration is at the bottom of this file (__attribute__((constructor))).

#include "AuroraBanditAgent.hpp"

#include <algorithm>
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <thread>

#include "geopm/Exception.hpp"
#include "geopm/Helper.hpp"
#include "geopm/PlatformIO.hpp"
#include "geopm/PlatformIOProf.hpp"
#include "geopm/PlatformTopo.hpp"
#include "geopm/PluginFactory.hpp"

#include "ActionGrid.hpp"
#include "FeatureExtractor.hpp"
#include "LinUCB.hpp"
#include "MinControlGuard.hpp"

namespace aurora_bandit {

namespace {

constexpr double DEFAULT_PERIOD_S = 0.020;   // 20 ms

double wait_period_from_env() {
    const char *p = std::getenv("GEOPM_PERIOD");
    if (p == nullptr || p[0] == '\0') return DEFAULT_PERIOD_S;
    char *end = nullptr;
    double v = std::strtod(p, &end);
    return (end == p || !std::isfinite(v) || v <= 0.0) ? DEFAULT_PERIOD_S : v;
}

bool env_flag(const char *name, bool dflt) {
    const char *v = std::getenv(name);
    if (v == nullptr || v[0] == '\0') return dflt;
    std::string s(v);
    std::transform(s.begin(), s.end(), s.begin(),
                   [](unsigned char c) { return (char)std::tolower(c); });
    return !(s == "0" || s == "false" || s == "no" || s == "off");
}

std::string format_double(double v) {
    if (std::isnan(v)) return "nan";
    std::ostringstream os; os << v; return os.str();
}

void set_default_if_nan(double &v, double d) {
    if (std::isnan(v)) v = d;
}

bool finite(double v) { return std::isfinite(v); }

} // namespace

// ===== Constructors / dtor =====

AuroraBanditAgent::AuroraBanditAgent()
    : AuroraBanditAgent(geopm::PlatformIOProf::platform_io(),
                        geopm::platform_topo(),
                        wait_period_from_env())
{}

AuroraBanditAgent::AuroraBanditAgent(geopm::PlatformIO &platform_io,
                                     const geopm::PlatformTopo &platform_topo,
                                     double period_sec)
    : m_platform_io(platform_io)
    , m_platform_topo(platform_topo)
    , m_period(period_sec)
{}

AuroraBanditAgent::~AuroraBanditAgent() {
    // ~MinControlGuard restores originals via its dtor.
}

// ===== Plugin identity =====

std::string AuroraBanditAgent::plugin_name() {
    return "aurora_bandit";
}

std::unique_ptr<geopm::Agent> AuroraBanditAgent::make_plugin() {
    return geopm::make_unique<AuroraBanditAgent>();
}

std::vector<std::string> AuroraBanditAgent::policy_names() {
    return {
        "POWER_CAP_WATTS",
        "RUNTIME_SLACK",
        "PERF_ENERGY_BIAS",
        "UCB_ALPHA",
        "LOG_DECISIONS"
    };
}

std::vector<std::string> AuroraBanditAgent::sample_names() {
    return {
        "NODE_COUNT",
        "BOARD_POWER_W",
        "LAST_ARM_IDX",
        "LAST_REWARD",
        "RUNTIME_SLACK_USED"
    };
}

// ===== Agent overrides =====

void AuroraBanditAgent::init(int level,
                             const std::vector<int> &fan_in,
                             bool is_level_root)
{
    if (level < 0 || level > (int)fan_in.size()) {
        throw geopm::Exception("AuroraBanditAgent::init: invalid level",
                               GEOPM_ERROR_INVALID, __FILE__, __LINE__);
    }
    m_level = level;
    m_is_level_root = is_level_root;
    m_num_children = (level == 0 ? 0 : fan_in[level - 1]);

    m_last_policy.assign(M_NUM_POLICY, NAN);
    m_last_sample.assign(M_NUM_SAMPLE, NAN);

    // Debug knobs (env-driven; same pattern as power_tree_agent).
    m_verbose          = env_flag("AURORA_BANDIT_VERBOSE", false);
    m_controls_enabled = env_flag("AURORA_BANDIT_ENABLE_CONTROLS", true);
    if (const char *stride = std::getenv("AURORA_BANDIT_LOG_STRIDE")) {
        int parsed = std::atoi(stride);
        if (parsed > 0) m_log_stride = parsed;
    }

    if (m_level != 0) {
        log("init non-leaf level=" + std::to_string(m_level) +
            " children=" + std::to_string(m_num_children));
        return;
    }

    // ----- LEAF setup -----

    // 1. Drop MIN_CONTROL floors so MAX arms can bind below the driver default.
    //    MANDATORY — without it, half the GPU_FREQ_MAX action space is silently
    //    inaccessible (Phase 0 v1 bug; see results/8509922).
    m_min_guard = std::make_unique<MinControlGuard>(m_platform_io,
                                                    m_platform_topo);
    int dropped = m_min_guard->drop_all();
    log("MinControlGuard dropped " + std::to_string(dropped) + " floors");

    // 2. Feature extractor: push PIO signals.
    m_features = std::make_unique<FeatureExtractor>(m_platform_io,
                                                    m_platform_topo);
    m_features->push_signals();
    m_last_x.assign(m_features->n_features(), 0.0);
    log("FeatureExtractor pushed " + std::to_string(m_features->n_signals()) +
        " signals, d=" + std::to_string(m_features->n_features()));

    // 3. Action grid: try policy.action_grid_path (TODO: not yet wired through
    //    the policy schema; v1 always uses built-in defaults).
    m_actions = std::make_unique<ActionGrid>();
    m_actions->load_default();
    log("ActionGrid loaded with " + std::to_string(m_actions->size()) + " arms");

    // 4. LinUCB: cold-start (warm-start file not in policy schema yet).
    m_bandit = std::make_unique<LinUCB>(m_actions->size(),
                                        m_features->n_features(),
                                        /*alpha=*/1.0, /*ridge=*/1.0);
    // Phase 1.5 update: disable arms marked class_hint=="_inactive" in the
    // grid (currently A6 bursty_gpu_idle — dominated by A4 on every safe-class
    // bench tested). The agent will reactivate them after Phase 1.5b lands
    // by removing the _inactive marker in action_grid_default.json.
    for (int a = 0; a < m_actions->size(); ++a) {
        if (m_actions->arms()[a].class_hint == "_inactive") {
            m_bandit->disable_arm(a);
            log("disabled arm " + std::to_string(a) + " (" +
                m_actions->arms()[a].name + "): marked _inactive");
        }
    }

    // 5. Pre-push every control referenced by every arm onto the batch.
    //    BatchControl stores (name, domain, instance, batch_idx, last_setting).
    if (m_controls_enabled) {
        const auto avail = m_platform_io.control_names();
        std::vector<std::string> unique_names;
        for (const auto &arm : m_actions->arms()) {
            for (const auto &cw : arm.controls) {
                if (std::find(unique_names.begin(), unique_names.end(),
                              cw.name) == unique_names.end()) {
                    unique_names.push_back(cw.name);
                }
            }
        }
        for (const auto &name : unique_names) {
            if (avail.count(name) == 0) continue;
            int dom;
            try { dom = m_platform_io.control_domain_type(name); }
            catch (const std::exception &) { continue; }
            int n = m_platform_topo.num_domain(dom);
            for (int i = 0; i < n; ++i) {
                try {
                    BatchControl bc;
                    bc.batch_idx = m_platform_io.push_control(name, dom, i);
                    bc.domain_type = dom;
                    bc.domain_idx = i;
                    bc.name = name;
                    m_controls.push_back(bc);
                }
                catch (const std::exception &ex) {
                    log("push_control failed: " + name + " idx=" +
                        std::to_string(i) + ": " + ex.what());
                }
            }
        }
        log("pushed " + std::to_string(m_controls.size()) + " control instances");
    }
}

void AuroraBanditAgent::validate_policy(std::vector<double> &policy) const {
    if (policy.size() != M_NUM_POLICY) {
        throw geopm::Exception("AuroraBanditAgent::validate_policy: wrong size",
                               GEOPM_ERROR_INVALID, __FILE__, __LINE__);
    }
    set_default_if_nan(policy[M_POLICY_POWER_CAP_WATTS],  0.0);   // 0 = no cap
    set_default_if_nan(policy[M_POLICY_RUNTIME_SLACK],    0.05);  // 5%
    set_default_if_nan(policy[M_POLICY_PERF_ENERGY_BIAS], 0.5);
    set_default_if_nan(policy[M_POLICY_UCB_ALPHA],        1.0);
    set_default_if_nan(policy[M_POLICY_LOG_DECISIONS],    1.0);

    if (policy[M_POLICY_RUNTIME_SLACK] < 0.0) {
        throw geopm::Exception("RUNTIME_SLACK must be ≥ 0",
                               GEOPM_ERROR_INVALID, __FILE__, __LINE__);
    }
    if (policy[M_POLICY_UCB_ALPHA] <= 0.0) {
        throw geopm::Exception("UCB_ALPHA must be > 0",
                               GEOPM_ERROR_INVALID, __FILE__, __LINE__);
    }
}

void AuroraBanditAgent::split_policy(const std::vector<double> &in_policy,
                                     std::vector<std::vector<double>> &out_policy) {
    // v1: pass-through. Every node gets the same policy.
    for (auto &child : out_policy) child = in_policy;
    m_do_send_policy = (in_policy != m_last_policy);
    m_last_policy = in_policy;
}

bool AuroraBanditAgent::do_send_policy() const {
    return m_do_send_policy;
}

void AuroraBanditAgent::aggregate_sample(
    const std::vector<std::vector<double>> &in_sample,
    std::vector<double> &out_sample)
{
    // v1: count nodes, sum board power, report worst-case slack used.
    out_sample.assign(M_NUM_SAMPLE, 0.0);
    double max_slack = 0.0;
    for (const auto &child : in_sample) {
        out_sample[M_SAMPLE_NODE_COUNT]    += child[M_SAMPLE_NODE_COUNT];
        out_sample[M_SAMPLE_BOARD_POWER_W] += child[M_SAMPLE_BOARD_POWER_W];
        max_slack = std::max(max_slack, child[M_SAMPLE_RUNTIME_SLACK_USED]);
    }
    out_sample[M_SAMPLE_LAST_ARM_IDX] = NAN;        // not meaningful aggregated
    out_sample[M_SAMPLE_LAST_REWARD] = NAN;
    out_sample[M_SAMPLE_RUNTIME_SLACK_USED] = max_slack;
    m_do_send_sample = (out_sample != m_last_sample);
    m_last_sample = out_sample;
}

bool AuroraBanditAgent::do_send_sample() const {
    return m_do_send_sample;
}

void AuroraBanditAgent::adjust_platform(const std::vector<double> &in_policy) {
    m_do_write_batch = false;
    if (m_level != 0 || !m_controls_enabled || !m_bandit) return;

    m_last_policy = in_policy;
    m_bandit->set_alpha(in_policy[M_POLICY_UCB_ALPHA]);

    // Safety tripwire: if we've burned past our slack budget, freeze on all_max.
    if (safety_tripwire_active()) {
        if (!m_safety_tripped) {
            log("safety tripwire fired — freezing on all_max");
            m_safety_tripped = true;
        }
        apply_arm(0);   // all_max
        return;
    }

    // Throttle awareness: if any tile reports THERMAL, fall back to all_max
    // for this tick (don't update bandit — the data is contaminated).
    if (!m_last_x.empty() &&
        m_last_x[FeatureExtractor::F_THROTTLE_BITSET] != 0.0) {
        apply_arm(0);
        return;
    }

    // Phase 1.5 hard filter: arms that combine CPU_FREQ=1.0 GHz with another
    // CPU-side bottleneck (CPU_PL or low UNCORE) are catastrophic on
    // CPU-bound benches. Block A showed A4 = +560% runtime on cpu-dgemm.
    // Block C additivity test showed A7's (CPU=1.0 + UNCORE=0.8) is a
    // compound bottleneck (predicted +38%, measured +76% on cpu-dgemm).
    // Until the bandit's runtime tripwire catches them (~one full epoch
    // later), preempt by disabling A4 and A7 when CPU is observably busy.
    // TODO(phase2): make penalize_arm transient (per-tick re-eval) so the
    // arms can come back when CPU goes idle again.
    if (!m_last_x.empty() && m_actions && m_bandit) {
        const double cpu_power_frac = m_last_x[FeatureExtractor::F_CPU_POWER_FRAC];
        if (cpu_power_frac > 0.5) {
            for (const char *arm_name : {"comm_wait_save", "aggressive_save"}) {
                int idx = m_actions->find(arm_name);
                if (idx >= 0) m_bandit->penalize_arm(idx);
            }
        }
        // Note: penalize_arm is sticky in v1 — once penalized, stays so.
    }

    // Normal path: pick an arm via LinUCB.
    int arm_idx = m_bandit->select(m_last_x, m_last_ucb_score);
    apply_arm(arm_idx);
    m_last_arm_idx = arm_idx;

    if (should_log(m_tick_count)) {
        const auto &arm = m_actions->arms()[arm_idx];
        log("tick=" + std::to_string(m_tick_count) +
            " arm=" + std::to_string(arm_idx) + "(" + arm.name + ")" +
            " ucb=" + format_double(m_last_ucb_score) +
            " gpu_act=" + format_double(m_last_x[FeatureExtractor::F_GPU_ACTIVITY_AVG]) +
            " cpu_pf=" + format_double(m_last_x[FeatureExtractor::F_CPU_POWER_FRAC]));
    }
}

bool AuroraBanditAgent::do_write_batch() const {
    return m_do_write_batch;
}

void AuroraBanditAgent::sample_platform(std::vector<double> &out_sample) {
    if (m_level != 0) {
        throw geopm::Exception("AuroraBanditAgent::sample_platform: leaf only",
                               GEOPM_ERROR_LOGIC, __FILE__, __LINE__);
    }

    // Build feature vector x_t.
    const double cap = m_last_policy.empty() ? 0.0
                          : m_last_policy[M_POLICY_POWER_CAP_WATTS];
    m_last_x = m_features->extract(cap);
    m_last_board_power_w = m_features->last_board_power_w();

    // Compute reward against the *previous* arm's outcome and update LinUCB.
    if (m_last_arm_idx >= 0 && m_bandit && !m_safety_tripped) {
        m_last_reward = compute_reward();
        m_bandit->update(m_last_x, m_last_arm_idx, m_last_reward);
    }

    out_sample.assign(M_NUM_SAMPLE, 0.0);
    out_sample[M_SAMPLE_NODE_COUNT]         = 1.0;
    out_sample[M_SAMPLE_BOARD_POWER_W]      = m_last_board_power_w;
    out_sample[M_SAMPLE_LAST_ARM_IDX]       = static_cast<double>(m_last_arm_idx);
    out_sample[M_SAMPLE_LAST_REWARD]        = m_last_reward;
    out_sample[M_SAMPLE_RUNTIME_SLACK_USED] = finite(m_baseline_runtime_s)
        ? std::max(0.0, (m_elapsed_s - m_baseline_runtime_s) / m_baseline_runtime_s)
        : 0.0;
    m_do_send_sample = true;
    m_last_sample = out_sample;
    m_tick_count++;
}

void AuroraBanditAgent::wait() {
    std::this_thread::sleep_for(std::chrono::duration<double>(m_period));
    m_elapsed_s += m_period;
}

// ===== Report / trace =====

std::vector<std::pair<std::string, std::string>>
AuroraBanditAgent::report_header() const {
    return {
        {"AuroraBandit period (s)", format_double(m_period)},
        {"AuroraBandit plugin name", plugin_name()},
    };
}

std::vector<std::pair<std::string, std::string>>
AuroraBanditAgent::report_host() const {
    std::vector<std::pair<std::string, std::string>> out;
    out.push_back({"Last arm index", format_double(m_last_arm_idx)});
    if (m_last_arm_idx >= 0 && m_actions && m_last_arm_idx < m_actions->size()) {
        out.push_back({"Last arm name", m_actions->arms()[m_last_arm_idx].name});
    }
    out.push_back({"Total ticks", std::to_string(m_tick_count)});
    out.push_back({"Safety tripwire fired", m_safety_tripped ? "true" : "false"});
    out.push_back({"Controls written", std::to_string(m_controls.size())});
    out.push_back({"MIN floors dropped",
                   std::to_string(m_min_guard ? (int)m_min_guard->log().size() : 0)});
    return out;
}

std::map<uint64_t, std::vector<std::pair<std::string, std::string>>>
AuroraBanditAgent::report_region() const {
    return {};
}

std::vector<std::string> AuroraBanditAgent::trace_names() const {
    return {
        "arm_idx", "ucb_score", "board_power_w",
        "cpu_freq_hz", "gpu_freq_hz",
        "energy_delta_j", "runtime_delta_s"
    };
}

std::vector<std::function<std::string(double)>>
AuroraBanditAgent::trace_formats() const {
    return std::vector<std::function<std::string(double)>>(
        M_NUM_TRACE, geopm::string_format_double);
}

void AuroraBanditAgent::trace_values(std::vector<double> &values) {
    values.assign(M_NUM_TRACE, NAN);
    values[M_TRACE_ARM_IDX]        = static_cast<double>(m_last_arm_idx);
    values[M_TRACE_UCB_SCORE]      = m_last_ucb_score;
    values[M_TRACE_BOARD_POWER_W]  = m_last_board_power_w;
    // Per-knob freq from feature vector (normalized); reverse-map below.
    if (!m_last_x.empty() && m_features) {
        values[M_TRACE_CPU_FREQ_HZ] = m_last_x[FeatureExtractor::F_CPU_FREQ_NORMALIZED] * 3.5e9;
        values[M_TRACE_GPU_FREQ_HZ] = m_last_x[FeatureExtractor::F_GPU_FREQ_NORMALIZED] * 1.6e9;
    }
    values[M_TRACE_ENERGY_DELTA_J]  = m_features ? m_features->last_board_energy_j() : NAN;
    values[M_TRACE_RUNTIME_DELTA_S] = m_period;
}

void AuroraBanditAgent::enforce_policy(const std::vector<double> &policy) const {
    // One-shot enforcement (geopmagent --enforce). Conservative: no-op.
    // The agent does its work inside the control loop; the static enforcement
    // case (when no controller is running) is left to other agents.
    (void)policy;
}

// ===== Helpers =====

void AuroraBanditAgent::apply_arm(int arm_idx) {
    if (!m_controls_enabled || !m_actions) return;
    const auto &writes = m_actions->resolve(arm_idx);

    for (const auto &cw : writes) {
        // Apply to every BatchControl instance whose name matches cw.name.
        for (auto &bc : m_controls) {
            if (bc.name != cw.name || bc.readback_failed) continue;
            if (finite(bc.last_setting) &&
                std::fabs(bc.last_setting - cw.value) < 1e-9) {
                continue;  // unchanged — don't re-issue
            }
            try {
                m_platform_io.adjust(bc.batch_idx, cw.value);
                bc.last_setting = cw.value;
                m_do_write_batch = true;
            }
            catch (const std::exception &ex) {
                log("adjust failed: " + bc.name + " idx=" +
                    std::to_string(bc.domain_idx) + ": " + ex.what());
                bc.readback_failed = true;
            }
        }
    }
    // TODO(phase2): on the NEXT sample tick, read back each adjusted control
    // and assert |readback - requested| / requested < 0.05. If it fails twice,
    // mark the control's bc.readback_failed = true and call
    // m_bandit->disable_arm() for every arm that uses it.
}

double AuroraBanditAgent::compute_reward() {
    // Per-tick reward: -ΔEnergy - λ · max(0, slack_overrun)
    //   slack_overrun = elapsed - (1+ε)·baseline_runtime
    // Energy delta is the change in BOARD_ENERGY since the last tick.
    // Baseline is initialized to first observation when not yet set.
    if (!m_features) return 0.0;
    static double last_energy = NAN;
    const double cur_energy = m_features->last_board_energy_j();
    double dE = 0.0;
    if (finite(last_energy) && finite(cur_energy) && cur_energy >= last_energy) {
        dE = cur_energy - last_energy;
    }
    last_energy = cur_energy;

    if (std::isnan(m_baseline_runtime_s)) {
        // Crude baseline init: assume the first observed BOARD_POWER is
        // representative; baseline_runtime = projected total. The real
        // version uses Phase 0 mean runtime per inferred workload class.
        m_baseline_runtime_s = 60.0;  // placeholder
        m_baseline_energy_J  = m_features->last_board_power_w() * m_baseline_runtime_s;
    }

    const double slack = m_last_policy.empty() ? 0.05
                            : m_last_policy[M_POLICY_RUNTIME_SLACK];
    const double overrun = std::max(0.0,
        m_elapsed_s - (1.0 + slack) * m_baseline_runtime_s);
    constexpr double LAMBDA = 100.0;   // penalty weight (tuned in Phase 3)

    return -dE - LAMBDA * overrun;
}

bool AuroraBanditAgent::safety_tripwire_active() const {
    if (!finite(m_baseline_runtime_s)) return false;
    const double slack = m_last_policy.empty() ? 0.05
                            : m_last_policy[M_POLICY_RUNTIME_SLACK];
    constexpr double SAFETY_MARGIN = 0.02;
    return m_elapsed_s > (1.0 + slack - SAFETY_MARGIN) * m_baseline_runtime_s;
}

void AuroraBanditAgent::log(const std::string &msg) const {
    if (m_verbose) {
        std::cerr << "[aurora_bandit] level=" << m_level << " " << msg << std::endl;
    }
}

bool AuroraBanditAgent::should_log(uint64_t count) const {
    return m_verbose && (count == 0 || count % (uint64_t)m_log_stride == 0);
}

} // namespace aurora_bandit

// ===== Plugin registration =====
//
// GEOPM dlopen()s libraries with the prefix libgeopmagent_ from
// GEOPM_PLUGIN_PATH. The constructor attribute runs at load time and
// registers the plugin with the Agent factory.

__attribute__((constructor))
static void aurora_bandit_agent_load(void)
{
    geopm::agent_factory().register_plugin(
        aurora_bandit::AuroraBanditAgent::plugin_name(),
        aurora_bandit::AuroraBanditAgent::make_plugin,
        geopm::Agent::make_dictionary(
            aurora_bandit::AuroraBanditAgent::policy_names(),
            aurora_bandit::AuroraBanditAgent::sample_names()));
}
