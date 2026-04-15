# SentriCore Security Gateway

SentriCore is a security-focused AI gateway project with two runtime tracks in one repository:

- `SentriCore API stack` (root): a 4-layer security pipeline in front of an LLM-driven assistant, with audit logging and dashboarding.
- `TrustChain MCP stack` (`trustchain_ig/`): an MCP security gateway with tool-call policy enforcement, trust scoring, HITL escalation, and telemetry.

This README is a high-level, end-to-end guide for running and testing both stacks.

---

## What This Project Does

### 1) SentriCore API stack (root)

The root API processes each chat request through a defense-in-depth pipeline:

1. **Threat scoring** (`person3_scorer.py`)  
   Hybrid detection using an ML prompt-injection classifier plus regex signature libraries.
2. **Input PII scrubbing** (`person2_security.py`)  
   Presidio-based entity detection and reversible tokenization.
3. **Agent execution with RBAC controls** (`person1_agent.py`)  
   LangGraph/LangChain-based assistant and tool calls with role checks.
4. **Output PII scrubbing** (`person2_security.py`)  
   Final response sanitization.

All key events are written to a tamper-evident hash chain (`audit_logger.py`).

### 2) TrustChain MCP stack (`trustchain_ig/`)

The MCP gateway secures tool calls over JSON-RPC/MCP:

- Injection detection (`trustchain_ig/engines/injection.py`)
- Capability token checks (`trustchain_ig/engines/capability.py`)
- Session trust scoring and decay (`trustchain_ig/gateway/session.py`)
- HITL escalation paths (`trustchain_ig/engines/hitl.py`)
- Audit chain (`trustchain_ig/audit/chain.py`)
- Metrics and observability hooks (`trustchain_ig/telemetry/metrics.py`)

---

## Repository Layout

- `api.py`: FastAPI app for SentriCore root stack.
- `app.py`: Streamlit dashboard (root stack).
- `person1_agent.py`: assistant agent + guarded tools.
- `person2_security.py`: PII detection/tokenization guard.
- `person3_scorer.py`: threat scoring engine.
- `audit_logger.py`, `database.py`, `schemas.py`: persistence and contracts.
- `frontend/`: React/Vite frontend for app pages.
- `trustchain_ig/`: MCP security gateway stack.
- `docker-compose.yml`: root API + Streamlit compose.
- `trustchain_ig/docker-compose.yml`: MCP + Prometheus + Grafana compose.

---

## Prerequisites

- Python 3.10+
- Node.js 18+ (for `frontend/`)
- pip
- Docker + Docker Compose (optional)

Optional but recommended:

- OpenRouter API key (`OPENROUTER_API_KEY`) for live LLM usage.

Without API key, the root agent uses mock mode so security layers are still testable.

---

## Quick Start Matrix

- **Run root API only**: `python -m uvicorn api:app --host 127.0.0.1 --port 8000`
- **Run root dashboard only**: `python -m streamlit run app.py`
- **Run root API + dashboard (Windows helper)**: `run.bat`
- **Run React frontend**: in `frontend/`, `npm install` then `npm run dev -- --host 127.0.0.1 --port=5173`
- **Run MCP gateway**: in `trustchain_ig/`, `python run_gateway.py`

---

## Setup: Root SentriCore API Stack

### 1) Install Python dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_lg
```

### 2) Configure environment (optional live LLM)

Linux/macOS:

```bash
export OPENROUTER_API_KEY=your_key_here
```

Windows (PowerShell):

```powershell
setx OPENROUTER_API_KEY "your_key_here"
```

### 3) Start API

```bash
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 4) Start Streamlit dashboard (new terminal)

```bash
python -m streamlit run app.py
```

### Root Stack URLs

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Streamlit dashboard: `http://localhost:8501`

---

## Setup: React Frontend (`frontend/`)

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port=5173
```

Frontend URL:

- `http://localhost:5173`

Build commands:

```bash
npm run build
npm run preview
```

---

## Setup: TrustChain MCP Gateway (`trustchain_ig/`)

### 1) Install dependencies

```bash
cd trustchain_ig
pip install -r requirements.txt
```

### 2) Run MCP gateway

```bash
python run_gateway.py
```

Default MCP gateway URL:

- `http://localhost:7070`

### Key MCP endpoints

- `POST /mcp` JSON-RPC entrypoint (`initialize`, `tools/list`, `tools/call`, `ping`)
- `GET /health`
- `GET /stats`
- `GET /hitl-queue`
- `POST /hitl-decision/{request_id}`
- `GET /audit`
- `GET /verify-chain`
- `GET /mcp/{server_id}/sse` and `POST /mcp/{server_id}/message` for stream transport proxying

---

## Docker

### Root API + Streamlit

From repository root:

```bash
docker-compose up --build
```

Services:

- API on `8000`
- Streamlit on `8501`

### MCP + Observability stack

From `trustchain_ig/`:

```bash
docker-compose up --build
```

Services:

- MCP gateway on `7070`
- Gateway metrics exposed via service mapping in compose
- Prometheus on host `9091`
- Grafana on host `3000`

---

## API Reference (Root SentriCore)

- `GET /health`: status, agent online/offline, audit chain validity
- `POST /api/v1/chat`: full 4-layer protected chat flow
- `GET /api/v1/analytics`: SOC metrics summary
- `GET /api/v1/logs`: recent audit entries
- `GET /api/v1/logs/verify`: hash chain integrity check
- `POST /api/v1/tools/red_team`: direct scorer check
- `POST /api/v1/tools/red_team_full`: per-layer red-team evaluation result

Minimal sample request:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"What is machine learning?"}'
```

---

## Environment Variables

### Root stack

- `OPENROUTER_API_KEY` (optional): enables live LLM via OpenRouter.
- `API_URL` (optional): dashboard target API URL (defaults to local API URL).

### TrustChain stack

Configuration is loaded from `trustchain_ig/config/defaults.yaml` and can be overridden with `TRUSTCHAIN_*` variables, for example:

- `TRUSTCHAIN_MCP_PORT`
- `TRUSTCHAIN_TELEMETRY_PROMETHEUS_ENABLED`
- `TRUSTCHAIN_AUDIT_DATABASE_URL`

---

## Security Testing

This repository includes security-focused pytest suites for both stacks.

Run all tests:

```bash
python -m pytest
```

Run security-only tests:

```bash
python -m pytest -m security
```

See `SECURITY_TESTING.md` for details on test categories and CI security gating.

---

## Troubleshooting

- **Port already in use**: free ports `8000`, `8501`, `5173`, `7070`, `3000`, `9091`.
- **HF model download delays**: first run of `person3_scorer.py` may download model weights.
- **No OpenRouter key**: root agent falls back to mock mode by design.
- **Frontend cannot reach backend**: check API URL config in frontend API client and confirm backend is running.
- **Pytest coverage flags fail**: install `pytest-cov` with `python -m pip install pytest-cov`.

---

## Current Maturity Notes

This project is strong as a security architecture demo and engineering prototype. Before production use, prioritize:

- Strong API authentication and server-side identity trust
- Tight CORS and deployment hardening
- Externalized secure token vaulting / secrets management
- Deeper test coverage and operational SLO/monitoring controls

---

## Windows One-Command Start (Root Stack)

Use:

```bash
run.bat
```

It initializes DB, cleans known local ports, starts FastAPI, then launches Streamlit.
