# Instructor Script — OS Exercise Lab

## Opening

Today we will not write kernel code. We will observe operating-system behavior through simulations.

The teaching flow is:

```text
Predict → Run → Observe → Explain
```

## Scenario 1 — Process States

Ask before running:

> If one process waits for I/O, should the CPU stay idle?

Run the CPU-bound vs I/O-bound scenario.

Explain:

- A process may be READY but not running.
- A process waiting for I/O is not using the CPU.
- The scheduler can run another READY process.

## Scenario 2 — CPU Scheduling

Use the same workload with FCFS, SJF and Round Robin.

Ask:

> Did the jobs change? Did the CPU change? What changed?

Explain:

Only the scheduling policy changed; waiting time and turnaround time changed.

## Scenario 3 — Threads and Data Race

Ask:

> If two threads each add 1 to counter=5, what should the result be?

Show safe execution first, then interleaved execution.

Explain:

- `counter++` is not necessarily one atomic step.
- It can be LOAD → ADD → STORE.
- If both threads load the old value, one update can be lost.

Main message:

> Multithreading is not the problem. Unsynchronized shared state is the problem.
