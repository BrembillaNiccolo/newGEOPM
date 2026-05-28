// ActionGrid.hpp
// Discrete arm set for the LinUCB bandit. Each arm is a partial setting of
// GEOPM controls; unspecified controls are left at the previous tick's value.
//
// Default arms reflect the Phase 0 winners (see analysis/agent_suggestions.md).
// Override via policy.action_grid_path JSON.

#pragma once

#include <map>
#include <string>
#include <vector>

namespace aurora_bandit {

struct ControlWrite {
    std::string name;        // e.g. "GPU_CORE_FREQUENCY_MAX_CONTROL"
    double      value;       // Hz, W, or 0..1 depending on knob
};

struct Arm {
    std::string                name;
    std::vector<ControlWrite>  controls;       // empty = "all_max" / no-op arm
    std::string                class_hint;     // workload class this arm is biased for
};

class ActionGrid {
public:
    // Load from JSON; if path is empty, use the built-in default grid.
    // Returns false on parse failure (caller falls back to default).
    bool load(const std::string &path);

    void load_default();

    const std::vector<Arm> &arms() const { return m_arms; }
    int  size() const { return static_cast<int>(m_arms.size()); }

    // Resolve arm_idx to a list of writes; arm_idx out of range returns empty.
    const std::vector<ControlWrite> &resolve(int arm_idx) const;

    // Index of an arm by name, or -1.
    int find(const std::string &name) const;

private:
    std::vector<Arm> m_arms;
    std::vector<ControlWrite> m_empty;
};

} // namespace aurora_bandit
