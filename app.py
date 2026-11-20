from __future__ import annotations

import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import streamlit as st

from qfabric.demo import build_demo_state
from qfabric.models import EntanglementRequest
from qfabric.planner import schedule_requests
from qfabric.certificate import issue_prediction_certificate
from qfabric.benchmark import run_benchmark


st.set_page_config(
    page_title="Q-FABRIC | Quantum Command Center",
    page_icon="⚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# QUANTUM SPACE DESIGN SYSTEM
# ---------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --cyan: #54eaff;
    --blue: #438cff;
    --purple: #a78bfa;
    --pink: #e879f9;
    --background: #050816;
    --glass: rgba(15, 28, 58, .58);
    --border: rgba(104, 190, 255, .22);
    --muted: #91a8c9;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background:
        radial-gradient(ellipse at 15% 10%, rgba(32, 87, 180, .22), transparent 38%),
        radial-gradient(ellipse at 85% 15%, rgba(126, 55, 190, .17), transparent 35%),
        radial-gradient(ellipse at 50% 100%, rgba(17, 100, 155, .16), transparent 45%),
        #050816;
    color: #eaf3ff;
}

.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    opacity: .32;
    background-image:
        radial-gradient(1px 1px at 10% 20%, #fff, transparent),
        radial-gradient(1px 1px at 30% 70%, #72dcff, transparent),
        radial-gradient(2px 2px at 70% 30%, #fff, transparent),
        radial-gradient(1px 1px at 90% 80%, #a78bfa, transparent),
        radial-gradient(1px 1px at 45% 40%, #fff, transparent);
    background-size: 250px 250px;
    animation: stars 45s linear infinite;
}

@keyframes stars {
    from { background-position: 0 0; }
    to { background-position: 250px 250px; }
}

@keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-7px); }
}

@keyframes glow {
    0%, 100% { box-shadow: 0 0 15px rgba(84,234,255,.08); }
    50% { box-shadow: 0 0 28px rgba(84,234,255,.22); }
}

@keyframes pulse {
    0%, 100% { opacity: .65; }
    50% { opacity: 1; }
}

.block-container {
    max-width: 1500px;
    padding-top: 2rem;
    padding-bottom: 4rem;
    position: relative;
    z-index: 1;
}

[data-testid="stSidebar"] {
    background: rgba(7, 13, 32, .92);
    border-right: 1px solid rgba(84,234,255,.18);
}

[data-testid="stSidebar"] * {
    color: #dceaff;
}

[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(24,45,82,.72), rgba(13,23,48,.62));
    border: 1px solid rgba(84,234,255,.24);
    border-radius: 17px;
    padding: 18px 20px;
    backdrop-filter: blur(18px);
    animation: float 7s ease-in-out infinite, glow 5s ease-in-out infinite;
    transition: .3s ease;
}

[data-testid="stMetric"]:hover {
    transform: translateY(-6px) scale(1.015);
    border-color: rgba(84,234,255,.65);
}

[data-testid="stMetricLabel"] {
    color: #9bb5d7 !important;
    font-size: .85rem;
}

[data-testid="stMetricValue"] {
    color: #eafaff !important;
    font-family: 'Orbitron', sans-serif;
}

.stButton > button {
    border: 1px solid rgba(84,234,255,.42);
    border-radius: 12px;
    background: linear-gradient(110deg, rgba(22,90,145,.75), rgba(94,55,160,.72));
    color: white;
    padding: .65rem 1.1rem;
    font-weight: 600;
    transition: all .25s ease;
    box-shadow: 0 0 16px rgba(84,234,255,.08);
}

.stButton > button:hover {
    border-color: #54eaff;
    color: white;
    transform: translateY(-3px);
    box-shadow: 0 0 24px rgba(84,234,255,.28);
}

.stButton > button:focus {
    color: white;
    border-color: #54eaff;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(145deg, rgba(20,37,70,.68), rgba(10,18,40,.65));
    border: 1px solid rgba(104,190,255,.2);
    border-radius: 18px;
    backdrop-filter: blur(18px);
    transition: .3s ease;
}

div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(84,234,255,.48);
    box-shadow: 0 8px 32px rgba(37,130,220,.12);
}

h1, h2, h3 {
    color: #e8f5ff;
    letter-spacing: -.4px;
}

h1 {
    font-family: 'Orbitron', sans-serif !important;
    text-shadow: 0 0 22px rgba(84,234,255,.3);
}

h2, h3 {
    font-weight: 600;
}

p, li, label {
    color: #c0d0e8;
}

[data-testid="stDataFrame"] {
    border: 1px solid rgba(84,234,255,.2);
    border-radius: 13px;
    overflow: hidden;
}

.stTabs [data-baseweb="tab"] {
    color: #a9c4e8;
    border-radius: 10px 10px 0 0;
}

.stTabs [aria-selected="true"] {
    color: #54eaff !important;
    border-bottom-color: #54eaff !important;
}

.stSelectbox, .stTextInput, .stNumberInput {
    background: transparent;
}

hr {
    border-color: rgba(84,234,255,.15);
}

.quantum-hero {
    position: relative;
    overflow: hidden;
    padding: 35px 36px;
    border-radius: 23px;
    border: 1px solid rgba(84,234,255,.3);
    background:
      radial-gradient(circle at 85% 20%, rgba(151,83,255,.22), transparent 35%),
      linear-gradient(115deg, rgba(12,36,76,.92), rgba(21,20,60,.84));
    box-shadow: 0 0 45px rgba(50,140,255,.12), inset 0 0 35px rgba(84,234,255,.035);
    margin-bottom: 24px;
}

.quantum-hero::after {
    content: "Q";
    position: absolute;
    right: 5%;
    top: -75px;
    font-family: 'Orbitron';
    font-size: 250px;
    color: rgba(84,234,255,.045);
    pointer-events: none;
}

.hero-kicker {
    color: #54eaff;
    font-family: 'Orbitron';
    font-size: 11px;
    letter-spacing: 4px;
    margin-bottom: 12px;
}

.hero-title {
    color: white;
    font-family: 'Orbitron';
    font-size: clamp(27px, 4vw, 48px);
    font-weight: 800;
    letter-spacing: 2px;
}

.hero-subtitle {
    color: #b9cce8;
    font-size: 15px;
    max-width: 760px;
    line-height: 1.8;
}

.status-pill {
    display: inline-block;
    border: 1px solid rgba(84,234,255,.35);
    border-radius: 30px;
    padding: 7px 13px;
    color: #70efff;
    background: rgba(40,170,220,.09);
    font-size: 11px;
    letter-spacing: 1px;
    margin-top: 14px;
}

.section-label {
    color: #54eaff;
    font-family: 'Orbitron';
    letter-spacing: 2px;
    font-size: 11px;
    margin-bottom: 8px;
}

.glass-card {
    padding: 20px;
    border: 1px solid rgba(84,234,255,.22);
    border-radius: 17px;
    background: linear-gradient(140deg, rgba(24,47,85,.68), rgba(12,20,45,.7));
    backdrop-filter: blur(18px);
    min-height: 125px;
    transition: .3s ease;
    animation: float 8s ease-in-out infinite;
}

.glass-card:hover {
    transform: translateY(-7px);
    border-color: rgba(84,234,255,.6);
    box-shadow: 0 10px 30px rgba(44,157,255,.15);
}

.card-icon {
    font-size: 24px;
    margin-bottom: 10px;
}

.card-title {
    color: #f0f7ff;
    font-weight: 700;
    font-size: 15px;
    margin-bottom: 7px;
}

.card-description {
    color: #9eb5d4;
    font-size: 12px;
    line-height: 1.65;
}

.small-muted {
    color: #91a8c9;
    font-size: 12px;
}

.neon-line {
    height: 1px;
    background: linear-gradient(90deg, transparent, #54eaff, #a78bfa, transparent);
    margin: 22px 0;
    opacity: .6;
}

.orbit-status {
    color: #54eaff;
    font-family: 'Orbitron';
    font-size: 10px;
    letter-spacing: 2px;
    animation: pulse 2.5s infinite;
}


/* HOLOGRAPHIC QUANTUM INTERFACE */

@keyframes holoSweep {
    0% { transform: translateX(-120%) rotate(18deg); opacity: 0; }
    20% { opacity: .45; }
    65% { opacity: .2; }
    100% { transform: translateX(120%) rotate(18deg); opacity: 0; }
}

@keyframes orbitPulse {
    0%, 100% { box-shadow: 0 0 12px rgba(84,234,255,.12); }
    50% { box-shadow: 0 0 30px rgba(167,139,250,.3); }
}

@keyframes scanMove {
    from { background-position: 0 -100%; }
    to { background-position: 0 200%; }
}

.glass-card {
    position: relative;
    isolation: isolate;
    overflow: hidden;
    transform-style: preserve-3d;
    will-change: transform;
    animation: float 8s ease-in-out infinite, orbitPulse 6s ease-in-out infinite;
}

.glass-card::before {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    padding: 1px;
    background: linear-gradient(
        125deg,
        rgba(84,234,255,.65),
        transparent 35%,
        rgba(167,139,250,.48) 70%,
        transparent
    );
    -webkit-mask: linear-gradient(#fff 0 0) content-box,
                  linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    pointer-events: none;
    z-index: 2;
}

.glass-card::after {
    content: "";
    position: absolute;
    top: -30%;
    bottom: -30%;
    left: -70%;
    width: 45%;
    background: linear-gradient(
        90deg,
        transparent,
        rgba(84,234,255,.13),
        rgba(255,255,255,.2),
        transparent
    );
    transform: rotate(18deg);
    pointer-events: none;
    animation: holoSweep 8s ease-in-out infinite;
}

.glass-card:hover {
    transform: translateY(-9px) perspective(900px) rotateX(2deg);
    border-color: rgba(84,234,255,.8);
    box-shadow:
        0 14px 38px rgba(44,157,255,.2),
        0 0 24px rgba(84,234,255,.13),
        inset 0 0 24px rgba(167,139,250,.08);
}

.quantum-hero {
    animation: orbitPulse 7s ease-in-out infinite;
}

.quantum-hero::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: linear-gradient(
        180deg,
        transparent 0%,
        rgba(84,234,255,.045) 48%,
        transparent 52%
    );
    background-size: 100% 200%;
    animation: scanMove 9s linear infinite;
}

.orbit-status {
    text-shadow: 0 0 12px rgba(84,234,255,.7);
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: .01ms !important;
        animation-iteration-count: 1 !important;
        scroll-behavior: auto !important;
        transition-duration: .01ms !important;
    }
}

footer {visibility: hidden;}
#MainMenu {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# APPLICATION DATA
# ---------------------------------------------------------

def make_requests():
    return [
        EntanglementRequest("R1", "user-1", "A", "D", 0.80, 5.0, 1, 2),
        EntanglementRequest("R2", "user-2", "A", "D", 0.82, 6.0, 1, 1),
        EntanglementRequest("R3", "user-1", "B", "C", 0.85, 3.0, 1, 0),
    ]


def serializable(value):
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return value


def hero(title, subtitle, kicker="QUANTUM NETWORK INTELLIGENCE"):
    st.markdown(f"""
    <div class="quantum-hero">
      <div class="hero-kicker">{kicker}</div>
      <div class="hero-title">{title}</div>
      <div class="hero-subtitle">{subtitle}</div>
      <span class="status-pill">Q-FABRIC v0.2.1 &nbsp; | &nbsp; RESEARCH PROTOTYPE</span>
    </div>
    """, unsafe_allow_html=True)


def section(label, title):
    st.markdown(
        f'<div class="section-label">{label}</div><h2>{title}</h2>',
        unsafe_allow_html=True,
    )


def info_card(icon, title, description):
    st.markdown(f"""
    <div class="glass-card">
      <div class="card-icon">{icon}</div>
      <div class="card-title">{title}</div>
      <div class="card-description">{description}</div>
    </div>
    """, unsafe_allow_html=True)


def network_graph():
    st.graphviz_chart("""
    graph QFABRIC {
      graph [bgcolor="transparent", rankdir=LR, nodesep=0.9, ranksep=1.2];
      node [shape=circle, style="filled", fillcolor="#102d55",
            color="#54eaff", penwidth=2, fontcolor="white",
            fontname="Arial", fontsize=20, width=0.85, height=0.85,
            fixedsize=true];
      edge [color="#54eaff", penwidth=2, fontcolor="#d7eaff",
            fontname="Arial", fontsize=11];
      A -- B [label="0.94"];
      B -- D [label="0.94"];
      A -- C [label="0.97"];
      C -- D [label="0.97"];
      B -- C [label="0.96"];
    }
    """, width="stretch")


# ---------------------------------------------------------
# SIDEBAR NAVIGATION
# ---------------------------------------------------------

st.sidebar.markdown("""
<div style="text-align:center;padding:12px 0 22px">
  <div style="font-family:Orbitron;font-size:27px;color:#54eaff;
       text-shadow:0 0 18px #268dff">Q-FABRIC</div>
  <div style="font-size:10px;letter-spacing:3px;color:#91a8c9">
       QUANTUM COMMAND CENTER</div>
</div>
""", unsafe_allow_html=True)

pages = [
    "Mission Control",
    "Network Topology",
    "Entanglement Planner",
    "Benchmark Laboratory",
    "SeQUeNCe Simulations",
    "Prediction Certificates",
    "System Diagnostics",
    "About Q-FABRIC",
]

if "requested_page" in st.session_state:
    requested = st.session_state.pop("requested_page")
    if requested in pages:
        st.session_state["qfabric_navigation"] = requested

page = st.sidebar.radio(
    "NAVIGATION",
    pages,
    key="qfabric_navigation",
    label_visibility="collapsed",
)

st.sidebar.markdown('<div class="neon-line"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="orbit-status">● SYSTEM INTERFACE READY</div>',
                    unsafe_allow_html=True)
st.sidebar.caption("Version 0.2.1")
st.sidebar.caption("Quantum network orchestration research prototype")
st.sidebar.caption("Predictions are not physical verification.")


# ---------------------------------------------------------
# MISSION CONTROL
# ---------------------------------------------------------

if page == "Mission Control":
    hero(
        "QUANTUM COMMAND",
        "A research platform for planning, scheduling and analyzing entanglement distribution across quantum networks.",
    )

    state = build_demo_state()
    requests = make_requests()
    allocations = schedule_requests(requests, state)

    accepted = sum(a.accepted for a in allocations)
    rejected = len(allocations) - accepted
    avg_fidelity = (
        sum(a.predicted_fidelity for a in allocations if a.accepted) / accepted
        if accepted else 0
    )

    st.markdown('<div class="section-label">LIVE PLANNER SNAPSHOT</div>',
                unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("NETWORK NODES", len(state.nodes))
    c2.metric("QUANTUM LINKS", len(state.links))
    c3.metric("ACCEPTED REQUESTS", f"{accepted}/{len(allocations)}")
    c4.metric("MEAN PREDICTED FIDELITY", f"{avg_fidelity:.4f}")

    st.markdown('<div class="neon-line"></div>', unsafe_allow_html=True)
    section("NETWORK VISUALIZATION", "Entanglement Network")

    left, right = st.columns([1.65, 1])

    with left:
        network_graph()

    with right:
        info_card("◈", "Network architecture",
                  "Four quantum nodes connected through five modeled quantum links.")
        st.write("")
        info_card("⌁", "Planning engine",
                  "Evaluates paths, fidelity, memory capacity and request deadlines.")
        st.write("")
        info_card("◇", "Prediction status",
                  "Planner outputs are estimates. They are not hardware measurements.")

    section("RESOURCE ALLOCATION", "Current Planning Results")
    st.dataframe(
        pd.DataFrame([asdict(a) for a in allocations]),
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="neon-line"></div>', unsafe_allow_html=True)
    section("QUICK ACCESS", "Explore the platform")

    quick = st.columns(4)
    destinations = [
        ("Network Topology", "Explore the modeled quantum network."),
        ("Entanglement Planner", "Run request allocation."),
        ("Benchmark Laboratory", "Compare scheduling policies."),
        ("About Q-FABRIC", "Read the technical documentation."),
    ]

    for col, (destination, description) in zip(quick, destinations):
        with col:
            info_card("✧", destination, description)
            if st.button("OPEN MODULE", key=f"quick_{destination}",
                         width="stretch"):
                st.session_state["requested_page"] = destination
                st.rerun()


# ---------------------------------------------------------
# NETWORK TOPOLOGY
# ---------------------------------------------------------

elif page == "Network Topology":
    hero(
        "NETWORK TOPOLOGY",
        "Inspect the nodes, links and modeled physical parameters used by the Q-FABRIC planning engine.",
        "QUANTUM INFRASTRUCTURE",
    )

    state = build_demo_state()
    section("TOPOLOGY MAP", "Four-node quantum network")
    network_graph()

    st.markdown('<div class="neon-line"></div>', unsafe_allow_html=True)
    section("NODE INVENTORY", "Quantum Nodes")

    st.dataframe(
        [{
            "Node ID": n.node_id,
            "Memory slots": n.memory_slots,
        } for n in state.nodes.values()],
        width="stretch",
        hide_index=True,
    )

    section("LINK INVENTORY", "Quantum Channel Parameters")
    st.dataframe(
        [{
            "Source": l.source,
            "Target": l.target,
            "Fidelity": l.fidelity,
            "Generation probability": l.generation_probability,
            "Attempt duration": l.attempt_duration,
            "Pair coherence time": l.pair_coherence_time,
            "Memory slots": l.memory_slots,
            "Classical latency": l.classical_latency,
        } for l in state.links],
        width="stretch",
        hide_index=True,
    )

    with st.expander("How to interpret these parameters"):
        st.markdown("""
        - **Fidelity** describes the modeled quality of an entangled pair.
        - **Generation probability** represents the probability assigned to successful pair generation.
        - **Attempt duration** represents the modeled time cost of an elementary-link attempt.
        - **Pair coherence time** represents the characteristic time used in memory-decoherence estimates.
        - **Memory slots** represent the modeled storage capacity.
        - **Classical latency** represents the communication delay used by the planner.

        These are configured simulation parameters, not live hardware telemetry.
        """)


# ---------------------------------------------------------
# ENTANGLEMENT PLANNER
# ---------------------------------------------------------

elif page == "Entanglement Planner":
    hero(
        "ENTANGLEMENT PLANNER",
        "Submit entanglement demands and evaluate candidate allocations against fidelity, memory and deadline constraints.",
        "SCHEDULING ENGINE",
    )

    state = build_demo_state()
    requests = make_requests()

    section("INPUT WORKLOAD", "Demo Entanglement Requests")
    st.dataframe(
        [{
            "Request": r.request_id,
            "User": r.user_id,
            "Source": r.source,
            "Target": r.target,
            "Required fidelity": r.required_fidelity,
            "Deadline": r.deadline,
            "Priority": r.priority,
        } for r in requests],
        width="stretch",
        hide_index=True,
    )

    st.markdown("""
    <div class="small-muted">
    The current interface runs the project's configured demonstration workload.
    Request values are taken from the application source.
    </div>
    """, unsafe_allow_html=True)

    if st.button("EXECUTE Q-FABRIC PLANNER", type="primary"):
        allocations = schedule_requests(requests, state)
        request_map = {r.request_id: r for r in requests}

        records = []
        certificates = []

        for allocation in allocations:
            records.append(asdict(allocation))
            cert = issue_prediction_certificate(
                request_map[allocation.request_id], allocation
            )
            certificates.append(asdict(cert))

        st.session_state["allocations"] = records
        st.session_state["certificates"] = certificates

    if "allocations" in st.session_state:
        results = st.session_state["allocations"]
        accepted_results = [a for a in results if a["accepted"]]

        a, b, c = st.columns(3)
        a.metric("Requests evaluated", len(results))
        b.metric("Accepted", len(accepted_results))
        c.metric("Rejected", len(results) - len(accepted_results))

        section("PLANNER OUTPUT", "Allocation Decisions")
        st.dataframe(pd.DataFrame(results), width="stretch",
                     hide_index=True)

        for item in results:
            with st.expander(f"Request {item['request_id']} — "
                             f"{'Accepted' if item['accepted'] else 'Rejected'}"):
                st.json(item)


# ---------------------------------------------------------
# BENCHMARK LABORATORY
# ---------------------------------------------------------

elif page == "Benchmark Laboratory":
    hero(
        "BENCHMARK LABORATORY",
        "Compare Q-FABRIC scheduling with alternative request-ordering policies under the same demonstration workload.",
        "PERFORMANCE EVALUATION",
    )

    section("EXPERIMENT DESIGN", "Scheduling Policy Comparison")

    st.markdown("""
    The benchmark currently evaluates four policies.

    - **Q-FABRIC** uses the project's scheduling algorithm.
    - **EDF** orders requests by earliest deadline.
    - **Priority First** orders requests by priority before deadline.
    - **Shortest Slack** orders requests by deadline minus arrival time.

    Each policy receives a cloned network state so reservations from one policy
    do not affect another policy's result.
    """)

    if st.button("RUN BENCHMARK EXPERIMENT", type="primary"):
        result = run_benchmark(make_requests(), build_demo_state())
        st.session_state["benchmark"] = result

    if "benchmark" in st.session_state:
        policies = st.session_state["benchmark"]["policies"]
        df = pd.DataFrame(policies).T

        section("EXPERIMENT RESULTS", "Policy Metrics")
        st.dataframe(df, width="stretch")

        x, y = st.columns(2)
        with x:
            st.subheader("Acceptance Rate")
            st.bar_chart(df["acceptance_rate"])
        with y:
            st.subheader("Mean Predicted Fidelity")
            st.bar_chart(df["mean_predicted_fidelity"])

        st.subheader("Mean Completion Time")
        st.bar_chart(df["mean_completion_time"])

        st.warning(
            "The current workload contains only three requests. "
            "It does not establish performance superiority or statistical significance."
        )

        with st.expander("Benchmark interpretation"):
            st.markdown("""
            Acceptance rate measures the fraction of requests accepted by a policy.
            Mean predicted fidelity averages the predicted fidelity of accepted allocations.
            Mean completion time averages the estimated completion time of accepted allocations.

            Results depend on the configured network and workload. A larger,
            varied workload is required for a meaningful comparative evaluation.
            """)


# ---------------------------------------------------------
# SEQUENCE SIMULATIONS
# ---------------------------------------------------------

elif page == "SeQUeNCe Simulations":
    hero(
        "SEQUENCЕ SIMULATION LAB",
        "Run the available integration smoke tests using the SeQUeNCe quantum network simulator.",
        "SIMULATION ENVIRONMENT",
    )

    st.metric("Simulator integration target", "SeQUeNCe 1.3.1")

    experiments = [
        ("Elementary Entanglement Link",
         "run_elementary_link_smoke_test", "elementary"),
        ("Three-node Entanglement Swapping",
         "run_three_node_swapping_smoke_test", "swapping"),
        ("BBPSSW Purification",
         "run_bbpssw_purification_smoke_test", "purification"),
    ]

    section("AVAILABLE EXPERIMENTS", "Integration Tests")

    for label, function_name, key in experiments:
        with st.container(border=True):
            st.subheader(label)

            descriptions = {
                "elementary": "Checks the elementary heralded entanglement-link smoke test.",
                "swapping": "Checks entanglement swapping across a three-node network.",
                "purification": "Checks BBPSSW purification and the retained pair.",
            }

            st.caption(descriptions[key])

            if st.button(f"RUN {label.upper()}", key=f"run_{key}"):
                try:
                    from qfabric import sequence_adapter
                    function = getattr(sequence_adapter, function_name)
                    result = function()
                    st.session_state[f"result_{key}"] = serializable(result)
                    st.session_state[f"error_{key}"] = None
                except Exception as exc:
                    st.session_state[f"error_{key}"] = (
                        f"{type(exc).__name__}: {exc}"
                    )

            error_key = f"error_{key}"
            result_key = f"result_{key}"

            if st.session_state.get(error_key):
                st.error(st.session_state[error_key])

            if result_key in st.session_state:
                st.success("Experiment returned a result.")
                st.json(st.session_state[result_key])

    st.info(
        "These are simulator integration experiments. They do not demonstrate "
        "operation on physical quantum hardware."
    )


# ---------------------------------------------------------
# CERTIFICATES
# ---------------------------------------------------------

elif page == "Prediction Certificates":
    hero(
        "PREDICTION CERTIFICATES",
        "Inspect the structured evidence generated for planner allocation decisions.",
        "ALLOCATION EVIDENCE",
    )

    section("CERTIFICATE SYSTEM", "SHA256 Evidence Records")

    if "certificates" not in st.session_state:
        st.info("Run the Entanglement Planner first to generate certificates.")
    else:
        for cert in st.session_state["certificates"]:
            evidence = cert.get("evidence", {})
            request_id = evidence.get("request_id", "Unknown")

            with st.container(border=True):
                st.subheader(f"Certificate — {request_id}")
                st.json(cert)

                digest = cert.get("sha256")
                if digest:
                    st.code(digest, language="text")

    st.markdown("""
    A prediction certificate records planner evidence and a SHA256 digest.
    The digest supports integrity checking of the recorded evidence.

    It does not prove that an allocation was physically executed or verified.
    """)


# ---------------------------------------------------------
# SYSTEM DIAGNOSTICS
# ---------------------------------------------------------

elif page == "System Diagnostics":
    hero(
        "SYSTEM DIAGNOSTICS",
        "Execute the automated project test suite and inspect the test process output.",
        "VALIDATION CENTER",
    )

    section("AUTOMATED VALIDATION", "Project Test Suite")

    if st.button("EXECUTE PYTEST", type="primary"):
        with st.spinner("Executing project tests..."):
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).resolve().parent,
            )

        st.session_state["test_output"] = (
            result.returncode,
            result.stdout,
            result.stderr,
        )

    if "test_output" in st.session_state:
        code, stdout, stderr = st.session_state["test_output"]

        if code == 0:
            st.success("All executed tests passed.")
        else:
            st.error("The test suite reported failures.")

        st.code(stdout or stderr)

    st.markdown('<div class="neon-line"></div>', unsafe_allow_html=True)
    section("ENVIRONMENT", "Runtime Information")

    e1, e2 = st.columns(2)
    e1.metric("Python version", sys.version.split()[0])
    e2.metric("Project version", "0.2.1")

    st.caption(f"Project directory: {Path(__file__).resolve().parent}")


# ---------------------------------------------------------
# COMPLETE PROJECT DOCUMENTATION
# ---------------------------------------------------------

elif page == "About Q-FABRIC":
    hero(
        "ABOUT Q-FABRIC",
        "A research prototype for deadline- and memory-aware orchestration of entanglement distribution in quantum networks.",
        "TECHNICAL DOCUMENTATION",
    )

    st.markdown("""
    ## 1. Project Overview

    Q-FABRIC is a software research prototype designed to coordinate
    entanglement-distribution requests across a modeled quantum network.

    Quantum networks use entanglement as a resource for distributed quantum
    communication and future quantum-network applications. Creating and
    maintaining entangled pairs requires coordination across network links,
    quantum memories and classical communication channels.

    Q-FABRIC addresses the orchestration problem. It evaluates network paths,
    estimates whether requests satisfy their requirements and schedules
    allocations while accounting for resource constraints.

    The project combines a planning engine, quantum-network models,
    approximate physical calculations, simulator integration and
    structured prediction certificates.

    ---

    ## 2. The Problem

    A quantum-network request may specify:

    - A source node.
    - A destination node.
    - A minimum fidelity requirement.
    - A deadline.
    - A priority.
    - An arrival time.

    A path that connects two endpoints is not automatically a suitable path.

    The network may have limited memory capacity. Entanglement generation
    may fail probabilistically. Stored quantum states may lose fidelity
    while waiting. Multi-hop communication may require entanglement swapping.
    Some requests may require purification to reach a target fidelity.

    The planner must therefore evaluate more than connectivity.

    ---

    ## 3. Project Objectives

    1. Model quantum nodes, links and entanglement requests.
    2. Enumerate candidate paths between source and destination.
    3. Estimate path feasibility using fidelity and resource constraints.
    4. Account for memory availability and reservation.
    5. Schedule requests under deadline and priority constraints.
    6. Estimate purification requirements and completion time.
    7. Integrate selected workflows with SeQUeNCe.
    8. Generate structured prediction certificates.
    9. Compare scheduling policies through repeatable benchmark workloads.

    ---

    ## 4. System Architecture

    **Network Model**

    Represents the network as nodes and quantum links. Nodes expose modeled
    memory capacity. Links contain parameters such as fidelity, generation
    probability, attempt duration, coherence time and classical latency.

    **Path Enumeration**

    Searches for candidate routes between requested endpoints. The planner
    evaluates available paths rather than assuming that the shortest route
    is always the best route.

    **Path Estimation**

    Estimates whether a candidate path satisfies the request's requirements.
    It evaluates predicted fidelity, expected resource consumption,
    completion time and purification requirements.

    **Scheduling Engine**

    Processes a collection of entanglement requests and selects feasible
    allocations. It reserves modeled resources as allocations are made.

    **Physics Module**

    Provides scoped calculations for Werner-state memory decay, pair
    coherence, entanglement swapping and BBPSSW purification.

    **Simulator Adapter**

    Connects selected experiments to SeQUeNCe 1.3.1. The adapter keeps
    simulator imports optional so the core planner can run independently.

    **Certificate Module**

    Produces structured allocation evidence and a SHA256 digest. Its status
    distinguishes predicted feasibility from physical verification.

    ---

    ## 5. Quantum Network Model

    The current demonstration network contains four nodes.

    | Node | Modeled memory slots |
    |---|---:|
    | A | 8 |
    | B | 8 |
    | C | 8 |
    | D | 8 |

    Five links connect these nodes.

    | Link | Fidelity | Generation probability |
    |---|---:|---:|
    | A-B | 0.94 | 0.90 |
    | B-D | 0.94 | 0.90 |
    | A-C | 0.97 | 0.75 |
    | C-D | 0.97 | 0.75 |
    | B-C | 0.96 | 0.85 |

    These values form the configured demonstration scenario. They are not
    measurements from a deployed quantum network.

    ---

    ## 6. Entanglement Planning

    The planner receives a request and a network state.

    It enumerates candidate paths and estimates each path. Paths that fail
    the configured requirements are rejected with reasons. Feasible paths
    are evaluated using the planner's selection criteria.

    An accepted allocation includes the selected route, predicted fidelity,
    estimated completion time and purification-round information.

    The planner then reserves the modeled resources for subsequent requests.

    This is a heuristic scheduling approach. The current implementation
    does not claim a globally optimal allocation or a formal fairness guarantee.

    ---

    ## 7. Fidelity and Quantum Physics

    Fidelity is used as a measure of how closely a modeled quantum state
    matches a target state.

    Quantum memories are not assumed to preserve their states indefinitely.
    The physics module includes Werner-state fidelity decay during waiting.

    The project also includes calculations related to:

    - Pair coherence.
    - Entanglement swapping.
    - BBPSSW purification.

    These calculations use explicit model assumptions. Idealized gates,
    measurements and state models limit how directly their outputs can be
    transferred to a physical device.

    ---

    ## 8. Entanglement Swapping

    Entanglement swapping allows two elementary entangled links to be
    connected through an intermediate node.

    In a three-node arrangement A-B-C, the intermediate node performs a
    Bell-state measurement. A successful operation can establish an
    end-to-end entangled pair between A and C.

    Q-FABRIC includes a SeQUeNCe integration smoke test for a three-node
    swapping workflow using the simulator's router, BSM node and protocol
    components.

    The test is a simulator integration check, not hardware validation.

    ---

    ## 9. BBPSSW Purification

    BBPSSW is a two-pair entanglement purification protocol.

    It uses two noisy entangled pairs and local operations with classical
    communication to probabilistically produce a pair with higher fidelity.

    The project includes a SeQUeNCe purification smoke test. Its reported
    result is based on the simulator execution and its configured conditions.

    Purification consumes additional pairs and time. A planner must therefore
    consider its resource cost alongside the fidelity improvement.

    ---

    ## 10. SeQUeNCe Integration

    The optional simulator integration targets SeQUeNCe version 1.3.1.

    The project contains smoke tests for:

    - Elementary entanglement generation.
    - Three-node entanglement swapping.
    - BBPSSW purification.

    The integration is intended to check selected protocol workflows and
    provide simulator-derived evidence for those workflows.

    It does not establish physical-device compatibility, deployment readiness
    or performance on a real quantum network.

    ---

    ## 11. Benchmark Methodology

    The benchmark module compares four scheduling policies.

    | Policy | Ordering principle |
    |---|---|
    | Q-FABRIC | Project scheduling algorithm |
    | EDF | Earliest deadline first |
    | Priority First | Priority followed by deadline |
    | Shortest Slack | Deadline minus arrival time |

    Each policy receives a cloned network state.

    Reported metrics include:

    - Total requests.
    - Accepted requests.
    - Rejected requests.
    - Acceptance rate.
    - Mean predicted fidelity.
    - Mean completion time.
    - Rejection reasons.

    The current demonstration workload contains three requests. It is useful
    as a functional check but is not sufficient to establish statistical
    significance or performance superiority.

    ---

    ## 12. Prediction Certificates

    Q-FABRIC generates a certificate for an allocation.

    The certificate records structured evidence and a SHA256 digest.

    Its purpose is to provide a stable integrity reference for the recorded
    prediction evidence.

    A certificate does not mean that the allocation has been executed.
    It does not prove that an entangled pair exists in physical hardware.

    The project explicitly uses the status:

    `PREDICTED_FEASIBLE_NOT_PHYSICALLY_VERIFIED`

    ---

    ## 13. Software Structure

    | File | Responsibility |
    |---|---|
    | models.py | Quantum nodes, links, requests and network state |
    | planner.py | Path enumeration, path estimation and scheduling |
    | physics.py | Quantum-state and fidelity calculations |
    | stochastic.py | Stochastic modeling utilities |
    | sequence_adapter.py | Optional SeQUeNCe integration |
    | sequence_smoke.py | Simulator smoke-test entry point |
    | benchmark.py | Scheduling policy benchmark |
    | certificate.py | Prediction certificate generation |
    | demo.py | Demonstration network and workload |
    | dashboard | Interactive research interface |

    ---

    ## 14. Current Capabilities

    - Quantum network data models.
    - Multi-path enumeration.
    - Fidelity-aware path evaluation.
    - Memory-aware resource allocation.
    - Deadline-aware request scheduling.
    - Purification-aware planning estimates.
    - Werner-state physics calculations.
    - Entanglement swapping calculations.
    - BBPSSW purification calculations.
    - SeQUeNCe integration smoke tests.
    - Stochastic modeling utilities.
    - Scheduling policy benchmarks.
    - SHA256 prediction certificates.
    - Interactive Streamlit dashboard.

    ---

    ## 15. Research Limitations

    Q-FABRIC is a research prototype.

    Its planner uses approximations for timing and physical processes.
    The current benchmark workload is small. No formal global optimality
    or fairness guarantee is claimed.

    Simulator results are not physical hardware measurements. The current
    integration tests cover selected workflows rather than a complete
    deployed quantum-network control plane.

    These limitations define the scope of the current implementation and
    should be considered when interpreting its outputs.

    ---

    ## 16. Future Research Directions

    1. Expand benchmark workloads across network sizes and traffic patterns.
    2. Evaluate larger topologies and heterogeneous memory capacities.
    3. Investigate fairness-aware and multi-objective scheduling.
    4. Improve stochastic treatment of generation and memory behavior.
    5. Integrate more complete time-dependent simulator workflows.
    6. Evaluate robustness under link failures and changing network conditions.
    7. Compare planner predictions against simulator traces.
    8. Investigate reproducible experiment reporting and certificate verification.

    ---

    ## 17. Reproducibility

    The project provides a Python package, test suite, demonstration scenario,
    benchmark module and optional SeQUeNCe integration.

    The core planner can run without the optional simulator dependency.
    The simulator smoke tests require the SeQUeNCe installation.

    The project test suite should be executed before preparing a release.

    ---

    ## 18. Research Positioning

    Q-FABRIC focuses on the orchestration layer between quantum-network
    resources and entanglement-service requests.

    Its contribution in the current implementation is a working prototype
    that combines path evaluation, modeled resource reservation, request
    scheduling, scoped physics calculations and selected simulator
    integration workflows.

    Claims about novelty, superiority or deployment performance require
    further literature comparison and experimental evaluation.
    """)

    st.markdown('<div class="neon-line"></div>', unsafe_allow_html=True)
    st.success("Q-FABRIC v0.2.1 — Technical documentation")


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.markdown('<div class="neon-line"></div>', unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;padding:12px;color:#7892b8;font-size:11px;
letter-spacing:2px">
Q-FABRIC &nbsp; | &nbsp; QUANTUM NETWORK ORCHESTRATION
<br><br>
RESEARCH PROTOTYPE · VERSION 0.2.1
</div>
""", unsafe_allow_html=True)
