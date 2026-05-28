// MinControlGuard.hpp
//
// Encapsulates the Phase 0 v1 fix: drop *_MIN_CONTROL knobs to their absolute
// floor at agent init so the *_MAX_CONTROL writes the agent issues can
// actually bind below the driver default. On Aurora PVC, GPU_CORE_FREQUENCY
// _MIN_CONTROL ships at 1.5 GHz, which silently clamps every MAX write below
// 1.5 GHz to 1.5 GHz. The whole low-frequency half of the action space is
// inaccessible without this drop. Verified in results/8509922.
//
// Restores originals on destruction.

#pragma once

#include <string>
#include <vector>

#include "geopm/PlatformIO.hpp"
#include "geopm/PlatformTopo.hpp"

namespace aurora_bandit {

class MinControlGuard {
public:
    MinControlGuard(geopm::PlatformIO &platform_io,
                    const geopm::PlatformTopo &platform_topo);
    ~MinControlGuard();

    // Push initial MIN values onto the restore stack and write floor values.
    // Returns the number of (control, instance) writes successfully issued.
    int drop_all();

    // Restore originals. Called from dtor; safe to call once explicitly too.
    void restore_all();

    // For report_host(): which controls we touched and what the originals were.
    struct Entry {
        std::string name;
        int domain_type;
        int domain_idx;
        double floor_value;
        double original_value;
        bool   drop_succeeded;
    };
    const std::vector<Entry> &log() const { return m_log; }

private:
    void try_drop_one(const std::string &control_name, double floor_value);

    geopm::PlatformIO          &m_pio;
    const geopm::PlatformTopo  &m_topo;
    std::vector<Entry>          m_log;
    bool                        m_restored = false;
};

} // namespace aurora_bandit
