#include <mpi.h>

#include <chrono>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <string>
#include <thread>

namespace {

struct Options {
    int compute_ms = 20;
    int wait_ms = 20;
    int iterations = 100;
    int skew_rank = -1;
    std::string mode = "barrier";
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
        if (arg == "--compute-ms") {
            opt.compute_ms = parse_int("--compute-ms", value("--compute-ms"));
        }
        else if (arg == "--wait-ms") {
            opt.wait_ms = parse_int("--wait-ms", value("--wait-ms"));
        }
        else if (arg == "--iterations") {
            opt.iterations = parse_int("--iterations", value("--iterations"));
        }
        else if (arg == "--skew-rank") {
            opt.skew_rank = parse_int("--skew-rank", value("--skew-rank"));
        }
        else if (arg == "--mode") {
            opt.mode = value("--mode");
        }
        else if (arg == "-h" || arg == "--help") {
            std::cout << "mpi_idle_wait --compute-ms N --wait-ms N --iterations N --mode barrier|allreduce\n";
            std::exit(0);
        }
        else {
            std::cerr << "Unknown argument: " << arg << "\n";
            std::exit(2);
        }
    }
    return opt;
}

void busy_for_ms(int ms, int rank, volatile double &sink)
{
    const auto end = std::chrono::steady_clock::now() + std::chrono::milliseconds(ms);
    double x = 1.0 + rank;
    while (std::chrono::steady_clock::now() < end) {
        for (int i = 0; i < 2048; ++i) {
            x = std::sin(x) + std::cos(x * 0.5) + 1.0000001;
        }
    }
    sink += x;
}

} // namespace

int main(int argc, char **argv)
{
    MPI_Init(&argc, &argv);
    const Options opt = parse_args(argc, argv);

    int rank = 0;
    int size = 1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    MPI_Barrier(MPI_COMM_WORLD);
    const double t0 = MPI_Wtime();
    double compute_s = 0.0;
    double wait_s = 0.0;
    volatile double sink = 0.0;

    for (int iter = 0; iter < opt.iterations; ++iter) {
        const double c0 = MPI_Wtime();
        busy_for_ms(opt.compute_ms, rank, sink);
        compute_s += MPI_Wtime() - c0;

        if (rank == opt.skew_rank && opt.wait_ms > 0) {
            std::this_thread::sleep_for(std::chrono::milliseconds(opt.wait_ms));
        }

        const double w0 = MPI_Wtime();
        if (opt.mode == "barrier") {
            MPI_Barrier(MPI_COMM_WORLD);
        }
        else if (opt.mode == "allreduce") {
            double in = sink + rank;
            double out = 0.0;
            MPI_Allreduce(&in, &out, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
            sink += out * 1.0e-30;
        }
        else {
            if (rank == 0) {
                std::cerr << "Unsupported mode: " << opt.mode << "\n";
            }
            MPI_Abort(MPI_COMM_WORLD, 2);
        }
        wait_s += MPI_Wtime() - w0;
    }
    MPI_Barrier(MPI_COMM_WORLD);
    const double runtime_s = MPI_Wtime() - t0;

    double max_runtime_s = 0.0;
    double max_compute_s = 0.0;
    double max_wait_s = 0.0;
    MPI_Reduce(&runtime_s, &max_runtime_s, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    MPI_Reduce(&compute_s, &max_compute_s, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    MPI_Reduce(&wait_s, &max_wait_s, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        std::cout << "benchmark=mpi-idle-wait\n"
                  << "workload_type=mpi_slack\n"
                  << "ranks=" << size << "\n"
                  << "mode=" << opt.mode << "\n"
                  << "compute_ms=" << opt.compute_ms << "\n"
                  << "wait_ms=" << opt.wait_ms << "\n"
                  << "iterations=" << opt.iterations << "\n"
                  << "runtime_s=" << max_runtime_s << "\n"
                  << "compute_s=" << max_compute_s << "\n"
                  << "wait_s=" << max_wait_s << "\n";
    }

    MPI_Finalize();
    return 0;
}
