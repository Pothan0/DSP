import streamlit as st
import requests
import json
import pandas as pd

API_BASE_URL = "http://localhost:7070/api/dashboard"
GATEWAY_URL = "http://localhost:7070"

st.set_page_config(page_title="TrustChain Gateway | NovaSentinel", page_icon="🔗", layout="wide", initial_sidebar_state="collapsed")

# ─── Design System CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    .stApp { background: radial-gradient(ellipse at 15% 50%, #0b0f19, #05070a); color: #e1e2e7; font-family: 'Inter', sans-serif; }
    header { visibility: hidden; }
    .glass-card {
        background: linear-gradient(145deg, rgba(25,28,31,0.7), rgba(12,14,18,0.9));
        backdrop-filter: blur(24px); border: 1px solid rgba(255,255,255,0.03);
        border-radius: 16px; padding: 28px; margin-bottom: 20px;
        box-shadow: 0 8px 40px rgba(0,240,255,0.04); position: relative; overflow: hidden;
    }
    .glass-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0,240,255,0.15), transparent);
    }
    h1 { font-weight: 800; letter-spacing: -1.5px; color: #ffffff; }
    h3 { font-weight: 700; color: #e1e2e7; font-size: 1.1rem; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px; background: rgba(12,14,18,0.8); padding: 6px; border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.03);
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px; background: transparent; border-radius: 8px;
        color: #8b9bb4; font-weight: 600; padding: 0 24px;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: rgba(0,240,255,0.08); color: #00f0ff;
    }
    div.stButton > button {
        font-weight: 700 !important; border-radius: 8px !important;
        padding: 10px 28px !important;
    }
    .hitl-card {
        background: rgba(17,20,23,0.8); border: 1px solid rgba(255,165,0,0.15);
        border-radius: 12px; padding: 20px; margin-bottom: 16px;
        border-left: 4px solid #ffaa00;
    }
    .hitl-label { font-size: 0.65rem; font-weight: 700; color: #ffaa00; text-transform: uppercase; letter-spacing: 2px; }
    .hitl-id { font-size: 0.8rem; color: #e1e2e7; font-weight: 600; margin: 8px 0; }
    
    [data-testid="stMetricValue"] { color: #ffffff !important; font-weight: 800; font-size: 2rem !important; }
    [data-testid="stMetricLabel"] { color: #8b9bb4 !important; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; font-size: 0.6rem !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='font-size:2rem; margin-bottom:8px;'>🔗 TrustChain MCP Gateway</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#8b9bb4; font-size:0.8rem; margin-bottom:24px;'>Transparent security proxy for MCP tool servers</p>", unsafe_allow_html=True)

# ─── Gateway Health Check ───────────────────────────────────────────────────
@st.cache_data(ttl=3)
def check_gateway_health():
    try:
        r = requests.get(f"{GATEWAY_URL}/health", timeout=2)
        return r.json() if r.status_code == 200 else None
    except:
        return None

gw_health = check_gateway_health()

# Status bar
if gw_health:
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.metric("Gateway Status", "Online")
        st.markdown("</div>", unsafe_allow_html=True)
    with sc2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.metric("Active Sessions", gw_health.get("active_sessions", 0))
        st.markdown("</div>", unsafe_allow_html=True)
    with sc3:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        chain_status = "Valid ✓" if gw_health.get("audit_chain_valid") else "⚠ Invalid"
        st.metric("Audit Chain", chain_status)
        st.markdown("</div>", unsafe_allow_html=True)
    with sc4:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.metric("Pending HITL", gw_health.get("pending_hitl", 0))
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.warning("⚠️ TrustChain Gateway is offline. Start it on port 7070.")

# ─── Tabs ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🚦 Live Traffic", "✋ HITL Queue", "🔍 Audit Explorer"])

def fetch_pending():
    try:
        response = requests.get(f"{API_BASE_URL}/pending", timeout=3)
        if response.status_code == 200:
            data = response.json()
            return data.get("pending", data) if isinstance(data, dict) else data
    except:
        pass
    return []

def fetch_logs():
    try:
        response = requests.get(f"{API_BASE_URL}/logs", timeout=3)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

def resolve_request(req_id, approved):
    try:
        response = requests.post(f"{API_BASE_URL}/resolve/{req_id}", json={"approved": approved})
        if response.status_code == 200:
            st.success(f"Request {req_id} {'approved' if approved else 'rejected'}")
        else:
            st.error(f"Failed: {response.text}")
    except Exception as e:
        st.error(f"Error: {e}")

with tab1:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<h3>📡 Live Traffic Logs</h3>", unsafe_allow_html=True)
    logs = fetch_logs()
    if logs:
        df = pd.DataFrame(logs)
        st.dataframe(df, use_container_width=True, height=400, hide_index=True)
    else:
        st.info("No recent traffic. The gateway is idle or offline.")
    st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<h3>✋ Human-in-the-Loop Review Queue</h3>", unsafe_allow_html=True)
    st.caption("Requests escalated due to policy violations or low trust scores")
    
    pending = fetch_pending()
    if not pending:
        st.markdown("<div style='text-align:center; padding:48px;'><span style='font-size:2.5rem;'>✅</span><br><span style='color:#00ff80; font-weight:600;'>All Clear</span><br><span style='color:#8b9bb4; font-size:0.85rem;'>No pending requests — agent traffic flowing normally</span></div>", unsafe_allow_html=True)
    else:
        for p in pending:
            req_id = p.get("message_id", p.get("id", str(p)))
            st.markdown(f"""
            <div class='hitl-card'>
                <div class='hitl-label'>Review Required</div>
                <div class='hitl-id'>{req_id}</div>
            </div>
            """, unsafe_allow_html=True)
            with st.expander(f"Details: {req_id}", expanded=False):
                st.json(p)
            c1, c2, _ = st.columns([1, 1, 3])
            with c1:
                if st.button("✅ Approve", key=f"approve_{req_id}"):
                    resolve_request(req_id, True)
                    st.rerun()
            with c2:
                if st.button("❌ Reject", key=f"reject_{req_id}"):
                    resolve_request(req_id, False)
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with tab3:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<h3>🔍 Audit Explorer</h3>", unsafe_allow_html=True)
    st.caption("Deep dive into the cryptographic audit trail")
    
    # Chain verification
    if gw_health:
        try:
            verify_res = requests.get(f"{GATEWAY_URL}/verify-chain", timeout=2)
            if verify_res.status_code == 200:
                vdata = verify_res.json()
                if vdata.get("valid"):
                    st.markdown("<div style='display:inline-flex; align-items:center; gap:8px; padding:8px 16px; background:rgba(0,255,128,0.06); border:1px solid rgba(0,255,128,0.15); border-radius:8px; margin-bottom:16px;'><span style='color:#00ff80; font-weight:700; font-size:0.8rem;'>✓ CHAIN INTEGRITY VERIFIED</span></div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div style='display:inline-flex; align-items:center; gap:8px; padding:8px 16px; background:rgba(255,50,50,0.06); border:1px solid rgba(255,50,50,0.15); border-radius:8px; margin-bottom:16px;'><span style='color:#ff3232; font-weight:700; font-size:0.8rem;'>⚠ CHAIN COMPROMISED</span></div>", unsafe_allow_html=True)
        except:
            pass
    
    logs = fetch_logs()
    if logs:
        st.json(logs)
    else:
        st.info("No audit trail available.")
    st.markdown("</div>", unsafe_allow_html=True)
