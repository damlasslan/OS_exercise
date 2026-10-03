# OS Exercise Lab

A no-code Operating Systems teaching interface built for classroom demos.

The app provides a Streamlit web interface for OSTEP-style simulations:

- Process states: READY, RUNNING, WAITING
- CPU scheduling: FCFS, SJF, Round Robin
- Threads, interleaving, lost update, data race

## Architecture

```text
Browser / Streamlit UI
        ↓
User selects scenario parameters
        ↓
Streamlit backend
        ↓
OSTEP Python scripts / classroom visualizer
        ↓
Visual output for teaching
```

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app automatically downloads the official OSTEP homework repository when it first needs it.

## Deploy online with Streamlit Community Cloud

1. Create a public GitHub repository named `OS_exercise`.
2. Upload these files to the repository.
3. Go to Streamlit Community Cloud.
4. Choose the repository.
5. Set the main file path to:

```text
app.py
```

6. Deploy.

## Classroom use

Recommended pattern:

```text
Predict → Run → Observe → Explain
```

Recommended demo order:

1. CPU-bound vs I/O-bound process
2. Same jobs with different scheduling policies
3. Two threads incrementing one shared counter

## Credits

This app is designed as a teaching interface around the concepts and simulation style of OSTEP: Operating Systems: Three Easy Pieces.
