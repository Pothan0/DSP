import json
import os
import re
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

import audit_logger
import database
import person1_agent
from person1_agent import CustomerServiceAgent
from person2_security import SecurityGuard
from person3_scorer import ThreatScorer
from schemas import AnalyticsResponse, ChatRequest, ChatResponse, RedTeamFullResponse, ThreatScoreResponse


APP_ENV = os.getenv("APP_ENV", "dev").lower()
ALLOW_DEV_IDENTITY_OVERRIDE = os.getenv("ALLOW_DEV_IDENTITY_OVERRIDE", "true").lower() == "true"
ENFORCE_AUTH = os.getenv("ENFORCE_AUTH", "false").lower() == "true"

DEFAULT_ALLOWED_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
if APP_ENV == "prod":
    DEFAULT_ALLOWED_ORIGINS = ""
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS).split(",") if o.strip()]

API_BEARER_TOKEN = os.getenv("API_BEARER_TOKEN")
if (APP_ENV == "prod" or ENFORCE_AUTH) and not API_BEARER_TOKEN:
    raise RuntimeError("API_BEARER_TOKEN must be set when APP_ENV=prod")

STRICT_AUTH = APP_ENV == "prod" or ENFORCE_AUTH or bool(API_BEARER_TOKEN)

RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "120"))

ADMIN_ROLES = {"admin", "security_admin"}
RED_TEAM_ROLES = {"admin", "security_admin", "red_team"}


class SimpleRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        bucket = self._buckets[key]
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True


app = FastAPI(
    title="NovaSentinel Agent API",
    description="Enterprise-grade Security Gateway for AI Agents",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-User-Id", "X-User-Name", "X-User-Role"],
)

guard = SecurityGuard()
person1_agent.security_guard = guard

scorer = ThreatScorer(threshold=0.75)
rate_limiter = SimpleRateLimiter(RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)

try:
    agent = CustomerServiceAgent()
    AGENT_ONLINE = True
except Exception as e:
    agent = None
    AGENT_ONLINE = False
    print(f"Warning: Agent failed to start: {e}")


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _extract_identity(request: Request):
    if STRICT_AUTH:
        auth = request.headers.get("authorization", "")
        expected = f"Bearer {API_BEARER_TOKEN}"
        if auth != expected:
            raise HTTPException(status_code=401, detail="Unauthorized")

    user_id = request.headers.get("x-user-id")
    user_name = request.headers.get("x-user-name")
    user_role = request.headers.get("x-user-role", "patient")

    if user_id and user_name:
        try:
            uid = int(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid X-User-Id header")
        return {"user_id": uid, "name": user_name, "role": user_role}

    return {"user_id": 0, "name": "anonymous", "role": "anonymous"}


def _resolve_user_context(request: Request, chat_request: ChatRequest):
    identity = _extract_identity(request)
    request_ctx = chat_request.user_context.dict() if chat_request.user_context else None

    if APP_ENV != "prod" and ALLOW_DEV_IDENTITY_OVERRIDE and request_ctx is not None:
        return request_ctx

    return identity


def _require_admin(identity):
    if not STRICT_AUTH and APP_ENV != "prod":
        return
    if identity.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden: admin role required")


def _require_red_team(identity):
    if not STRICT_AUTH and APP_ENV != "prod":
        return
    if identity.get("role") not in RED_TEAM_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden: red-team role required")


def _enforce_rate_limit(request: Request):
    key = _get_client_ip(request)
    if not rate_limiter.allow(key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


def _sanitize_agent_text(text: str) -> str:
    if not text:
        return text

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    filtered = []
    for line in lines:
        lower = line.lower()
        if lower.startswith("the user asked:"):
            continue
        if lower.startswith("i should"):
            continue
        if lower.startswith("so answer:"):
            continue
        filtered.append(line)

    if not filtered:
        filtered = [text.strip()]

    joined = " ".join(filtered)
    joined = re.sub(r"<(PERSON|EMAIL_ADDRESS|US_SSN|INTERNAL_RECORD_ID)_[0-9a-f]{8}>", "[REDACTED]", joined)
    joined = re.sub(r"\s+", " ", joined).strip()
    return joined


@app.on_event("startup")
def startup_event():
    database.init_db()
    audit_logger.init_log_table()


@app.get("/health")
def health_check(request: Request):
    _enforce_rate_limit(request)
    chain_ok = audit_logger.verify_chain()
    return {
        "status": "online",
        "agent_status": "online" if AGENT_ONLINE else "offline",
        "audit_chain_valid": chain_ok,
        "env": APP_ENV,
    }


@app.post("/api/v1/chat", response_model=ChatResponse)
def process_chat(request: Request, chat_request: ChatRequest):
    _enforce_rate_limit(request)
    if not AGENT_ONLINE:
        raise HTTPException(status_code=503, detail="Agent engine offline")

    user_input = chat_request.query
    user_context_dict = _resolve_user_context(request, chat_request)

    score_data = scorer.score_prompt(user_input)
    is_threat = score_data["is_malicious"]

    threat_assessment = ThreatScoreResponse(
        threat_score=score_data["threat_score"],
        is_malicious=is_threat,
        semantic_score=score_data["semantic_score"],
        pattern_detected=score_data["pattern_detected"],
        category=score_data.get("category", "Unknown"),
        patterns=score_data.get("patterns", []),
        detected_categories=score_data.get("detected_categories", {}),
    )

    if is_threat:
        audit_logger.log_event("THREAT_BLOCKED", {
            "category": score_data.get("category", "Unknown"),
            "threat_score": score_data["threat_score"],
            "semantic_score": score_data["semantic_score"],
            "pattern_detected": score_data["pattern_detected"],
            "detected_categories": score_data.get("detected_categories", {}),
            "user_id": user_context_dict.get("user_id", 0),
            "query_preview": user_input[:120],
        })
        return ChatResponse(
            safe_response=(
                "**Security Breach Blocked.**\n"
                f"Threat Score: {score_data['threat_score']:.2f}\n"
                f"Category: {score_data.get('category', 'Unknown')}"
            ),
            input_threat_assessment=threat_assessment,
            pii_scrubbed_input=False,
            pii_scrubbed_output=False,
            blocked=True,
            block_reason=score_data.get("category", "Malicious Intent Detected"),
        )

    safe_input, input_pii_meta = guard.scrub_input_pii_with_meta(user_input)
    pii_scrubbed_input = safe_input != user_input

    try:
        raw_response = agent.respond(safe_input, user_context=user_context_dict)
    except Exception:
        raise HTTPException(status_code=500, detail="Agent execution failed")

    rbac_blocked = "Access Denied" in raw_response

    if rbac_blocked:
        safe_response = (
            "Access blocked due to RBAC policy. "
            "You are not authorized to access records for another user."
        )
        output_pii_meta = {"pii_detected": False, "entity_counts": {}}
        pii_scrubbed_output = False
    else:
        safe_response, output_pii_meta = guard.scrub_output_pii_with_meta(raw_response)
        safe_response = _sanitize_agent_text(safe_response)
        pii_scrubbed_output = safe_response != raw_response

    audit_logger.log_event("AGENT_INTERACTION", {
        "query": safe_input,
        "threat_score": score_data["threat_score"],
        "category": score_data.get("category", "Clean"),
        "rbac_blocked": rbac_blocked,
        "pii_detected_input": input_pii_meta.get("pii_detected", False),
        "pii_detected_output": output_pii_meta.get("pii_detected", False),
        "pii_counts_input": input_pii_meta.get("entity_counts", {}),
        "pii_counts_output": output_pii_meta.get("entity_counts", {}),
        "user_id": user_context_dict.get("user_id", 0),
    })

    return ChatResponse(
        safe_response=safe_response,
        input_threat_assessment=threat_assessment,
        pii_scrubbed_input=pii_scrubbed_input,
        pii_scrubbed_output=pii_scrubbed_output,
        blocked=rbac_blocked,
        block_reason="Blocked due to RBAC policy" if rbac_blocked else None,
    )


@app.get("/api/v1/analytics", response_model=AnalyticsResponse)
def get_analytics(request: Request):
    _enforce_rate_limit(request)
    identity = _extract_identity(request)
    _require_admin(identity)
    data = audit_logger.get_analytics_summary()
    return AnalyticsResponse(**data)


@app.get("/api/v1/logs")
def get_logs(request: Request, limit: int = 50):
    _enforce_rate_limit(request)
    identity = _extract_identity(request)
    _require_admin(identity)
    return audit_logger.fetch_all_logs(limit=limit)


@app.get("/api/v1/logs/verify")
def verify_logs(request: Request):
    _enforce_rate_limit(request)
    identity = _extract_identity(request)
    _require_admin(identity)
    return {"chain_valid": audit_logger.verify_chain()}


@app.post("/api/v1/tools/red_team")
def test_scorer(request: Request, chat_request: ChatRequest):
    _enforce_rate_limit(request)
    identity = _extract_identity(request)
    _require_red_team(identity)
    return scorer.score_prompt(chat_request.query)


@app.post("/api/v1/tools/red_team_full", response_model=RedTeamFullResponse)
def test_full_pipeline(request: Request, chat_request: ChatRequest):
    _enforce_rate_limit(request)
    identity = _extract_identity(request)
    _require_red_team(identity)

    user_input = chat_request.query
    user_context_dict = _resolve_user_context(request, chat_request)

    layers = {}
    blocked_at = None

    score_data = scorer.score_prompt(user_input)
    layers["threat_scoring"] = {
        "threat_score": score_data["threat_score"],
        "is_malicious": score_data["is_malicious"],
        "semantic_score": score_data["semantic_score"],
        "pattern_detected": score_data["pattern_detected"],
        "category": score_data.get("category", "Unknown"),
        "patterns_matched": len(score_data.get("patterns", [])),
        "detected_categories": score_data.get("detected_categories", {}),
        "status": "BLOCKED" if score_data["is_malicious"] else "PASSED",
    }

    if score_data["is_malicious"]:
        blocked_at = "Layer 1: Threat Scoring"
        return RedTeamFullResponse(
            query=user_input,
            layers=layers,
            final_verdict="BLOCKED",
            blocked_at_layer=blocked_at,
            response_text=f"Blocked by threat scorer. Category: {score_data.get('category', 'Unknown')}",
        )

    safe_input, input_pii_meta = guard.scrub_input_pii_with_meta(user_input)
    layers["pii_input_scrub"] = {
        "pii_detected": input_pii_meta.get("pii_detected", False),
        "entity_counts": input_pii_meta.get("entity_counts", {}),
        "original_length": len(user_input),
        "scrubbed_length": len(safe_input),
        "status": "SCRUBBED" if input_pii_meta.get("pii_detected", False) else "CLEAN",
    }

    if AGENT_ONLINE:
        try:
            raw_response = agent.respond(safe_input, user_context=user_context_dict)
            agent_blocked = "Access Denied" in raw_response
            layers["agent_execution"] = {
                "executed": True,
                "rbac_blocked": agent_blocked,
                "response_preview": raw_response[:200],
                "status": "RBAC_BLOCKED" if agent_blocked else "EXECUTED",
            }
            if agent_blocked:
                blocked_at = "Layer 3: RBAC Authorization"
        except Exception:
            raw_response = "Agent execution failed"
            layers["agent_execution"] = {
                "executed": False,
                "error": "Agent execution failed",
                "status": "ERROR",
            }
    else:
        raw_response = "Agent offline"
        layers["agent_execution"] = {
            "executed": False,
            "error": "Agent offline",
            "status": "OFFLINE",
        }

    safe_response, output_pii_meta = guard.scrub_output_pii_with_meta(raw_response)
    layers["pii_output_scrub"] = {
        "pii_detected": output_pii_meta.get("pii_detected", False),
        "entity_counts": output_pii_meta.get("entity_counts", {}),
        "status": "SCRUBBED" if output_pii_meta.get("pii_detected", False) else "CLEAN",
    }

    final_verdict = "BLOCKED" if blocked_at else "PASSED"
    return RedTeamFullResponse(
        query=user_input,
        layers=layers,
        final_verdict=final_verdict,
        blocked_at_layer=blocked_at,
        response_text=safe_response[:300] if not blocked_at else None,
    )
