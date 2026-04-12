# SentriCore - Enterprise Roadmap

## Current State Assessment (The "Student" Baseline)
Right now, the project is a very solid Proof of Concept (PoC) demonstrating the core concepts of agent security. However, it relies heavily on local, mocked, and non-scalable solutions:
- **Architecture:** Monolithic Streamlit application (`app.py`).
- **Input Security:** Basic regex pattern matching and semantic similarity against 7 hardcoded jailbreak prompts using a small `SentenceTransformer` (`person3_scorer.py`).
- **DLP/Privacy:** Basic PII shredding using Presidio (`person2_security.py`).
- **Agent Logic:** Local LangChain instance running a tiny 1B parameter model (`Llama 3.2 1b`) with fragile JSON-repair logic and mock SQLite tools (`person1_agent.py` & `database.py`).
- **Audit Logging:** Local SQLite DB with a simple SHA-256 hash chain and hardcoded mock analytics (`audit_logger.py`).

## The Vision: Industry-Ready, Shippable Agent Security Gateway
To make this a real-world, enterprise-grade product, we need to transition from a single-node script to a High-Performance API Gateway for AI Agents.

Here are the Core Capabilities required to make this shippable:

### 1. Advanced Threat Detection Engine
*   **Move beyond Regex/Static Embeddings:** Implement dedicated, fine-tuned security models (e.g., LlamaGuard, prompt-injection-classifiers) to detect complex, zero-day prompt injections, jailbreaks, and prompt leaking.
*   **Contextual Guardrails:** Add semantic routing and topic restrictions to ensure the agent physically cannot talk about out-of-bounds topics.
*   **Toxicity & Hallucination Checks:** Add output validation to ensure the LLM hasn't hallucinated fake records or generated toxic content.

### 2. Enterprise Data Loss Prevention (DLP)
*   **Vault-Based Tokenization:** Instead of "shredding" PII (which breaks context), implement format-preserving encryption or tokenization (e.g., mapping `Alice` to `[PERSON_1]`, sending `[PERSON_1]` to the LLM, and detokenizing the response back to `Alice` before sending to the user).
*   **Compliance:** Ensure the DLP pipeline meets PCI-DSS and HIPAA standards by preparing it for enterprise Vaults (like HashiCorp Vault).

### 3. Secure Agent Execution & Identity
*   **Identity & RBAC (Role-Based Access Control):** Inject User Identity/OAuth Context into the agent so it can only execute tools authorized for the authenticated user.
*   **Sandboxed Tool Execution:** Tools must run in isolated environments with strict timeouts and least-privilege database access.
*   **Schema Enforcement:** Move away from string parsing/regex fixes. Use strict structured output enforcement (via Pydantic and Instructor or strict function calling).

### 4. Enterprise Audit & SIEM Integration
*   **Centralized Logging:** Stream logs asynchronously to enterprise SIEMs (Splunk, Datadog, ELK stack) instead of a local SQLite file.
*   **True Immutability:** Prepare integration with a managed ledger (like AWS QLDB) or WORM (Write Once Read Many) cloud storage.
*   **Real Analytics:** Replace hardcoded metrics with live aggregations from a time-series database.

### 5. Scalable Architecture
*   **API-First (Headless):** Separate the Streamlit UI from the core logic. Build a high-throughput FastAPI backend that clients (or other microservices) can call.
*   **Asynchronous Processing:** Use asyncio to prevent the gateway from blocking while waiting for LLM generation or security scans.
*   **Containerization:** Fully Dockerize the system with `docker-compose` and prepare Helm charts for Kubernetes deployment.

## Execution Plan
We are starting with **Phase 1: Architecture Overhaul (The Foundation)** to decouple the frontend from the core logic, establishing a robust API-first backend.
