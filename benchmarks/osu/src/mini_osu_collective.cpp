#include <mpi.h>

#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

namespace {

struct Options {
    std::string collective = "allreduce";
    int min_bytes = 1;
    int max_bytes = 1024 * 1024;
    int iters = 100;
    int warmup = 10;
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

void parse_range(const std::string &range, Options &opt)
{
    const size_t colon = range.find(':');
    if (colon == std::string::npos) {
        opt.min_bytes = parse_int("-m", range.c_str());
        opt.max_bytes = opt.min_bytes;
        return;
    }
    opt.min_bytes = parse_int("-m", range.substr(0, colon).c_str());
    opt.max_bytes = parse_int("-m", range.substr(colon + 1).c_str());
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
        if (arg == "--collective") {
            opt.collective = value("--collective");
        }
        else if (arg == "-m" || arg == "--message-range") {
            parse_range(value(arg.c_str()), opt);
        }
        else if (arg == "--iters") {
            opt.iters = parse_int("--iters", value("--iters"));
        }
        else if (arg == "--warmup") {
            opt.warmup = parse_int("--warmup", value("--warmup"));
        }
        else if (arg == "-h" || arg == "--help") {
            std::cout << "mini_osu_collective --collective allreduce|alltoall -m MIN:MAX --iters N\n";
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
    MPI_Init(&argc, &argv);
    const Options opt = parse_args(argc, argv);

    int rank = 0;
    int size = 1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    double total_s = 0.0;
    double max_latency_us = 0.0;
    int samples = 0;

    for (int bytes = opt.min_bytes; bytes <= opt.max_bytes; bytes *= 2) {
        const int count = std::max(1, bytes / (int)sizeof(double));
        std::vector<double> send((opt.collective == "alltoall" ? count * size : count), rank + 1.0);
        std::vector<double> recv((opt.collective == "alltoall" ? count * size : count), 0.0);

        for (int iter = 0; iter < opt.warmup; ++iter) {
            if (opt.collective == "allreduce") {
                MPI_Allreduce(send.data(), recv.data(), count, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
            }
            else if (opt.collective == "alltoall") {
                MPI_Alltoall(send.data(), count, MPI_DOUBLE, recv.data(), count, MPI_DOUBLE, MPI_COMM_WORLD);
            }
            else {
                if (rank == 0) {
                    std::cerr << "Unsupported collective: " << opt.collective << "\n";
                }
                MPI_Abort(MPI_COMM_WORLD, 2);
            }
        }

        MPI_Barrier(MPI_COMM_WORLD);
        const double t0 = MPI_Wtime();
        for (int iter = 0; iter < opt.iters; ++iter) {
            if (opt.collective == "allreduce") {
                MPI_Allreduce(send.data(), recv.data(), count, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
            }
            else {
                MPI_Alltoall(send.data(), count, MPI_DOUBLE, recv.data(), count, MPI_DOUBLE, MPI_COMM_WORLD);
            }
        }
        MPI_Barrier(MPI_COMM_WORLD);
        const double elapsed = MPI_Wtime() - t0;
        const double latency_us = elapsed / opt.iters * 1.0e6;
        total_s += elapsed;
        max_latency_us = std::max(max_latency_us, latency_us);
        samples += 1;
    }

    if (rank == 0) {
        std::cout << "benchmark=osu\n"
                  << "workload_type=mpi_communication\n"
                  << "collective=" << opt.collective << "\n"
                  << "ranks=" << size << "\n"
                  << "min_bytes=" << opt.min_bytes << "\n"
                  << "max_bytes=" << opt.max_bytes << "\n"
                  << "iters=" << opt.iters << "\n"
                  << "samples=" << samples << "\n"
                  << "runtime_s=" << total_s << "\n"
                  << "latency_us=" << max_latency_us << "\n";
    }

    MPI_Finalize();
    return 0;
}
