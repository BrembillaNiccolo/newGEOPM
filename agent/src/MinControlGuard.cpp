// MinControlGuard.cpp

#include "MinControlGuard.hpp"

#include <cmath>
#include <iostream>

#include "geopm/Exception.hpp"

namespace aurora_bandit {

namespace {
// Verified absolute floors on Aurora Xeon Max + PVC.
// Source: experiments/phase1/strict_knobs.json + results/8509922.
constexpr double CPU_FREQ_FLOOR_HZ        = 8.0e8;   // 0.8 GHz
constexpr double CPU_UNCORE_FLOOR_HZ      = 8.0e8;   // 0.8 GHz
constexpr double GPU_CORE_FLOOR_HZ        = 2.0e8;   // 0.2 GHz
}

MinControlGuard::MinControlGuard(geopm::PlatformIO &platform_io,
                                 const geopm::PlatformTopo &platform_topo)
    : m_pio(platform_io)
    , m_topo(platform_topo)
{}

MinControlGuard::~MinControlGuard() {
    if (!m_restored) {
        restore_all();
    }
}

int MinControlGuard::drop_all() {
    int written = 0;
    try_drop_one("CPU_FREQUENCY_MIN_CONTROL",          CPU_FREQ_FLOOR_HZ);
    try_drop_one("CPU_UNCORE_FREQUENCY_MIN_CONTROL",   CPU_UNCORE_FLOOR_HZ);
    try_drop_one("GPU_CORE_FREQUENCY_MIN_CONTROL",     GPU_CORE_FLOOR_HZ);
    for (const auto &e : m_log) {
        if (e.drop_succeeded) {
            ++written;
        }
    }
    return written;
}

void MinControlGuard::try_drop_one(const std::string &control_name,
                                   double floor_value) {
    int domain_type;
    try {
        domain_type = m_pio.control_domain_type(control_name);
    }
    catch (const std::exception &ex) {
        // Control not exposed on this platform — skip; not fatal.
        return;
    }
    if (domain_type == GEOPM_DOMAIN_INVALID) {
        return;
    }

    const int domain_count = m_topo.num_domain(domain_type);
    for (int idx = 0; idx < domain_count; ++idx) {
        Entry e;
        e.name = control_name;
        e.domain_type = domain_type;
        e.domain_idx = idx;
        e.floor_value = floor_value;
        e.original_value = NAN;
        e.drop_succeeded = false;

        try {
            // Read current MIN_CONTROL via synchronous PIO read.
            // (We can't use batch IO here because batch is not set up until
            // the FeatureExtractor pushes signals, which happens after us.)
            e.original_value = m_pio.read_signal(control_name, domain_type, idx);
            m_pio.write_control(control_name, domain_type, idx, floor_value);
            e.drop_succeeded = true;
        }
        catch (const std::exception &ex) {
            std::cerr << "[aurora_bandit] MinControlGuard: failed to drop "
                      << control_name << " domain=" << domain_type
                      << " idx=" << idx << ": " << ex.what() << std::endl;
        }
        m_log.push_back(e);
    }
}

void MinControlGuard::restore_all() {
    if (m_restored) {
        return;
    }
    m_restored = true;
    for (auto it = m_log.rbegin(); it != m_log.rend(); ++it) {
        if (!it->drop_succeeded || std::isnan(it->original_value)) {
            continue;
        }
        try {
            m_pio.write_control(it->name, it->domain_type, it->domain_idx,
                                it->original_value);
        }
        catch (const std::exception &ex) {
            std::cerr << "[aurora_bandit] MinControlGuard: failed to restore "
                      << it->name << " idx=" << it->domain_idx
                      << ": " << ex.what() << std::endl;
        }
    }
}

} // namespace aurora_bandit
