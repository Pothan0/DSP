from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode
from typing import Dict, Any, Optional

from config import get_config


_tracer: Optional[trace.Tracer] = None


def setup_otel(service_name: str = "trustchain-gateway") -> trace.Tracer:
    """Initialize OpenTelemetry tracing."""
    global _tracer
    
    config = get_config()
    
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0"
    })
    
    provider = TracerProvider(resource=resource)
    
    if config.telemetry.otel_enabled and config.telemetry.otel_endpoint:
        exporter = OTLPSpanExporter(
            endpoint=config.telemetry.otel_endpoint,
            insecure=True
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(__name__)
    
    return _tracer


def get_tracer() -> trace.Tracer:
    """Get the global tracer."""
    global _tracer
    if _tracer is None:
        _tracer = setup_otel()
    return _tracer


def trace_tool_call(
    session_id: str,
    tool_name: str,
    decision: str,
    trust_score: float,
    flags: list,
    framework: str = "unknown"
):
    """Create a trace span for a tool call."""
    tracer = get_tracer()
    
    with tracer.start_as_current_span(f"mcp.tools.call.{tool_name}") as span:
        span.set_attribute("trustchain.session_id", session_id)
        span.set_attribute("trustchain.trust_score", trust_score)
        span.set_attribute("trustchain.decision", decision)
        span.set_attribute("trustchain.flags", ",".join(flags))
        span.set_attribute("mcp.tool_name", tool_name)
        span.set_attribute("agent.framework", framework)
        
        if decision == "BLOCK":
            span.set_status(Status(StatusCode.ERROR, "Tool call blocked"))
        elif decision == "ESCALATE":
            span.set_status(Status(StatusCode.WARNING, "Escalated to human"))
        
        return span


def trace_security_check(
    check_name: str,
    result: bool,
    details: Dict[str, Any] = None
):
    """Create a trace span for a security check."""
    tracer = get_tracer()
    
    with tracer.start_as_current_span(f"security.{check_name}") as span:
        span.set_attribute(f"security.{check_name}.result", result)
        if details:
            for key, value in details.items():
                span.set_attribute(f"security.{check_name}.{key}", str(value))
        
        return span


class TrustChainSpanProcessor:
    """Custom span processor for adding TrustChain attributes."""
    
    def __init__(self):
        self._config = get_config()
    
    def on_end(self, span):
        """Add additional attributes before span ends."""
        pass
    
    def on_start(self, span):
        """Add additional attributes when span starts."""
        pass