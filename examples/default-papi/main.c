#include <time.h>
#include <errno.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
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
    long N = ((long) 1*256000000)/sizeof(double);
    double* A;
    A = (double*) malloc(sizeof(double) * (long) N);
    printf("Generated unaligned buffer of size %ld elements\n", N);
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
    if(PAPI_hl_region_begin("main") != PAPI_OK) { printf("Failed to begin PAPI region main\n"); }
    double result = 0.0;
    time_t begin = time(NULL);
    for (int i = 0; i < N - 2; i += 1) {
        B[i] = A[i];
    }
    printf("Temp: %f\n", temp);
    result = A[0]; // do not optimize away loop
    double time_spent = (double)(time(NULL) - begin);
    if(PAPI_hl_region_end("main") != PAPI_OK) { printf("Failed to end PAPI region main\n"); }
    printf("Computation took: %.3fs\n", time_spent);
    printf("Result: %f\n", result);
    printf("Workload has been completed. Cleaning up...\n");


    // Finalization
    free(A);
    free(B);
    if(PAPI_hl_stop() != PAPI_OK) { printf("Failed to stop PAPI hl API"); }


    return 0;
}