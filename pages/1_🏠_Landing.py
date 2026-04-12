import streamlit as st

st.set_page_config(page_title="AegisHealth Nexus Gateway", page_icon="⚕️", layout="wide", initial_sidebar_state="collapsed")

# ─── Full Landing Page CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    .stApp { background: #05070a; color: #e1e2e7; font-family: 'Inter', sans-serif; }
    header, [data-testid="stSidebar"] { display: none !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    
    /* Hero Section */
    .hero-section {
        min-height: 100vh; display: flex; flex-direction: column; align-items: center;
        justify-content: center; text-align: center; position: relative; overflow: hidden;
        background: radial-gradient(ellipse at 50% 0%, rgba(0,240,255,0.08) 0%, transparent 60%),
                    radial-gradient(ellipse at 80% 80%, rgba(0,102,255,0.05) 0%, transparent 50%),
                    #05070a;
    }
    .hero-section::before {
        content: ''; position: absolute; top: 50%; left: 50%; width: 600px; height: 600px;
        transform: translate(-50%, -50%);
        background: radial-gradient(circle, rgba(0,240,255,0.06) 0%, transparent 70%);
        animation: pulse-glow 4s ease-in-out infinite;
    }
    @keyframes pulse-glow { 0%,100% { opacity: 0.5; transform: translate(-50%,-50%) scale(1); } 50% { opacity: 1; transform: translate(-50%,-50%) scale(1.15); } }
    
    .hero-badge {
        display: inline-flex; align-items: center; gap: 8px; padding: 8px 20px;
        background: rgba(0,240,255,0.08); border: 1px solid rgba(0,240,255,0.2);
        border-radius: 100px; font-size: 0.75rem; font-weight: 600; color: #00f0ff;
        text-transform: uppercase; letter-spacing: 2px; margin-bottom: 32px; z-index: 1;
    }
    .hero-badge::before { content: ''; width: 6px; height: 6px; background: #00f0ff; border-radius: 50%; animation: blink 2s infinite; }
    @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }
    
    .hero-title {
        font-size: clamp(3rem, 6vw, 5.5rem); font-weight: 800; letter-spacing: -2px;
        line-height: 1.05; margin-bottom: 24px; z-index: 1;
        background: linear-gradient(135deg, #ffffff 0%, #00f0ff 50%, #0066ff 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        font-size: 1.25rem; font-weight: 300; color: #8b9bb4; max-width: 640px;
        line-height: 1.7; margin-bottom: 48px; z-index: 1; letter-spacing: 0.02em;
    }
    .hero-cta {
        display: inline-flex; align-items: center; gap: 10px; padding: 16px 40px;
        background: linear-gradient(135deg, #00f0ff, #0066ff); color: #002022;
        font-weight: 700; font-size: 1rem; border-radius: 8px; text-decoration: none;
        z-index: 1; box-shadow: 0 8px 32px rgba(0,240,255,0.3);
        transition: all 0.3s ease; cursor: pointer; border: none;
    }
    .hero-cta:hover { transform: translateY(-3px); box-shadow: 0 12px 40px rgba(0,240,255,0.5); }
    
    /* Metrics Bar */
    .metrics-bar {
        display: flex; justify-content: center; gap: 64px; padding: 48px 0;
        border-top: 1px solid rgba(255,255,255,0.04); border-bottom: 1px solid rgba(255,255,255,0.04);
        background: rgba(10,14,23,0.5); z-index: 1; position: relative;
    }
    .metric-item { text-align: center; }
    .metric-value { font-size: 2rem; font-weight: 800; color: #00f0ff; letter-spacing: -1px; }
    .metric-label { font-size: 0.7rem; font-weight: 600; color: #8b9bb4; text-transform: uppercase; letter-spacing: 2px; margin-top: 4px; }
    
    /* Layers Section */
    .layers-section { padding: 120px 80px; background: #05070a; }
    .section-label { font-size: 0.7rem; font-weight: 700; color: #00f0ff; text-transform: uppercase; letter-spacing: 3px; margin-bottom: 16px; }
    .section-title { font-size: 2.8rem; font-weight: 800; letter-spacing: -1.5px; color: #ffffff; margin-bottom: 64px; }
    
    .layers-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; max-width: 1200px; margin: 0 auto; }
    .layer-card {
        background: linear-gradient(145deg, rgba(25,28,31,0.8), rgba(12,14,18,0.9));
        backdrop-filter: blur(24px); border-radius: 16px; padding: 40px;
        position: relative; overflow: hidden; transition: all 0.4s cubic-bezier(0.175,0.885,0.32,1.275);
        border: 1px solid rgba(255,255,255,0.03);
    }
    .layer-card:hover { transform: translateY(-6px); box-shadow: 0 20px 60px rgba(0,240,255,0.08); border-color: rgba(0,240,255,0.15); }
    .layer-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0,240,255,0.3), transparent);
    }
    .layer-num { font-size: 4rem; font-weight: 800; color: rgba(0,240,255,0.08); position: absolute; top: 16px; right: 24px; }
    .layer-icon { font-size: 2rem; margin-bottom: 16px; }
    .layer-title { font-size: 1.2rem; font-weight: 700; color: #ffffff; margin-bottom: 12px; }
    .layer-desc { font-size: 0.9rem; color: #8b9bb4; line-height: 1.7; }
    
    /* Architecture Section */
    .arch-section { padding: 120px 80px; background: linear-gradient(180deg, #05070a, #0b0f19); text-align: center; }
    .arch-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px; max-width: 1000px; margin: 0 auto; }
    .arch-item {
        padding: 32px; background: rgba(25,28,31,0.5); border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.03);
    }
    .arch-icon { font-size: 2.5rem; margin-bottom: 16px; }
    .arch-title { font-size: 1rem; font-weight: 700; color: #ffffff; margin-bottom: 8px; }
    .arch-desc { font-size: 0.8rem; color: #8b9bb4; line-height: 1.6; }
    
    /* Footer */
    .footer {
        padding: 48px 80px; text-align: center; border-top: 1px solid rgba(255,255,255,0.04);
        background: #05070a;
    }
    .footer-text { color: #8b9bb4; font-size: 0.8rem; }
    .footer-brand { color: #00f0ff; font-weight: 700; }
    
    /* Nav */
    .top-nav {
        position: fixed; top: 0; left: 0; right: 0; z-index: 100; padding: 16px 48px;
        display: flex; justify-content: space-between; align-items: center;
        background: rgba(5,7,10,0.8); backdrop-filter: blur(20px);
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .nav-logo { font-size: 1.2rem; font-weight: 800; color: #ffffff; }
    .nav-logo span { color: #00f0ff; }
    .nav-links { display: flex; gap: 32px; align-items: center; }
    .nav-links a { color: #8b9bb4; text-decoration: none; font-size: 0.85rem; font-weight: 500; transition: color 0.2s; }
    .nav-links a:hover { color: #00f0ff; }
</style>
""", unsafe_allow_html=True)

# ─── Navigation ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="top-nav">
    <div class="nav-logo"><span>Aegis</span>Health</div>
    <div class="nav-links">
        <a href="#">Platform</a>
        <a href="#">Documentation</a>
        <a href="#">Architecture</a>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Hero Section ────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <div class="hero-badge">Enterprise Security Gateway — Now Active</div>
    <div class="hero-title">AegisHealth<br>Nexus Gateway</div>
    <div class="hero-subtitle">Industry-grade transparent security proxy for Agentic AI in Healthcare. Zero-trust protection with zero code changes. HIPAA & SOC2 ready.</div>
</div>
""", unsafe_allow_html=True)

# ─── Metrics Bar ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="metrics-bar">
    <div class="metric-item"><div class="metric-value">99.9%</div><div class="metric-label">Uptime SLA</div></div>
    <div class="metric-item"><div class="metric-value">14ms</div><div class="metric-label">Avg Latency</div></div>
    <div class="metric-item"><div class="metric-value">HIPAA</div><div class="metric-label">Compliant</div></div>
    <div class="metric-item"><div class="metric-value">SOC2</div><div class="metric-label">Audit Ready</div></div>
    <div class="metric-item"><div class="metric-value">4</div><div class="metric-label">Security Layers</div></div>
</div>
""", unsafe_allow_html=True)

# ─── Protection Layers ──────────────────────────────────────────────────────
st.markdown("""
<div class="layers-section">
    <div class="section-label">Core Protection</div>
    <div class="section-title">4 Layers of Defense</div>
    <div class="layers-grid">
        <div class="layer-card">
            <div class="layer-num">01</div>
            <div class="layer-icon">🔐</div>
            <div class="layer-title">PII & PHI Encryption Shield</div>
            <div class="layer-desc">Advanced NLP via Microsoft Presidio detects SSNs, Medical Record IDs, and names. Replaces PHI with secure cryptographic tokens before the prompt reaches the LLM.</div>
        </div>
        <div class="layer-card">
            <div class="layer-num">02</div>
            <div class="layer-icon">🧠</div>
            <div class="layer-title">Semantic Threat Guardian</div>
            <div class="layer-desc">ML-powered detection using ProtectAI DeBERTa model combined with heuristic regex patterns to intercept jailbreaks, system prompt leaks, and RAG poisoning.</div>
        </div>
        <div class="layer-card">
            <div class="layer-num">03</div>
            <div class="layer-icon">🛡️</div>
            <div class="layer-title">Context-Aware RBAC</div>
            <div class="layer-desc">Dynamic user context injection prevents IDOR attacks. If a patient queries another patient's records, the gateway intercepts and blocks the tool execution.</div>
        </div>
        <div class="layer-card">
            <div class="layer-num">04</div>
            <div class="layer-icon">⛓️</div>
            <div class="layer-title">Cryptographic Ledger</div>
            <div class="layer-desc">Every interaction is SHA-256 chained into a tamper-proof audit trail. One-click CSV export for HIPAA and SOC2 compliance audits.</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Architecture Section ───────────────────────────────────────────────────
st.markdown("""
<div class="arch-section">
    <div class="section-label">Architecture</div>
    <div class="section-title">Enterprise-Grade Stack</div>
    <div class="arch-grid">
        <div class="arch-item">
            <div class="arch-icon">⚡</div>
            <div class="arch-title">FastAPI Backend</div>
            <div class="arch-desc">High-performance ASGI gateway handling routing, security engines, and MCP transport protocol.</div>
        </div>
        <div class="arch-item">
            <div class="arch-icon">🤖</div>
            <div class="arch-title">LangGraph Agents</div>
            <div class="arch-desc">ReAct agent architecture with native tool calling and RBAC-enforced data access patterns.</div>
        </div>
        <div class="arch-item">
            <div class="arch-icon">🔬</div>
            <div class="arch-title">ML Threat Classifier</div>
            <div class="arch-desc">ProtectAI DeBERTa v3 model for real-time prompt injection detection with composite scoring.</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Footer ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    <div class="footer-text">Built for the future of secure, autonomous healthcare AI. <span class="footer-brand">AegisHealth Nexus Gateway</span> © 2024</div>
</div>
""", unsafe_allow_html=True)
