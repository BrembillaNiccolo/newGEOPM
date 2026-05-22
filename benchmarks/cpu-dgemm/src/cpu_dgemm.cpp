#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <string>
#include <vector>

namespace {

struct Options {
    int m = 1024;
    int n = 1024;
    int k = 1024;
    int iters = 3;
    int block = 64;
    bool check = true;
};

void usage(const char *prog)
{
    std::cerr
        << "Usage: " << prog << " [--m N] [--n N] [--k N] [--iters N] [--block N] [--no-check]\n"
        << "\n"
        << "Small Phase 0 CPU DGEMM benchmark. Prints key=value metrics on stdout.\n";
}

int parse_positive_int(const char *name, const char *value)
{
    char *end = nullptr;
    long parsed = std::strtol(value, &end, 10);
    if (*value == '\0' || *end != '\0' || parsed <= 0 || parsed > std::numeric_limits<int>::max()) {
        std::cerr << "Invalid value for " << name << ": " << value << "\n";
        std::exit(2);
    }
    return static_cast<int>(parsed);
}

Options parse_args(int argc, char **argv)
{
    Options opt;
    for (int i = 1; i < argc; ++i) {
        const std::string arg(argv[i]);
        auto need_value = [&](const char *name) -> const char * {
            if (i + 1 >= argc) {
                std::cerr << "Missing value for " << name << "\n";
                std::exit(2);
            }
            return argv[++i];
        };

        if (arg == "--m") {
            opt.m = parse_positive_int("--m", need_value("--m"));
        }
        else if (arg == "--n") {
            opt.n = parse_positive_int("--n", need_value("--n"));
        }
        else if (arg == "--k") {
            opt.k = parse_positive_int("--k", need_value("--k"));
        }
        else if (arg == "--iters") {
            opt.iters = parse_positive_int("--iters", need_value("--iters"));
        }
        else if (arg == "--block") {
            opt.block = parse_positive_int("--block", need_value("--block"));
        }
        else if (arg == "--no-check") {
            opt.check = false;
        }
        else if (arg == "--help" || arg == "-h") {
            usage(argv[0]);
            std::exit(0);
        }
        else {
            std::cerr << "Unknown argument: " << arg << "\n";
            usage(argv[0]);
            std::exit(2);
        }
    }
    return opt;
}

void fill_matrix(std::vector<double> &x, int rows, int cols, double offset)
{
    for (int r = 0; r < rows; ++r) {
        for (int c = 0; c < cols; ++c) {
            const double v = static_cast<double>(((r * 131 + c * 17) % 97) - 48);
            x[static_cast<size_t>(r) * cols + c] = (v + offset) / 97.0;
        }
    }
}

void zero_matrix(std::vector<double> &x)
{
    std::fill(x.begin(), x.end(), 0.0);
}

void dgemm_blocked(const std::vector<double> &a,
                   const std::vector<double> &b,
                   std::vector<double> &c,
                   int m,
                   int n,
                   int k,
                   int block)
{
#pragma omp parallel for schedule(static)
    for (int ii = 0; ii < m; ii += block) {
        for (int kk = 0; kk < k; kk += block) {
            for (int jj = 0; jj < n; jj += block) {
                const int i_end = std::min(ii + block, m);
                const int k_end = std::min(kk + block, k);
                const int j_end = std::min(jj + block, n);
                for (int i = ii; i < i_end; ++i) {
                    for (int p = kk; p < k_end; ++p) {
                        const double av = a[static_cast<size_t>(i) * k + p];
                        const size_t b_row = static_cast<size_t>(p) * n;
                        const size_t c_row = static_cast<size_t>(i) * n;
                        for (int j = jj; j < j_end; ++j) {
                            c[c_row + j] += av * b[b_row + j];
                        }
                    }
                }
            }
        }
    }
}

double checksum_sample(const std::vector<double> &c, int m, int n)
{
    double sum = 0.0;
    const int row_stride = std::max(1, m / 16);
    const int col_stride = std::max(1, n / 16);
    for (int i = 0; i < m; i += row_stride) {
        for (int j = 0; j < n; j += col_stride) {
            sum += c[static_cast<size_t>(i) * n + j];
        }
    }
    return sum;
}

} // namespace

int main(int argc, char **argv)
{
    const Options opt = parse_args(argc, argv);

    const size_t a_size = static_cast<size_t>(opt.m) * opt.k;
    const size_t b_size = static_cast<size_t>(opt.k) * opt.n;
    const size_t c_size = static_cast<size_t>(opt.m) * opt.n;

    std::vector<double> a(a_size);
    std::vector<double> b(b_size);
    std::vector<double> c(c_size);
    fill_matrix(a, opt.m, opt.k, 0.25);
    fill_matrix(b, opt.k, opt.n, -0.25);

    double best_s = std::numeric_limits<double>::infinity();
    double total_s = 0.0;
    double checksum = 0.0;

    for (int iter = 0; iter < opt.iters; ++iter) {
        zero_matrix(c);
        const auto t0 = std::chrono::steady_clock::now();
        dgemm_blocked(a, b, c, opt.m, opt.n, opt.k, opt.block);
        const auto t1 = std::chrono::steady_clock::now();
        const double elapsed_s = std::chrono::duration<double>(t1 - t0).count();
        best_s = std::min(best_s, elapsed_s);
        total_s += elapsed_s;
        if (opt.check) {
            checksum += checksum_sample(c, opt.m, opt.n);
        }
    }

    const double flop = 2.0 * static_cast<double>(opt.m) * opt.n * opt.k;
    const double best_gflops = flop / best_s / 1.0e9;
    const double avg_s = total_s / opt.iters;
    const double avg_gflops = flop / avg_s / 1.0e9;

    std::cout << std::setprecision(10)
              << "benchmark=cpu-dgemm\n"
              << "workload_type=cpu_compute\n"
              << "m=" << opt.m << "\n"
              << "n=" << opt.n << "\n"
              << "k=" << opt.k << "\n"
              << "iters=" << opt.iters << "\n"
              << "block=" << opt.block << "\n"
              << "runtime_s=" << total_s << "\n"
              << "avg_iter_s=" << avg_s << "\n"
              << "best_iter_s=" << best_s << "\n"
              << "avg_gflops=" << avg_gflops << "\n"
              << "best_gflops=" << best_gflops << "\n"
              << "checksum=" << checksum << "\n";

    if (!std::isfinite(checksum) && opt.check) {
        std::cerr << "Checksum is not finite\n";
        return 1;
    }
    return 0;
}
