# NovaSentinel / SentriCore

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white" />
  <img alt="React" src="https://img.shields.io/badge/React-Frontend-61DAFB?logo=react&logoColor=black" />
  <img alt="MCP" src="https://img.shields.io/badge/MCP-Secured%20Gateway-6E56CF" />
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" />
  <img alt="License" src="https://img.shields.io/badge/Status-Engineering%20Prototype-orange" />
</p>

<p align="center">
  Enterprise AI Security Gateway for <strong>REST + MCP</strong> runtimes.<br/>
  Injection defense, trust-aware tool governance, HITL escalation, and tamper-evident auditability.
</p>

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Why This Product](#why-this-product)
- [Architecture Overview](#architecture-overview)
- [MCP as the Strategic Differentiator](#mcp-as-the-strategic-differentiator)
- [Agents and Security Engines](#agents-and-security-engines)
- [End-to-End Workflows](#end-to-end-workflows)
- [Repository Layout](#repository-layout)
- [Quick Start](#quick-start)
- [Runbook: API + Frontend](#runbook-api--frontend)
- [Runbook: MCP Gateway](#runbook-mcp-gateway)
- [MCP Usage Guide (JSON-RPC)](#mcp-usage-guide-json-rpc)
- [Security Model](#security-model)
- [Observability and Operations](#observability-and-operations)
- [Configuration](#configuration)
- [Testing and Quality Gates](#testing-and-quality-gates)
- [Troubleshooting](#troubleshooting)
- [Current Maturity and Production Hardening](#current-maturity-and-production-hardening)
- [Roadmap Direction](#roadmap-direction)

---

## Executive Summary

NovaSentinel (SentriCore) secures AI agent interactions with a policy-first gateway model:

- **Root API track** delivers product-facing secure chat and analytics consumed by the React frontend.
- **TrustChain MCP track** secures Model Context Protocol tool traffic with a dedicated security pipeline.

The platform is designed for teams building agentic systems that need:

- deterministic policy enforcement,
- runtime risk controls on tool execution,
- and verifiable audit evidence.

---

## Why This Product

Most AI applications secure prompts, but not the runtime execution path where real damage happens.

NovaSentinel addresses this gap with layered controls:

1. Detect malicious or manipulative intent before execution.
2. Enforce authorization and risk tiers at tool-call time.
3. Escalate critical actions to humans when trust is low.
4. Preserve immutable cryptographic evidence for governance and incident response.

---

## Architecture Overview

### Runtime Tracks

- **Track A: Secure API Gateway (root)**
  - Entry: `api.py`
  - Product UX: `frontend/`
  - Security pipeline: threat score -> input PII scrub -> agent/RBAC -> output scrub -> audit

- **Track B: MCP Security Gateway (`trustchain_ig/`)**
  - Entry: `trustchain_ig/run_gateway.py`
  - Transport: MCP JSON-RPC + SSE/stdio proxying
  - Security pipeline: injection + embedding drift -> capability auth -> HITL/trust -> audit/metrics

### High-Level Dataflow

```text
Client Request
  -> Security Gateway
  -> Threat/Injection Analysis
  -> Privacy + Authorization Controls
  -> Tool/Agent Execution (PASS / BLOCK / ESCALATE)
  -> Output Sanitization
  -> Audit Chain + Metrics
  -> Safe Response
```

---

## MCP as the Strategic Differentiator

MCP is the strongest product lever because it governs **tool execution**, not just model text.

With `trustchain_ig`, each `tools/call` can be:

- **Passed** when clean and authorized,
- **Blocked** when injection, abuse, or policy violations are detected,
- **Escalated** to HITL when risk is high or trust falls below threshold.

This gives enterprise teams a practical control plane for agent operations across frameworks.

### Why buyers care

- Security policies are centralized and enforceable at runtime.
- Sensitive operations gain approval gates and forensic traceability.
- Teams can adopt agentic automation without blind trust in model behavior.

---

## Agents and Security Engines

### Root Stack Components

- `person3_scorer.py` - prompt threat scoring (ML + signatures)
- `person2_security.py` - PII detection, masking policy, token vault
- `person1_agent.py` - tool-enabled assistant with RBAC checks
- `audit_logger.py` - tamper-evident hash-chain security logging
- `database.py` - local storage for demo records and audit backing data

### MCP Stack Components (`trustchain_ig`)

- `engines/injection.py` - signature and embedding-drift detector
- `engines/capability.py` - HMAC capability token issue/validation
- `engines/hitl.py` - human approval queue and decisions
- `gateway/session.py` - session trust score lifecycle and decay
- `audit/chain.py` - cryptographic ledger with chain verification
- `telemetry/metrics.py` - Prometheus metrics surface

---

## End-to-End Workflows

### A) API Chat Workflow (Root)

1. Client sends `POST /api/v1/chat`
2. Threat scorer evaluates malicious intent
3. Input PII scrub policy executes
4. Agent/tool flow runs with RBAC-aware controls
5. Output sanitization and response normalization
6. Security event written to audit chain
7. Frontend receives secure response + assessment metadata

### B) MCP Tool Workflow

1. MCP client sends `tools/call` to `/mcp`
2. Session and trust context loaded
3. Injection + semantic drift analysis performed
4. Capability token validated for high/critical tools
5. Decision path:
   - `PASS` -> execute/forward
   - `BLOCK` -> JSON-RPC error with reason
   - `ESCALATE` -> HITL request created
6. Decision and flags written to cryptographic audit log

---

## Repository Layout

- `api.py` - FastAPI root gateway
- `frontend/` - React/Vite production frontend
- `person1_agent.py` - assistant and guarded tool access
- `person2_security.py` - PII scrub engines and policy helpers
- `person3_scorer.py` - threat scoring engine
- `audit_logger.py`, `database.py`, `schemas.py` - contracts + persistence
- `trustchain_ig/` - MCP gateway, engines, audit, transport, telemetry
- `docker-compose.yml` - root API + frontend runtime
- `trustchain_ig/docker-compose.yml` - MCP + Prometheus + Grafana

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- pip
- Docker + Docker Compose (optional)

Optional for live LLM behavior:

- `OPENROUTER_API_KEY`

---

## Runbook: API + Frontend

### 1) Install backend dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_lg
```

### 2) (Optional) set OpenRouter key

Linux/macOS:

```bash
export OPENROUTER_API_KEY=your_key_here
```

Windows PowerShell:

```powershell
setx OPENROUTER_API_KEY "your_key_here"
```

### 3) Start backend

```bash
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 4) Start frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port=5173
```

### URLs

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`

### Windows one-command helper

```bash
run.bat
```

---

## Runbook: MCP Gateway

### 1) Install MCP dependencies

```bash
cd trustchain_ig
pip install -r requirements.txt
```

### 2) Start MCP gateway

```bash
python run_gateway.py
```

### MCP URL

- `http://localhost:7070`

### Core operational endpoints

- `POST /mcp` - JSON-RPC entrypoint
- `GET /health` - service health + chain status
- `GET /stats` - sessions/HITL/audit statistics
- `GET /sessions/{session_id}` - trust/session state
- `GET /hitl-queue` - pending approvals
- `POST /hitl-decision/{request_id}` - approve/reject
- `GET /audit` - audit query
- `GET /verify-chain` - chain integrity check
- `GET /metrics` - Prometheus metrics

### Upstream transport proxy endpoints

- `GET /mcp/{server_id}/sse`
- `POST /mcp/{server_id}/message`

---

## MCP Usage Guide (JSON-RPC)

### 1) Initialize

```bash
curl -X POST http://localhost:7070/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: sess_demo_001" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"clientInfo":{"name":"demo-client"}}}'
```

### 2) List tools

```bash
curl -X POST http://localhost:7070/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: sess_demo_001" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

### 3) Call tool

```bash
curl -X POST http://localhost:7070/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: sess_demo_001" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_database","arguments":{"query":"find patient 123"}}}'
```

If blocked/escalated, you receive JSON-RPC errors with structured reason data.

---

## Security Model

### Controls

- Injection signature detection
- Semantic drift scoring
- Capability-token checks for privileged tools
- HITL escalation for critical/low-trust operations
- Session trust scoring + termination thresholding
- PII input/output sanitization (root stack)
- Tamper-evident audit chain verification

### Tool risk tiers (`trustchain_ig/config/defaults.yaml`)

- `low` - baseline allowed
- `medium` - controlled operations
- `high` - token-bound authorization + max-call ceilings
- `critical` - requires HITL

---

## Observability and Operations

### Built-in visibility

- Gateway health and trust session stats
- HITL queue inspection and actions
- Audit event querying and integrity verification
- Prometheus metrics endpoint for dashboards and alerting

### Dockerized observability (`trustchain_ig/docker-compose.yml`)

- MCP Gateway: `7070`
- Prometheus: `9091`
- Grafana: `3000`

---

## Configuration

### Root environment variables

- `OPENROUTER_API_KEY` - optional live model key
- `APP_ENV` - environment mode (`dev`/`prod`)
- `ALLOWED_ORIGINS` - CORS allowed origins
- `API_BEARER_TOKEN` - auth token when auth is enforced
- `ENFORCE_AUTH` - force strict auth in non-prod
- `RATE_LIMIT_WINDOW_SECONDS`, `RATE_LIMIT_MAX_REQUESTS`

### MCP environment variables

All `trustchain_ig` config values are overrideable via `TRUSTCHAIN_*`.

Examples:

- `TRUSTCHAIN_MCP_PORT`
- `TRUSTCHAIN_TELEMETRY_PROMETHEUS_ENABLED`
- `TRUSTCHAIN_AUDIT_DATABASE_URL`

Canonical defaults live in `trustchain_ig/config/defaults.yaml`.

---

## Testing and Quality Gates

Run full suite:

```bash
python -m pytest
```

Run security-only suites:

```bash
python -m pytest -m security
```

Security test strategy and CI gates are documented in `SECURITY_TESTING.md`.

---

## Troubleshooting

- **Port conflict**: free `8000`, `5173`, `7070`, `3000`, `9091`
- **Model initialization delay**: first run may download model assets
- **No OpenRouter key**: root stack runs in safe mock-compatible mode
- **Frontend/API mismatch**: verify backend is live and token/origin config is correct
- **Coverage command errors**: install `pytest-cov`

---

## Current Maturity and Production Hardening

Current state: strong engineering prototype with real security controls.

Before production rollout, prioritize:

- strict authn/authz on all sensitive endpoints
- secret management for capability signing keys
- tenant-aware policy boundaries
- hardened CORS/network posture and rate policy tuning
- SIEM integration and incident response runbooks

---

## Roadmap Direction

Target architecture is a unified gateway:

- MCP security pipeline as the canonical control plane
- REST endpoints as stable product-facing facade
- one policy model, one trust model, one audit model, one telemetry layer

This delivers lower operational complexity and higher governance consistency.
