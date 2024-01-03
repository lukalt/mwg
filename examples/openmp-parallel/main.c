#include <time.h>
#include <errno.h>
#include <stdio.h>
#include <unistd.h>
#include <omp.h>
#include <stdlib.h>
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
    long N = ((long) 1*256000000)/sizeof(double);
    double* A;
    A = (double*) malloc(sizeof(double) * (long) N);
    printf("Generated unaligned buffer of size %ld elements\n", N);
    #pragma omp parallel for
    for (int i = 0; i < N; i++) {
        A[i] = 0.0;
    }
    printf("Initialization of A completed\n");
    double* B;
    B = (double*) malloc(sizeof(double) * (long) N);
    printf("Generated unaligned buffer of size %ld elements\n", N);
    double temp = 0;
    temp = 1;


    // Actual code
    double result = 0.0;
    double begin = omp_get_wtime();
    #pragma omp parallel for firstprivate(A) lastprivate(temp)
    for (int i = 0; i < N - 2; i += 1) {
        B[i] = A[i];
    }
    printf("Temp: %f\n", temp);
    result = A[0]; // do not optimize away loop
    double time_spent = omp_get_wtime() - begin;
    printf("Computation took: %.3fs\n", time_spent);
    printf("Result: %f\n", result);
    printf("Workload has been completed. Cleaning up...\n");


    // Finalization
    free(A);
    free(B);


    return 0;
}