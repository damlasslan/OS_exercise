# Instructor Script — Week 6 · CPU Scheduling

The full step-by-step script (Turkish) is the Word file *Week6_Ders_Senaryosu_v3.docx*; slide numbers refer to
*Week6_CPU_Scheduling_101_Visual_StepByStep_v3.pptx* (PPT) and to the site's Lecture Mode (LM).

Teaching pattern for every demo: **Predict → Run → Observe → Explain**, across four layers
(application code → OS kernel → run on site → result).

## Plan (180 minutes)

| Time | PPT | LM | Content |
| --- | --- | --- | --- |
| 00–45 | 1–28 | 1–9 | Big picture, process states, OSTEP, Demo 1, thread-level scheduling: roles and snapshot, I/O-bound ≠ CPU-free, activities that do not execute as CPU threads, application vs OS vs hardware (optional: PPT 127–128 measure it yourself) |
| 45–70 | 29–45 | 10–13 | Concurrency vs parallelism, four cases, blocking, Demo 2 (lost update, mutex) (optional: PPT 129–130 Week 5 tools seen by the scheduler, spinlock vs mutex) |
| 70–100 | 46–67 | 14 + Real-World 1–16 | Five real systems (synchronization + scheduling, real mechanisms, video rendering), preemption; Round Robin is first named on LM 14 |
| 100–110 | — | — | Break |
| 110–160 | 68–111 | 15–20 + Real-World 17–21 | FCFS, SJF, SRTF, Demo 3, Demo 4 (which quantum performs best?), engineering decisions (PPT 86–90), Priority, MLFQ, metrics, practice |
| 160–180 | 112–126 | 21–22 | Multicore, bank example, wrap-up |

## Key messages

- A blocked thread uses no CPU; the OS runs another READY thread (Demo 1, thread demo).
- I/O-bound ≠ CPU-free: a file reader runs CPU instructions to request I/O and to process the data; it is CPU-free only while the device works. Disk, DMA and NIC activity have no thread states.
- A woken thread becomes READY first; when it runs depends on the ready-queue order and the scheduler, not only the quantum.
- main (T0) is the process's first thread: like a parent it creates T1 and T2 and waits in `pthread_join` (cf. `fork()`/`wait()` in Week 3).
- `counter++` is LOAD → ADD → STORE; unsynchronized shared state loses updates even on one core (Demo 2).
- Week 5's five tools seen by the scheduler (LM 13): mutex, semaphore and condition variable make a waiter BLOCKED; a spinlock leaves it RUNNING and burning CPU (live: 1 core 15 vs 13 ticks, 2 cores 9 vs 10); an atomic operation never waits.
- Same jobs, different policy, different waiting time (Demos 3–4).
- Each policy asks one question — FCFS: who came first? SJF: who has the shortest job? RR: who is next in the queue? RR does not favour short jobs; it favours turn-taking (Demo 3).
- Measure first: `real ≈ user + sys` → CPU-bound; `real ≫ user + sys` → the program waits — find out where (I/O, lock, sleep, run queue).
- There is no universally best scheduling policy: the best choice depends on requirements, workload and trade-offs. Best response time ≠ best overall performance (Demo 4: q = 1 has the most switches); quantum size is an engineering trade-off; developers design the workload, the OS schedules it.
- Don't start by choosing an algorithm; start by identifying the engineering problem: Problem → Requirement → Mechanism → Verification (five real systems incl. video rendering; complementary deck Week6_Five_Engineering_Cases.pptx).
- Scheduling ≠ synchronization: speed and timing come from the scheduler, correctness from locks, transactions and atomic operations.
