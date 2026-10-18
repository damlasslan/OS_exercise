import os
import sys
import json
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
ASSETS = BASE_DIR / "assets"
# Store the downloaded OSTEP backend in /tmp on Streamlit Cloud.
# This avoids cross-device move errors with Streamlit's mounted source tree.
OSTEP_DIR = Path(tempfile.gettempdir()) / "ostep-homework"

st.set_page_config(page_title="OS Exercise Lab", page_icon="🧠", layout="wide")

CSS = """
<style>
.block-container {padding-top: 1.7rem; padding-bottom: 2rem; max-width: 1200px;}
.big-card {border: 1px solid #E5E7EB; border-radius: 18px; padding: 20px; background: #F8FAFC; margin: 8px 0 16px 0;}
.small {font-size: 0.92rem; color:#4B5563;}
.slide-card {border:1px solid #CBD5E1; border-radius:24px; padding:28px 32px; background:white; margin:18px 0 14px 0; box-shadow:0 6px 24px rgba(15,23,42,.06);}
.slide-kicker {font-size:.82rem; letter-spacing:.08em; text-transform:uppercase; color:#64748B; font-weight:700;}
.slide-title {font-size:2rem; line-height:1.15; font-weight:800; margin:.35rem 0 1rem 0; color:#0F172A;}
.slide-body {font-size:1.08rem; line-height:1.65; color:#334155;}
.flow {font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background:#F8FAFC; border:1px dashed #94A3B8; padding:14px 18px; border-radius:14px; font-weight:700; text-align:center; margin:12px 0;}
.demo-label {display:inline-block;background:#0F172A;color:#fff;padding:5px 10px;border-radius:999px;font-size:.78rem;font-weight:700;margin-bottom:6px;}
.nav-caption {text-align:center;color:#64748B;font-size:.9rem;margin-top:.35rem;}
.layers {display:flex; gap:6px; flex-wrap:wrap; margin:0 0 4px 0;}
.layer {padding:4px 12px; border-radius:999px; font-size:.75rem; font-weight:700; letter-spacing:.04em; border:1px solid #CBD5E1; color:#94A3B8; background:#fff;}
.layer.on.app {background:#2563EB; color:#fff; border-color:#2563EB;}
.layer.on.os {background:#0D9488; color:#fff; border-color:#0D9488;}
.layer.on.run {background:#D97706; color:#fff; border-color:#D97706;}
.layer.on.res {background:#6D4AA8; color:#fff; border-color:#6D4AA8;}
.code-label {font-size:.8rem; font-weight:700; letter-spacing:.04em; text-transform:uppercase; margin:6px 0 2px 0;}
.code-label.app {color:#2563EB;}
.code-label.os {color:#0D9488;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# OSTEP backend
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Downloading the OSTEP simulators (first run only)...")
def _download_ostep():
    """Download OSTEP once per server. cache_resource also serialises concurrent
    first clicks, so two students cannot delete each other's half-copied folder."""
    marker = OSTEP_DIR / "cpu-intro" / "process-run.py"
    if marker.exists():
        return True
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
            raise RuntimeError("OSTEP archive was downloaded, but its extracted folder was not found.")
        # copytree works even when source and destination are on different mounts.
        shutil.copytree(extracted, OSTEP_DIR)
    if not marker.exists():
        raise RuntimeError("OSTEP repository was copied, but process-run.py is missing.")
    return True


def ensure_ostep():
    try:
        _download_ostep()
        return True, "OSTEP repository is available."
    except Exception as e:  # not cached, so the next click retries
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
    # st.code keeps column alignment and never interprets `$...$` as math.
    st.code(text or "(no output)", language="text")


def scenario_card(title, observe, explain):
    st.markdown(f"""
    <div class='big-card'>
    <h4>{title}</h4>
    <p><b>Observe:</b> {observe}</p>
    <p><b>Explain:</b> {explain}</p>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Scheduling visualizer
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Reusable demos (used by Lecture Mode and by the numbered tabs)
# ---------------------------------------------------------------------------
def render_process_demo(key_prefix, p0=(1, 0), p1=(4, 100), switch="SWITCH_ON_IO", show_cmd_open=False):
    c1,c2,c3,c4 = st.columns(4)
    with c1: p0_len = st.number_input("P0 instructions", 1, 20, p0[0], key=f"{key_prefix}_p0len")
    with c2: p0_cpu = st.slider("P0 CPU probability", 0, 100, p0[1], key=f"{key_prefix}_p0cpu")
    with c3: p1_len = st.number_input("P1 instructions", 1, 20, p1[0], key=f"{key_prefix}_p1len")
    with c4: p1_cpu = st.slider("P1 CPU probability", 0, 100, p1[1], key=f"{key_prefix}_p1cpu")
    options = ["SWITCH_ON_IO", "SWITCH_ON_END"]
    sw = st.selectbox("Switch behavior", options, index=options.index(switch), key=f"{key_prefix}_switch")
    cmd_args=["-l", f"{p0_len}:{p0_cpu},{p1_len}:{p1_cpu}", "-S", sw, "-c", "-p"]
    with st.expander("Show the OSTEP command", expanded=show_cmd_open):
        st.code("python cpu-intro/process-run.py " + " ".join(cmd_args), language="bash")
    if st.button("▶ Run process-state simulation", type="primary", key=f"{key_prefix}_run_process"):
        ok,msg,out=run_ostep("cpu-intro", "process-run.py", cmd_args)
        (st.success if ok else st.error)(msg)
        output_box(out)
        st.caption("OSTEP prints BLOCKED for the WAITING state. An asterisk (*) marks the step where an I/O completes.")


DEFAULT_JOBS = [("P1",0,8),("P2",1,4),("P3",2,2),("P4",3,5)]

def render_scheduling_demo(key_prefix, jobs=None, n_jobs=4, policy="FCFS", quantum=2):
    jobs = list(jobs or DEFAULT_JOBS)
    jobs += DEFAULT_JOBS[len(jobs):]
    n = st.radio("Number of processes", [2, 3, 4], index=[2, 3, 4].index(n_jobs), horizontal=True, key=f"{key_prefix}_n")
    chosen=[]
    cols=st.columns(4)
    for idx,(name,a,b) in enumerate(jobs[:4]):
        with cols[idx]:
            if idx < n:
                st.markdown(f"**{name}**")
                ar=st.number_input(f"{name} arrival",0,20,a,key=f"{key_prefix}_ar{name}")
                bu=st.number_input(f"{name} burst",1,30,b,key=f"{key_prefix}_bu{name}")
                chosen.append((name,ar,bu))
    pols = ["FCFS", "SJF", "Round Robin"]
    pol=st.radio("Policy", pols, index=pols.index(policy), horizontal=True, key=f"{key_prefix}_policy")
    q=st.slider("Time Quantum (Round Robin)",1,10,quantum,key=f"{key_prefix}_quantum")
    if st.button("▶ Run scheduling simulation", type="primary", key=f"{key_prefix}_run_sched"):
        if pol=="FCFS": rows,metrics=gantt_fcfs(chosen)
        elif pol=="SJF": rows,metrics=gantt_sjf(chosen)
        else: rows,metrics=gantt_rr(chosen, q)
        render_gantt(rows)
        st.dataframe(metrics, hide_index=True, width="stretch")
        c1,c2,c3=st.columns(3)
        c1.metric("Average waiting time", f"{metrics['Waiting'].mean():.2f}")
        c2.metric("Average turnaround time", f"{metrics['Turnaround'].mean():.2f}")
        c3.metric("Average response time", f"{metrics['Response'].mean():.2f}")


def render_thread_demo(key_prefix, backend_open=False):
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
    with st.expander("Run the real OSTEP x86.py backend", expanded=backend_open):
        st.caption("Two threads run threads-intro/simple-race.s. The counter starts at 0, so the correct result is 2. "
                   "The final value is the leftmost number on the last line.")
        interval=st.slider("Interrupt interval (-i)",1,10,1,key=f"{key_prefix}_interval")
        cmd_args=["-p","simple-race.s","-t","2","-i",str(interval),"-M","2000","-c"]
        st.code("python threads-intro/x86.py " + " ".join(cmd_args), language="bash")
        if st.button("▶ Run OSTEP thread simulation", key=f"{key_prefix}_run_thread"):
            ok,msg,out=run_ostep("threads-intro", "x86.py", cmd_args)
            (st.success if ok else st.error)(msg)
            output_box(out)
            if ok:
                lines=[l for l in out.splitlines() if l.strip() and l.strip()[0].isdigit()]
                if lines:
                    val=lines[-1].split()[0]
                    (st.success if val=="2" else st.error)(f"Final counter value: {val} (expected 2)")


# ---------------------------------------------------------------------------
# Lecture Mode content
# ---------------------------------------------------------------------------
@st.cache_data
def board_manifest():
    path = ASSETS / "board" / "manifest.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {f"{e['code']}_{e['board']}": e for e in data}


# ---------------------------------------------------------------------------
# Glossary: expansion and definition of each mechanism (shown on slides)
# ---------------------------------------------------------------------------
GLOSSARY = {
    "FCFS": ("First-Come, First-Served", "Runs ready jobs in arrival order. Non-preemptive: a running job keeps the CPU until it finishes or blocks."),
    "SJF": ("Shortest Job First", "Picks the ready job with the shortest (predicted) CPU burst. Non-preemptive in our examples."),
    "SRTF": ("Shortest Remaining Time First", "Preemptive SJF: at every arrival it compares remaining times and preempts the running job if the newcomer is shorter."),
    "RR": ("Round Robin", "Each ready job runs for at most one time quantum, then goes to the back of the ready queue."),
    "Quantum": ("Time quantum (time slice)", "The maximum CPU time a job may use per turn in Round Robin. A job that finishes earlier releases the CPU immediately."),
    "Preemption": ("Preemption", "The OS takes the CPU away from a job that could still run (timer interrupt or a more urgent arrival)."),
    "Context switch": ("Context switch", "Saving the registers of the running thread and restoring another thread's registers. Useful, but it costs CPU time."),
    "Convoy effect": ("Convoy effect", "Short jobs stuck behind one long job in FCFS, so average waiting time grows."),
    "Priority": ("Priority scheduling", "The ready job with the highest priority runs first. Can be preemptive or non-preemptive."),
    "Starvation": ("Starvation", "A ready job waits indefinitely because others are always chosen first."),
    "Aging": ("Aging", "Gradually raising the priority of a job that has waited long, to prevent starvation."),
    "MLFQ": ("Multi-Level Feedback Queue", "Several priority queues; a job moves down when it uses its full slice and is periodically boosted back to the top."),
    "Mutex": ("Mutual exclusion lock", "Only one thread at a time may hold it; others trying to lock it wait (WAITING)."),
    "Transaction": ("Database transaction", "A group of reads and writes that the database applies atomically and in isolation (all or nothing)."),
    "Lost update": ("Lost update", "Two read-modify-write sequences overlap and one write overwrites the other."),
    "Real-time": ("Real-time scheduling", "Correctness depends on finishing before a deadline, not only on the result."),
    "SCHED_FIFO": ("POSIX real-time FIFO policy", "Fixed-priority, preemptive policy: the highest-priority runnable thread runs until it blocks or yields."),
    "Deadline": ("Deadline", "The latest time by which a job must finish; missing it is a failure in a real-time system."),
    "WCET": ("Worst-Case Execution Time", "The longest time a task can take; needed to prove that deadlines are met."),
    "Priority inversion": ("Priority inversion", "A high-priority thread waits for a lock held by a low-priority thread, while a medium-priority thread keeps the low one off the CPU."),
    "Priority inheritance": ("Priority inheritance", "A lock holder temporarily inherits the priority of the highest-priority thread waiting for that lock."),
    "Race condition": ("Race condition (check-then-act)", "The result depends on timing: two workers check a condition, both see it true, both act."),
    "Atomic": ("Atomic operation", "Happens as one indivisible step; no other worker can observe or act in the middle of it."),
    "Producer–consumer": ("Producer–consumer", "One thread fills a shared buffer, another empties it; they must coordinate when it is full or empty."),
    "Condition variable": ("Condition variable", "Lets a thread sleep (WAITING) until another thread signals that a condition may now be true."),
    "Underrun": ("Buffer underrun", "The consumer finds the buffer empty and must wait: for video, playback stalls."),
}


def render_terms(keys):
    """Small definitions table under a slide: term, full name, meaning."""
    keys = [k for k in (keys or []) if k in GLOSSARY]
    if not keys:
        return
    rows = "".join(
        f"<tr><td style='padding:6px 10px;font-weight:700;white-space:nowrap'>{k}</td>"
        f"<td style='padding:6px 10px;white-space:nowrap'>{GLOSSARY[k][0]}</td>"
        f"<td style='padding:6px 10px'>{GLOSSARY[k][1]}</td></tr>" for k in keys)
    st.markdown(
        "<div style='border:1px solid #CBD5E1;border-radius:14px;padding:8px 10px;margin:4px 0 12px 0;background:#F8FAFC'>"
        "<div class='slide-kicker' style='margin:2px 0 4px 10px'>Terms</div>"
        "<table style='width:100%;border-collapse:collapse;font-size:.95rem;color:#334155'>"
        f"{rows}</table></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Instructor panel (Turkish with English underneath, or English only)
# ---------------------------------------------------------------------------
def _bi(tr, en, lang):
    if lang == "en" or not tr:
        return en or tr
    if not en or en == tr:
        return tr
    return f"{tr}<br><span style='color:#64748B;font-style:italic'>EN: {en}</span>"


def render_board(board_keys, say_tr, say_en=None, lang="tr", links=False, qa=None):
    """Instructor-only panel: what to say, questions with answers, and the board drawing."""
    if not board_keys and not say_tr and not qa:
        return
    t = UI[lang]
    say_en = say_en or []
    with st.expander(t["panel"], expanded=False):
        if say_tr or say_en:
            st.markdown(f"**{t['say']}**")
            n = max(len(say_tr), len(say_en))
            for i in range(n):
                tr = say_tr[i] if i < len(say_tr) else ""
                en = say_en[i] if i < len(say_en) else ""
                st.markdown(f"- {_bi(tr, en, lang)}", unsafe_allow_html=True)
        if links:
            st.markdown(OSTEP_LINKS[lang] if lang == "en" else OSTEP_LINKS["tr"])
        if qa:
            st.markdown(f"**{t['qa']}**")
            for q_tr, a_tr, q_en, a_en in qa:
                st.markdown(f"**{t['q']}:** {_bi(q_tr, q_en, lang)}<br>**{t['a']}:** {_bi(a_tr, a_en, lang)}",
                            unsafe_allow_html=True)
        man = board_manifest()
        for key in board_keys:
            e = man.get(key)
            if not e:
                continue
            part = f" ({e['board']}/{e['boards']})" if e["boards"] > 1 else ""
            st.markdown(f"**{t['board']} {e['code']}{part} · {e['title']}** · {t['slides']} {e['slides']}")
            img = ASSETS / "board" / e["img"]
            if img.exists():
                st.image(str(img), width="stretch")
            st.markdown(f"**{t['steps']}**")
            caps_tr, caps_en = e["caps"], e.get("caps_en", e["caps"])
            lines = [f"{i}. {_bi(a, b, lang)}" for i, (a, b) in enumerate(zip(caps_tr, caps_en), 1)]
            st.markdown("<br>".join(lines), unsafe_allow_html=True)
        codes = sorted({k.split("_")[0] for k in board_keys})
        for code in codes:
            vid = ASSETS / "video" / ("en" if lang == "en" else "") / f"{code}.mp4"
            if vid.exists() and st.toggle(f"▶ {code} · {t['video']}", key=f"vid_{lang}_{code}_{'_'.join(board_keys)}"):
                st.video(str(vid))


def notes_lang():
    return "en" if st.session_state.get("notes_lang", "Türkçe + EN") == "English" else "tr"


# ---------------------------------------------------------------------------
# Generic slide deck (used by Lecture Mode and by Real-World Systems)
# ---------------------------------------------------------------------------
def render_deck(prefix, slides, demos, say_en_map=None, qa_map=None, links_on_first=False):
    n = len(slides)
    idx_key, jump_key = f"{prefix}_slide_idx", f"{prefix}_jump"
    if idx_key not in st.session_state:
        st.session_state[idx_key] = 0
    st.session_state[idx_key] = min(st.session_state[idx_key], n - 1)
    titles = [f"{i+1}. {s['title']}" for i, s in enumerate(slides)]

    def go(i):
        st.session_state[idx_key] = i
        st.session_state[jump_key] = titles[i]

    def on_jump():
        st.session_state[idx_key] = titles.index(st.session_state[jump_key])

    if st.session_state.get(jump_key) not in titles:
        st.session_state[jump_key] = titles[st.session_state[idx_key]]
    st.selectbox("Jump to slide", titles, key=jump_key, on_change=on_jump, label_visibility="collapsed")

    idx = st.session_state[idx_key]
    cur = slides[idx]
    layer_pills(cur.get("layers"))
    lecture_slide(cur["kicker"], cur["title"], cur["body"], cur.get("flow"))
    render_terms(cur.get("terms"))
    if cur.get("code"):
        code_pair(*cur["code"])
    demo = cur.get("demo")
    if demo:
        st.markdown("<span class='demo-label'>LIVE DEMO</span>", unsafe_allow_html=True)
        demos[demo](f"{prefix}_s{idx+1}", **cur.get("demo_args", {}))

    lang = notes_lang()
    say_tr = cur.get("say", [])
    say_en = cur.get("say_en") or (say_en_map or {}).get(idx + 1, [])
    qa = cur.get("qa") or (qa_map or {}).get(idx + 1)
    render_board(cur.get("board", []), say_tr, say_en, lang, links=(links_on_first and idx == 0), qa=qa)

    st.divider()
    left, mid, right = st.columns([1, 2, 1])
    with left:
        st.button("← Previous", width="stretch", disabled=idx == 0, key=f"{prefix}_prev", on_click=go, args=(max(idx - 1, 0),))
    with mid:
        st.markdown(f"<div class='nav-caption'>Slide {idx + 1} of {n}</div>", unsafe_allow_html=True)
    with right:
        st.button("Next →", width="stretch", disabled=idx == n - 1, key=f"{prefix}_next", on_click=go, args=(min(idx + 1, n - 1),))


def layer_pills(active):
    if not active:
        return
    names = [("app", "APPLICATION"), ("os", "OS KERNEL"), ("run", "RUN ON SITE"), ("res", "RESULT")]
    html = "<div class='layers'>" + "".join(
        f"<span class='layer {k}{' on' if k in active else ''}'>{n}</span>" for k, n in names) + "</div>"
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


def code_pair(left, right):
    """Show application code next to OS pseudocode. Each item: (kind, label, code)."""
    cols = st.columns(len([c for c in (left, right) if c]))
    for col, item in zip(cols, [c for c in (left, right) if c]):
        kind, label, code = item
        with col:
            st.markdown(f"<div class='code-label {kind}'>{label}</div>", unsafe_allow_html=True)
            st.code(code, language="c")


APP_P0 = """int main(void) {
    char buffer[4096];
    int fd = open("data.txt", O_RDONLY);

    read(fd, buffer, sizeof buffer); // I/O
    close(fd);
    return 0;
}"""
APP_P1 = """int main(void) {
    volatile long result = 0;

    for (long i = 0; i < 100000000; i++)
        result += i;              // CPU work

    return 0;
}"""
OS_SWITCH_IO = """// SWITCH_ON_IO (pseudocode)
if (current_blocks_for_io()) {
    current->state = BLOCKED;
    next = ready_queue_pop();
    context_switch(next);   // CPU stays busy
}
on_io_complete(p):
    p->state = READY;       // back in the queue"""
OS_SWITCH_END = """// SWITCH_ON_END (OSTEP teaching policy)
if (current_blocks_for_io()) {
    current->state = BLOCKED;
    cpu_idle_until_io_done(); // no switch
}
// switch only when current FINISHES
// (not typical modern OS behavior)"""
APP_THREADS = """int counter = 5;               // shared data

void *worker(void *arg) {
    counter++;                 // LOAD, ADD, STORE
    return NULL;
}

int main(void) {
    pthread_t t1, t2;
    pthread_create(&t1, NULL, worker, NULL);
    pthread_create(&t2, NULL, worker, NULL);
    pthread_join(t1, NULL); pthread_join(t2, NULL);
    printf("%d\\n", counter);   // expect 7
}"""
OS_TIMER = """on_timer_interrupt():
    save_registers(current);   // T1's %eax = 5
    current->state = READY;
    ready_queue_push(current);

    next = pick_next();        // T2
    restore_registers(next);
    next->state = RUNNING;
    return_to_user(next);"""
APP_MUTEX = """pthread_mutex_t m = PTHREAD_MUTEX_INITIALIZER;

void *worker(void *arg) {
    pthread_mutex_lock(&m);
    counter++;               // critical section
    pthread_mutex_unlock(&m);
    return NULL;
}"""
OS_MUTEX = """mutex_lock(m):
    if (m->owner != NULL) {
        current->state = WAITING;
        schedule();          // run someone else
    }
    m->owner = current;

mutex_unlock(m): wake_one_waiter(m);"""
APP_TWO_JOBS = """P1: generate_report();   // arrives 0, 10 ms CPU
P2: handle_request();    // arrives 3,  2 ms CPU"""
OS_THREE_POLICIES = """// FCFS (non-preemptive)
on_arrival(p):  ready_queue_push(p);    // never interrupts

// Round Robin, quantum q
on_timer_tick(): if (++current->used == q) preempt(current);

// SRTF (preemptive shortest remaining time)
on_arrival(p):
    ready_queue_push(p);
    if (p->remaining < current->remaining) preempt(current);"""
APP_THREE_JOBS = """P1: encode_video();     // 12 ms
P2: make_thumbnail();   //  3 ms
P3: write_log();        //  2 ms
// all READY at t = 0"""
OS_PICK_NEXT = """Process *pick_next(void) {
  switch (policy) {
  case FCFS: return earliest_arrival(ready_queue);
  case SJF:  return shortest_burst(ready_queue); // needs an estimate!
  case RR:   return ready_queue_head();          // + preempt after quantum
  }
}"""
OS_TICK = """on_timer_tick():
    current->used++;
    if (current->used == QUANTUM) {
        if (ready_queue_empty())
            current->used = 0;   // keep running, no switch
        else
            preempt(current);    // to the back of the queue
    }

on_exit(p):  schedule();       // finished early: switch now"""

SAY_EN = {
    1: ["OSTEP is a free operating-systems textbook; we use the simulators from its homework as our engine.",
        "The simulator is not a real kernel; it models the behavior. We will not show the simulator's code."],
    2: ["In every demo we walk through these four layers in order. The coloured labels on top show which layer we are in."],
    3: ["READY: can run but waits for the CPU. WAITING: cannot run even if you give it the CPU; it waits for an event."],
    4: ["Ask: when P0 starts I/O and waits, must the CPU stay idle?",
        "A real read() does not always block; if the data is cached it returns immediately. The number of C lines does not map one-to-one to OSTEP instructions."],
    5: ["SWITCH_ON_END is not the same as non-preemptive: even a non-preemptive scheduler can run a READY thread when the running one blocks.",
        "SWITCH_ON_IO is not preemption either: the process gives up the CPU because it cannot continue during I/O."],
    6: ["Run A: at times 2–5 P0 is BLOCKED, but the CPU column shows 1. The CPU is not idle; it runs P1.",
        "Run B: change only the switch behavior. Total time goes from 7 to 11."],
    7: ["Both runs do the same work. The second takes longer because the I/O wait and P1's CPU work do not overlap.",
        "The second question is today's topic: FCFS, SJF, Round Robin, Priority, MLFQ."],
    8: ["Cases 1–2 are the top timeline, cases 3–4 the bottom one. Process or thread does not change the timeline."],
    9: ["The code is correct on its own. The problem appears when the steps of two threads interleave, even on one core."],
    10: ["The program is three instructions: read, add, write. If the interrupt lands between them, an update is lost.",
         "The code never changed, only the interrupt timing. A program that relies on timing for correctness is broken."],
    11: ["On Linux a thread waiting for a lock is put to sleep with a futex. Scheduling ≠ synchronization."],
    12: ["FCFS: P2 arrived at time 3 but waits until P1 finishes.",
         "RR q=2: at time 2 P2 has not arrived yet, so P1 continues; at time 4 it is P2's turn."],
    13: ["The total work is still 14 ms. Only the order changed. A real OS does not know job lengths; it estimates them from the past."],
    14: ["SRTF is not on the site; draw it on the board. If short jobs keep arriving, a long job can starve."],
    15: ["The answer is SJF: P3 finishes at time 2, P2 at time 5. But SJF assumes job lengths are known in advance."],
    16: ["The two P1 boxes at 9–13 and 13–17 are not a real switch; nobody else is in the queue.",
         "Tiny quantum: everyone gets a turn quickly, but switching costs grow. Huge quantum: RR turns into FCFS."],
    17: ["Matching the SJF order is a coincidence. Present MLFQ as a strategy, not as implementation detail."],
    18: ["Give students 5 minutes to draw it on paper, then check on the site."],
    19: ["Moving is not free: T3's data was in Core 1's cache."],
    20: ["Exit question: which of today's results came from waiting, which from scheduling, which from shared memory?"],
}

# (question_tr, answer_tr, question_en, answer_en) per Lecture Mode slide
QA = {
    1: [("OSTEP simülatörü gerçek işletim sistemini değiştirir mi?",
         "Hayır. Kullanıcı alanında çalışan sıradan bir Python programıdır; kernel'e dokunmaz, yalnızca davranışı modeller.",
         "Does the OSTEP simulator change the real operating system?",
         "No. It is an ordinary Python program in user space; it never touches the kernel, it only models the behavior.")],
    2: [("Uygulama ne zaman çalışacağına kendisi karar verebilir mi?",
         "Hayır. Uygulama öncelik veya çekirdek tercihi isteyebilir, ama kararı OS kendi politikasına göre verir.",
         "Can an application decide when it runs?",
         "No. It can request a priority or core affinity, but the OS makes the decision under its own policy.")],
    3: [("Her durumda süreç CPU'yu kullanıyor mu, kullanabilir mi?",
         "RUNNING: kullanıyor. READY: kullanmıyor ama CPU verilirse hemen kullanabilir. WAITING: kullanmıyor ve verilse de kullanamaz, bir olay bekliyor.",
         "In each state, is the process using the CPU, and could it?",
         "RUNNING: using it. READY: not using it, but could immediately. WAITING: not using it and could not even if given the CPU; it waits for an event."),
        ("Tek çekirdekte aynı anda kaç thread yürütülür?",
         "Bir. Diğerleri READY veya WAITING durumundadır.",
         "How many threads execute at the same instant on one core?",
         "One. The others are READY or WAITING."),
        ("I/O'su biten süreç doğrudan RUNNING olur mu?",
         "Hayır. Önce READY olur ve scheduler'ın onu seçmesini bekler.",
         "Does a process whose I/O completes go straight to RUNNING?",
         "No. It becomes READY and waits for the scheduler to pick it.")],
    4: [("P0 I/O başlatıp beklemeye geçince CPU boş kalmak zorunda mı?",
         "Hayır. OS P0'ı BLOCKED yapar ve READY olan P1'i çalıştırır. Demo 1'de bu zaman 2–5 arasında görünür.",
         "When P0 starts I/O and waits, must the CPU stay idle?",
         "No. The OS marks P0 BLOCKED and runs the READY process P1. In Demo 1 this is visible at times 2–5.")],
    5: [("SWITCH_ON_END non-preemptive scheduling ile aynı şey mi?",
         "Hayır. Non-preemptive bir scheduler çalışan işi zorla kesmez, ama iş bloke olunca READY olan başka işi çalıştırabilir. SWITCH_ON_END buna bile izin vermez.",
         "Is SWITCH_ON_END the same as non-preemptive scheduling?",
         "No. A non-preemptive scheduler never forces the running job off, but it can run another READY job when the current one blocks. SWITCH_ON_END does not even allow that."),
        ("Modern bir işletim sistemi hangisine benzer davranır?",
         "SWITCH_ON_IO'ya. Bloke olan thread'in yerine runnable bir thread çalıştırılır.",
         "Which one resembles a modern operating system?",
         "SWITCH_ON_IO: a runnable thread is scheduled when the current thread blocks.")],
    6: [("P0 I/O beklerken CPU'yu kim kullanır?",
         "P1. Zaman 2–5 arasında P0 BLOCKED, P1 RUN:cpu ve CPU sütununda 1 var. Sonuç: Total Time 7, CPU %85,71.",
         "While P0 waits for I/O, who uses the CPU?",
         "P1. At times 2–5 P0 is BLOCKED, P1 is RUN:cpu and the CPU column shows 1. Result: total time 7, CPU 85.71%."),
        ("Run B'de aynı iş yapılıyor; neden daha uzun sürüyor?",
         "SWITCH_ON_END'de P1, P0'ın I/O'su bitene kadar READY bekliyor; I/O ile CPU işi örtüşmüyor. Süre 7'den 11'e çıkıyor, CPU %54,55.",
         "Run B does the same work; why is it slower?",
         "With SWITCH_ON_END, P1 waits READY until P0's I/O completes, so I/O and CPU work do not overlap. Time grows from 7 to 11, CPU 54.55%.")],
    7: [("Q1 · Çalışan süreç devam edemezse ne olur?",
         "BLOCKED olur ve CPU'yu bırakır; OS READY olan başka bir süreci çalıştırabilir.",
         "Q1 · What happens when the running process cannot continue?",
         "It becomes BLOCKED and gives up the CPU; the OS can run another READY process."),
        ("Q2 · Birden çok süreç READY ise hangisi çalışır?",
         "Bunu CPU scheduler, politikasına göre seçer: FCFS, SJF, Round Robin, Priority, MLFQ. Bugünün konusu bu.",
         "Q2 · If several processes are READY, which one runs?",
         "The CPU scheduler chooses according to its policy: FCFS, SJF, Round Robin, Priority, MLFQ. That is today's topic.")],
    8: [("Tek çekirdekte A ve B aynı milisaniyede çalışıyor mu?",
         "Hayır, sırayla çalışıyorlar. Ama ikisi de ilerliyor: bu concurrency.",
         "On one core, do A and B run in the same millisecond?",
         "No, they take turns. But both make progress: that is concurrency."),
        ("İki çekirdekte?",
         "Evet. Aynı zaman sütununda ikisi de gerçekten çalışıyor: bu parallelism.",
         "And on two cores?",
         "Yes. In the same time column both truly run: that is parallelism.")],
    9: [("Bu kodda hata var mı?",
         "Tek thread'le çalışınca yok. İki thread'de counter++ atomik değil: LOAD ile STORE arasında bir context switch olursa bir artırma kaybolur.",
         "Is there a bug in this code?",
         "Not with one thread. With two threads counter++ is not atomic: a context switch between LOAD and STORE loses one increment.")],
    10: [("Sayaç 5, iki thread birer kez artırıyor: sonuç 6 mı, 7 mi?",
          "Doğrusu 7. Adımlar araya girerse (iki thread de 5'i okursa) sonuç 6 olur.",
          "Counter 5, both threads increment once: is the result 6 or 7?",
          "The correct result is 7. If the steps interleave (both threads read 5), the result is 6."),
         ("x86.py'de kesme aralığı 3 olunca neden sonuç doğru çıkıyor?",
          "Program üç komut: oku, artır, yaz. Kesme her 3 komutta bir gelince her thread üç adımını kesintisiz bitiriyor ve sonuç 2 oluyor. Bu, programın güvenli olduğu anlamına gelmez; yalnızca bu zamanlamada şanslıyız.",
          "Why is the result correct in x86.py with interrupt interval 3?",
          "The program is three instructions: read, add, write. With an interrupt every 3 instructions, each thread finishes its three steps uninterrupted, giving 2. That does not make the program safe; we are just lucky with this timing.")],
    11: [("Preempt edilen thread tuttuğu mutex'i bırakır mı?",
          "Hayır. CPU'yu kaybetmek kilidi bırakmak demek değil; kilit sahibinde kalır ve diğer thread'ler bekler.",
          "Does a preempted thread release the mutex it holds?",
          "No. Losing the CPU does not release the lock; it stays with its owner and the others wait."),
         ("Kilit bekleyen thread CPU kullanır mı?",
          "Blocking mutex'te hayır: WAITING durumuna geçer ve uyur. Spinlock'ta ise döngüde CPU harcar.",
          "Does a thread waiting for a lock use the CPU?",
          "With a blocking mutex, no: it goes to WAITING and sleeps. With a spinlock it burns CPU in a loop.")],
    12: [("P2 zaman 3'te gelince OS P1'i keser mi?",
          "FCFS: hayır, P2 7 ms bekler. RR q=2: dilim dolunca, zaman 4'te sıra P2'ye geçer, 1 ms bekler. SRTF: hemen keser, P2 hiç beklemez.",
          "When P2 arrives at time 3, does the OS interrupt P1?",
          "FCFS: no, P2 waits 7 ms. RR q=2: when the slice ends at time 4 it is P2's turn, it waits 1 ms. SRTF: immediately, P2 does not wait at all."),
         ("Hangi politikada P2 en az bekler?",
          "SRTF (0 ms), sonra RR (1 ms), en son FCFS (7 ms).",
          "In which policy does P2 wait least?",
          "SRTF (0 ms), then RR (1 ms), then FCFS (7 ms).")],
    13: [("FCFS mi SJF mi daha düşük ortalama bekleme verir?",
          "SJF: 2,67 ms. FCFS: 6,67 ms. Toplam iş aynı, yalnızca sıra değişti.",
          "Which gives the lower average waiting time, FCFS or SJF?",
          "SJF: 2.67 ms. FCFS: 6.67 ms. Same total work, only the order changed."),
         ("Gerçek bir OS neden saf SJF kullanamaz?",
          "Bir işin CPU süresini önceden bilmez; geçmiş davranıştan tahmin eder. Ayrıca kısa işler sürekli gelirse uzun iş aç kalabilir.",
          "Why can't a real OS use pure SJF?",
          "It does not know a job's CPU time in advance; it estimates it from past behavior. Also, a long job can starve if short jobs keep arriving.")],
    14: [("Zaman 1'de P2 neden P1'i keser?",
          "P1'in kalan süresi 7 ms, P2'nin ihtiyacı 4 ms. SRTF kalan süresi en kısa olanı seçer.",
          "Why does P2 interrupt P1 at time 1?",
          "P1 has 7 ms left, P2 needs 4 ms. SRTF picks the shortest remaining time."),
         ("SRTF'nin riski nedir?",
          "Starvation: kısa işler sürekli gelirse uzun iş CPU'yu hiç alamayabilir.",
          "What is the risk of SRTF?",
          "Starvation: if short jobs keep arriving, a long job may never get the CPU.")],
    15: [("P2 ve P3 hangi politikada en erken biter?",
          "SJF: P3 zaman 2'de, P2 zaman 5'te biter. RR q=4'te 9 ve 7, FCFS'te 17 ve 15. Ortalama bekleme: SJF 2,33 · RR 5,33 · FCFS 9,00 ms.",
          "In which policy do P2 and P3 finish earliest?",
          "SJF: P3 at time 2, P2 at time 5. With RR q=4 at 9 and 7, with FCFS at 17 and 15. Average waiting: SJF 2.33 · RR 5.33 · FCFS 9.00 ms.")],
    16: [("P2'nin bloğu neden 4–8 değil de 4–7?",
          "P2'nin yalnızca 3 ms işi vardı. Quantum bir üst sınır; iş bitince CPU hemen bırakılır.",
          "Why is P2's block 4–7 and not 4–8?",
          "P2 only needed 3 ms. The quantum is an upper limit; the CPU is released as soon as the job ends."),
         ("Quantum çok küçülürse ne olur?",
          "İlk yanıt hızlanır (q=1'de ortalama response 1,00 ms), ama context switch sayısı artar (8) ve her switch'in maliyeti var.",
          "What happens if the quantum becomes very small?",
          "First response gets faster (average response 1.00 ms at q=1), but context switches increase (8) and each switch has a cost."),
         ("Quantum çok büyürse?",
          "Round Robin FCFS'e döner: q=12'de çizelge FCFS ile birebir aynı (ortalama bekleme 9,00 ms).",
          "And if the quantum becomes very large?",
          "Round Robin turns into FCFS: at q=12 the schedule is identical to FCFS (average waiting 9.00 ms).")],
    17: [("Priority ile SJF neden aynı sırayı verdi?",
          "Tesadüf. Öncelik önemi, SJF ise süreyi ölçer; bu örnekte ikisi aynı sırayı üretti.",
          "Why did Priority and SJF give the same order?",
          "Coincidence. Priority measures importance, SJF measures length; in this example they happened to agree."),
         ("Starvation nasıl önlenir?",
          "Aging: bekleyen işin önceliği zamanla artırılır. MLFQ'daki periyodik boost da aynı fikir.",
          "How is starvation prevented?",
          "Aging: a waiting job's priority grows over time. The periodic boost in MLFQ is the same idea."),
         ("MLFQ'da boost hangi sorunu azaltır?",
          "Alt kuyruktaki uzun işlerin hiç CPU alamamasını (starvation) ve davranışı değişen işlerin altta takılı kalmasını.",
          "Which problem does the boost in MLFQ reduce?",
          "Long jobs in the lower queues never getting the CPU (starvation), and jobs whose behavior changed staying stuck at the bottom.")],
    18: [("Alıştırma: FCFS mi SJF mi daha düşük ortalama bekleme verir?",
          "SJF: (0 + 2 + 6) / 3 = 2,67 ms. FCFS: (0 + 6 + 8) / 3 = 4,67 ms.",
          "Practice: which gives the lower average waiting time, FCFS or SJF?",
          "SJF: (0 + 2 + 6) / 3 = 2.67 ms. FCFS: (0 + 6 + 8) / 3 = 4.67 ms."),
         ("FCFS örneğinde P2'nin response, waiting ve turnaround süreleri nedir?",
          "Geliş 0, ilk çalışma 8, bitiş 12: response 8, waiting 8, turnaround 12 ms.",
          "In the FCFS example, what are P2's response, waiting and turnaround times?",
          "Arrival 0, first run 8, completion 12: response 8, waiting 8, turnaround 12 ms.")],
    19: [("İlk resimde yanlış olan ne?",
          "Yük dengesiz: Core 1'de dört iş var, Core 2 boş.",
          "What is wrong in the first picture?",
          "The load is unbalanced: Core 1 has four jobs, Core 2 is idle."),
         ("Banka örneğinde mutex yoksa sonuç ne olabilir?",
          "İkisi de 100'ü okursa: T1 110, T2 80 yazar ve en son yazan kazanır. Sonuç 110 veya 80 olur; doğrusu 90.",
          "In the bank example, without a mutex what can the result be?",
          "If both read 100: T1 writes 110, T2 writes 80, and the last writer wins. The result is 110 or 80; the correct value is 90."),
         ("İki çekirdek her programı iki kat hızlandırır mı?",
          "Hayır. Yalnızca paralel çalışabilen kısım hızlanır; kilitle korunan kısım sırayla çalışır.",
          "Do two cores make every program twice as fast?",
          "No. Only the part that can run in parallel speeds up; the part protected by a lock still runs one at a time.")],
    20: [("Bugünkü sonuçlardan hangisi beklemeden, hangisi scheduling'den, hangisi paylaşılan bellekten kaynaklandı?",
          "Bekleme: Demo 1, I/O sırasında CPU'nun boş kalması (7'ye karşı 11). Scheduling: Demo 3 ve 4, aynı işlerde farklı bekleme süreleri. Paylaşılan bellek: Demo 2, kaybolan güncelleme (7 yerine 6).",
          "Which of today's results came from waiting, which from scheduling, which from shared memory?",
          "Waiting: Demo 1, the CPU idling during I/O (7 vs 11). Scheduling: Demos 3 and 4, different waiting times for the same jobs. Shared memory: Demo 2, the lost update (6 instead of 7).")],
}

OSTEP_LINKS = {
    "tr": "📖 **OSTEP kitabı (ücretsiz):** [pages.cs.wisc.edu/~remzi/OSTEP](https://pages.cs.wisc.edu/~remzi/OSTEP/) · "
          "**Simülatörler:** [github.com/remzi-arpacidusseau/ostep-homework](https://github.com/remzi-arpacidusseau/ostep-homework)",
    "en": "📖 **OSTEP book (free):** [pages.cs.wisc.edu/~remzi/OSTEP](https://pages.cs.wisc.edu/~remzi/OSTEP/) · "
          "**Simulators:** [github.com/remzi-arpacidusseau/ostep-homework](https://github.com/remzi-arpacidusseau/ostep-homework)",
}

UI = {
    "tr": {"panel": "📝 Eğitmen · tahtaya çizilecekler ve anlatım", "say": "Söyleyin", "board": "Tahta",
           "slides": "PPT v2 slayt", "steps": "Çizim ve anlatım sırası", "video": "tahta videosunu göster",
           "qa": "Sorular ve cevaplar", "q": "S", "a": "C"},
    "en": {"panel": "📝 Instructor · board drawing and script", "say": "Say", "board": "Board",
           "slides": "PPT v2 slides", "steps": "Drawing and narration steps", "video": "show the board video",
           "qa": "Questions and answers", "q": "Q", "a": "A"},
}

SLIDES = [
    {
        "kicker": "Slide 1 · What is OSTEP?",
        "title": "OSTEP: the simulation engine behind this website",
        "body": """
        <b>OSTEP</b> = <i>Operating Systems: Three Easy Pieces</i> by Remzi and Andrea Arpaci-Dusseau (UW–Madison),
        a free textbook organised around <b>virtualization, concurrency and persistence</b> (<a href='https://pages.cs.wisc.edu/~remzi/OSTEP/' target='_blank'>pages.cs.wisc.edu/~remzi/OSTEP</a>).
        Its homework folder contains small Python simulators such as <code>process-run.py</code> and <code>x86.py</code>.
        <br><br>
        They <b>model</b> OS behavior step by step. They do <b>not</b> run or change a real kernel.
        Instead of the simulator's code, we will look at <b>application code</b> and <b>OS kernel pseudocode</b>.
        """,
        "flow": "Browser → OS Exercise Lab → OSTEP simulator → output on the projector",
        "say": ["OSTEP ücretsiz bir işletim sistemleri ders kitabı; ödevlerindeki simülatörleri motor olarak kullanıyoruz.",
                "Simülatör gerçek kernel değil, davranışı modelliyor. Simülatörün kodunu göstermeyeceğiz."],
    },
    {
        "kicker": "Slide 2 · Four layers",
        "title": "Every live demo has four layers",
        "body": """
        <b>1 · Application code</b> (user space): what a developer writes — read(), loops, threads, locks.<br>
        <b>2 · OS kernel</b> (kernel space): scheduler, process states, context switch.<br>
        <b>3 · Run on site</b>: the workload and policy we feed to the simulator.<br>
        <b>4 · Observed result</b>: total time, CPU utilization, waiting time, final value.
        <br><br>
        <b>Applications define the work. The operating system manages the execution.</b>
        """,
        "layers": ["app", "os", "run", "res"],
        "say": ["Her demoda bu dört katmanı sırayla gezeceğiz. Üstteki renkli etiketler hangi katmanda olduğumuzu gösterir."],
    },
    {
        "kicker": "Slide 3 · Process states",
        "title": "A process does not continuously own the CPU",
        "body": """
        <b>READY</b>: can run, waits for a core. <b>RUNNING</b>: executes instructions.
        <b>WAITING / BLOCKED</b>: waits for I/O or a lock — not using the CPU and not in the ready queue.
        <br><br>
        When the event completes, the process returns to <b>READY</b>, not directly to RUNNING.
        """,
        "flow": "READY → RUNNING → WAITING → READY   (or → FINISHED)",
        "board": ["V01_1"],
        "say": ["READY: çalışabilir ama CPU bekliyor. WAITING: CPU verseniz de çalışamaz, bir olay bekliyor."],
    },
    {
        "kicker": "Slide 4 · Demo 1 · Layer 1",
        "title": "Meet our two applications",
        "body": """
        P0 reads a file (<b>I/O-bound</b>). P1 only computes (<b>CPU-bound</b>). One CPU core.
        <br>In the simulator: <b>P0 = 1 instruction, 100% I/O</b> · <b>P1 = 4 instructions, 100% CPU</b>.
        <br><br><b>Neither program says WHEN it runs.</b> That decision belongs to the operating system.
        """,
        "layers": ["app"],
        "code": (("app", "P0 · I/O-bound application", APP_P0), ("app", "P1 · CPU-bound application", APP_P1)),
        "say": ["Sorun: P0 I/O başlatıp beklemeye geçince CPU boş kalmak zorunda mı?",
                "Gerçek read() her zaman bloke olmaz; veri önbellekteyse hemen döner. C satır sayısı OSTEP komut sayısına birebir karşılık gelmez."],
    },
    {
        "kicker": "Slide 5 · Demo 1 · Layer 2",
        "title": "SWITCH_ON_IO vs SWITCH_ON_END",
        "body": """
        Two switch policies of the <b>OSTEP simulator</b> — not Linux or Windows scheduler names.
        <br><b>SWITCH_ON_IO</b>: when the running process starts I/O, another READY process may run → CPU–I/O overlap.
        <br><b>SWITCH_ON_END</b>: no switch until the running process finishes → the CPU idles during I/O.
        <br><br><i>The code below is pseudocode that explains the behavior, not real kernel source.</i>
        """,
        "layers": ["os"],
        "code": (("os", "SWITCH_ON_IO · OS pseudocode", OS_SWITCH_IO), ("os", "SWITCH_ON_END · OSTEP policy", OS_SWITCH_END)),
        "say": ["SWITCH_ON_END non-preemptive ile aynı şey değil: non-preemptive bir scheduler bile bloke olan thread'in yerine READY bir thread çalıştırabilir.",
                "SWITCH_ON_IO da preemption sayılmaz: process I/O yüzünden devam edemediği için CPU'yu bırakır."],
    },
    {
        "kicker": "Slide 6 · LIVE DEMO 1 · Layer 3",
        "title": "Run A with SWITCH_ON_IO, then Run B with SWITCH_ON_END",
        "body": """
        Defaults are already set: <b>P0 1 / 0%</b>, <b>P1 4 / 100%</b>, <b>SWITCH_ON_IO</b>.
        <br><b>Predict first:</b> while P0 waits for I/O, who uses the CPU?
        <br>Then change <b>only</b> Switch behavior to <b>SWITCH_ON_END</b> and run again.
        """,
        "layers": ["run"],
        "demo": "process",
        "board": ["V01_2"],
        "say": ["Run A: zaman 2–5 arası P0 BLOCKED, ama CPU sütununda 1 var. CPU boş değil, P1'i çalıştırıyor.",
                "Run B: yalnız switch behavior'u değiştirin. Toplam süre 7'den 11'e çıkar."],
    },
    {
        "kicker": "Slide 7 · Demo 1 · Layer 4",
        "title": "Same work, different switch decision",
        "body": """
        <table style='width:100%;border-collapse:collapse;font-size:1.05rem'>
        <tr style='background:#F1F5F9'><th style='text-align:left;padding:6px'></th><th style='text-align:left'>SWITCH_ON_IO</th><th style='text-align:left'>SWITCH_ON_END</th></tr>
        <tr><td style='padding:6px'><b>Total time</b></td><td>7</td><td>11</td></tr>
        <tr><td style='padding:6px'><b>CPU utilization</b></td><td>85.71%</td><td>54.55%</td></tr></table>
        <br><b>Q1:</b> The running process cannot continue? → It becomes BLOCKED; the OS can run another READY process.
        <br><b>Q2:</b> Several processes are READY? → <b>The CPU scheduler must decide which one runs next.</b>
        """,
        "layers": ["res"],
        "say": ["İki senaryoda aynı iş yapılıyor. İkincisi daha uzun, çünkü I/O beklemesi ile P1'in CPU işi örtüşmüyor.",
                "İkinci soru bugünün konusu: FCFS, SJF, Round Robin, Priority, MLFQ."],
    },
    {
        "kicker": "Slide 8 · Concurrency vs parallelism",
        "title": "Overlapping progress is not the same as simultaneous execution",
        "body": """
        <b>One core:</b> A and B alternate — both make progress, never at the same instant (concurrency).
        <br><b>Two cores:</b> A and B can execute in the same time column (parallelism).
        <br><br>Threads of one process share memory, so even one core can corrupt shared data.
        """,
        "flow": "Concurrency = overlapping progress   ·   Parallelism = same instant",
        "board": ["V02_1"],
        "say": ["Vaka 1–2 üst çizelge, vaka 3–4 alt çizelge. Process mi thread mi olduğu çizelgeyi değiştirmez."],
    },
    {
        "kicker": "Slide 9 · Demo 2 · Layers 1–2",
        "title": "Two threads, one counter — and the timer interrupt",
        "body": """
        <b>counter++</b> is one line of C but three machine steps: <b>LOAD → ADD → STORE</b>.
        The OS timer may switch threads between any two steps. <b>The scheduler does not know about your counter.</b>
        """,
        "layers": ["app", "os"],
        "code": (("app", "Application code · user space", APP_THREADS), ("os", "OS kernel · pseudocode", OS_TIMER)),
        "say": ["Kod tek başına doğru. Sorun, iki thread'in adımları araya girince çıkıyor. Bu tek çekirdekte bile olur."],
    },
    {
        "kicker": "Slide 10 · LIVE DEMO 2 · Layers 3–4",
        "title": "Two threads + one shared variable = possible data race",
        "body": """
        <b>Predict:</b> counter = 5, both threads increment once. Is the result 6 or 7?
        <br>Step 1 · <b>Safe execution</b> → 7. Step 2 · <b>Interleaved race</b> → 6.
        <br>Step 3 · real OSTEP <code>x86.py</code>: interrupt interval <b>1 → 1</b>, <b>2 → 1</b>, <b>3 → 2</b> (expected 2).
        """,
        "layers": ["run", "res"],
        "demo": "thread",
        "board": ["V03_1", "V03_2"],
        "say": ["Program üç komut: oku, artır, yaz. Kesme bu üçünün arasına düşerse güncelleme kaybolur.",
                "Kod hiç değişmedi, sadece kesme zamanı değişti. Doğruluğu zamanlamaya bırakan program bozuktur."],
    },
    {
        "kicker": "Slide 11 · Demo 2 · The fix",
        "terms": ["Mutex"],
        "title": "The fix lives in the application: a mutex",
        "body": """
        The OS puts a thread that cannot get the lock into <b>WAITING</b> and wakes it on unlock.
        <b>Preemption does not release a mutex</b>: a preempted lock holder keeps it, so the result is always 7.
        """,
        "flow": "Scheduler: WHO runs now?   ·   Mutex: WHO may touch the shared data?",
        "layers": ["app", "os", "res"],
        "code": (("app", "Application code · with a mutex", APP_MUTEX), ("os", "OS kernel · pseudocode", OS_MUTEX)),
        "say": ["Linux'ta kilit bekleyen thread futex ile uyutulur. Scheduling ≠ synchronization."],
    },
    {
        "kicker": "Slide 12 · Preemption · all four layers",
        "terms": ["FCFS", "RR", "SRTF", "Preemption", "Quantum"],
        "title": "Same two jobs, three OS policies",
        "body": """
        P1 arrives at 0 (10 ms), P2 arrives at 3 (2 ms). Defaults: <b>2 processes</b>, FCFS.
        Run <b>FCFS</b> (P2 waits 7), then <b>Round Robin, quantum 2</b> (P2 waits 1).
        SRTF is not on the site: P1 0–3, P2 3–5, P1 5–12 (P2 waits 0).
        """,
        "flow": "Preemption is a capability. The algorithm decides WHEN to use it.",
        "layers": ["app", "os", "run", "res"],
        "code": (("app", "Applications (unchanged)", APP_TWO_JOBS), ("os", "OS kernel · three policies (pseudocode)", OS_THREE_POLICIES)),
        "demo": "schedule",
        "demo_args": {"jobs": [("P1", 0, 10), ("P2", 3, 2), ("P3", 20, 1), ("P4", 20, 1)], "n_jobs": 2, "policy": "FCFS", "quantum": 2},
        "board": ["V04_1"],
        "say": ["FCFS: P2 zaman 3'te geldi ama P1 bitene kadar bekliyor.",
                "RR q=2: zaman 2'de P2 henüz yok, P1 devam eder; zaman 4'te sıra P2'ye geçer."],
    },
    {
        "kicker": "Slide 13 · FCFS vs SJF",
        "terms": ["FCFS", "SJF", "Convoy effect"],
        "title": "Same 14 ms of work, different order",
        "body": """
        P1 = 8, P2 = 4, P3 = 2 ms, all at t = 0. <b>FCFS</b>: average wait 6.67 ms (convoy effect).
        <b>SJF</b>: average wait 2.67 ms — but SJF must know burst lengths in advance.
        """,
        "demo": "schedule",
        "demo_args": {"jobs": [("P1", 0, 8), ("P2", 0, 4), ("P3", 0, 2), ("P4", 20, 1)], "n_jobs": 3, "policy": "FCFS", "quantum": 2},
        "board": ["V05_1"],
        "say": ["Toplam iş yine 14 ms. Değişen sadece sıra. Gerçek OS iş süresini bilmez, geçmişten tahmin eder."],
    },
    {
        "kicker": "Slide 14 · SRTF (board only)",
        "terms": ["SRTF", "Starvation"],
        "title": "Shortest Remaining Time First: decide again at every arrival",
        "body": """
        P1 arrives at 0 (8 ms), P2 at 1 (4 ms). At t = 1: P1 has <b>7</b> left, P2 needs <b>4</b> → preempt P1.
        <br>Timeline: P1 0–1 · P2 1–5 · P1 5–12. Waiting: P1 4, P2 0.
        """,
        "flow": "compare remaining times at every arrival",
        "board": ["V06_1"],
        "say": ["SRTF sitede yok; tahtaya çizin. Sürekli kısa iş gelirse uzun iş aç kalabilir."],
    },
    {
        "kicker": "Slide 15 · LIVE DEMO 3 · all four layers",
        "terms": ["FCFS", "SJF", "RR"],
        "title": "One workload, three scheduling policies",
        "body": """
        P1 = 12, P2 = 3, P3 = 2 ms, all at t = 0. <b>Predict:</b> which policy finishes P2 and P3 earliest?
        <br>Expected average waiting: <b>FCFS 9.00</b> · <b>SJF 2.33</b> · <b>RR q=4 5.33</b> ms.
        """,
        "layers": ["app", "os", "run", "res"],
        "code": (("app", "Applications (unchanged)", APP_THREE_JOBS), ("os", "OS kernel · pick_next() (pseudocode)", OS_PICK_NEXT)),
        "demo": "schedule",
        "demo_args": {"jobs": [("P1", 0, 12), ("P2", 0, 3), ("P3", 0, 2), ("P4", 20, 1)], "n_jobs": 3, "policy": "FCFS", "quantum": 4},
        "board": ["V08_1"],
        "say": ["Cevap SJF: P3 zaman 2'de, P2 zaman 5'te biter. Ama SJF iş sürelerini önceden bilmeyi varsayar."],
    },
    {
        "kicker": "Slide 16 · LIVE DEMO 4 · Round Robin",
        "terms": ["RR", "Quantum", "Context switch"],
        "title": "A time quantum is a LIMIT, not a fixed duration",
        "body": """
        Same workload, Round Robin. With quantum 4, P2 runs 4–7 and exits early.
        Then try quantum <b>1, 2, 4, 12</b>: average response 1.00 / 2.00 / 3.67 / 9.00 ms;
        real context switches 8 / 5 / 3 / 2. Quantum 12 = FCFS.
        """,
        "layers": ["os", "run", "res"],
        "code": (("os", "OS kernel · Round Robin timer tick (pseudocode)", OS_TICK), None),
        "demo": "schedule",
        "demo_args": {"jobs": [("P1", 0, 12), ("P2", 0, 3), ("P3", 0, 2), ("P4", 20, 1)], "n_jobs": 3, "policy": "Round Robin", "quantum": 4},
        "board": ["V07_1", "V08_2"],
        "say": ["9–13 ve 13–17 arasındaki iki P1 kutusu gerçek bir switch değil; kuyrukta başka iş yok.",
                "Küçük quantum: herkes çabuk sıra alır ama switch maliyeti artar. Büyük quantum: RR, FCFS'e döner."],
    },
    {
        "kicker": "Slide 17 · Priority and MLFQ (board only)",
        "terms": ["Priority", "Starvation", "Aging", "MLFQ"],
        "title": "Importance, starvation and adaptive queues",
        "body": """
        <b>Priority</b> (smaller number = higher): P2 0–4, P3 4–6, P1 6–14. Priority means importance, not length.
        <br><b>Starvation</b>: a low-priority task may wait forever → aging / periodic boost.
        <br><b>MLFQ</b>: start in Q0; use a full slice → move down; periodic boost → back to Q0.
        """,
        "board": ["V09_1", "V10_1"],
        "say": ["SJF ile aynı sıra çıkması tesadüf. MLFQ'yu ayrıntı değil strateji olarak anlatın."],
    },
    {
        "kicker": "Slide 18 · Metrics and practice",
        "title": "One task, three clocks",
        "body": """
        <b>Response</b> = first run − arrival · <b>Waiting</b> = time in the ready queue ·
        <b>Turnaround</b> = completion − arrival.
        <br>Practice: P1 = 6, P2 = 2, P3 = 4 at t = 0 → FCFS 4.67 ms, SJF 2.67 ms average wait.
        """,
        "demo": "schedule",
        "demo_args": {"jobs": [("P1", 0, 6), ("P2", 0, 2), ("P3", 0, 4), ("P4", 20, 1)], "n_jobs": 3, "policy": "FCFS", "quantum": 2},
        "board": ["V11_1", "V12_1"],
        "say": ["Öğrencilere 5 dakika verin, kağıda çizsinler; sonra sitede kontrol edin."],
    },
    {
        "kicker": "Slide 19 · Multicore (board only)",
        "title": "Balance the load, but respect cache locality",
        "body": """
        Load balancing moves work to an idle core; <b>affinity</b> keeps a thread where its cache is warm.
        <br>Two cores do not make shared data correct: balance 100, T1 +10, T2 −20 → 90, or 110 / 80 without a lock.
        """,
        "board": ["V13_1"],
        "say": ["Taşımak bedava değil: T3'ün verisi Core 1'in cache'indeydi."],
    },
    {
        "kicker": "Slide 20 · Final mental model",
        "title": "Connect the whole story",
        "body": """
        <b>Programs</b> become processes. A <b>process</b> contains threads.
        The <b>scheduler</b> decides which runnable thread gets CPU time, and where.
        Threads can <b>share memory</b>, so shared state needs <b>synchronization</b>.
        """,
        "flow": "PROGRAM → PROCESS → THREAD(S) → SCHEDULER → CPU CORE(S)",
        "say": ["Çıkış sorusu: bugünkü sonuçlardan hangisi beklemeden, hangisi scheduling'den, hangisi paylaşılan bellekten kaynaklandı?"],
    },
]


LECTURE_DEMOS = {
    "process": lambda key, **kw: render_process_demo(key, **kw),
    "thread": lambda key, **kw: render_thread_demo(key, backend_open=True),
    "schedule": lambda key, **kw: render_scheduling_demo(key, **kw),
}


# ---------------------------------------------------------------------------
# Real-World Systems: four sector examples, each with two dimensions
#   Section 2 · Synchronization (safety)  and  Section 3 · CPU Scheduling (execution)
# ---------------------------------------------------------------------------
def _steps_table(rows, cols):
    st.table(pd.DataFrame(rows, columns=cols).set_index(cols[0]))


def render_lanes(lanes, colors, total=None):
    """lanes: list of (label, timeline list of names per ms). Draws one row per lane."""
    total = total or max(len(tl) for _, tl in lanes)
    html = ""
    for label, tl in lanes:
        segs, start = [], 0
        for i in range(1, len(tl) + 1):
            if i == len(tl) or tl[i] != tl[start]:
                segs.append((tl[start], start, i)); start = i
        html += (f"<div style='display:flex;align-items:center;gap:6px;margin:4px 0'>"
                 f"<div style='width:90px;font-weight:700;font-size:.85rem;color:#334155'>{label}</div>"
                 f"<div style='display:flex;gap:2px;flex:1'>")
        for name, a, b in segs:
            bg = colors.get(name, "#E5E7EB") if name != "idle" else "#FFFFFF"
            html += (f"<div style='width:{(b-a)/total*100}%;background:{bg};border:1px solid #CBD5E1;border-radius:8px;"
                     f"padding:6px 2px;text-align:center;font-weight:700;font-size:.8rem'>{'' if name == 'idle' else name}"
                     f"<br><span class='small'>{a}-{b}</span></div>")
        html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)


def periodic_simulate(tasks, policy, horizon, quantum=2):
    """tasks: (name, period or None, cpu ms, priority). One core, 1 ms ticks.
    policy 'priority' = fixed priority, preemptive; 'rr' = Round Robin."""
    jobs, timeline, queue = [], [], []
    current, used = None, 0
    for t in range(horizon):
        for name, period, cpu, prio in tasks:
            if (period and t % period == 0) or (period is None and t == 0):
                job = {"task": name, "release": t, "deadline": (t + period) if period else None,
                       "left": cpu, "prio": prio, "finish": None}
                jobs.append(job); queue.append(job)
        ready = [j for j in queue if j["left"] > 0]
        if policy == "priority":
            current = max(ready, key=lambda j: (j["prio"], -j["release"])) if ready else None
        else:
            if current is not None and (current["left"] == 0 or used >= quantum):
                if current["left"] > 0:
                    queue.remove(current); queue.append(current)
                current, used = None, 0
            if current is None:
                ready = [j for j in queue if j["left"] > 0]
                current, used = (ready[0], 0) if ready else (None, 0)
        if current is None:
            timeline.append("idle"); continue
        timeline.append(current["task"])
        current["left"] -= 1; used += 1
        if current["left"] == 0:
            current["finish"] = t + 1
    return timeline, jobs


def multicore_simulate(jobs, cores, policy="FCFS", quantum=1):
    """jobs: (name, arrival, burst). Global ready queue shared by `cores` cores, 1 ms ticks."""
    state = {n: {"arrival": a, "burst": b, "left": b, "first": None, "finish": None} for n, a, b in jobs}
    queue, running, used, t, seen = [], [None] * cores, [0] * cores, 0, set()
    timeline = [[] for _ in range(cores)]
    while any(s["left"] > 0 for s in state.values()):
        for n, a, b in sorted(jobs, key=lambda j: (j[1], j[0])):
            if a <= t and n not in seen:
                queue.append(n); seen.add(n)
        for c in range(cores):
            r = running[c]
            if r is not None and (state[r]["left"] == 0 or (policy == "RR" and used[c] >= quantum and queue)):
                if state[r]["left"] > 0:
                    queue.append(r)
                running[c] = None
            if running[c] is None and queue:
                running[c] = queue.pop(0); used[c] = 0
        for c in range(cores):
            r = running[c]
            timeline[c].append(r or "idle")
            if r is not None:
                s = state[r]
                if s["first"] is None: s["first"] = t
                s["left"] -= 1; used[c] += 1
                if s["left"] == 0: s["finish"] = t + 1
        t += 1
    return state, timeline


def _deadline_table(jobs, task_names):
    rows = []
    for j in jobs:
        if j["deadline"] is None or j["task"] not in task_names:
            continue
        met = j["finish"] is not None and j["finish"] <= j["deadline"]
        rows.append({"Task": j["task"], "Released (ms)": j["release"], "Deadline (ms)": j["deadline"],
                     "Finished (ms)": str(j["finish"]) if j["finish"] is not None else "not yet",
                     "Deadline met?": "yes" if met else "MISSED"})
    return rows


# --- Banking -------------------------------------------------------------------
def bank_trace(cores, lock, interleaved, last_writer):
    """Return (rows, cols, final) for T1 +10 and T2 −20 on balance 100."""
    if cores == 1:
        cols = ["Time", "CPU (one core)", "balance"]
        if lock:
            rows = [[1, "T1: lock ✓", 100], [2, "T1: READ 100", 100], [3, "— timer → T2: lock → WAITING (T1 holds it)", 100],
                    [4, "T1: ADD → 110", 100], [5, "T1: WRITE 110, unlock → T2 READY", 110],
                    [6, "T2: READ 110", 110], [7, "T2: SUB → 90", 110], [8, "T2: WRITE 90, unlock", 90]]
        elif not interleaved:
            rows = [[1, "T1: READ 100", 100], [2, "T1: ADD → 110", 100], [3, "T1: WRITE 110", 110],
                    [4, "T2: READ 110", 110], [5, "T2: SUB → 90", 110], [6, "T2: WRITE 90", 90]]
        elif last_writer == "T1":
            rows = [[1, "T1: READ 100", 100], [2, "— timer → T2: READ 100", 100], [3, "T2: SUB → 80", 100],
                    [4, "T2: WRITE 80", 80], [5, "— switch → T1: ADD → 110", 80], [6, "T1: WRITE 110", 110]]
        else:
            rows = [[1, "T1: READ 100", 100], [2, "T1: ADD → 110", 100], [3, "— timer → T2: READ 100", 100],
                    [4, "— switch → T1: WRITE 110", 110], [5, "T2: SUB → 80", 110], [6, "T2: WRITE 80", 80]]
    else:
        cols = ["Time", "Core 1", "Core 2", "balance"]
        if lock:
            rows = [[1, "T1: lock ✓", "T2: lock → WAITING", 100], [2, "T1: READ 100", "(waiting)", 100],
                    [3, "T1: ADD → 110", "(waiting)", 100], [4, "T1: WRITE 110, unlock", "T2 wakes up", 110],
                    [5, "", "T2: READ 110", 110], [6, "", "T2: SUB → 90", 110], [7, "", "T2: WRITE 90, unlock", 90]]
        elif not interleaved:
            rows = [[1, "T1: READ 100", "", 100], [2, "T1: ADD → 110", "", 100], [3, "T1: WRITE 110", "", 110],
                    [4, "", "T2: READ 110", 110], [5, "", "T2: SUB → 90", 110], [6, "", "T2: WRITE 90", 90]]
        elif last_writer == "T1":
            rows = [[1, "T1: READ 100", "T2: READ 100", 100], [2, "T1: ADD → 110", "T2: SUB → 80", 100],
                    [3, "", "T2: WRITE 80", 80], [4, "T1: WRITE 110", "", 110]]
        else:
            rows = [[1, "T1: READ 100", "T2: READ 100", 100], [2, "T1: ADD → 110", "T2: SUB → 80", 100],
                    [3, "T1: WRITE 110", "", 110], [4, "", "T2: WRITE 80", 80]]
    return rows, cols, rows[-1][-1]


def render_bank_demo(key):
    c1, c2, c3 = st.columns(3)
    with c1:
        cores = st.radio("CPU cores", [1, 2], horizontal=True, key=f"{key}_cores")
    with c2:
        timing = st.radio("Timing", ["One after the other", "Overlapping"], index=1, key=f"{key}_timing")
    with c3:
        last = st.radio("Who writes last?", ["T2", "T1"], horizontal=True, key=f"{key}_last")
    lock = st.toggle("Protect the balance with a mutex (or a DB transaction)", key=f"{key}_lock")
    rows, cols, final = bank_trace(cores, lock, timing == "Overlapping", last)
    _steps_table(rows, cols)
    m1, m2 = st.columns(2)
    m1.metric("Expected balance", 90)
    m2.metric("Actual balance", final)
    if final == 90:
        st.success("Correct: both updates are kept." + (" The lock made T2 wait (WAITING) instead of reading the old value." if lock else " Here only because the timing was lucky."))
    else:
        st.error(f"Lost update: the {'deposit' if final == 80 else 'withdrawal'} was overwritten. Both threads read 100.")


BANK_COLORS = {"Report": "#E5E7EB", "ATM-A": "#DBEAFE", "Mobile-B": "#DCFCE7", "ATM-C": "#FEF3C7"}


def render_bank_sched_demo(key):
    c1, c2 = st.columns([2, 1])
    with c1:
        pol = st.radio("Scheduling policy", ["FCFS", "SJF", "Round Robin (quantum 2 ms)"], horizontal=True, key=f"{key}_pol")
    with c2:
        rep = st.slider("End-of-day report (ms)", 4, 14, 10, key=f"{key}_rep")
    jobs = [("Report", 0, rep), ("ATM-A", 1, 1), ("Mobile-B", 2, 2), ("ATM-C", 3, 1)]
    if pol == "FCFS": rows, m = gantt_fcfs(jobs)
    elif pol == "SJF": rows, m = gantt_sjf(jobs)
    else: rows, m = gantt_rr(jobs, 2)
    tl = []
    for name, a, b in rows:
        tl += [name] * (b - a)
    render_lanes([("CPU", tl)], BANK_COLORS)
    st.dataframe(m, hide_index=True, width="stretch")
    short = m[m["Process"] != "Report"]
    c1, c2 = st.columns(2)
    c1.metric("Avg response of the 3 short requests", f"{short['Response'].mean():.2f} ms")
    c2.metric("Report finishes at", f"{int(m[m['Process'] == 'Report']['Finish'].iloc[0])} ms")
    if short["Response"].mean() > 3:
        st.error("Convoy effect: customers at the ATM wait behind the batch report.")
    else:
        st.success("Short requests get the CPU within a few ms; the report finishes a bit later. That is the trade-off.")


# --- Robotic surgery ------------------------------------------------------------
ROBOT_TASKS = [("Motor", 4, 1, 3), ("Camera", 8, 4, 2), ("Logging", None, 8, 1)]
ROBOT_COLORS = {"Motor": "#FECACA", "Camera": "#DBEAFE", "Logging": "#E5E7EB"}


def render_robot_sched_demo(key):
    c1, c2 = st.columns([2, 1])
    with c1:
        pol = st.radio("Scheduling policy", ["Round Robin (quantum 3 ms)", "Fixed priority, preemptive (SCHED_FIFO-like)"], key=f"{key}_pol")
    with c2:
        log_ms = st.slider("Logging work (ms)", 2, 12, 8, key=f"{key}_log")
    tasks = [(n, p, (log_ms if n == "Logging" else c), pr) for n, p, c, pr in ROBOT_TASKS]
    timeline, jobs = periodic_simulate(tasks, "priority" if pol.startswith("Fixed") else "rr", 16, quantum=3)
    render_lanes([("CPU", timeline)], ROBOT_COLORS)
    table = _deadline_table(jobs, {"Motor", "Camera"})
    st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")
    misses = sum(1 for r in table if r["Task"] == "Motor" and r["Deadline met?"] == "MISSED")
    st.metric("Motor-control deadline misses (0–16 ms)", misses)
    if misses:
        st.error("The motor-control loop missed a deadline: it waited in the Round Robin queue behind camera and logging work.")
    else:
        st.success("Motor control met every deadline: as soon as it is released it preempts lower-priority work.")


def robot_inversion_trace(inherit):
    """Logging (low) holds the state lock; Motor (high) needs it; Camera (medium) does not."""
    if not inherit:
        tl = ["Logging", "Logging*", "Logging*", "Camera", "Camera", "Camera", "Camera", "Camera", "Logging*", "Motor", "Motor"]
        events = [[0, "Logging runs (priority 1)", ""], [1, "Logging locks the shared state", "lock: Logging"],
                  [2, "Motor arrives (priority 3), needs the lock → WAITING", "lock: Logging"],
                  [3, "Camera arrives (priority 2) and preempts Logging", "lock: Logging"],
                  [8, "Camera done; Logging finally continues", "lock: Logging"],
                  [9, "Logging unlocks → Motor runs", "lock: Motor"], [11, "Motor finishes (deadline was 6)", "free"]]
        finish = 11
    else:
        tl = ["Logging", "Logging*", "Logging*", "Logging*", "Motor", "Motor", "Camera", "Camera", "Camera", "Camera", "Camera"]
        events = [[0, "Logging runs (priority 1)", ""], [1, "Logging locks the shared state", "lock: Logging"],
                  [2, "Motor arrives, needs the lock → WAITING; Logging inherits priority 3", "lock: Logging"],
                  [3, "Camera arrives (priority 2) but cannot preempt Logging (now 3)", "lock: Logging"],
                  [4, "Logging unlocks, drops back to priority 1 → Motor runs", "lock: Motor"],
                  [6, "Motor finishes on time → Camera runs", "free"], [11, "Camera finishes", "free"]]
        finish = 6
    return tl, events, finish


def render_robot_inversion_demo(key):
    inherit = st.toggle("Use a priority-inheritance mutex (PTHREAD_PRIO_INHERIT)", key=f"{key}_inherit")
    tl, events, finish = robot_inversion_trace(inherit)
    colors = {"Motor": "#FECACA", "Camera": "#DBEAFE", "Logging": "#E5E7EB", "Logging*": "#FDE68A"}
    render_lanes([("CPU", tl)], colors)
    st.caption("Logging* = Logging inside the critical section (holding the lock).")
    _steps_table(events, ["Time (ms)", "Event", "Lock"])
    c1, c2 = st.columns(2)
    c1.metric("Motor finishes at", f"{finish} ms")
    c2.metric("Motor deadline", "6 ms")
    if finish > 6:
        st.error("Priority inversion: the medium-priority camera delayed the high-priority motor task by keeping the lock holder off the CPU.")
    else:
        st.success("Priority inheritance let Logging finish its critical section quickly; Motor met its deadline.")


# --- Online ticket reservation ------------------------------------------------
def render_ticket_demo(key):
    c1, c2 = st.columns(2)
    with c1:
        mode = st.radio("Booking code", ["Check, then book (SELECT, then UPDATE)", "One atomic conditional UPDATE"], key=f"{key}_mode")
    with c2:
        timing = st.radio("Two users click 'Buy' for the last seat", ["5 ms apart", "At the same moment (2 cores)"], index=1, key=f"{key}_timing")
    safe = mode.startswith("One atomic")
    together = timing.startswith("At the same")
    cols = ["Time", "Worker 1 · User A", "Worker 2 · User B", "Seat A12 owner"]
    if not together:
        rows = [[1, "check: seat free" if not safe else "UPDATE … WHERE owner IS NULL → 1 row", "", "—" if not safe else "A"],
                [2, "book: owner = A" if not safe else "COMMIT", "", "A"],
                [3, "confirm ✓", "", "A"],
                [4, "", "check: seat taken → sold out" if not safe else "UPDATE … → 0 rows → sold out", "A"]]
        confirmed, owner = 1, "A"
    elif not safe:
        rows = [[1, "check: seat free", "check: seat free", "—"],
                [2, "book: owner = A", "book: owner = B", "B (overwrote A)"],
                [3, "confirm ✓", "confirm ✓", "B"]]
        confirmed, owner = 2, "B"
    else:
        rows = [[1, "UPDATE … WHERE owner IS NULL → 1 row", "UPDATE … (waits for the row lock)", "A"],
                [2, "COMMIT", "→ 0 rows changed", "A"],
                [3, "confirm ✓", "sold out", "A"]]
        confirmed, owner = 1, "A"
    _steps_table(rows, cols)
    m1, m2, m3 = st.columns(3)
    m1.metric("Seats available", 1)
    m2.metric("Tickets confirmed", confirmed)
    m3.metric("Seat owner in DB", owner)
    if confirmed > 1:
        st.error("Double booking: both workers checked before either booked. User A holds a confirmation for a seat that belongs to B.")
    else:
        st.success("Exactly one ticket was sold." + (" The database made check-and-book one atomic step." if safe else " Here only because the requests did not overlap."))


def render_ticket_sched_demo(key):
    c1, c2 = st.columns(2)
    with c1:
        cores = st.radio("CPU cores (one worker per core)", [1, 2, 4], horizontal=True, key=f"{key}_cores")
    with c2:
        pol = st.radio("Scheduling policy", ["FCFS", "Round Robin (quantum 1 ms)"], horizontal=True, key=f"{key}_pol")
    reqs = [(f"R{i}", 0, 2) for i in range(1, 9)]
    state, timeline = multicore_simulate(reqs, cores, "RR" if pol.startswith("Round") else "FCFS", 1)
    palette = ["#DBEAFE", "#DCFCE7", "#FEF3C7", "#FCE7F3", "#EDE9FE", "#E0F2FE", "#FFE4E6", "#ECFCCB"]
    colors = {f"R{i}": palette[i - 1] for i in range(1, 9)}
    render_lanes([(f"Core {c+1}", tl) for c, tl in enumerate(timeline)], colors)
    resp = [s["first"] - s["arrival"] for s in state.values()]
    fin = [s["finish"] for s in state.values()]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg response", f"{sum(resp)/len(resp):.2f} ms")
    c2.metric("Avg completion", f"{sum(fin)/len(fin):.2f} ms")
    c3.metric("Last request done", f"{max(fin)} ms")
    c4.metric("Requests running at the same instant", cores)
    st.info("More cores finish the burst sooner, but they also let more workers check the same seat at the same instant: "
            "the double-booking race from the previous slide becomes more likely, not less.")


# --- Video streaming --------------------------------------------------------------
def stream_simulate(capacity=4, prebuffer=2, rate=2, slow_rate=0, slow_len=6, slow_start=5, horizon=20):
    level, started, rows, stalls = 0, False, [], 0
    for t in range(horizon):
        r = slow_rate if slow_start <= t < slow_start + slow_len else rate
        add = min(r, capacity - level)
        net_state = "WAITING (buffer full)" if add < r else ("RUNNING (download)" if r else "WAITING (network I/O)")
        level += add
        if not started and level >= prebuffer:
            started = True
        if not started:
            dec = "WAITING (prebuffering)"
        elif level > 0:
            level -= 1; dec = "RUNNING (decode + render)"
        else:
            dec = "WAITING (buffer empty → STALL)"; stalls += 1
        rows.append({"t": t, "Chunks arriving": r, "Buffer level": level, "Network thread": net_state, "Decoder thread": dec})
    return rows, stalls


def render_stream_demo(key):
    c1, c2, c3 = st.columns(3)
    with c1:
        cap = st.slider("Buffer capacity (chunks)", 2, 10, 4, key=f"{key}_cap")
    with c2:
        slow = st.slider("Congestion length (ticks, from t = 5)", 0, 10, 6, key=f"{key}_slow")
    with c3:
        rate = st.slider("Normal network speed (chunks/tick)", 1, 3, 2, key=f"{key}_rate")
    rows, stalls = stream_simulate(capacity=cap, rate=rate, slow_len=slow)
    df = pd.DataFrame(rows)
    st.line_chart(df.set_index("t")[["Buffer level"]], height=180)
    st.dataframe(df, hide_index=True, width="stretch", height=260)
    m1, m2 = st.columns(2)
    m1.metric("Playback stalls (ticks)", stalls)
    m2.metric("Decoder consumes", "1 chunk / tick")
    if stalls:
        st.error("Buffer underrun: the decoder found the buffer empty and slept on the condition variable. The viewer sees a stall.")
    else:
        st.success("No stall: the buffer absorbed the congestion. While the network thread waited for I/O, the decoder kept running.")


def render_stream_sched_demo(key):
    c1, c2 = st.columns([2, 1])
    with c1:
        pol = st.radio("Scheduling policy", ["Fair Round Robin (quantum 2 ms)", "Decoder has higher priority"], key=f"{key}_pol")
    with c2:
        upd = st.slider("Background update work (ms)", 6, 30, 20, key=f"{key}_upd")
    tasks = [("Decoder", 5, 3, 2), ("Update", None, upd, 1)]
    timeline, jobs = periodic_simulate(tasks, "priority" if pol.startswith("Decoder") else "rr", 30, quantum=2)
    render_lanes([("CPU", timeline)], {"Decoder": "#DCFCE7", "Update": "#E5E7EB"})
    table = _deadline_table(jobs, {"Decoder"})
    for r in table:
        r["Frame"] = r.pop("Task")
    st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")
    dropped = sum(1 for r in table if r["Deadline met?"] == "MISSED")
    st.metric("Dropped frames (0–30 ms, one frame every 5 ms)", dropped)
    if dropped:
        st.error("Frames were late: fair sharing gave the background update the CPU while a frame was due.")
    else:
        st.success("Every frame was ready on time; the update simply used the CPU between frames.")


# --- Application and OS code shown on the slides --------------------------------------
APP_BANK = """void deposit(Account *a, int amount) {      // ATM, +10
    pthread_mutex_lock(&a->lock);
    a->balance = a->balance + amount;       // READ, ADD, WRITE
    pthread_mutex_unlock(&a->lock);
}

-- or, in the database:
BEGIN;
UPDATE accounts SET balance = balance - 20 WHERE id = 42;
COMMIT;"""
OS_BANK = """// two cores: each core runs its own READY thread
core1: run(T1);   core2: run(T2);     // truly parallel

mutex_lock(m):
    if (m->owner != NULL) {
        current->state = WAITING;     // sleeps, uses no CPU
        schedule();
    }
    m->owner = current;"""
APP_BANK_SCHED = """// nightly batch job: long CPU burst
void end_of_day_report(void) {
    setpriority(PRIO_PROCESS, 0, 19);   // ask for LOW priority
    for (each account) add_interest();
}

// request handlers: tiny CPU bursts
void handle_atm(Request *r) {
    check_pin(r);
    update_balance(r);
}"""
OS_BANK_SCHED = """// FCFS: the report keeps the CPU until it finishes
// Round Robin: share the CPU in slices
on_timer_tick():
    if (++current->used == QUANTUM && !ready_empty())
        preempt(current);        // ATM request runs next

on_arrival(req):  ready_push(req);"""
APP_ROBOT_LOCK = """pthread_mutexattr_t attr;
pthread_mutexattr_init(&attr);
pthread_mutexattr_setprotocol(&attr, PTHREAD_PRIO_INHERIT);
pthread_mutex_init(&state_lock, &attr);

// Logging (low):  lock → copy robot state → unlock
// Motor   (high): lock → read robot state → unlock → actuate"""
OS_ROBOT_LOCK = """mutex_lock(m):
    if (m->owner != NULL) {
        if (m->protocol == PRIO_INHERIT &&
            m->owner->prio < current->prio)
            m->owner->prio = current->prio;   // boost holder
        current->state = WAITING;
        schedule();
    }

mutex_unlock(m):
    current->prio = current->base_prio;      // drop boost
    wake_highest_waiter(m);"""
APP_RT = """void *motor_control(void *arg) {           // every 4 ms
    for (;;) {
        read_sensors();
        compute_command();
        send_to_actuator();
        wait_until_next_period(4);
    }
}

struct sched_param p = { .sched_priority = 80 };
pthread_setschedparam(motor, SCHED_FIFO, &p);  // request RT priority"""
OS_RT = """on_release(job):                     // timer: new period
    ready_push(job);
    if (job->prio > current->prio)
        preempt(current);                // urgent work first

pick_next(): return highest_priority(ready_queue);"""
APP_TICKET = """-- UNSAFE: check, then act (two statements)
SELECT owner FROM seats WHERE id = 'A12';     -- NULL: free
UPDATE seats SET owner = :user WHERE id = 'A12';

-- SAFE: one atomic conditional statement
UPDATE seats SET owner = :user
 WHERE id = 'A12' AND owner IS NULL;          -- 0 rows = sold out"""
OS_TICKET = """// two workers on two cores: same instant
core1: run(worker_A);   core2: run(worker_B);

// the database, not the scheduler, serialises the row:
row_lock(seat_A12):
    if (locked) { current->state = WAITING; schedule(); }"""
APP_TICKET_SCHED = """// web server: one worker thread per CPU core
for (int i = 0; i < num_cores; i++)
    pthread_create(&w[i], NULL, worker_loop, NULL);

void *worker_loop(void *arg) {
    for (;;) {
        Request r = next_request();   // burst at sale opening
        book_seat(&r);                // ~2 ms of CPU
        reply(&r);
    }
}"""
OS_TICKET_SCHED = """// global ready queue shared by all cores
on_core_idle(core):
    core->current = ready_pop();     // load balancing

// Round Robin, quantum 1 ms: everyone starts early
on_timer_tick(core):
    if (++core->current->used == 1 && !ready_empty())
        preempt(core->current);"""
APP_STREAM = """void *network(void *a) {                       // producer
    for (;;) {
        Chunk c = download_next();             // I/O: blocks
        lock(&m);
        while (full())  cond_wait(&not_full, &m);
        put(c);  cond_signal(&not_empty);
        unlock(&m);
    }
}
void *decoder(void *a) {                       // consumer
    for (;;) {
        lock(&m);
        while (empty()) cond_wait(&not_empty, &m);
        Chunk c = take();  cond_signal(&not_full);
        unlock(&m);
        decode_and_render(c);                  // CPU work
    }
}"""
OS_STREAM = """cond_wait(cv, m):
    current->state = WAITING;   // off the ready queue
    wait_queue_add(cv, current);
    mutex_unlock(m);
    schedule();                 // CPU runs someone else

cond_signal(cv):
    t = wait_queue_pop(cv);
    t->state = READY;           // scheduler may pick it"""
APP_STREAM_SCHED = """// decoder: 3 ms of CPU for every frame, one frame every 5 ms
struct sched_param p = { .sched_priority = 50 };
pthread_setschedparam(decoder, SCHED_FIFO, &p);

// background app update: 20 ms of CPU, not urgent
setpriority(PRIO_PROCESS, updater_pid, 19);"""
OS_STREAM_SCHED = """on_frame_timer():                  // every 5 ms
    release(decoder_job, deadline = now + 5);

pick_next():
    // fair RR: decoder and update take turns
    // priority: decoder first whenever it is READY
    return policy == RR ? ready_head() : highest_priority();"""


def _design_table(rows):
    body = "".join(f"<tr><td style='padding:6px 10px;font-weight:700;vertical-align:top'>{a}</td><td style='padding:6px 10px'>{b}</td></tr>" for a, b in rows)
    return f"<table style='width:100%;border-collapse:collapse;font-size:1.02rem'>{body}</table>"


S2 = "Section 2 · Synchronization"
S3 = "Section 3 · CPU Scheduling"

SECTOR_SLIDES = [
    {
        "kicker": "Real-world systems · Overview",
        "title": "Four systems, two dimensions",
        "body": """
        Every real system needs <b>both</b> dimensions from this week:
        <br><b>Section 2 · Synchronization (safety):</b> can shared data stay correct?
        <br><b>Section 3 · CPU Scheduling (execution):</b> who runs, when, and on which core?
        <br><br>For each system we ask: <b>What must run? What must be protected? What must be optimized?</b>
        <br><br><b>Banking</b> · <b>Robotic surgery</b> · <b>Online ticket reservation</b> · <b>Video streaming</b>
        """,
        "flow": "Scheduling ≠ synchronization — both affect the same running system",
        "say": ["Bu dört örnek ders notlarındaki dört mimari. Her birinde iki demo var: biri senkronizasyon (bölüm 2), biri scheduling (bölüm 3).",
                "Her sistemde üç soruyu soracağız: ne çalışmalı, ne korunmalı, ne optimize edilmeli?"],
        "say_en": ["These are the four architectures from the lecture notes. Each has two demos: one for synchronization (section 2) and one for scheduling (section 3).",
                   "For each system we ask three questions: what must run, what must be protected, what must be optimized?"],
        "qa": [("Scheduling ile synchronization arasındaki fark nedir?",
                "Scheduling kimin, ne zaman ve hangi çekirdekte çalışacağına karar verir. Synchronization paylaşılan verinin doğru kalmasını sağlar. İkisi aynı sistemde birlikte gerekir.",
                "What is the difference between scheduling and synchronization?",
                "Scheduling decides who runs, when and on which core. Synchronization keeps shared data correct. A real system needs both.")],
    },
    # ======================= Banking =======================
    {
        "kicker": f"Banking · {S2}",
        "board": ["V14_1"],
        "title": "Banking: two requests, one account",
        "body": """
        An ATM deposit (<b>+10</b>) and a mobile transfer (<b>−20</b>) hit the same account (balance <b>100</b>) at the same time.
        <br><b>Predict:</b> without a lock, both threads read 100. What can the final balance be?
        Try 1 and 2 cores, change who writes last, then turn the <b>mutex</b> on.
        """,
        "layers": ["app", "os", "run", "res"],
        "terms": ["Mutex", "Transaction", "Lost update"],
        "code": (("app", "Application code · C and SQL", APP_BANK), ("os", "OS kernel · pseudocode", OS_BANK)),
        "demo": "bank",
        "say": ["Bu, Demo 2'nin bankacılık versiyonu. Önce kilitsiz, 'Overlapping' ile çalıştırın: sonuç 80 veya 110. Sonra mutex'i açın: her zaman 90.",
                "Gerçek bankalar bunu çoğunlukla veritabanı transaction'ı ve izolasyonla çözer; mutex aynı fikrin bellek içi hali."],
        "say_en": ["This is the banking version of Demo 2. First run without the lock, 'Overlapping': the result is 80 or 110. Then turn the mutex on: always 90.",
                   "Real banks usually solve this with database transactions and isolation; a mutex is the in-memory form of the same idea."],
        "qa": [("Mutex yoksa sonuç ne olabilir?",
                "İkisi de 100'ü okur. T1 110, T2 80 yazar; en son yazan kazanır. Sonuç 110 veya 80 olur, doğrusu 90.",
                "Without a mutex, what can the result be?",
                "Both read 100. T1 writes 110, T2 writes 80; the last writer wins. The result is 110 or 80; the correct value is 90."),
               ("'One after the other' seçeneğinde kilitsiz sonuç neden doğru?",
                "Çünkü adımlar örtüşmedi. Bu şans; zamanlama değişince hata geri gelir.",
                "Why is the result correct without a lock when requests come one after the other?",
                "Because the steps did not overlap. That is luck; when the timing changes the bug returns.")],
    },
    {
        "kicker": f"Banking · {S3}",
        "board": ["V14_1"],
        "title": "Banking: ATM customers behind a batch report",
        "body": """
        At 0 ms a 10 ms <b>end-of-day report</b> starts. Three short requests arrive at 1, 2 and 3 ms (ATM 1 ms, mobile 2 ms, ATM 1 ms).
        <br><b>Predict:</b> which policy gives the short requests the fastest response?
        """,
        "layers": ["app", "os", "run", "res"],
        "terms": ["FCFS", "SJF", "RR", "Convoy effect"],
        "code": (("app", "Application code · C", APP_BANK_SCHED), ("os", "OS kernel · pseudocode", OS_BANK_SCHED)),
        "demo": "bank_sched",
        "say": ["FCFS'te ATM müşterileri raporun arkasında bekliyor: ortalama yanıt 9,33 ms. Convoy effect.",
                "SJF de yardım etmiyor (9,00 ms): non-preemptive, rapor zaten başlamış. Round Robin'de 2,00 ms; bedeli raporun 10 yerine 14'te bitmesi."],
        "say_en": ["With FCFS the ATM customers wait behind the report: average response 9.33 ms. Convoy effect.",
                   "SJF does not help either (9.00 ms): it is non-preemptive and the report has already started. Round Robin gives 2.00 ms; the price is the report finishing at 14 instead of 10."],
        "qa": [("Kısa isteklere en hızlı yanıtı hangi politika verir?",
                "Round Robin: ortalama 2,00 ms. FCFS 9,33 ms, SJF 9,00 ms.",
                "Which policy gives the short requests the fastest response?",
                "Round Robin: 2.00 ms on average. FCFS 9.33 ms, SJF 9.00 ms."),
               ("SJF burada neden işe yaramıyor?",
                "Bizim SJF'miz non-preemptive. Kısa istekler geldiğinde rapor zaten CPU'da; bitene kadar kesilmiyor.",
                "Why does SJF not help here?",
                "Our SJF is non-preemptive. When the short requests arrive the report is already on the CPU and is not interrupted until it ends."),
               ("Rapor işi kendi önceliğini düşürebilir mi?",
                "Evet: setpriority(…, 19) ile düşük öncelik isteyebilir (Linux'ta nice). Karar yine OS'nin.",
                "Can the report job lower its own priority?",
                "Yes: it can request a low priority with setpriority(…, 19) (nice on Linux). The decision is still the OS's.")],
    },
    {
        "kicker": "Banking · Design decision",
        "board": ["V14_1"],
        "title": "Banking: correct first, then responsive",
        "body": _design_table([
            ("What must run?", "Short request handlers (ATM, mobile, web) and long batch jobs"),
            ("What must be protected?", "Account balances: transactions / isolation, no lost update, no double spending"),
            ("What must be optimized?", "Correctness first; then fast response for short requests"),
            ("Section 2 answer", "Mutex or DB transaction around every read-modify-write"),
            ("Section 3 answer", "Preemptive time sharing (RR) or low priority for batch jobs"),
        ]),
        "flow": "More cores = more real parallel races, so correctness never comes from the scheduler",
        "say": ["Scheduler bakiyeyi koruyamaz; doğruluk transaction veya kilitle sağlanır. Scheduler ise müşterinin ne kadar beklediğini belirler."],
        "say_en": ["The scheduler cannot protect the balance; correctness comes from transactions or locks. The scheduler decides how long customers wait."],
        "qa": [("İki çekirdek bankayı daha hızlı yapar mı?",
                "Farklı hesaplara gelen işlemler paralel hızlanır. Aynı hesabı güncelleyenler kilit yüzünden sırayla çalışır.",
                "Do two cores make the bank faster?",
                "Requests for different accounts speed up in parallel. Requests for the same account still take turns because of the lock.")],
    },
    # ======================= Robotic surgery =======================
    {
        "kicker": f"Robotic surgery · {S2}",
        "board": ["V15_1"],
        "title": "Robotic surgery: priority inversion",
        "body": """
        <b>Logging</b> (priority 1) and <b>motor control</b> (priority 3) share the robot-state lock. <b>Camera</b> (priority 2) does not need it.
        Motor control arrives at 2 ms with a deadline of 6 ms.
        <br><b>Predict:</b> can the medium-priority camera delay the high-priority motor task? Then turn on <b>priority inheritance</b>.
        """,
        "layers": ["app", "os", "run", "res"],
        "terms": ["Priority inversion", "Priority inheritance", "Mutex"],
        "code": (("app", "Application code · C (POSIX)", APP_ROBOT_LOCK), ("os", "OS kernel · pseudocode", OS_ROBOT_LOCK)),
        "demo": "robot_lock",
        "say": ["Kilitsiz değil, kilit var; ama kilit sahibi düşük öncelikli. Kamera onu kesince motor kontrolü dolaylı olarak kamerayı bekliyor: 11'de bitiyor, deadline 6.",
                "Priority inheritance açılınca Logging geçici olarak öncelik 3'e çıkıyor, kritik bölümü 4'te bitiriyor, motor 6'da bitiyor.",
                "Bilinen örnek: 1997'de Mars Pathfinder'daki tekrar eden resetler priority inversion yüzündendi; priority inheritance açılarak düzeltildi."],
        "say_en": ["There is a lock, but its holder has low priority. When the camera preempts it, motor control indirectly waits for the camera: it finishes at 11, deadline 6.",
                   "With priority inheritance, Logging temporarily runs at priority 3, finishes its critical section at 4, and motor control finishes at 6.",
                   "A well-known case: the repeated resets on Mars Pathfinder in 1997 were caused by priority inversion and fixed by enabling priority inheritance."],
        "qa": [("Priority inversion nedir?",
                "Yüksek öncelikli thread, düşük öncelikli thread'in tuttuğu kilidi bekler; bu sırada orta öncelikli thread düşük olanı CPU'dan uzak tutar.",
                "What is priority inversion?",
                "A high-priority thread waits for a lock held by a low-priority thread, while a medium-priority thread keeps the low one off the CPU."),
               ("Priority inheritance olmadan ve onunla motor kontrolü ne zaman bitiyor?",
                "Olmadan 11 ms'de (deadline 6, kaçırıldı). Onunla 6 ms'de (zamanında).",
                "When does motor control finish without and with priority inheritance?",
                "Without it at 11 ms (deadline 6, missed). With it at 6 ms (on time)."),
               ("Bu bir senkronizasyon sorunu mu, scheduling sorunu mu?",
                "İkisinin kesiştiği yer: kilit (senkronizasyon) ile öncelikli scheduling'in etkileşimi. Çözüm de ikisini birleştiriyor.",
                "Is this a synchronization problem or a scheduling problem?",
                "It sits where they meet: a lock (synchronization) interacting with priority scheduling. The fix combines both.")],
    },
    {
        "kicker": f"Robotic surgery · {S3}",
        "board": ["V15_1"],
        "title": "Robotic surgery: Round Robin vs fixed priority",
        "body": """
        Motor control: <b>1 ms</b> every <b>4 ms</b>. Camera: <b>4 ms</b> every <b>8 ms</b>. Logging: background work.
        <br><b>Predict:</b> with fair Round Robin (quantum 3 ms), does motor control meet every 4 ms deadline?
        Then switch to <b>fixed priority, preemptive</b>, and try a short logging job (2 ms).
        """,
        "layers": ["app", "os", "run", "res"],
        "terms": ["Real-time", "SCHED_FIFO", "Deadline", "WCET"],
        "code": (("app", "Application code · C (POSIX)", APP_RT), ("os", "OS kernel · pseudocode", OS_RT)),
        "demo": "robot_sched",
        "say": ["Round Robin adil ama adil olmak burada yanlış hedef: motor kontrolü kamera ve log işinin arkasında bekliyor ve 2 deadline kaçırıyor.",
                "Sabit öncelikte motor kontrolü her periyot başında diğer işleri kesiyor ve hiç deadline kaçırmıyor."],
        "say_en": ["Round Robin is fair, but fairness is the wrong goal here: motor control waits behind camera and logging work and misses 2 deadlines.",
                   "With fixed priority, motor control preempts the others at the start of every period and never misses a deadline."],
        "qa": [("Round Robin'de motor kontrolü neden deadline kaçırıyor?",
                "Kuyrukta kamera ve log işinin arkasında bekliyor. Log 8 ms iken 8. ms'de gelen iş 13'te bitiyor (deadline 12), 12. ms'deki iş hiç bitmiyor. Log 2 ms'ye inince RR de yetişiyor.",
                "Why does motor control miss a deadline with Round Robin?",
                "It waits behind camera and logging work. With 8 ms of logging, the job released at 8 ms finishes at 13 (deadline 12) and the one released at 12 never finishes. With 2 ms of logging RR also makes it."),
               ("Real-time scheduling tek başına güvenliği garanti eder mi?",
                "Hayır. WCET analizi, doğru öncelikler, priority inversion'a karşı önlem ve güvenli tasarım da gerekir.",
                "Does real-time scheduling alone guarantee safety?",
                "No. You also need WCET analysis, correct priorities, protection against priority inversion and a safe design.")],
    },
    {
        "kicker": "Robotic surgery · Design decision",
        "board": ["V15_1"],
        "title": "Robotic surgery: deadlines, not throughput",
        "body": _design_table([
            ("What must run?", "Sensor → control → actuator loop, camera/vision, logging"),
            ("What must be protected?", "Shared robot state and commands, with short, bounded critical sections"),
            ("What must be optimized?", "Verified deadlines (WCET), not throughput or fairness"),
            ("Section 2 answer", "Priority-inheritance mutexes, short critical sections"),
            ("Section 3 answer", "Fixed real-time priorities, admission and deadline analysis; control and vision on separate cores"),
        ]),
        "flow": "A missed deadline is a failure, even if the average is excellent",
        "say": ["Bu sistemde iki boyut iç içe: öncelikli scheduling, kilitlerle birlikte doğru kurulmazsa priority inversion çıkar."],
        "say_en": ["Here the two dimensions are intertwined: priority scheduling combined with locks causes priority inversion unless set up correctly."],
        "qa": [("Bu sistemde neyi optimize ederiz?",
                "Ortalama bekleme süresini değil, son tarihleri. Bir deadline kaçırmak güvenlik hatasıdır.",
                "What do we optimize in this system?",
                "Deadlines, not average waiting time. Missing one deadline is a safety failure.")],
    },
    # ======================= Ticket reservation =======================
    {
        "kicker": f"Online ticket reservation · {S2}",
        "board": ["V16_1"],
        "title": "Ticket reservation: the last seat",
        "body": """
        Two users try to buy the <b>last seat (A12)</b> at the same moment, served by two workers on two cores.
        <br><b>Predict:</b> how many tickets are confirmed for one seat? Run <b>check, then book</b>, then <b>one atomic conditional UPDATE</b>.
        """,
        "layers": ["app", "os", "run", "res"],
        "terms": ["Race condition", "Atomic"],
        "code": (("app", "Application code · SQL", APP_TICKET), ("os", "OS kernel and database · pseudocode", OS_TICKET)),
        "demo": "ticket",
        "say": ["Önce kontrol et, sonra yaz: iki ayrı adım. Aynı anda tıklayınca iki onay çıkıyor; biri gerçekte koltuğa sahip değil.",
                "Atomik UPDATE'te veritabanı satırı kilitliyor; ikinci istek 0 satır değiştiriyor ve 'tükendi' alıyor."],
        "say_en": ["Check, then write: two separate steps. When both click at the same moment two confirmations appear; one of them does not really own the seat.",
                   "With the atomic UPDATE the database locks the row; the second request changes 0 rows and gets 'sold out'."],
        "qa": [("Aynı anda tıklanınca kaç bilet onaylanıyor?",
                "Kontrol-sonra-yaz kodunda 2 (double booking). Atomik UPDATE ile 1.",
                "How many tickets are confirmed when both click at the same moment?",
                "Two with check-then-book (double booking). One with the atomic UPDATE."),
               ("SELECT sonra UPDATE neden güvensiz?",
                "İki adım arasında başka bir worker da koltuğu boş görebilir; ikisi de satın alır.",
                "Why is SELECT followed by UPDATE unsafe?",
                "Between the two steps another worker can also see the seat as free; both buy it.")],
    },
    {
        "kicker": f"Online ticket reservation · {S3}",
        "board": ["V16_1"],
        "title": "Ticket reservation: the burst at sale opening",
        "body": """
        When sales open, <b>8 requests</b> (2 ms of CPU each) arrive at the same moment. One worker runs per core.
        <br><b>Predict:</b> how does the average response change with 1, 2 and 4 cores? What does Round Robin (quantum 1 ms) change?
        """,
        "layers": ["app", "os", "run", "res"],
        "terms": ["FCFS", "RR", "Quantum"],
        "code": (("app", "Application code · C", APP_TICKET_SCHED), ("os", "OS kernel · pseudocode", OS_TICKET_SCHED)),
        "demo": "ticket_sched",
        "say": ["FCFS'te ortalama yanıt 1 çekirdekte 7, 2'de 3, 4'te 1 ms. Çekirdek arttıkça patlama daha çabuk eriyor.",
                "Round Robin (q=1) tek çekirdekte ilk yanıtı 7'den 3,5 ms'ye indiriyor ama ortalama bitişi 9'dan 12,5'e çıkarıyor: herkes erken başlıyor, geç bitiyor.",
                "Aynı anda çalışan worker sayısı çekirdek sayısına eşit; bu da önceki slayttaki yarışın ihtimalini artırıyor."],
        "say_en": ["With FCFS the average response is 7 ms on 1 core, 3 on 2 and 1 on 4. More cores melt the burst faster.",
                   "Round Robin (q=1) on one core lowers the first response from 7 to 3.5 ms but raises the average completion from 9 to 12.5: everyone starts early and finishes late.",
                   "The number of workers running at the same instant equals the number of cores, which makes the race from the previous slide more likely."],
        "qa": [("1, 2 ve 4 çekirdekte ortalama yanıt nedir (FCFS)?",
                "7, 3 ve 1 ms. Son istek 16, 8 ve 4 ms'de bitiyor.",
                "What is the average response on 1, 2 and 4 cores (FCFS)?",
                "7, 3 and 1 ms. The last request finishes at 16, 8 and 4 ms."),
               ("Round Robin tek çekirdekte neyi iyileştirir, neyi kötüleştirir?",
                "Ortalama yanıtı 7'den 3,5 ms'ye iyileştirir; ortalama bitişi 9'dan 12,5 ms'ye kötüleştirir. Son istek yine 16'da biter.",
                "On one core, what does Round Robin improve and what does it make worse?",
                "It improves average response from 7 to 3.5 ms and worsens average completion from 9 to 12.5 ms. The last request still finishes at 16."),
               ("Daha fazla çekirdek double booking hatasını azaltır mı?",
                "Hayır, artırır: daha çok worker gerçekten aynı anda çalışır. Çözüm atomik veritabanı işlemi.",
                "Do more cores reduce the double-booking bug?",
                "No, they increase it: more workers truly run at the same instant. The fix is an atomic database operation.")],
    },
    {
        "kicker": "Online ticket reservation · Design decision",
        "board": ["V16_1"],
        "title": "Ticket reservation: fast AND never sell one seat twice",
        "body": _design_table([
            ("What must run?", "Many short request handlers in a worker pool"),
            ("What must be protected?", "Each seat: atomic allocation, database constraints"),
            ("What must be optimized?", "Response latency and fairness under burst traffic"),
            ("Section 2 answer", "One atomic conditional UPDATE or a unique constraint per seat"),
            ("Section 3 answer", "More cores and time sharing to melt the burst quickly"),
        ]),
        "flow": "Speed comes from the scheduler and the cores; correctness comes from the database",
        "say": ["Hız ve doğruluk ayrı katmanlarda çözülüyor: hız scheduler'da ve çekirdeklerde, doğruluk veritabanında."],
        "say_en": ["Speed and correctness are solved in different layers: speed in the scheduler and cores, correctness in the database."],
        "qa": [("Bu sistemde scheduler neyi optimize etmeli?",
                "Yanıt süresini ve adaleti: patlama anında her kullanıcı kısa sürede yanıt almalı.",
                "What should the scheduler optimize here?",
                "Response time and fairness: during a burst every user should get a quick answer.")],
    },
    # ======================= Video streaming =======================
    {
        "kicker": f"Video streaming · {S2}",
        "board": ["V17_1"],
        "title": "Video streaming: producer, consumer and the buffer",
        "body": """
        A <b>network thread</b> downloads chunks into a buffer; a <b>decoder thread</b> takes one chunk per tick.
        <br><b>Predict:</b> the network stops for 6 ticks. With a buffer of 4 chunks, does playback stall? Then try a larger buffer.
        """,
        "layers": ["app", "os", "run", "res"],
        "terms": ["Producer–consumer", "Condition variable", "Underrun"],
        "code": (("app", "Application code · C (pthreads)", APP_STREAM), ("os", "OS kernel · pseudocode", OS_STREAM)),
        "demo": "stream",
        "say": ["Buffer boşsa decoder cond_wait ile uyur ve CPU'yu bırakır; ağ yeni parça getirince uyandırılır.",
                "Varsayılan ayarlarda (buffer 4, tıkanma 6) 3 tık takılma oluyor; buffer 8 olunca 1 tık."],
        "say_en": ["If the buffer is empty, the decoder sleeps in cond_wait and gives up the CPU; it is woken when the network brings a new chunk.",
                   "With the defaults (buffer 4, congestion 6) playback stalls for 3 ticks; with a buffer of 8, for 1 tick."],
        "qa": [("Varsayılan ayarlarda kaç tık takılma oluyor?",
                "3 tık. Buffer tıkanma başladığında 3 parça içeriyor; 3 tıkta boşalıyor ve tıkanmanın kalan 3 tıkında decoder bekliyor.",
                "How many stall ticks happen with the default settings?",
                "3 ticks. The buffer holds 3 chunks when congestion starts; it drains in 3 ticks and the decoder waits for the remaining 3 ticks."),
               ("Neden while (empty()) yazıyoruz, if değil?",
                "Uyandırıldığında koşul hâlâ doğru olmayabilir (başka thread parçayı almış olabilir veya sahte uyanma). Koşul tekrar kontrol edilir.",
                "Why do we write while (empty()) and not if?",
                "When woken, the condition may no longer hold (another thread took the chunk, or a spurious wake-up). The condition is checked again."),
               ("Takılma sırasında decoder CPU kullanır mı?",
                "Hayır. Condition variable üzerinde WAITING durumunda uyur; CPU başka işleri çalıştırabilir.",
                "Does the decoder use the CPU during a stall?",
                "No. It sleeps in the WAITING state on the condition variable; the CPU can run other work.")],
    },
    {
        "kicker": f"Video streaming · {S3}",
        "board": ["V17_1"],
        "title": "Video streaming: frame deadlines vs a background update",
        "body": """
        Every <b>5 ms</b> a frame is due; decoding it takes <b>3 ms</b>. A background app update needs <b>20 ms</b> of CPU.
        <br><b>Predict:</b> with fair Round Robin, are frames dropped? Then give the decoder higher priority.
        """,
        "layers": ["app", "os", "run", "res"],
        "terms": ["RR", "Priority", "Deadline"],
        "code": (("app", "Application code · C (POSIX)", APP_STREAM_SCHED), ("os", "OS kernel · pseudocode", OS_STREAM_SCHED)),
        "demo": "stream_sched",
        "say": ["Adil Round Robin'de güncelleme işi kare zamanı gelmişken CPU'yu alıyor: 30 ms'de 5 kare gecikiyor.",
                "Decoder öncelikli olunca hiç kare düşmüyor; güncelleme kareler arasındaki boşlukta ilerliyor."],
        "say_en": ["With fair Round Robin the update takes the CPU while a frame is due: 5 frames are late in 30 ms.",
                   "With decoder priority no frame is dropped; the update makes progress in the gaps between frames."],
        "qa": [("Adil Round Robin'de kaç kare düşüyor?",
                "Varsayılan ayarlarla 30 ms içinde 5 kare (5, 10, 15, 20 ve 25. ms'de gelen kareler). Decoder öncelikliyken 0.",
                "How many frames are dropped with fair Round Robin?",
                "With the defaults, 5 frames in 30 ms (those released at 5, 10, 15, 20 and 25 ms). With decoder priority, 0."),
               ("Decoder'a öncelik vermek güncelleme işini aç bırakır mı?",
                "Bu örnekte hayır: decoder CPU'nun %60'ını kullanıyor, kalan %40'ta güncelleme ilerliyor. Decoder CPU'nun tamamını isteseydi starvation olurdu.",
                "Does giving the decoder priority starve the update?",
                "Not here: the decoder uses 60% of the CPU and the update progresses in the remaining 40%. If the decoder wanted the whole CPU, the update would starve.")],
    },
    {
        "kicker": "Video streaming · Design decision",
        "board": ["V17_1"],
        "title": "Video streaming: smooth playback",
        "body": _design_table([
            ("What must run?", "Network (producer, I/O-bound), decoder/renderer (consumer, CPU-bound), background work"),
            ("What must be protected?", "The shared buffer: mutex + condition variables (or semaphores)"),
            ("What must be optimized?", "No stalls and no late frames; low start-up latency"),
            ("Section 2 answer", "Bounded buffer with condition variables, sized to absorb congestion"),
            ("Section 3 answer", "Decoder ahead of background work; decode and render may overlap on distinct cores"),
        ]),
        "flow": "I/O-bound producer + CPU-bound consumer + bounded buffer + the right priority = smooth video",
        "say": ["Dört sistemin ortak dersi: uygulama işi tanımlar, OS yürütür; synchronization doğruluğu, scheduling zamanlamayı korur."],
        "say_en": ["The common lesson of all four systems: the application defines the work, the OS executes it; synchronization protects correctness, scheduling protects timing."],
        "qa": [("Bu dört sistemin hangisinde en önemli hedef deadline, hangisinde doğruluk?",
                "Robotik cerrahi ve videoda deadline (kontrol periyodu, kare zamanı). Banka ve bilette doğruluk (kayıp güncelleme ve çift satış olmamalı); ardından yanıt süresi.",
                "In which systems is the main goal a deadline, and in which correctness?",
                "Robotic surgery and video: deadlines (control period, frame time). Banking and tickets: correctness (no lost update, no double booking), then response time.")],
    },
]

SECTOR_DEMOS = {
    "bank": render_bank_demo, "bank_sched": render_bank_sched_demo,
    "robot_lock": render_robot_inversion_demo, "robot_sched": render_robot_sched_demo,
    "ticket": render_ticket_demo, "ticket_sched": render_ticket_sched_demo,
    "stream": render_stream_demo, "stream_sched": render_stream_sched_demo,
}


def render_sector_mode():
    st.header("🏭 Real-World Systems")
    st.caption("Lecture Mode for the four architectures in the Week 6 notes. Each system has a Section 2 · Synchronization demo, "
               "a Section 3 · CPU Scheduling demo and a design decision.")
    render_deck("sector", SECTOR_SLIDES, SECTOR_DEMOS)


def render_lecture_mode():
    st.header("🎓 Lecture Mode")
    st.caption("Present one concept at a time. Instructor notes and board drawings are in the collapsed 📝 panel.")
    render_deck("lecture", SLIDES, LECTURE_DEMOS, SAY_EN, QA, links_on_first=True)


def main():
    head, langcol = st.columns([3, 1])
    with head:
        st.title("🧠 OS Exercise Lab")
        st.caption("A no-code teaching interface for OSTEP-style operating-system simulations")
    with langcol:
        st.radio("Instructor notes", ["Türkçe + EN", "English"], key="notes_lang")
    tabs = st.tabs(["🎓 Lecture Mode", "Overview", "1 Process States", "2 Threads & Data Race",
                    "3 CPU Scheduling", "4 Real-World Systems", "Instructor Notes"])

    with tabs[0]:
        render_lecture_mode()

    with tabs[1]:
        st.header("Why this lab? Cut through abstraction.")
        st.markdown("""
        This web interface turns operating-system concepts into observable scenarios.

        **OSTEP** (*Operating Systems: Three Easy Pieces*) provides the simulation scripts.
        **This Streamlit app** provides a classroom-friendly visual interface.
        """)
        col1,col2,col3 = st.columns(3)
        with col1:
            scenario_card("cpu-intro", "Process states", "READY, RUNNING, WAITING")
        with col2:
            scenario_card("threads-intro", "Thread interleavings", "lost update and data race")
        with col3:
            scenario_card("cpu-sched", "Scheduling policies", "FCFS, SJF, Round Robin")
        st.markdown("""
        <div class='big-card'><b>Teaching pattern:</b> Predict → Run → Observe → Explain</div>
        """, unsafe_allow_html=True)

    with tabs[2]:
        st.header("Scenario 1 — CPU-bound vs I/O-bound processes")
        st.markdown("**Goal:** show that processes move between `RUNNING`, `READY`, and `WAITING`, and that the CPU can run another process while one waits for I/O.")
        render_process_demo("tab_process", show_cmd_open=True)
        st.markdown("**Ask students:** When one process is waiting for I/O, what can the CPU do?")

    with tabs[3]:
        st.header("Scenario 2 — Two threads, one shared variable")
        st.markdown("**Goal:** show how interleaving creates a lost update.")
        render_thread_demo("tab_thread", backend_open=True)

    with tabs[4]:
        st.header("Scenario 3 — Same jobs, different scheduler")
        st.markdown("**Goal:** show that changing only the scheduling policy changes waiting and turnaround times.")
        render_terms(["FCFS", "SJF", "RR", "Quantum"])
        render_scheduling_demo("tab_sched")
        st.caption("The visualizer computes the classroom Gantt chart directly. OSTEP scheduler.py can be used in parallel for command-line verification.")
        st.markdown("**Ask students:** Did the jobs change, or did only the policy change?")

    with tabs[5]:
        render_sector_mode()

    with tabs[6]:
        st.header("Suggested classroom script")
        st.markdown("""
        Every live demo follows **four layers**:

        1. **Application code** — what the developer writes (user space).
        2. **OS kernel** — how the scheduler and process states react (pseudocode, not real kernel source).
        3. **Run on site** — enter the parameters and predict before running.
        4. **Observed result** — total time, CPU utilization, waiting time, final value.

        Recommended order:

        - Process states: `READY → RUNNING → WAITING` · SWITCH_ON_IO vs SWITCH_ON_END
        - Threads: `shared memory + interleaving → data race` · fix with a mutex
        - Scheduling: `same jobs + different policy → different waiting time`
        - Real-world systems: banking, robotic surgery, ticket reservation, video streaming
        """)
        st.markdown("""
        **Important explanation:** Multithreading is not the problem.
        The problem is unsynchronized access to shared state.
        """)

if __name__ == "__main__":
    main()
