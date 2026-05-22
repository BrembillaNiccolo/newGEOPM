#include <sycl/sycl.hpp>

#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

namespace {

struct Options {
    size_t size = 1 << 24;
    int iters = 20;
};

size_t parse_size(const char *name, const char *value)
{
    char *end = nullptr;
    unsigned long long parsed = std::strtoull(value, &end, 10);
    if (*value == '\0' || *end != '\0' || parsed == 0) {
        std::cerr << "Invalid value for " << name << ": " << value << "\n";
        std::exit(2);
    }
    return static_cast<size_t>(parsed);
}

int parse_int(const char *name, const char *value)
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
        auto value = [&](const char *name) -> const char * {
            if (i + 1 >= argc) {
                std::cerr << "Missing value for " << name << "\n";
                std::exit(2);
            }
            return argv[++i];
        };
        if (arg == "-s" || arg == "--size") {
            opt.size = parse_size(arg.c_str(), value(arg.c_str()));
        }
        else if (arg == "--iters") {
            opt.iters = parse_int("--iters", value("--iters"));
        }
        else if (arg == "-h" || arg == "--help") {
            std::cout << "mini_babelstream_sycl -s ELEMENTS --iters N\n";
            std::exit(0);
        }
        else {
            std::cerr << "Unknown argument: " << arg << "\n";
            std::exit(2);
        }
    }
    return opt;
}

} // namespace

int main(int argc, char **argv)
{
    const Options opt = parse_args(argc, argv);
    sycl::queue queue(sycl::default_selector_v);
    double *a = sycl::malloc_shared<double>(opt.size, queue);
    double *b = sycl::malloc_shared<double>(opt.size, queue);
    double *c = sycl::malloc_shared<double>(opt.size, queue);
    if (!a || !b || !c) {
        std::cerr << "SYCL allocation failed\n";
        return 1;
    }

    queue.parallel_for(sycl::range<1>(opt.size), [=](sycl::id<1> idx) {
        const size_t i = idx[0];
        a[i] = 1.0;
        b[i] = 2.0;
        c[i] = 0.0;
    }).wait();

    double best_s = std::numeric_limits<double>::infinity();
    double total_s = 0.0;
    const double scalar = 3.0;
    for (int iter = 0; iter < opt.iters; ++iter) {
        const auto t0 = std::chrono::steady_clock::now();
        queue.parallel_for(sycl::range<1>(opt.size), [=](sycl::id<1> idx) {
            const size_t i = idx[0];
            c[i] = a[i] + scalar * b[i];
        }).wait();
        const auto t1 = std::chrono::steady_clock::now();
        const double elapsed = std::chrono::duration<double>(t1 - t0).count();
        best_s = std::min(best_s, elapsed);
        total_s += elapsed;
    }

    double checksum = 0.0;
    const size_t stride = std::max<size_t>(1, opt.size / 1024);
    for (size_t i = 0; i < opt.size; i += stride) {
        checksum += c[i];
    }

    const double bytes = 3.0 * static_cast<double>(opt.size) * sizeof(double);
    const double triad_bandwidth_mb_s = bytes / best_s / 1.0e6;

    std::cout << std::setprecision(10)
              << "benchmark=babelstream\n"
              << "workload_type=gpu_memory\n"
              << "device=" << queue.get_device().get_info<sycl::info::device::name>() << "\n"
              << "size=" << opt.size << "\n"
              << "iters=" << opt.iters << "\n"
              << "runtime_s=" << total_s << "\n"
              << "best_triad_s=" << best_s << "\n"
              << "triad_bandwidth_mb_s=" << triad_bandwidth_mb_s << "\n"
              << "checksum=" << checksum << "\n";

    sycl::free(a, queue);
    sycl::free(b, queue);
    sycl::free(c, queue);
    return std::isfinite(checksum) ? 0 : 1;
}
