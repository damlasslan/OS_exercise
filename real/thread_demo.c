/* thread_demo.c — the program from Week 6, slides 22-25.
 * One process, two worker threads:
 *   T1 (reader)     prints, blocks in sleep(), prints   -> waits without using the CPU
 *   T2 (calculator) prints, runs a CPU loop, prints     -> pure CPU work
 * main waits for both with pthread_join().
 *
 * Optional arguments (used by the OS Exercise Lab measurement page):
 *   argv[1] = seconds T1 sleeps        (default 3; 0 = no sleep -> CPU-bound run)
 *   argv[2] = loop iterations for T2   (default 100000000)
 *
 * Build: gcc -O0 -pthread thread_demo.c -o thread_demo
 */
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <unistd.h>

static unsigned int sleep_seconds = 3;
static unsigned long iterations = 100000000UL;

void *reader(void *arg) {
    (void)arg;
    printf("T1: Waiting for I/O...\n");
    fflush(stdout);
    if (sleep_seconds > 0)
        sleep(sleep_seconds);          /* blocking wait, no CPU */
    printf("T1: Finished waiting!\n");
    fflush(stdout);
    return NULL;
}

void *calculator(void *arg) {
    (void)arg;
    printf("T2: Starting calculation...\n");
    fflush(stdout);
    volatile unsigned long result = 0;
    for (unsigned long i = 0; i < iterations; i++)
        result += i;                   /* CPU work */
    printf("T2: Calculation finished!\n");
    fflush(stdout);
    return NULL;
}

int main(int argc, char **argv) {
    if (argc > 1) sleep_seconds = (unsigned int)strtoul(argv[1], NULL, 10);
    if (argc > 2) iterations = strtoul(argv[2], NULL, 10);

    pthread_t t1, t2;
    pthread_create(&t1, NULL, reader, NULL);
    pthread_create(&t2, NULL, calculator, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return 0;
}
