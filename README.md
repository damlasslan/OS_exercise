# OS Exercise Lab

A no-code Operating Systems teaching site for CENG 331 (Week 6 · CPU Scheduling), built with Streamlit and the OSTEP homework simulators.

Live: https://damlasslan-os-exercise.streamlit.app/

## What is on the site

| Tab | Content |
| --- | --- |
| 🎓 Lecture Mode | 22 slides: OSTEP and the four layers, process states, Demo 1 (SWITCH_ON_IO / SWITCH_ON_END), thread-level scheduling (main/T0, T1, T2) with real measurement, concurrency vs parallelism, Demo 2 (lost update + mutex), preemption, FCFS/SJF/SRTF, Demo 3 and 4 (Round Robin quantum), Priority/MLFQ, metrics, multicore |
| Overview | What the lab is for |
| 1 Process States | OSTEP `process-run.py` with parameter explanations (what they mean, real-life examples, how to measure) |
| 2 Threads & Data Race | 2a thread-level scheduling simulator · 2b lost update (table + OSTEP `x86.py`) · 2c real measurement of `real/thread_demo.c` on the server |
| 3 CPU Scheduling | FCFS / SJF / Round Robin Gantt charts for 2–4 processes |
| 4 Real-World Systems | Banking, robotic surgery, ticket reservation, video streaming — each with a synchronization demo and a scheduling demo; then four engineering-decision slides (criteria per system, decision matrix, an interactive "choose the metric" exercise, who makes the scheduling decision) |
| Instructor Notes | Teaching order and the four-layer pattern |

Every live demo follows four layers: **application code → OS kernel pseudocode → run on site → observed result**.
Each slide has a collapsed 📝 instructor panel (Turkish + English): notes, questions with answers, the board drawing and a board video.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The OSTEP homework repository is downloaded on first use. The real-measurement panel needs Linux and `gcc`
(on Streamlit Community Cloud `packages.txt` installs `build-essential`).

## Repository layout

```text
app.py                 the whole site
real/thread_demo.c     the POSIX threads program measured on the server
assets/board/          board drawings (JPG) and their narration steps (manifest.json, TR + EN)
assets/video/          board videos with Turkish captions; assets/video/en/ with English captions
docs/instructor_script.md
```

## Credits

Simulators: OSTEP — *Operating Systems: Three Easy Pieces*, R. H. and A. C. Arpaci-Dusseau,
https://pages.cs.wisc.edu/~remzi/OSTEP/ and https://github.com/remzi-arpacidusseau/ostep-homework
