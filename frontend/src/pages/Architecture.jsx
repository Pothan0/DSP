import { useState, useEffect } from 'react'
import { Layers, Users, Shield, Brain, Lock, Network, Activity, Server, Database, ArrowRight, CheckCircle } from 'lucide-react'
import Navbar from '../components/Navbar'
import { checkHealth, getAnalytics, verifyChain } from '../api'
import './Architecture.css'

const PIPELINE_NODES = [
  { name: 'User / Agent', desc: 'MCP client request', icon: Users, color: 'blue', type: 'source' },
  { name: 'MCP Transport', desc: 'JSON-RPC intercept', icon: Activity, color: 'cyan', type: 'engine' },
  { name: 'PII/PHI Shield', desc: 'Presidio NLP scan', icon: Shield, color: 'cyan', type: 'engine' },
  { name: 'Injection Detector', desc: 'DeBERTa ML model', icon: Brain, color: 'red', type: 'engine' },
  { name: 'RBAC Gate', desc: 'Context-aware auth', icon: Lock, color: 'amber', type: 'engine' },
  { name: 'Anomaly Engine', desc: 'Behavioral scoring', icon: Network, color: 'purple', type: 'engine' },
  { name: 'Trust Scorer', desc: 'Composite analysis', icon: CheckCircle, color: 'green', type: 'engine' },
  { name: 'Tool Server', desc: 'Verified execution', icon: Server, color: 'green', type: 'dest' },
]

export default function Architecture() {
  const [health, setHealth] = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [chainValid, setChainValid] = useState(null)

  useEffect(() => {
    const load = async () => {
      const [h, a, c] = await Promise.all([checkHealth(), getAnalytics(), verifyChain()])
      if (h) setHealth(h)
      if (a) setAnalytics(a)
      if (c) setChainValid(c.chain_valid)
    }
    load()
  }, [])

  const isOnline = health?.status === 'online'
  const totalBlocks = analytics
    ? (analytics.event_counts?.THREAT_BLOCKED || 0) + (analytics.event_counts?.AGENT_INTERACTION || 0)
    : 0

  return (
    <>
      <Navbar />
      <div className="architecture-page">
        <div className="arch-container">
          {/* Header */}
          <div className="arch-header">
            <h1 className="arch-title">
              <div className="arch-title-icon"><Layers size={20} /></div>
              System Architecture
            </h1>
            <p className="arch-subtitle">
              AegisHealth's multi-layered security pipeline for AI agent traffic. 
              Every request traverses the full security gauntlet before reaching the tool server.
            </p>
          </div>

          {/* Pipeline Flow */}
          <div className="pipeline-section">
            <div className="pipeline-label">Security Pipeline</div>
            <div className="glass-card-static" style={{ padding: '36px 24px', overflow: 'visible' }}>
              <div className="pipeline-flow">
                {PIPELINE_NODES.map((node, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'stretch', flex: 1, minWidth: 0 }}>
                    <div className="pipeline-node">
                      <div className={`node-card ${node.type}`}>
                        <div className={`node-icon ${node.color}`}>
                          <node.icon size={20} />
                        </div>
                        <div className="node-name">{node.name}</div>
                        <div className="node-desc">{node.desc}</div>
                      </div>
                    </div>
                    {i < PIPELINE_NODES.length - 1 && (
                      <div className="flow-connector">
                        <span className="flow-arrow">→</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Rejected Path */}
              <div className="rejected-path">
                <div className="rejected-label">Rejected Requests</div>
                <div className="rejected-arrow"><ArrowRight size={16} /></div>
                <div className="rejected-dest">
                  <Database size={14} />
                  Cryptographic Audit Ledger (SHA-256 Chain)
                </div>
              </div>
            </div>
          </div>

          {/* Detail Grid */}
          <div className="detail-grid">
            {/* Interceptor Bus */}
            <div className="glass-card detail-card animate-in-delay-1">
              <div className="card-title-icon" style={{ marginBottom: '16px' }}>
                <Activity size={14} />
              </div>
              <div className="detail-card-title">Interceptor Bus</div>
              <div className="detail-card-desc">
                Central message routing system that forces all inter-agent 
                and agent-to-tool communications through the security gauntlet.
              </div>
              <div className="audit-stats">
                <div className="audit-stat">
                  <span className="audit-stat-label">Protocol</span>
                  <span className="audit-stat-value">JSON-RPC 2.0</span>
                </div>
                <div className="audit-stat">
                  <span className="audit-stat-label">Transport</span>
                  <span className="audit-stat-value">MCP / SSE</span>
                </div>
                <div className="audit-stat">
                  <span className="audit-stat-label">API Status</span>
                  <span className="audit-stat-value" style={{ color: isOnline ? 'var(--success)' : 'var(--danger)' }}>
                    {isOnline ? 'Online ✓' : 'Offline'}
                  </span>
                </div>
              </div>
            </div>

            {/* Security Engines */}
            <div className="glass-card detail-card animate-in-delay-2">
              <div className="card-title-icon" style={{ marginBottom: '16px', background: 'rgba(255,50,50,0.06)', borderColor: 'rgba(255,50,50,0.12)', color: 'var(--danger)' }}>
                <Shield size={14} />
              </div>
              <div className="detail-card-title">Security Engines</div>
              <div className="detail-card-desc">
                Four specialized engines evaluate each message envelope 
                and can alter its state or block it entirely.
              </div>
              <div className="engine-list">
                {[
                  { name: 'PII/PHI Shield (Presidio)', status: 'online' },
                  { name: 'Injection Detector (DeBERTa)', status: 'online' },
                  { name: 'RBAC Gate (Context Injection)', status: 'online' },
                  { name: 'Cryptographic Audit (SHA-256)', status: 'online' },
                ].map((e, i) => (
                  <div className="engine-item" key={i}>
                    <span className="engine-name">{e.name}</span>
                    <span className="badge-online" style={{ padding: '3px 10px', fontSize: '0.55rem' }}>
                      <span className="pulse-dot green" style={{ width: '5px', height: '5px' }}></span>
                      {e.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Audit Chain — live data */}
            <div className="glass-card detail-card animate-in-delay-3">
              <div className="card-title-icon" style={{ marginBottom: '16px', background: 'rgba(0,255,128,0.06)', borderColor: 'rgba(0,255,128,0.12)', color: 'var(--success)' }}>
                <Database size={14} />
              </div>
              <div className="detail-card-title">Audit Chain</div>
              <div className="detail-card-desc">
                Immutable cryptographic ledger with SHA-256 hash chaining 
                for tamper-proof compliance logging.
              </div>
              <div className="audit-stats">
                <div className="audit-stat">
                  <span className="audit-stat-label">Total Blocks</span>
                  <span className="audit-stat-value">{totalBlocks > 0 ? totalBlocks.toLocaleString() : '—'}</span>
                </div>
                <div className="audit-stat">
                  <span className="audit-stat-label">Chain Integrity</span>
                  <span className="audit-stat-value" style={{ color: chainValid === true ? 'var(--success)' : chainValid === false ? 'var(--danger)' : 'var(--text-secondary)' }}>
                    {chainValid === true ? 'Verified ✓' : chainValid === false ? 'COMPROMISED ⚠' : 'Checking…'}
                  </span>
                </div>
                <div className="audit-stat">
                  <span className="audit-stat-label">Hash Algorithm</span>
                  <span className="audit-stat-value">SHA-256</span>
                </div>
                <div className="audit-stat">
                  <span className="audit-stat-label">Agent Status</span>
                  <span className="audit-stat-value" style={{ color: health?.agent_status === 'online' ? 'var(--success)' : 'var(--warning)' }}>
                    {health?.agent_status === 'online' ? 'Online ✓' : health?.agent_status || '—'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Tech Stack */}
          <div className="tech-section">
            <div className="glass-card-static" style={{ padding: '36px' }}>
              <div className="card-header">
                <div className="card-title">
                  <div className="card-title-icon"><Server size={14} /></div>
                  Technology Stack
                </div>
              </div>
              <div className="tech-stack">
                {[
                  'Python 3.10+', 'FastAPI', 'LangChain', 'LangGraph',
                  'Microsoft Presidio', 'ProtectAI DeBERTa v3', 'SQLite3',
                  'SHA-256', 'OpenRouter', 'React', 'Vite', 'Plotly.js',
                  'MCP Protocol', 'Uvicorn'
                ].map((tech, i) => (
                  <span className="tech-pill" key={i}>{tech}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
