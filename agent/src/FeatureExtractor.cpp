// FeatureExtractor.cpp

#include "FeatureExtractor.hpp"

#include <algorithm>
#include <iostream>

#include "geopm/Exception.hpp"

namespace aurora_bandit {

namespace {
double safe_div(double a, double b, double fallback) {
    if (!std::isfinite(a) || !std::isfinite(b) || b == 0.0) return fallback;
    return a / b;
}
bool finite(double v) { return std::isfinite(v); }
}

FeatureExtractor::FeatureExtractor(geopm::PlatformIO &platform_io,
                                   const geopm::PlatformTopo &platform_topo)
    : m_pio(platform_io)
    , m_topo(platform_topo)
{}

int FeatureExtractor::n_signals() const {
    return static_cast<int>(
        m_board_power.size() + m_board_energy.size() +
        m_gpu_activity.size() + m_gpu_power.size() + m_gpu_freq.size() +
        m_cpu_power.size() + m_cpu_freq.size() + m_uncore_freq.size() +
        m_dram_power.size() + m_gpu_throttle.size());
}

void FeatureExtractor::push_signals() {
    // Board-level
    push_first_signal_group({"BOARD_POWER"},  m_board_power);
    push_first_signal_group({"BOARD_ENERGY"}, m_board_energy);

    // GPU per-tile (native domain GPU_CHIP on Aurora = 12 tiles).
    push_first_signal_group({"GPU_CORE_ACTIVITY",
                             "LEVELZERO::GPU_CORE_ACTIVITY",
                             "GPU_UTILIZATION"}, m_gpu_activity);
    push_first_signal_group({"GPU_POWER", "LEVELZERO::GPU_POWER"}, m_gpu_power);
    push_first_signal_group({"GPU_CORE_FREQUENCY_STATUS",
                             "LEVELZERO::GPU_CORE_FREQUENCY"}, m_gpu_freq);
    push_first_signal_group({"LEVELZERO::GPU_CORE_THROTTLE_REASONS"},
                            m_gpu_throttle);

    // CPU per-package
    push_first_signal_group({"CPU_POWER"}, m_cpu_power);
    push_first_signal_group({"CPU_FREQUENCY_STATUS"}, m_cpu_freq);
    push_first_signal_group({"CPU_UNCORE_FREQUENCY_STATUS"}, m_uncore_freq);
    push_first_signal_group({"DRAM_POWER"}, m_dram_power);

    // Defaults / AVAIL — read synchronously once.
    auto try_read = [&](const std::string &name, int dom, int idx) -> double {
        try { return m_pio.read_signal(name, dom, idx); }
        catch (const std::exception &) { return NAN; }
    };
    m_gpu_power_limit_default = try_read("GPU_POWER_LIMIT_DEFAULT",
                                         GEOPM_DOMAIN_GPU, 0);
    m_cpu_power_limit_default = try_read("CPU_POWER_LIMIT_DEFAULT",
                                         GEOPM_DOMAIN_PACKAGE, 0);
    m_dram_power_limit_default = try_read("DRAM_POWER_LIMIT_DEFAULT",
                                          GEOPM_DOMAIN_PACKAGE, 0);
    m_gpu_freq_max_avail = try_read("GPU_CORE_FREQUENCY_MAX_AVAIL",
                                    GEOPM_DOMAIN_GPU_CHIP, 0);
    if (!finite(m_gpu_freq_max_avail)) m_gpu_freq_max_avail = 1.6e9;
    m_cpu_freq_max_avail = try_read("CPU_FREQUENCY_MAX_AVAIL",
                                    GEOPM_DOMAIN_CORE, 0);
    if (!finite(m_cpu_freq_max_avail)) m_cpu_freq_max_avail = 3.5e9;
    m_uncore_freq_max_avail = try_read("CPU_UNCORE_FREQUENCY_MAX_AVAIL",
                                       GEOPM_DOMAIN_PACKAGE, 0);
    if (!finite(m_uncore_freq_max_avail)) m_uncore_freq_max_avail = 2.3e9;
}

void FeatureExtractor::push_first_signal_group(
    const std::vector<std::string> &candidate_names,
    std::vector<BatchSignal> &out)
{
    const auto avail = m_pio.signal_names();
    for (const auto &name : candidate_names) {
        if (avail.count(name) == 0) continue;
        try {
            const int domain = m_pio.signal_domain_type(name);
            push_all_signals(name, domain, out);
            if (!out.empty()) return;
        }
        catch (const std::exception &ex) {
            std::cerr << "[aurora_bandit] FeatureExtractor: " << name
                      << " push failed: " << ex.what() << std::endl;
        }
    }
}

void FeatureExtractor::push_all_signals(const std::string &name,
                                        int domain_type,
                                        std::vector<BatchSignal> &out)
{
    if (domain_type == GEOPM_DOMAIN_INVALID) return;
    const int n = m_topo.num_domain(domain_type);
    for (int idx = 0; idx < n; ++idx) {
        try {
            BatchSignal s;
            s.batch_idx = m_pio.push_signal(name, domain_type, idx);
            s.domain_type = domain_type;
            s.domain_idx = idx;
            s.name = name;
            out.push_back(s);
        }
        catch (const std::exception &) { /* per-instance failure, skip */ }
    }
}

void FeatureExtractor::sample_group(std::vector<BatchSignal> &group) {
    for (auto &s : group) {
        s.value = m_pio.sample(s.batch_idx);
    }
}

double FeatureExtractor::sum(const std::vector<BatchSignal> &g) const {
    double s = 0.0;
    for (const auto &x : g) if (finite(x.value)) s += x.value;
    return s;
}

double FeatureExtractor::mean(const std::vector<BatchSignal> &g, double fb) const {
    double s = 0.0; int n = 0;
    for (const auto &x : g) if (finite(x.value)) { s += x.value; ++n; }
    return n == 0 ? fb : s / n;
}

double FeatureExtractor::variance(const std::vector<BatchSignal> &g) const {
    double m = mean(g, 0.0);
    double v = 0.0; int n = 0;
    for (const auto &x : g) if (finite(x.value)) { v += (x.value - m) * (x.value - m); ++n; }
    return n == 0 ? 0.0 : v / n;
}

std::vector<double> FeatureExtractor::extract(double power_cap_watts) {
    sample_group(m_board_power);
    sample_group(m_board_energy);
    sample_group(m_gpu_activity);
    sample_group(m_gpu_power);
    sample_group(m_gpu_freq);
    sample_group(m_cpu_power);
    sample_group(m_cpu_freq);
    sample_group(m_uncore_freq);
    sample_group(m_dram_power);
    sample_group(m_gpu_throttle);

    std::vector<double> x(N_FEATURES, 0.0);

    m_last_board_power = sum(m_board_power);
    m_last_board_energy = sum(m_board_energy);

    const double cap = power_cap_watts > 0.0 ? power_cap_watts : 4500.0;  // Aurora default
    x[F_BOARD_POWER_FRAC]  = safe_div(m_last_board_power, cap, 0.0);
    x[F_GPU_ACTIVITY_AVG]  = mean(m_gpu_activity, 0.0);
    x[F_GPU_POWER_FRAC]    = safe_div(sum(m_gpu_power),
                                      (finite(m_gpu_power_limit_default) ?
                                       m_gpu_power_limit_default * std::max(1, (int)m_gpu_power.size())
                                       : 600.0 * 6), 0.0);
    x[F_GPU_FREQ_NORMALIZED] = safe_div(mean(m_gpu_freq, 0.0), m_gpu_freq_max_avail, 0.0);
    x[F_CPU_POWER_FRAC]    = safe_div(sum(m_cpu_power),
                                      (finite(m_cpu_power_limit_default) ?
                                       m_cpu_power_limit_default * std::max(1, (int)m_cpu_power.size())
                                       : 350.0 * 2), 0.0);
    x[F_CPU_FREQ_NORMALIZED] = safe_div(mean(m_cpu_freq, 0.0), m_cpu_freq_max_avail, 0.0);
    x[F_UNCORE_FREQ_NORMALIZED] = safe_div(mean(m_uncore_freq, 0.0), m_uncore_freq_max_avail, 0.0);
    x[F_DRAM_POWER_FRAC] = safe_div(sum(m_dram_power),
                                    (finite(m_dram_power_limit_default) ?
                                     m_dram_power_limit_default * std::max(1, (int)m_dram_power.size())
                                     : 20.0 * 2), 0.0);
    x[F_GPU_ACTIVITY_VARIANCE] = variance(m_gpu_activity);

    // MPI wait proxy: 1 - normalized CPU power (when CPU is idle, it's likely waiting).
    x[F_MPI_WAIT_FRAC] = std::max(0.0, 1.0 - x[F_CPU_POWER_FRAC]);

    // Throttle bitset: any tile non-zero in the throttle reasons bitmask => 1.
    double throttle_any = 0.0;
    for (const auto &t : m_gpu_throttle) {
        if (finite(t.value) && t.value != 0.0) { throttle_any = 1.0; break; }
    }
    x[F_THROTTLE_BITSET] = throttle_any;

    return x;
}

} // namespace aurora_bandit
