from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from schemas import ChatRequest, ChatResponse, ThreatScoreResponse, AnalyticsResponse, RedTeamFullResponse
import person1_agent
from person1_agent import CustomerServiceAgent
from person2_security import SecurityGuard
from person3_scorer import ThreatScorer
import audit_logger
import database
import json

app = FastAPI(
    title="NovaSentinel Agent API",
    description="Enterprise-grade Security Gateway for AI Agents",
    version="2.0.0"
)

# CORS middleware for potential frontend decoupling
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize global dependencies
guard = SecurityGuard()
person1_agent.security_guard = guard

scorer = ThreatScorer(threshold=0.75)
try:
    agent = CustomerServiceAgent()
    AGENT_ONLINE = True
except Exception as e:
    agent = None
    AGENT_ONLINE = False
    print(f"Warning: Agent failed to start: {e}")

@app.on_event("startup")
def startup_event():
    """Ensure database and logs are initialized on boot."""
    database.init_db()
    audit_logger.init_log_table()

@app.get("/health")
def health_check():
    chain_ok = audit_logger.verify_chain()
    return {
        "status": "online", 
        "agent_status": "online" if AGENT_ONLINE else "offline",
        "audit_chain_valid": chain_ok
    }

@app.post("/api/v1/chat", response_model=ChatResponse)
def process_chat(request: ChatRequest):
    if not AGENT_ONLINE:
        raise HTTPException(status_code=503, detail="Agent engine offline")

    user_input = request.query
    
    # Convert Pydantic UserContext to dict for the agent
    user_context_dict = request.user_context.dict() if request.user_context else None

    # LAYER 1: Input Threat Scanning
    score_data = scorer.score_prompt(user_input)
    is_threat = score_data["is_malicious"]
    
    threat_assessment = ThreatScoreResponse(
        threat_score=score_data["threat_score"],
        is_malicious=is_threat,
        semantic_score=score_data["semantic_score"],
        pattern_detected=score_data["pattern_detected"],
        category=score_data.get("category", "Unknown"),
        patterns=score_data.get("patterns", []),
        detected_categories=score_data.get("detected_categories", {})
    )

    if is_threat:
        # Block the request
        audit_logger.log_event("THREAT_BLOCKED", score_data)
        return ChatResponse(
            safe_response=f"**Security Breach Blocked.**\nThreat Score: {score_data['threat_score']:.2f}\nCategory: {score_data.get('category', 'Unknown')}",
            input_threat_assessment=threat_assessment,
            pii_scrubbed_input=False,
            pii_scrubbed_output=False,
            blocked=True,
            block_reason=score_data.get("category", "Malicious Intent Detected")
        )

    # LAYER 2: PII Scrubbing (Input)
    safe_input = guard.scrub_pii(user_input)
    pii_scrubbed_input = (safe_input != user_input)

    # LAYER 3: Core Agent Execution
    try:
        raw_response = agent.respond(safe_input, user_context=user_context_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent Execution Error: {str(e)}")

    # LAYER 4: PII Scrubbing (Output)
    safe_response = guard.scrub_pii(raw_response)
    pii_scrubbed_output = (safe_response != raw_response)

    # Final Logging
    audit_logger.log_event("AGENT_INTERACTION", {
        "query": safe_input,
        "threat_score": score_data["threat_score"],
        "pii_detected_input": pii_scrubbed_input,
        "pii_detected_output": pii_scrubbed_output,
        "user_id": user_context_dict.get("user_id") if user_context_dict else "anonymous"
    })

    return ChatResponse(
        safe_response=safe_response,
        input_threat_assessment=threat_assessment,
        pii_scrubbed_input=pii_scrubbed_input,
        pii_scrubbed_output=pii_scrubbed_output,
        blocked=False
    )

@app.get("/api/v1/analytics", response_model=AnalyticsResponse)
def get_analytics():
    """Fetch dashboard analytics."""
    data = audit_logger.get_analytics_summary()
    return AnalyticsResponse(**data)

@app.get("/api/v1/logs")
def get_logs(limit: int = 5):
    """Fetch recent audit logs."""
    return audit_logger.fetch_all_logs(limit=limit)

@app.get("/api/v1/logs/verify")
def verify_logs():
    """Verify integrity of the audit chain."""
    return {"chain_valid": audit_logger.verify_chain()}

@app.post("/api/v1/tools/red_team")
def test_scorer(request: ChatRequest):
    """Exposed endpoint for the Red Team sandbox to test prompts directly."""
    return scorer.score_prompt(request.query)

@app.post("/api/v1/tools/red_team_full", response_model=RedTeamFullResponse)
def test_full_pipeline(request: ChatRequest):
    """
    Full-pipeline red team test: runs a prompt through all 4 security layers
    and returns per-layer analysis results.
    """
    user_input = request.query
    user_context_dict = request.user_context.dict() if request.user_context else {
        "user_id": 1, "name": "Alice Smith", "role": "patient"
    }

    layers = {}
    blocked_at = None

    # LAYER 1: Threat Scoring
    score_data = scorer.score_prompt(user_input)
    layers["threat_scoring"] = {
        "threat_score": score_data["threat_score"],
        "is_malicious": score_data["is_malicious"],
        "semantic_score": score_data["semantic_score"],
        "pattern_detected": score_data["pattern_detected"],
        "category": score_data.get("category", "Unknown"),
        "patterns_matched": len(score_data.get("patterns", [])),
        "detected_categories": score_data.get("detected_categories", {}),
        "status": "BLOCKED" if score_data["is_malicious"] else "PASSED"
    }

    if score_data["is_malicious"]:
        blocked_at = "Layer 1: Threat Scoring"
        return RedTeamFullResponse(
            query=user_input,
            layers=layers,
            final_verdict="BLOCKED",
            blocked_at_layer=blocked_at,
            response_text=f"Blocked by threat scorer. Category: {score_data.get('category', 'Unknown')}"
        )

    # LAYER 2: PII Scrubbing (Input)
    safe_input = guard.scrub_pii(user_input)
    pii_scrubbed = safe_input != user_input
    layers["pii_input_scrub"] = {
        "pii_detected": pii_scrubbed,
        "original_length": len(user_input),
        "scrubbed_length": len(safe_input),
        "status": "SCRUBBED" if pii_scrubbed else "CLEAN"
    }

    # LAYER 3: Agent Execution (with RBAC)
    if AGENT_ONLINE:
        try:
            raw_response = agent.respond(safe_input, user_context=user_context_dict)
            agent_blocked = "Access Denied" in raw_response
            layers["agent_execution"] = {
                "executed": True,
                "rbac_blocked": agent_blocked,
                "response_preview": raw_response[:200],
                "status": "RBAC_BLOCKED" if agent_blocked else "EXECUTED"
            }
            if agent_blocked:
                blocked_at = "Layer 3: RBAC Authorization"
        except Exception as e:
            raw_response = f"Agent error: {str(e)}"
            layers["agent_execution"] = {
                "executed": False,
                "error": str(e),
                "status": "ERROR"
            }
    else:
        raw_response = "Agent offline"
        layers["agent_execution"] = {
            "executed": False,
            "error": "Agent offline",
            "status": "OFFLINE"
        }

    # LAYER 4: PII Scrubbing (Output)
    safe_response = guard.scrub_pii(raw_response)
    output_scrubbed = safe_response != raw_response
    layers["pii_output_scrub"] = {
        "pii_detected": output_scrubbed,
        "status": "SCRUBBED" if output_scrubbed else "CLEAN"
    }

    final_verdict = "BLOCKED" if blocked_at else "PASSED"

    return RedTeamFullResponse(
        query=user_input,
        layers=layers,
        final_verdict=final_verdict,
        blocked_at_layer=blocked_at,
        response_text=safe_response[:300] if not blocked_at else None
    )
