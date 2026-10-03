import os
import sys
import zipfile
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

import pandas as pd
import streamlit as st

OSTEP_URL = "https://github.com/remzi-arpacidusseau/ostep-homework/archive/refs/heads/master.zip"
BASE_DIR = Path(__file__).parent
# Store the downloaded OSTEP backend in /tmp on Streamlit Cloud.
# This avoids cross-device move errors with Streamlit's mounted source tree.
OSTEP_DIR = Path(tempfile.gettempdir()) / "ostep-homework"

st.set_page_config(page_title="OS Exercise Lab", page_icon="🧠", layout="wide")

CSS = """
<style>
.block-container {padding-top: 1.7rem; padding-bottom: 2rem; max-width: 1200px;}
.big-card {border: 1px solid #E5E7EB; border-radius: 18px; padding: 20px; background: #F8FAFC; margin: 8px 0 16px 0;}
.good {color:#047857; font-weight:700;}
.warn {color:#B45309; font-weight:700;}
.bad {color:#B91C1C; font-weight:700;}
.small {font-size: 0.92rem; color:#4B5563;}
.codebox {font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background:#111827; color:#F9FAFB; padding:12px; border-radius:12px; white-space:pre-wrap; font-size:0.88rem;}
.state-run {background:#DCFCE7; color:#166534; padding:4px 8px; border-radius:10px; font-weight:700;}
.state-ready {background:#FEF3C7; color:#92400E; padding:4px 8px; border-radius:10px; font-weight:700;}
.state-wait {background:#DBEAFE; color:#1E40AF; padding:4px 8px; border-radius:10px; font-weight:700;}
.slide-card {border:1px solid #CBD5E1; border-radius:24px; padding:28px 32px; background:white; margin:18px 0 14px 0; box-shadow:0 6px 24px rgba(15,23,42,.06);}
.slide-kicker {font-size:.82rem; letter-spacing:.08em; text-transform:uppercase; color:#64748B; font-weight:700;}
.slide-title {font-size:2rem; line-height:1.15; font-weight:800; margin:.35rem 0 1rem 0; color:#0F172A;}
.slide-body {font-size:1.08rem; line-height:1.65; color:#334155;}
.flow {font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background:#F8FAFC; border:1px dashed #94A3B8; padding:14px 18px; border-radius:14px; font-weight:700; text-align:center; margin:12px 0;}
.demo-label {display:inline-block;background:#0F172A;color:#fff;padding:5px 10px;border-radius:999px;font-size:.78rem;font-weight:700;margin-bottom:6px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def ensure_ostep():
    """Download OSTEP homework if it is not already present."""
    marker = OSTEP_DIR / "cpu-intro" / "process-run.py"
    if marker.exists():
        return True, "OSTEP repository is available locally."

    try:
        # Clean up any incomplete prior download.
        if OSTEP_DIR.exists():
            shutil.rmtree(OSTEP_DIR, ignore_errors=True)

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            zip_path = td_path / "ostep.zip"
            urllib.request.urlretrieve(OSTEP_URL, zip_path)

            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(td_path)

            extracted = td_path / "ostep-homework-master"
            if not extracted.exists():
                return False, "OSTEP archive was downloaded, but its extracted folder was not found."

            # copytree works safely even when source and destination are on
            # different filesystems/mounts.
            shutil.copytree(extracted, OSTEP_DIR)

        if not marker.exists():
            return False, "OSTEP repository was copied, but process-run.py is missing."

        return True, "OSTEP repository downloaded successfully."
    except Exception as e:
        return False, f"Could not download OSTEP repository: {e}"


def run_ostep(folder, script, args):
    ok, msg = ensure_ostep()
    if not ok:
        return False, msg, ""
    cwd = OSTEP_DIR / folder
    cmd = [sys.executable, script] + args
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=20)
        output = p.stdout.strip()
        err = p.stderr.strip()
        if p.returncode != 0:
            return False, "Command failed.", output + "\n" + err
        return True, "Command completed.", output
    except Exception as e:
        return False, "Execution error.", str(e)


def output_box(text):
    st.markdown(f"<div class='codebox'>{text}</div>", unsafe_allow_html=True)


def scenario_card(title, observe, explain):
    st.markdown(f"""
    <div class='big-card'>
    <h4>{title}</h4>
    <p><b>Observe:</b> {observe}</p>
    <p><b>Explain:</b> {explain}</p>
    </div>
    """, unsafe_allow_html=True)


def gantt_fcfs(jobs):
    t=0; rows=[]; metrics=[]
    for name, arrival, burst in sorted(jobs, key=lambda x:(x[1],x[0])):
        if t < arrival: t = arrival
        start=t; end=t+burst; t=end
        rows.append((name,start,end))
        metrics.append({"Process":name,"Start":start,"Finish":end,"Waiting":start-arrival,"Turnaround":end-arrival,"Response":start-arrival})
    return rows, pd.DataFrame(metrics)

def gantt_sjf(jobs):
    jobs=[dict(name=n,arrival=a,burst=b,remaining=b) for n,a,b in jobs]
    t=0; rows=[]; metrics=[]; done=set()
    while len(done)<len(jobs):
        avail=[j for j in jobs if j["arrival"]<=t and j["name"] not in done]
        if not avail:
            t=min(j["arrival"] for j in jobs if j["name"] not in done); continue
        j=sorted(avail, key=lambda x:(x["burst"],x["arrival"],x["name"]))[0]
        start=t; end=t+j["burst"]; t=end; done.add(j["name"])
        rows.append((j["name"],start,end))
        metrics.append({"Process":j["name"],"Start":start,"Finish":end,"Waiting":start-j["arrival"],"Turnaround":end-j["arrival"],"Response":start-j["arrival"]})
    return rows, pd.DataFrame(metrics)

def gantt_rr(jobs, q):
    jobs={n:{"arrival":a,"burst":b,"remaining":b,"first":None,"finish":None} for n,a,b in jobs}
    t=0; rows=[]; ready=[]; seen=set()
    def add_arrivals():
        for n,j in sorted(jobs.items(), key=lambda kv:(kv[1]["arrival"],kv[0])):
            if j["arrival"]<=t and n not in seen and j["remaining"]>0:
                ready.append(n); seen.add(n)
    while any(j["remaining"]>0 for j in jobs.values()):
        add_arrivals()
        if not ready:
            t=min(j["arrival"] for n,j in jobs.items() if j["remaining"]>0 and n not in seen)
            add_arrivals()
        n=ready.pop(0); j=jobs[n]
        if j["first"] is None: j["first"]=t
        run=min(q,j["remaining"]); start=t; end=t+run; rows.append((n,start,end)); t=end; j["remaining"]-=run
        add_arrivals()
        if j["remaining"]>0: ready.append(n)
        else: j["finish"]=t
    metrics=[]
    for n,j in jobs.items():
        metrics.append({"Process":n,"Start":j["first"],"Finish":j["finish"],"Waiting":j["finish"]-j["arrival"]-j["burst"],"Turnaround":j["finish"]-j["arrival"],"Response":j["first"]-j["arrival"]})
    return rows, pd.DataFrame(metrics)

def render_gantt(rows):
    max_t=max(e for _,_,e in rows) if rows else 0
    html="<div style='display:flex;align-items:center;gap:2px;width:100%;margin:12px 0;'>"
    colors={"P1":"#DBEAFE","P2":"#DCFCE7","P3":"#FEF3C7","P4":"#FCE7F3","P5":"#EDE9FE"}
    for name,start,end in rows:
        w=max(4, (end-start)/max_t*100)
        html += f"<div style='width:{w}%;background:{colors.get(name,'#E5E7EB')};border:1px solid #CBD5E1;border-radius:8px;padding:10px 2px;text-align:center;font-weight:700;'>{name}<br><span class='small'>{start}-{end}</span></div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)



def lecture_slide(kicker, title, body_html, flow=None):
    flow_html = f"<div class='flow'>{flow}</div>" if flow else ""
    st.markdown(
        f"""
        <div class='slide-card'>
          <div class='slide-kicker'>{kicker}</div>
          <div class='slide-title'>{title}</div>
          <div class='slide-body'>{body_html}</div>
          {flow_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_process_demo(key_prefix="lecture"):
    c1,c2,c3,c4 = st.columns(4)
    with c1: p0_len = st.number_input("P0 instructions", 1, 20, 5, key=f"{key_prefix}_p0len")
    with c2: p0_cpu = st.slider("P0 CPU probability", 0, 100, 100, key=f"{key_prefix}_p0cpu")
    with c3: p1_len = st.number_input("P1 instructions", 1, 20, 5, key=f"{key_prefix}_p1len")
    with c4: p1_cpu = st.slider("P1 CPU probability", 0, 100, 0, key=f"{key_prefix}_p1cpu")
    switch = st.selectbox("Switch behavior", ["SWITCH_ON_IO", "SWITCH_ON_END"], key=f"{key_prefix}_switch")
    cmd_args=["-l", f"{p0_len}:{p0_cpu},{p1_len}:{p1_cpu}", "-S", switch, "-c", "-p"]
    with st.expander("Show the OSTEP command"):
        st.code("python cpu-intro/process-run.py " + " ".join(cmd_args), language="bash")
    if st.button("▶ Run process-state simulation", type="primary", key=f"{key_prefix}_run_process"):
        ok,msg,out=run_ostep("cpu-intro", "process-run.py", cmd_args)
        st.info(msg)
        output_box(out)

def render_scheduling_demo(key_prefix="lecture"):
    jobs=[]
    cols=st.columns(4)
    defaults=[("P1",0,8),("P2",1,4),("P3",2,2),("P4",3,5)]
    for idx,(n,a,b) in enumerate(defaults):
        with cols[idx]:
            st.markdown(f"**{n}**")
            ar=st.number_input(f"{n} arrival",0,20,a,key=f"{key_prefix}_ar{n}")
            bu=st.number_input(f"{n} burst",1,30,b,key=f"{key_prefix}_bu{n}")
            jobs.append((n,ar,bu))
    policy=st.radio("Policy", ["FCFS", "SJF", "Round Robin"], horizontal=True, key=f"{key_prefix}_policy")
    quantum=st.slider("Time Quantum (Round Robin)",1,10,2,key=f"{key_prefix}_quantum")
    if st.button("▶ Run scheduling simulation", type="primary", key=f"{key_prefix}_run_sched"):
        if policy=="FCFS": rows,metrics=gantt_fcfs(jobs)
        elif policy=="SJF": rows,metrics=gantt_sjf(jobs)
        else: rows,metrics=gantt_rr(jobs, quantum)
        render_gantt(rows)
        st.dataframe(metrics, use_container_width=True)
        c1,c2=st.columns(2)
        c1.metric("Average waiting time", round(metrics["Waiting"].mean(),2))
        c2.metric("Average turnaround time", round(metrics["Turnaround"].mean(),2))

def render_thread_demo(key_prefix="lecture"):
    initial=st.number_input("Shared counter initial value", 0, 100, 5, key=f"{key_prefix}_counter")
    mode=st.radio("Execution pattern", ["Safe execution", "Interleaved race"], horizontal=True, key=f"{key_prefix}_mode")
    if mode=="Safe execution":
        rows=[("T1","LOAD",initial), ("T1","ADD",initial+1), ("T1","STORE",initial+1),
              ("T2","LOAD",initial+1), ("T2","ADD",initial+2), ("T2","STORE",initial+2)]
        final=initial+2; expected=initial+2
    else:
        rows=[("T1","LOAD",initial), ("T2","LOAD",initial), ("T1","ADD",initial+1),
              ("T2","ADD",initial+1), ("T1","STORE",initial+1), ("T2","STORE",initial+1)]
        final=initial+1; expected=initial+2
    st.table(pd.DataFrame(rows, columns=["Thread","Step","Value seen/written"]))
    c1,c2=st.columns(2)
    c1.metric("Expected final value", expected)
    c2.metric("Actual final value", final)
    if final==expected:
        st.success("No update was lost.")
        st.caption("T1 finishes its read-modify-write sequence before T2 reads the shared value.")
    else:
        st.error("Lost update: both threads used the same old value. This is a data race.")
        st.caption("Both threads read the same old value before either STORE completes, so one increment is overwritten.")
    with st.expander("Run the real OSTEP x86.py backend"):
        interval=st.slider("Interrupt interval (-i)",1,10,1,key=f"{key_prefix}_interval")
        cmd_args=["-p","simple-race.s","-t","2","-i",str(interval),"-M","2000","-c"]
        st.code("python threads-intro/x86.py " + " ".join(cmd_args), language="bash")
        if st.button("▶ Run OSTEP thread simulation", key=f"{key_prefix}_run_thread"):
            ok,msg,out=run_ostep("threads-intro", "x86.py", cmd_args)
            st.info(msg)
            output_box(out)


def main():
    st.title("🧠 OS Exercise Lab")
    st.caption("A no-code teaching interface for OSTEP-style operating-system simulations")
    tabs = st.tabs(["🎓 Lecture Mode", "Overview", "1 Process States", "2 CPU Scheduling", "3 Threads & Data Race", "Instructor Notes"])


    with tabs[0]:
        st.header("🎓 Lecture Mode — Slides + Live OSTEP Demos")
        st.caption("Use this tab during class. Scroll from concept → prediction → live simulation → explanation.")

        lecture_slide(
            "Slide 1 · Why OSTEP?",
            "Operating Systems are easier to learn when behavior is visible",
            """
            <b>OSTEP</b> provides small simulation programs for operating-system concepts.
            We use them as a <b>simulation engine</b>, while this web app provides a classroom-friendly interface.
            <br><br>
            The goal is not to develop an OS kernel. The goal is to <b>observe OS behavior</b> and connect it to the lecture.
            """,
            "Theory → Prediction → Simulation → Evidence → Explanation"
        )

        lecture_slide(
            "Slide 2 · Architecture",
            "What is running behind this website?",
            """
            The web page does not replace OSTEP. It calls the original Python simulators in the backend.
            <br><br>
            <b>Frontend:</b> Streamlit teaching interface<br>
            <b>Backend:</b> OSTEP Python simulation scripts<br>
            <b>Student task:</b> observe, compare, explain
            """,
            "Browser → Streamlit → OSTEP Python scripts → Simulation output"
        )

        lecture_slide(
            "Slide 3 · Repository Map",
            "Which OSTEP components are we using?",
            """
            <b>cpu-intro</b> → process states and CPU/I/O behavior<br>
            <b>cpu-sched</b> → scheduling policies<br>
            <b>threads-intro</b> → threads, interleaving and shared-memory races
            <br><br>
            Later in the semester, the repository also contains virtual-memory and file-system exercises.
            """
        )

        st.divider()
        lecture_slide(
            "Slide 4 · Scenario 1",
            "A process does not continuously own the CPU",
            """
            A process can be <b>RUNNING</b>, <b>READY</b>, or <b>WAITING</b>.
            When a process requests I/O, it may become WAITING. The CPU can then execute another READY process.
            <br><br>
            <b>Prediction:</b> What should happen when an I/O-bound process starts waiting?
            """,
            "RUNNING → I/O request → WAITING   |   another READY process → RUNNING"
        )
        st.markdown("<span class='demo-label'>LIVE DEMO 1</span>", unsafe_allow_html=True)
        render_process_demo("lecture_process")
        st.info("Explain: waiting for I/O does not mean the whole CPU must wait.")

        st.divider()
        lecture_slide(
            "Slide 5 · Scenario 2",
            "Same jobs. Same CPU. Different scheduler.",
            """
            The scheduler decides <b>which runnable process/thread gets CPU time next</b>.
            Changing the scheduling policy can change waiting, turnaround and response times even when the workload is identical.
            <br><br>
            Compare <b>FCFS</b>, <b>SJF</b> and <b>Round Robin</b>.
            <br><br>
            <b>Prediction:</b> If the jobs do not change, why can waiting time change?
            """,
            "Same workload + Different policy → Different execution order → Different metrics"
        )
        st.markdown("<span class='demo-label'>LIVE DEMO 2</span>", unsafe_allow_html=True)
        render_scheduling_demo("lecture_sched")
        st.info("Explain: the workload did not change; only the scheduling decision changed.")

        st.divider()
        lecture_slide(
            "Slide 6 · One Process, Multiple Threads",
            "Threads share a process, but have separate execution states",
            """
            Threads in the same process share code, heap and global data.
            Each thread still has its own stack, registers and execution state.
            <br><br>
            Shared memory makes communication fast — but it also creates synchronization risks.
            """,
            "Process → Thread 1 + Thread 2 + ... → shared heap/global data"
        )

        lecture_slide(
            "Slide 7 · Why counter++ is dangerous",
            "One line of code may be several machine-level steps",
            """
            An increment such as <b>counter++</b> is conceptually:
            <b>LOAD → ADD → STORE</b>.
            A context switch can occur between those steps.
            <br><br>
            If two threads read the same old value before either STORE completes, one update can be lost.
            """,
            "LOAD → ADD → STORE + interleaving → possible lost update"
        )

        lecture_slide(
            "Slide 8 · Scenario 3",
            "Two threads + one shared variable = possible data race",
            """
            Multithreading itself is not the problem.
            The problem is <b>unsynchronized access to shared state</b>.
            <br><br>
            <b>Prediction:</b> Starting from counter = 5, if both threads increment once, should the final value be 6 or 7?
            """
        )
        st.markdown("<span class='demo-label'>LIVE DEMO 3</span>", unsafe_allow_html=True)
        render_thread_demo("lecture_thread")
        st.info("Explain: expected 7, but an unsafe interleaving can produce 6 — a lost update/data race.")

        st.divider()
        lecture_slide(
            "Slide 9 · Final Mental Model",
            "Connect the whole story",
            """
            <b>Programs</b> become processes when executed.<br>
            A <b>process</b> contains one or more threads.<br>
            The <b>scheduler</b> decides which runnable thread gets CPU time.<br>
            Threads in the same process can <b>share memory</b>.<br>
            Shared state may require <b>synchronization</b>.
            """,
            "PROGRAM → PROCESS → THREAD(S) → SCHEDULER → CPU CORE(S)"
        )
        st.success("End-of-demo question: Which result today was caused by waiting, which by scheduling, and which by shared memory?")

    with tabs[1]:
        st.header("Why this lab? Cut through abstraction.")
        st.markdown("""
        This local web interface turns operating-system concepts into observable scenarios.

        **OSTEP repository** provides the simulation scripts.  
        **This Streamlit app** provides a classroom-friendly visual interface.
        """)
        col1,col2,col3 = st.columns(3)
        with col1:
            scenario_card("cpu-intro", "Process states", "READY, RUNNING, WAITING")
        with col2:
            scenario_card("cpu-sched", "Scheduling policies", "FIFO, SJF, Round Robin")
        with col3:
            scenario_card("threads-intro", "Thread interleavings", "lost update and data race")
        st.markdown("""
        <div class='big-card'><b>Teaching pattern:</b> Predict → Run → Observe → Explain</div>
        """, unsafe_allow_html=True)

    with tabs[2]:
        st.header("Scenario 1 — CPU-bound vs I/O-bound processes")
        st.markdown("**Goal:** show that processes move between `RUNNING`, `READY`, and `WAITING`.")
        c1,c2,c3,c4 = st.columns(4)
        with c1: p0_len = st.number_input("P0 instructions", 1, 20, 5)
        with c2: p0_cpu = st.slider("P0 CPU probability", 0, 100, 100)
        with c3: p1_len = st.number_input("P1 instructions", 1, 20, 5)
        with c4: p1_cpu = st.slider("P1 CPU probability", 0, 100, 0)
        switch = st.selectbox("Switch behavior", ["SWITCH_ON_IO", "SWITCH_ON_END"])
        cmd_args=["-l", f"{p0_len}:{p0_cpu},{p1_len}:{p1_cpu}", "-S", switch, "-c", "-p"]
        st.code("python cpu-intro/process-run.py " + " ".join(cmd_args), language="bash")
        if st.button("Run process-state simulation", type="primary"):
            ok,msg,out=run_ostep("cpu-intro", "process-run.py", cmd_args)
            st.info(msg)
            output_box(out)
        st.markdown("""
        **Ask students:** When one process is waiting for I/O, what can the CPU do?
        """)

    with tabs[3]:
        st.header("Scenario 2 — Same jobs, different scheduler")
        st.markdown("**Goal:** show that changing only the scheduling policy changes waiting and turnaround times.")
        st.write("Default workload:")
        jobs=[]
        cols=st.columns(4)
        defaults=[("P1",0,8),("P2",1,4),("P3",2,2),("P4",3,5)]
        for idx,(n,a,b) in enumerate(defaults):
            with cols[idx]:
                st.subheader(n)
                ar=st.number_input(f"{n} arrival",0,20,a,key=f"ar{n}")
                bu=st.number_input(f"{n} burst",1,30,b,key=f"bu{n}")
                jobs.append((n,ar,bu))
        policy=st.radio("Policy", ["FCFS", "SJF", "Round Robin"], horizontal=True)
        quantum=st.slider("Time Quantum (Round Robin)",1,10,2)
        if st.button("Run scheduling simulation", type="primary"):
            if policy=="FCFS": rows,metrics=gantt_fcfs(jobs)
            elif policy=="SJF": rows,metrics=gantt_sjf(jobs)
            else: rows,metrics=gantt_rr(jobs, quantum)
            render_gantt(rows)
            st.dataframe(metrics, use_container_width=True)
            st.metric("Average waiting time", round(metrics["Waiting"].mean(),2))
            st.metric("Average turnaround time", round(metrics["Turnaround"].mean(),2))
            # Also show approximate OSTEP command for instructor continuity
            st.caption("The visualizer computes the classroom Gantt chart directly. OSTEP scheduler.py can be used in parallel for command-line verification.")
        st.markdown("**Ask students:** Did the jobs change, or did only the policy change?")

    with tabs[4]:
        st.header("Scenario 3 — Two threads, one shared variable")
        st.markdown("**Goal:** show how interleaving creates a lost update.")
        initial=st.number_input("Shared counter initial value", 0, 100, 5)
        mode=st.radio("Execution pattern", ["Safe execution", "Interleaved race"], horizontal=True)
        if mode=="Safe execution":
            rows=[("T1","LOAD",initial), ("T1","ADD",initial+1), ("T1","STORE",initial+1), ("T2","LOAD",initial+1), ("T2","ADD",initial+2), ("T2","STORE",initial+2)]
            final=initial+2; expected=initial+2
        else:
            rows=[("T1","LOAD",initial), ("T2","LOAD",initial), ("T1","ADD",initial+1), ("T2","ADD",initial+1), ("T1","STORE",initial+1), ("T2","STORE",initial+1)]
            final=initial+1; expected=initial+2
        st.table(pd.DataFrame(rows, columns=["Thread","Step","Value seen/written"]))
        c1,c2=st.columns(2)
        c1.metric("Expected final value", expected)
        c2.metric("Actual final value", final)
        if final==expected:
            st.success("No update was lost.")
            st.caption("T1 completes its read-modify-write sequence before T2 reads the shared value.")
        else:
            st.error("Lost update: both threads used the same old value. This is a data race.")
            st.caption("Both threads read the same old value before either STORE completes, so one increment is overwritten.")
        st.divider()
        st.subheader("Run OSTEP x86.py backend")
        st.caption("This executes the OSTEP threads-intro/simple-race.s example in the backend.")
        interval=st.slider("Interrupt interval (-i)",1,10,1)
        cmd_args=["-p","simple-race.s","-t","2","-i",str(interval),"-M","2000","-c"]
        st.code("python threads-intro/x86.py " + " ".join(cmd_args), language="bash")
        if st.button("Run OSTEP thread simulation"):
            ok,msg,out=run_ostep("threads-intro", "x86.py", cmd_args)
            st.info(msg)
            output_box(out)

    with tabs[5]:
        st.header("Suggested classroom script")
        st.markdown("""
        1. **Predict:** Ask what students expect before each run.  
        2. **Run:** Execute the scenario.  
        3. **Observe:** Ask students to point to the evidence.  
        4. **Explain:** Connect the observation to OS terminology.

        Recommended order:

        - Process states: `READY → RUNNING → WAITING`
        - Scheduling: `same jobs + different policy → different waiting time`
        - Threads: `shared memory + interleaving → data race`
        """)
        st.markdown("""
        **Important explanation:** Multithreading is not the problem.  
        The problem is unsynchronized access to shared state.
        """)

if __name__ == "__main__":
    main()
