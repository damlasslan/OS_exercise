# Instructor Script — Week 6 · CPU Scheduling

The full step-by-step script (Turkish) is the Word file *Week6_Ders_Senaryosu_v3.docx*; slide numbers refer to
*Week6_CPU_Scheduling_101_Visual_StepByStep_v3.pptx* (PPT) and to the site's Lecture Mode (LM).

Teaching pattern for every demo: **Predict → Run → Observe → Explain**, across four layers
(application code → OS kernel → run on site → result).

## Plan (180 minutes)

| Time | PPT | LM | Content |
| --- | --- | --- | --- |
| 00–45 | 1–25 | 1–9 | Big picture, process states, OSTEP, Demo 1, thread-level scheduling (optional: PPT 119–120 measure it yourself) |
| 45–70 | 26–42 | 10–13 | Concurrency vs parallelism, four cases, blocking, Demo 2 (lost update, mutex) |
| 70–100 | 43–64 | 14 + Real-World | Four real systems (synchronization + scheduling), preemption; Round Robin is first named on LM 14 |
| 100–110 | — | — | Break |
| 110–160 | 65–103 | 15–20 | FCFS, SJF, SRTF, Demo 3, Demo 4 (Round Robin quantum), Priority, MLFQ, metrics, practice |
| 160–180 | 104–118 | 21–22 | Multicore, bank example, wrap-up |

## Key messages

- A blocked thread uses no CPU; the OS runs another READY thread (Demo 1, thread demo).
- main (T0) is the process's first thread: like a parent it creates T1 and T2 and waits in `pthread_join` (cf. `fork()`/`wait()` in Week 3).
- `counter++` is LOAD → ADD → STORE; unsynchronized shared state loses updates even on one core (Demo 2).
- Same jobs, different policy, different waiting time (Demos 3–4).
- Measure first: `real ≈ user + sys` → CPU-bound; `real ≫ user + sys` → the program waits — find out where (I/O, lock, sleep, run queue).
- Scheduling ≠ synchronization: speed and timing come from the scheduler, correctness from locks, transactions and atomic operations.
