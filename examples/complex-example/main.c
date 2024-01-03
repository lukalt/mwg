#include <time.h>
#include <errno.h>
#include <stdio.h>
#include <unistd.h>
#include <omp.h>
#include <memkind.h>
#include "papi.h"
#include <math.h>




void msleep(long msec)
{
    struct timespec sleep_duration;
    sleep_duration.tv_sec = 0;
    sleep_duration.tv_nsec = msec * 1000 * 1000;
    nanosleep(&sleep_duration, NULL);
}

int main(int argc, char* argv[]) {
    // Initialization
    printf("Using OpenMP parallel implementation with %d threads\n", omp_get_max_threads());
    memkind_t kind = MEMKIND_DAX_KMEM;
    printf("Allocating on memkind 'MEMKIND_DAX_KMEM'\n");
    long N = ((long) 8*170666666)/sizeof(float);
    float* A;
    A = (float*) memkind_malloc(kind, sizeof(float) * (size_t) N);
    if(A == NULL) {
            printf("err: failed to allocate\n");
        return 1;
    }
    printf("Allocated buffer A of size N\n");
    #pragma omp parallel for
    for (int i = 0; i < N; i++) {
        A[i] = 0.0;
    }
    printf("Initialization of A completed\n");
    float* B;
    B = (float*) memkind_malloc(kind, sizeof(float) * (size_t) N);
    if(B == NULL) {
            printf("err: failed to allocate\n");
        return 1;
    }
    printf("Allocated buffer B of size N\n");
    #pragma omp parallel for
    for (int i = 0; i < N; i++) {
        B[i] = 0.0;
    }
    printf("Initialization of B completed\n");
    float* C;
    C = (float*) memkind_malloc(kind, sizeof(float) * (size_t) N);
    if(C == NULL) {
            printf("err: failed to allocate\n");
        return 1;
    }
    printf("Allocated buffer C of size N\n");
    float temp = 0;
    temp = 1;


    // Actual code
    if(PAPI_hl_region_begin("main") != PAPI_OK) { printf("Failed to begin PAPI region main\n"); }
    double result = 0.0;
    double begin = omp_get_wtime();
    #pragma omp parallel for firstprivate(A, B) lastprivate(temp)
    for (int i = 0; i < N - 24; i += 23) {
        for (int j = 0; j < 16; j += 1) {
            C[i + j] = A[i + j] + 3 * B[i + j];
        }
    }
    printf("Temp: %f\n", temp);
    result = A[0]; // do not optimize away loop
    double time_spent = omp_get_wtime() - begin;
    if(PAPI_hl_region_end("main") != PAPI_OK) { printf("Failed to end PAPI region main\n"); }
    printf("Computation took: %.3fs\n", time_spent);
    printf("Result: %f\n", result);
    printf("Workload has been completed. Cleaning up...\n");


    // Finalization
    memkind_free(kind, A);
    memkind_free(kind, B);
    memkind_free(kind, C);
    if(PAPI_hl_stop() != PAPI_OK) { printf("Failed to stop PAPI hl API"); }


    return 0;
}