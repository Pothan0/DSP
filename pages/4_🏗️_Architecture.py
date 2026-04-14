import streamlit as st
import os
import requests

API_URL = os.environ.get("API_URL", "http://localhost:8000")
GATEWAY_URL = "http://localhost:7070"

st.set_page_config(page_title="Architecture | NovaSentinel", page_icon="🏗️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    .stApp { background: radial-gradient(ellipse at 15% 50%, #0b0f19, #05070a); color: #e1e2e7; font-family: 'Inter', sans-serif; }
    header { visibility: hidden; }
    .glass-card {
        background: linear-gradient(145deg, rgba(25,28,31,0.7), rgba(12,14,18,0.9));
        backdrop-filter: blur(24px); border: 1px solid rgba(255,255,255,0.03);
        border-radius: 16px; padding: 28px; margin-bottom: 20px;
        position: relative; overflow: hidden;
    }
    .glass-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0,240,255,0.15), transparent);
    }
    h1 { font-weight: 800; letter-spacing: -1.5px; color: #ffffff; }
    h3 { font-weight: 700; color: #e1e2e7; font-size: 1.1rem; }
    .layer-badge {
        display: inline-block; padding: 6px 14px; border-radius: 6px; font-size: 0.7rem;
        font-weight: 700; letter-spacing: 1px; text-transform: uppercase; margin-right: 8px;
    }
    .arch-flow {
        display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
        padding: 24px 0;
    }
    .flow-node {
        padding: 16px 24px; background: rgba(17,20,23,0.8);
        border: 1px solid rgba(0,240,255,0.1); border-radius: 10px;
        text-align: center; min-width: 140px;
    }
    .flow-node-title { font-size: 0.75rem; font-weight: 700; color: #00f0ff; text-transform: uppercase; letter-spacing: 1px; }
    .flow-node-desc { font-size: 0.7rem; color: #8b9bb4; margin-top: 4px; }
    .flow-arrow { color: #3b494b; font-size: 1.5rem; }
    
    [data-testid="stMetricValue"] { color: #ffffff !important; font-weight: 800; font-size: 2rem !important; }
    [data-testid="stMetricLabel"] { color: #8b9bb4 !important; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; font-size: 0.6rem !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='font-size:2rem; margin-bottom:8px;'>🏗️ System Architecture</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#8b9bb4; font-size:0.8rem; margin-bottom:32px;'>NovaSentinel Gateway — Enterprise security architecture overview</p>", unsafe_allow_html=True)

# ─── Status ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3)
def get_statuses():
    api_ok = False
    gw_ok = False
    try:
        r = requests.get(f"{API_URL}/health", timeout=2)
        api_ok = r.status_code == 200
    except: pass
    try:
        r = requests.get(f"{GATEWAY_URL}/health", timeout=2)
        gw_ok = r.status_code == 200
    except: pass
    return api_ok, gw_ok

api_ok, gw_ok = get_statuses()

s1, s2, s3, s4 = st.columns(4)
with s1:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.metric("API Engine", "Online" if api_ok else "Offline")
    st.markdown("</div>", unsafe_allow_html=True)
with s2:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.metric("MCP Gateway", "Online" if gw_ok else "Offline")
    st.markdown("</div>", unsafe_allow_html=True)
with s3:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.metric("Security Layers", "4")
    st.markdown("</div>", unsafe_allow_html=True)
with s4:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.metric("Protection Mode", "Zero-Trust")
    st.markdown("</div>", unsafe_allow_html=True)

# ─── Data Flow ───────────────────────────────────────────────────────────────
st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
st.markdown("<h3>📡 Security Pipeline Flow</h3>", unsafe_allow_html=True)
st.markdown("""
<div class='arch-flow'>
    <div class='flow-node'>
        <div class='flow-node-title'>🤖 AI Agent</div>
        <div class='flow-node-desc'>LangGraph ReAct</div>
    </div>
    <div class='flow-arrow'>→</div>
    <div class='flow-node' style='border-color: rgba(255,50,50,0.3);'>
        <div class='flow-node-title' style='color:#ff3232;'>🧠 ML Classifier</div>
        <div class='flow-node-desc'>DeBERTa v3 + Regex</div>
    </div>
    <div class='flow-arrow'>→</div>
    <div class='flow-node' style='border-color: rgba(112,0,255,0.3);'>
        <div class='flow-node-title' style='color:#a855f7;'>🔐 PII Scrubber</div>
        <div class='flow-node-desc'>Presidio Engine</div>
    </div>
    <div class='flow-arrow'>→</div>
    <div class='flow-node' style='border-color: rgba(255,165,0,0.3);'>
        <div class='flow-node-title' style='color:#ffaa00;'>🛡️ RBAC Gate</div>
        <div class='flow-node-desc'>Context Injection</div>
    </div>
    <div class='flow-arrow'>→</div>
    <div class='flow-node' style='border-color: rgba(0,255,128,0.3);'>
        <div class='flow-node-title' style='color:#00ff80;'>⛓️ Audit Ledger</div>
        <div class='flow-node-desc'>SHA-256 Chain</div>
    </div>
    <div class='flow-arrow'>→</div>
    <div class='flow-node'>
        <div class='flow-node-title'>🏥 Tool Server</div>
        <div class='flow-node-desc'>Patient DB / API</div>
    </div>
</div>
""", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ─── Protection Layers Detail ───────────────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("""
    <span class='layer-badge' style='background:rgba(0,240,255,0.1); color:#00f0ff;'>Layer 1</span>
    <h3 style='margin-top:12px;'>PII & PHI Encryption Shield</h3>
    """, unsafe_allow_html=True)
    st.markdown("""
    - **Engine:** Microsoft Presidio Analyzer + Anonymizer
    - **Input Scrubbing:** PHI → cryptographic vault tokens before LLM
    - **Output Scrubbing:** Prevents LLM from leaking PHI to unauthorized users
    - **Custom Entities:** `INTERNAL_RECORD_ID` (REC-XXXX format)
    - **Reversible:** Vault-based tokenization allows authorized unmasking
    """)
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("""
    <span class='layer-badge' style='background:rgba(255,165,0,0.1); color:#ffaa00;'>Layer 3</span>
    <h3 style='margin-top:12px;'>Context-Aware RBAC (Anti-IDOR)</h3>
    """, unsafe_allow_html=True)
    st.markdown("""
    - **Mechanism:** Dynamic user context injection into tool calls
    - **Protection:** Prevents cross-patient data access
    - **Role Support:** Patient (restricted) and Admin (full access)
    - **Enforcement:** Tool-level RBAC on `fetch_patient_data` and `fetch_prescriptions`
    """)
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("""
    <span class='layer-badge' style='background:rgba(255,50,50,0.1); color:#ff3232;'>Layer 2</span>
    <h3 style='margin-top:12px;'>Semantic Threat Guardian</h3>
    """, unsafe_allow_html=True)
    st.markdown("""
    - **ML Model:** `ProtectAI/deberta-v3-base-prompt-injection-v2`
    - **Heuristic Patterns:** 7 regex rules for known injection vectors
    - **Composite Scoring:** `max(semantic_score, 0.85 if pattern_match)`
    - **Categories:** Jailbreak, High Risk Probe, Known Injection Pattern
    - **Threshold:** Configurable (default 0.75)
    """)
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("""
    <span class='layer-badge' style='background:rgba(0,255,128,0.1); color:#00ff80;'>Layer 4</span>
    <h3 style='margin-top:12px;'>Cryptographic Audit Ledger</h3>
    """, unsafe_allow_html=True)
    st.markdown("""
    - **Storage:** SQLite with tamper-evident chain
    - **Hashing:** SHA-256 of `prev_hash|timestamp|event|details`
    - **Verification:** Full chain integrity validation on demand
    - **Export:** One-click SOC2 CSV for compliance audits
    - **Events:** `THREAT_BLOCKED`, `AGENT_INTERACTION`, `INTEGRITY_CHECK`
    """)
    st.markdown("</div>", unsafe_allow_html=True)

# ─── Tech Stack ──────────────────────────────────────────────────────────────
st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
st.markdown("<h3>🔧 Technology Stack</h3>", unsafe_allow_html=True)

tc1, tc2, tc3, tc4 = st.columns(4)
with tc1:
    st.markdown("**Backend**")
    st.markdown("- FastAPI + Uvicorn\n- Python 3.10+\n- SQLite3")
with tc2:
    st.markdown("**AI/ML**")
    st.markdown("- LangChain / LangGraph\n- HuggingFace Transformers\n- OpenRouter LLMs")
with tc3:
    st.markdown("**Security**")
    st.markdown("- Microsoft Presidio\n- ProtectAI DeBERTa\n- SHA-256 Chaining")
with tc4:
    st.markdown("**Frontend**")
    st.markdown("- Streamlit (Multi-Page)\n- Plotly Interactive Charts\n- Real-time Telemetry")

st.markdown("</div>", unsafe_allow_html=True)
