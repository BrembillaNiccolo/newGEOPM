#include <sycl/sycl.hpp>

#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>
#include <thread>

namespace {

struct Options {
    int kernel_ms = 20;
    int gap_ms = 80;
    int iterations = 100;
    std::string gap_mode = "sleep";
    size_t elements = 1 << 22;
};

int parse_int(const char *name, const char *value)
{
    char *end = nullptr;
    long parsed = std::strtol(value, &end, 10);
    if (*value == '\0' || *end != '\0' || parsed < 0 || parsed > std::numeric_limits<int>::max()) {
        std::cerr << "Invalid value for " << name << ": " << value << "\n";
        std::exit(2);
    }
    return static_cast<int>(parsed);
}

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
        if (arg == "--kernel-ms") {
            opt.kernel_ms = parse_int("--kernel-ms", value("--kernel-ms"));
        }
        else if (arg == "--gap-ms") {
            opt.gap_ms = parse_int("--gap-ms", value("--gap-ms"));
        }
        else if (arg == "--iterations") {
            opt.iterations = parse_int("--iterations", value("--iterations"));
        }
        else if (arg == "--gap-mode") {
            opt.gap_mode = value("--gap-mode");
        }
        else if (arg == "--elements") {
            opt.elements = parse_size("--elements", value("--elements"));
        }
        else if (arg == "-h" || arg == "--help") {
            std::cout << "gpu_bursty_idle --kernel-ms N --gap-ms N --iterations N --gap-mode sleep|cpu\n";
            std::exit(0);
        }
        else {
            std::cerr << "Unknown argument: " << arg << "\n";
            std::exit(2);
        }
    }
    return opt;
}

void cpu_gap_ms(int ms, volatile double &sink)
{
    const auto end = std::chrono::steady_clock::now() + std::chrono::milliseconds(ms);
    double x = sink + 1.0;
    while (std::chrono::steady_clock::now() < end) {
        for (int i = 0; i < 1024; ++i) {
            x = std::sin(x) + std::cos(x * 0.5) + 1.0000001;
        }
    }
    sink += x;
}

} // namespace

int main(int argc, char **argv)
{
    const Options opt = parse_args(argc, argv);
    sycl::queue queue(sycl::default_selector_v);
    double *x = sycl::malloc_shared<double>(opt.elements, queue);
    if (!x) {
        std::cerr << "SYCL allocation failed\n";
        return 1;
    }

    queue.parallel_for(sycl::range<1>(opt.elements), [=](sycl::id<1> idx) {
        x[idx[0]] = 1.0;
    }).wait();

    double kernel_s = 0.0;
    double gap_s = 0.0;
    volatile double sink = 0.0;
    const auto total0 = std::chrono::steady_clock::now();

    for (int iter = 0; iter < opt.iterations; ++iter) {
        const auto k0 = std::chrono::steady_clock::now();
        do {
            queue.parallel_for(sycl::range<1>(opt.elements), [=](sycl::id<1> idx) {
                const size_t i = idx[0];
                double v = x[i];
                for (int inner = 0; inner < 16; ++inner) {
                    v = v * 1.0000001 + 0.0000003;
                }
                x[i] = v;
            }).wait();
        } while (std::chrono::steady_clock::now() - k0 < std::chrono::milliseconds(opt.kernel_ms));
        const auto k1 = std::chrono::steady_clock::now();
        kernel_s += std::chrono::duration<double>(k1 - k0).count();

        const auto g0 = std::chrono::steady_clock::now();
        if (opt.gap_mode == "sleep") {
            std::this_thread::sleep_for(std::chrono::milliseconds(opt.gap_ms));
        }
        else if (opt.gap_mode == "cpu") {
            cpu_gap_ms(opt.gap_ms, sink);
        }
        else {
            std::cerr << "Unsupported gap mode: " << opt.gap_mode << "\n";
            return 2;
        }
        const auto g1 = std::chrono::steady_clock::now();
        gap_s += std::chrono::duration<double>(g1 - g0).count();
    }

    const double runtime_s = std::chrono::duration<double>(std::chrono::steady_clock::now() - total0).count();
    double checksum = 0.0;
    const size_t stride = std::max<size_t>(1, opt.elements / 1024);
    for (size_t i = 0; i < opt.elements; i += stride) {
        checksum += x[i];
    }

    std::cout << std::setprecision(10)
              << "benchmark=gpu-bursty-idle\n"
              << "workload_type=gpu_bursty_idle\n"
              << "device=" << queue.get_device().get_info<sycl::info::device::name>() << "\n"
              << "kernel_ms=" << opt.kernel_ms << "\n"
              << "gap_ms=" << opt.gap_ms << "\n"
              << "iterations=" << opt.iterations << "\n"
              << "gap_mode=" << opt.gap_mode << "\n"
              << "runtime_s=" << runtime_s << "\n"
              << "kernel_s=" << kernel_s << "\n"
              << "gap_s=" << gap_s << "\n"
              << "checksum=" << checksum + sink * 1.0e-30 << "\n";

    sycl::free(x, queue);
    return std::isfinite(checksum) ? 0 : 1;
}
