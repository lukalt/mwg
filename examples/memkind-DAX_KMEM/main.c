#include <time.h>
#include <errno.h>
#include <stdio.h>
#include <unistd.h>
#include <memkind.h>
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
    memkind_t kind = MEMKIND_DAX_KMEM;
    printf("Allocating on memkind 'MEMKIND_DAX_KMEM'\n");
    long N = ((long) 1*256000000)/sizeof(double);
    double* A;
    A = (double*) memkind_malloc(kind, sizeof(double) * (size_t) N);
    if(A == NULL) {
            printf("err: failed to allocate\n");
        return 1;
    }
    printf("Allocated buffer A of size N\n");
    for (int i = 0; i < N; i++) {
        A[i] = 0.0;
    }
    printf("Initialization of A completed\n");
    double* B;
    B = (double*) memkind_malloc(kind, sizeof(double) * (size_t) N);
    if(B == NULL) {
            printf("err: failed to allocate\n");
        return 1;
    }
    printf("Allocated buffer B of size N\n");
    double temp = 0;
    temp = 1;


    // Actual code
    double result = 0.0;
    time_t begin = time(NULL);
    for (int i = 0; i < N - 2; i += 1) {
        B[i] = A[i];
    }
    printf("Temp: %f\n", temp);
    result = A[0]; // do not optimize away loop
    double time_spent = (double)(time(NULL) - begin);
    printf("Computation took: %.3fs\n", time_spent);
    printf("Result: %f\n", result);
    printf("Workload has been completed. Cleaning up...\n");


    // Finalization
    memkind_free(kind, A);
    memkind_free(kind, B);


    return 0;
}