import { Link } from 'react-router-dom'
import { Shield, Brain, Lock, Network, ArrowRight, Zap, Eye, Server } from 'lucide-react'
import Navbar from '../components/Navbar'
import './Landing.css'

export default function Landing() {
  return (
    <>
      <Navbar />
      <div className="landing-page">
        {/* Hero Section */}
        <section className="hero-section" id="hero">
          <div className="hero-bg-glow" />
          <div className="hero-content">
            <div className="hero-badge">
              <span className="pulse-dot cyan"></span>
              Enterprise Security Gateway
            </div>
            <h1 className="hero-title">
              AegisHealth<br />
              <span className="text-gradient">Nexus Gateway</span>
            </h1>
            <p className="hero-subtitle">
              Industry-grade transparent security proxy for Agentic AI in Healthcare. 
              Zero-trust protection with zero code changes. HIPAA & SOC2 ready.
            </p>
            <div className="hero-actions">
              <Link to="/dashboard" className="btn-primary">
                Launch Console <ArrowRight size={18} />
              </Link>
              <Link to="/architecture" className="btn-ghost">
                View Architecture
              </Link>
            </div>
          </div>
        </section>

        {/* Metrics Banner */}
        <section className="metrics-banner" id="metrics">
          <div className="metric-item">
            <div className="metric-value">99.9%</div>
            <div className="metric-label">Uptime SLA</div>
          </div>
          <div className="metric-divider" />
          <div className="metric-item">
            <div className="metric-value">14ms</div>
            <div className="metric-label">Avg Latency</div>
          </div>
          <div className="metric-divider" />
          <div className="metric-item">
            <div className="metric-value">HIPAA</div>
            <div className="metric-label">Compliant</div>
          </div>
          <div className="metric-divider" />
          <div className="metric-item">
            <div className="metric-value">SOC2</div>
            <div className="metric-label">Audit Ready</div>
          </div>
        </section>

        {/* Features Section */}
        <section className="features-section" id="features">
          <div className="container">
            <div className="section-header">
              <div className="section-label">Core Protection</div>
              <h2 className="section-title">4 Layers of Defense</h2>
              <p className="section-subtitle">
                AegisHealth provides a multi-tiered security gauntlet that intercepts,
                analyzes, and sanitizes all agent traffic in real-time.
              </p>
            </div>

            <div className="features-grid">
              <div className="glass-card feature-card animate-in">
                <div className="feature-icon bg-cyan">
                  <Shield size={24} />
                </div>
                <div className="feature-number">01</div>
                <h3>PII & PHI Encryption Shield</h3>
                <p>Advanced NLP via Microsoft Presidio detects SSNs, Medical Record IDs, and names. Replaces PHI with secure cryptographic tokens before the prompt reaches the LLM.</p>
              </div>

              <div className="glass-card feature-card animate-in-delay-1">
                <div className="feature-icon bg-danger">
                  <Brain size={24} />
                </div>
                <div className="feature-number">02</div>
                <h3>Semantic Threat Guardian</h3>
                <p>ML-powered detection using ProtectAI DeBERTa model combined with heuristic regex patterns to intercept jailbreaks, system prompt leaks, and RAG poisoning.</p>
              </div>

              <div className="glass-card feature-card animate-in-delay-2">
                <div className="feature-icon bg-warning">
                  <Lock size={24} />
                </div>
                <div className="feature-number">03</div>
                <h3>Context-Aware RBAC</h3>
                <p>Dynamic user context injection prevents IDOR attacks. If a patient queries another patient's records, the gateway intercepts and blocks the tool execution.</p>
              </div>

              <div className="glass-card feature-card animate-in-delay-3">
                <div className="feature-icon bg-success">
                  <Network size={24} />
                </div>
                <div className="feature-number">04</div>
                <h3>Cryptographic Ledger</h3>
                <p>Every interaction is SHA-256 chained into a tamper-proof audit trail. One-click CSV export for HIPAA and SOC2 compliance audits.</p>
              </div>
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="how-section" id="how-it-works">
          <div className="container">
            <div className="section-header">
              <div className="section-label">Zero Code Changes</div>
              <h2 className="section-title">How It Works</h2>
              <p className="section-subtitle">
                Deploy AegisHealth as a transparent proxy between your AI agents and MCP tool servers. No SDK required.
              </p>
            </div>

            <div className="how-grid">
              <div className="glass-card-static how-step animate-in-delay-1">
                <div className="how-step-number">Step 01</div>
                <div className="how-step-icon">
                  <Zap size={28} />
                </div>
                <h3>Point & Intercept</h3>
                <p>Configure your agent's MCP endpoint to route through the AegisHealth gateway. One config line change.</p>
              </div>

              <div className="glass-card-static how-step animate-in-delay-2">
                <div className="how-step-number">Step 02</div>
                <div className="how-step-icon">
                  <Eye size={28} />
                </div>
                <h3>Analyze & Protect</h3>
                <p>Every message flows through 4 security engines — PII detection, injection analysis, RBAC enforcement, and anomaly scoring.</p>
              </div>

              <div className="glass-card-static how-step animate-in-delay-3">
                <div className="how-step-number">Step 03</div>
                <div className="how-step-icon">
                  <Server size={28} />
                </div>
                <h3>Forward & Audit</h3>
                <p>Clean requests reach your tool server. Every decision is SHA-256 chained into an immutable cryptographic audit ledger.</p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="cta-section">
          <div className="container">
            <div className="glass-card-static cta-card">
              <h2>Ready to Secure Your AI Agents?</h2>
              <p>Deploy zero-trust security in under 5 minutes. No code changes required.</p>
              <div className="hero-actions" style={{ justifyContent: 'center' }}>
                <Link to="/dashboard" className="btn-primary">
                  Launch Console <ArrowRight size={18} />
                </Link>
                <Link to="/redteam" className="btn-danger">
                  Run Red Team Test
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="footer">
          <div className="container flex-between">
            <div className="footer-brand">
              <Shield size={16} /> AegisHealth Nexus Gateway
            </div>
            <div className="footer-links">
              <span>© 2026 Aegis Health Security</span>
            </div>
          </div>
        </footer>
      </div>
    </>
  )
}
