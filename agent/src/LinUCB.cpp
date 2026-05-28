// LinUCB.cpp
// Tiny dense Cholesky solver — sufficient for d≈11 features and ≤32 arms.
// Replace with Eigen if d grows or the inner loop becomes a bottleneck.

#include "LinUCB.hpp"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <limits>

namespace aurora_bandit {

LinUCB::LinUCB(int n_arms, int n_features, double alpha, double ridge)
    : m_n_arms(n_arms)
    , m_d(n_features)
    , m_alpha(alpha)
    , m_ridge(ridge)
    , m_arms(n_arms)
{
    for (auto &arm : m_arms) {
        arm.A.assign(m_d * m_d, 0.0);
        for (int i = 0; i < m_d; ++i) arm.A[i * m_d + i] = m_ridge;
        arm.b.assign(m_d, 0.0);
        arm.theta.assign(m_d, 0.0);
    }
}

uint64_t LinUCB::update_count(int arm_idx) const {
    if (arm_idx < 0 || arm_idx >= m_n_arms) return 0;
    return m_arms[arm_idx].n_updates;
}

// Cholesky factorization A = L L^T (lower-triangular L stored in lower half of out).
// Returns true on success; false if A is not positive definite.
namespace {
bool cholesky_factor(const std::vector<double> &A, int d, std::vector<double> &L) {
    L.assign(d * d, 0.0);
    for (int i = 0; i < d; ++i) {
        for (int j = 0; j <= i; ++j) {
            double sum = A[i * d + j];
            for (int k = 0; k < j; ++k) sum -= L[i * d + k] * L[j * d + k];
            if (i == j) {
                if (sum <= 0.0) return false;
                L[i * d + j] = std::sqrt(sum);
            } else {
                L[i * d + j] = sum / L[j * d + j];
            }
        }
    }
    return true;
}

// Solve L y = b   (forward sub)
void forward_sub(const std::vector<double> &L, int d,
                 const std::vector<double> &b, std::vector<double> &y) {
    y.assign(d, 0.0);
    for (int i = 0; i < d; ++i) {
        double sum = b[i];
        for (int k = 0; k < i; ++k) sum -= L[i * d + k] * y[k];
        y[i] = sum / L[i * d + i];
    }
}

// Solve L^T x = y  (back sub)
void back_sub(const std::vector<double> &L, int d,
              const std::vector<double> &y, std::vector<double> &x) {
    x.assign(d, 0.0);
    for (int i = d - 1; i >= 0; --i) {
        double sum = y[i];
        for (int k = i + 1; k < d; ++k) sum -= L[k * d + i] * x[k];
        x[i] = sum / L[i * d + i];
    }
}
} // namespace

void LinUCB::cholesky_solve(const std::vector<double> &A,
                            const std::vector<double> &b,
                            std::vector<double> &x) const {
    std::vector<double> L, y;
    if (!cholesky_factor(A, m_d, L)) {
        // A not PD (shouldn't happen with ridge > 0). Return zeros.
        x.assign(m_d, 0.0);
        return;
    }
    forward_sub(L, m_d, b, y);
    back_sub(L, m_d, y, x);
}

double LinUCB::quadratic_form_inv(const std::vector<double> &A,
                                  const std::vector<double> &x) const {
    // x^T A^{-1} x: solve A z = x, return x^T z.
    std::vector<double> z;
    cholesky_solve(A, x, z);
    double s = 0.0;
    for (int i = 0; i < m_d; ++i) s += x[i] * z[i];
    return std::max(0.0, s);   // numerical guard
}

void LinUCB::recompute_theta(ArmState &arm) const {
    if (!arm.theta_dirty) return;
    cholesky_solve(arm.A, arm.b, arm.theta);
    arm.theta_dirty = false;
}

int LinUCB::select(const std::vector<double> &x, double &out_score) const {
    int best_arm = 0;
    double best_score = -std::numeric_limits<double>::infinity();
    bool any_enabled = false;

    for (int a = 0; a < m_n_arms; ++a) {
        auto &arm = m_arms[a];
        if (arm.disabled) continue;
        any_enabled = true;

        recompute_theta(arm);
        double mean = 0.0;
        for (int i = 0; i < m_d; ++i) mean += arm.theta[i] * x[i];
        double bonus = m_alpha * std::sqrt(quadratic_form_inv(arm.A, x));
        double s = mean + bonus;
        if (arm.penalized) s -= 1.0;   // soft demotion

        if (s > best_score) {
            best_score = s;
            best_arm = a;
        }
    }
    out_score = best_score;
    return any_enabled ? best_arm : 0;
}

void LinUCB::update(const std::vector<double> &x, int arm_idx, double reward) {
    if (arm_idx < 0 || arm_idx >= m_n_arms) return;
    auto &arm = m_arms[arm_idx];
    if (arm.disabled) return;
    for (int i = 0; i < m_d; ++i) {
        for (int j = 0; j < m_d; ++j) {
            arm.A[i * m_d + j] += x[i] * x[j];
        }
        arm.b[i] += reward * x[i];
    }
    arm.n_updates += 1;
    arm.theta_dirty = true;
}

void LinUCB::disable_arm(int arm_idx) {
    if (arm_idx < 0 || arm_idx >= m_n_arms) return;
    m_arms[arm_idx].disabled = true;
}

void LinUCB::penalize_arm(int arm_idx) {
    if (arm_idx < 0 || arm_idx >= m_n_arms) return;
    m_arms[arm_idx].penalized = true;
}

bool LinUCB::warm_start_from_json(const std::string &path) {
    if (path.empty()) return false;
    std::ifstream f(path);
    if (!f.good()) {
        std::cerr << "[aurora_bandit] LinUCB: warm-start file not found: "
                  << path << "; using cold start" << std::endl;
        return false;
    }
    // TODO(phase2): parse JSON priors and overwrite arm.A / arm.b.
    // Skeleton ships as cold-start; analysis/scripts/generate_phase2_priors.py
    // is the upstream producer (to be written).
    std::cerr << "[aurora_bandit] LinUCB: warm-start JSON parsing not yet "
                 "implemented; using cold start" << std::endl;
    return false;
}

} // namespace aurora_bandit
