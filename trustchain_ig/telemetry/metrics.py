from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import FastAPI
from typing import Dict

trustchain_calls_total = Counter(
    "trustchain_calls_total",
    "Total number of tool calls processed",
    ["decision"]
)

trustchain_trust_score = Gauge(
    "trustchain_trust_score",
    "Current trust score for sessions",
    ["session_id"]
)

trustchain_injection_detections = Counter(
    "trustchain_injection_detections_total",
    "Total number of injection detections",
    ["method", "flag"]
)

trustchain_hitl_pending = Gauge(
    "trustchain_hitl_pending_count",
    "Number of pending HITL requests"
)

trustchain_proxy_latency = Histogram(
    "trustchain_proxy_latency_seconds",
    "Proxy latency for tool calls",
    ["tool", "decision"]
)

trustchain_sessions_active = Gauge(
    "trustchain_sessions_active",
    "Number of active sessions"
)

trustchain_audit_records = Counter(
    "trustchain_audit_records_total",
    "Total number of audit records written",
    ["event_type"]
)


def setup_metrics(app: FastAPI):
    """Set up Prometheus metrics endpoint."""
    
    @app.get("/metrics")
    async def metrics():
        """Expose Prometheus metrics."""
        return Response(
            content=generate_latest(),
            media_type="text/plain"
        )


def record_call(decision: str):
    """Record a tool call in metrics."""
    trustchain_calls_total.labels(decision=decision).inc()


def record_injection(method: str, flag: str):
    """Record an injection detection."""
    trustchain_injection_detections.labels(method=method, flag=flag).inc()


def record_hitl_pending(count: int):
    """Record pending HITL count."""
    trustchain_hitl_pending.set(count)


def record_latency(tool: str, decision: str, latency_seconds: float):
    """Record proxy latency."""
    trustchain_proxy_latency.labels(tool=tool, decision=decision).observe(latency_seconds)


def update_session_score(session_id: str, score: float):
    """Update session trust score."""
    trustchain_trust_score.labels(session_id=session_id).set(score)


def update_active_sessions(count: int):
    """Update active session count."""
    trustchain_sessions_active.set(count)


def record_audit_event(event_type: str):
    """Record an audit event."""
    trustchain_audit_records.labels(event_type=event_type).inc()