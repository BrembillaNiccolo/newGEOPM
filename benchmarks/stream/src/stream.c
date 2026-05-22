#define _POSIX_C_SOURCE 200809L

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#ifndef STREAM_ARRAY_SIZE
#define STREAM_ARRAY_SIZE 10000000
#endif

#ifndef NTIMES
#define NTIMES 10
#endif

static double now_s(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + 1.0e-9 * (double)ts.tv_nsec;
}

static void *checked_alloc(size_t bytes)
{
    void *ptr = NULL;
    if (posix_memalign(&ptr, 64, bytes) != 0 || ptr == NULL) {
        fprintf(stderr, "allocation failed for %zu bytes\n", bytes);
        exit(1);
    }
    return ptr;
}

int main(void)
{
    const size_t n = STREAM_ARRAY_SIZE;
    const double scalar = 3.0;
    double *a = (double *)checked_alloc(n * sizeof(double));
    double *b = (double *)checked_alloc(n * sizeof(double));
    double *c = (double *)checked_alloc(n * sizeof(double));

#pragma omp parallel for schedule(static)
    for (size_t i = 0; i < n; ++i) {
        a[i] = 1.0;
        b[i] = 2.0;
        c[i] = 0.0;
    }

    double best_triad_s = 1.0e300;
    double total_s = 0.0;
    for (int iter = 0; iter < NTIMES; ++iter) {
        double t0 = now_s();
#pragma omp parallel for schedule(static)
        for (size_t i = 0; i < n; ++i) {
            c[i] = a[i] + scalar * b[i];
        }
        double t1 = now_s();
        const double elapsed = t1 - t0;
        if (elapsed < best_triad_s) {
            best_triad_s = elapsed;
        }
        total_s += elapsed;
    }

    double checksum = 0.0;
#pragma omp parallel for reduction(+ : checksum) schedule(static)
    for (size_t i = 0; i < n; ++i) {
        checksum += c[i];
    }

    const double bytes = 3.0 * (double)n * sizeof(double);
    const double triad_bandwidth_mb_s = bytes / best_triad_s / 1.0e6;

    printf("benchmark=stream\n");
    printf("workload_type=cpu_memory\n");
    printf("array_size=%zu\n", n);
    printf("iters=%d\n", NTIMES);
    printf("runtime_s=%.10f\n", total_s);
    printf("best_triad_s=%.10f\n", best_triad_s);
    printf("triad_bandwidth_mb_s=%.10f\n", triad_bandwidth_mb_s);
    printf("checksum=%.10f\n", checksum);

    if (!isfinite(checksum)) {
        fprintf(stderr, "checksum is not finite\n");
        return 1;
    }

    free(a);
    free(b);
    free(c);
    return 0;
}
