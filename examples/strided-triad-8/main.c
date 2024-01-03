#include <time.h>
#include <errno.h>
#include <stdio.h>
#include <unistd.h>
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
    long N = ((long) 8*170666666)/sizeof(double);
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
    for (int i = 0; i < N; i++) {
        B[i] = 0.0;
    }
    printf("Initialization of B completed\n");
    double* C;
    C = (double*) malloc(sizeof(double) * (long) N);
    printf("Generated unaligned buffer of size %ld elements\n", N);
    double temp = 0;
    temp = 1;


    // Actual code
    double result = 0.0;
    time_t begin = time(NULL);
    for (int i = 0; i < N - 9; i += 8) {
        C[i] = A[i] + 3 * B[i];
    }
    printf("Temp: %f\n", temp);
    result = A[0]; // do not optimize away loop
    double time_spent = (double)(time(NULL) - begin);
    printf("Computation took: %.3fs\n", time_spent);
    printf("Result: %f\n", result);
    printf("Workload has been completed. Cleaning up...\n");


    // Finalization
    free(A);
    free(B);
    free(C);


    return 0;
}