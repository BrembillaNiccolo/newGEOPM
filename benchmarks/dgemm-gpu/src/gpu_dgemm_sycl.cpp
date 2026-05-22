#include <sycl/sycl.hpp>

#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>

namespace {

struct Options {
    int m = 1024;
    int n = 1024;
    int k = 1024;
    int iters = 5;
    int tile = 16;
};

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
        if (arg == "--M" || arg == "--m") {
            opt.m = parse_int(arg.c_str(), value(arg.c_str()));
        }
        else if (arg == "--N" || arg == "--n") {
            opt.n = parse_int(arg.c_str(), value(arg.c_str()));
        }
        else if (arg == "--K" || arg == "--k") {
            opt.k = parse_int(arg.c_str(), value(arg.c_str()));
        }
        else if (arg == "--iters") {
            opt.iters = parse_int("--iters", value("--iters"));
        }
        else if (arg == "--tile") {
            opt.tile = parse_int("--tile", value("--tile"));
        }
        else if (arg == "--dtype") {
            (void)value("--dtype");
        }
        else if (arg == "-h" || arg == "--help") {
            std::cout << "gpu_dgemm_sycl --M N --N N --K N --iters N\n";
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

    const size_t a_size = static_cast<size_t>(opt.m) * opt.k;
    const size_t b_size = static_cast<size_t>(opt.k) * opt.n;
    const size_t c_size = static_cast<size_t>(opt.m) * opt.n;
    double *a = sycl::malloc_shared<double>(a_size, queue);
    double *b = sycl::malloc_shared<double>(b_size, queue);
    double *c = sycl::malloc_shared<double>(c_size, queue);
    if (!a || !b || !c) {
        std::cerr << "SYCL allocation failed\n";
        return 1;
    }

    queue.parallel_for(sycl::range<1>(a_size), [=](sycl::id<1> idx) {
        const size_t i = idx[0];
        a[i] = static_cast<double>((i * 17) % 97) / 97.0;
    });
    queue.parallel_for(sycl::range<1>(b_size), [=](sycl::id<1> idx) {
        const size_t i = idx[0];
        b[i] = static_cast<double>((i * 31) % 89) / 89.0;
    }).wait();

    const sycl::range<2> global((size_t)opt.m, (size_t)opt.n);
    double best_s = std::numeric_limits<double>::infinity();
    double total_s = 0.0;
    for (int iter = 0; iter < opt.iters; ++iter) {
        const auto t0 = std::chrono::steady_clock::now();
        queue.parallel_for(global, [=](sycl::id<2> idx) {
            const int row = (int)idx[0];
            const int col = (int)idx[1];
            double sum = 0.0;
            for (int p = 0; p < opt.k; ++p) {
                sum += a[(size_t)row * opt.k + p] * b[(size_t)p * opt.n + col];
            }
            c[(size_t)row * opt.n + col] = sum;
        }).wait();
        const auto t1 = std::chrono::steady_clock::now();
        const double elapsed = std::chrono::duration<double>(t1 - t0).count();
        best_s = std::min(best_s, elapsed);
        total_s += elapsed;
    }

    double checksum = 0.0;
    const size_t stride = std::max<size_t>(1, c_size / 1024);
    for (size_t i = 0; i < c_size; i += stride) {
        checksum += c[i];
    }

    const double flop = 2.0 * static_cast<double>(opt.m) * opt.n * opt.k;
    const double avg_s = total_s / opt.iters;
    const double avg_gflops = flop / avg_s / 1.0e9;
    const double best_gflops = flop / best_s / 1.0e9;

    std::cout << std::setprecision(10)
              << "benchmark=dgemm-gpu\n"
              << "workload_type=gpu_compute\n"
              << "device=" << queue.get_device().get_info<sycl::info::device::name>() << "\n"
              << "m=" << opt.m << "\n"
              << "n=" << opt.n << "\n"
              << "k=" << opt.k << "\n"
              << "iters=" << opt.iters << "\n"
              << "runtime_s=" << total_s << "\n"
              << "avg_iter_s=" << avg_s << "\n"
              << "best_iter_s=" << best_s << "\n"
              << "avg_gflops=" << avg_gflops << "\n"
              << "best_gflops=" << best_gflops << "\n"
              << "checksum=" << checksum << "\n";

    sycl::free(a, queue);
    sycl::free(b, queue);
    sycl::free(c, queue);
    return std::isfinite(checksum) ? 0 : 1;
}
