#include <time.h>
#include <errno.h>
#include <stdio.h>
#include <unistd.h>
#include <numa.h>
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
    if (numa_available() == -1) {
      printf("err: libnuma not available\n");
      return 0;
    }
    long N = ((long) 1*256000000)/sizeof(double);
    double* A;
    A = (double*) numa_alloc_onnode(sizeof(double) * (long) N, 2);
    if(A == NULL) {
      printf("err: failed to allocate on numa\n");
      return 1;
    }
    printf("Allocated 512000000 array elements using libnuma\n");
    for (int i = 0; i < N; i++) {
        A[i] = 0.0;
    }
    printf("Initialization of A completed\n");
    double* B;
    B = (double*) numa_alloc_onnode(sizeof(double) * (long) N, 2);
    if(B == NULL) {
      printf("err: failed to allocate on numa\n");
      return 1;
    }
    printf("Allocated 512000000 array elements using libnuma\n");
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
    numa_free(A, sizeof(double) * N);
    numa_free(B, sizeof(double) * N);


    return 0;
}