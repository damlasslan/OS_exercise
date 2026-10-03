import os
import sys
import zipfile
import subprocess
import tempfile
import urllib.request
from pathlib import Path

import pandas as pd
import streamlit as st

OSTEP_URL = "https://github.com/remzi-arpacidusseau/ostep-homework/archive/refs/heads/master.zip"
BASE_DIR = Path(__file__).parent
OSTEP_DIR = BASE_DIR / "ostep-homework"

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
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def ensure_ostep():
    """Download OSTEP homework if it is not already present."""
    marker = OSTEP_DIR / "cpu-intro" / "process-run.py"
    if marker.exists():
        return True, "OSTEP repository is available locally."
    try:
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / "ostep.zip"
            urllib.request.urlretrieve(OSTEP_URL, zip_path)
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(td)
            extracted = Path(td) / "ostep-homework-master"
            if OSTEP_DIR.exists():
                pass
            else:
                extracted.rename(OSTEP_DIR)
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


def main():
    st.title("🧠 OS Exercise Lab")
    st.caption("A no-code teaching interface for OSTEP-style operating-system simulations")
    tabs = st.tabs(["Overview", "1 Process States", "2 CPU Scheduling", "3 Threads & Data Race", "Instructor Notes"])

    with tabs[0]:
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

    with tabs[1]:
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

    with tabs[2]:
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
        quantum=st.slider("RR quantum",1,10,2)
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

    with tabs[3]:
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
        else:
            st.error("Lost update: both threads used the same old value. This is a data race.")
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

    with tabs[4]:
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
