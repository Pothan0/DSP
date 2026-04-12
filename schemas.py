from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class UserContext(BaseModel):
    user_id: int
    name: str
    role: str = "customer" # "customer" or "admin"

class ChatRequest(BaseModel):
    query: str = Field(..., description="The user's query to the banking agent")
    user_context: Optional[UserContext] = Field(None, description="Injected context identifying the authenticated user")

class ThreatScoreResponse(BaseModel):
    threat_score: float
    is_malicious: bool
    semantic_score: float
    pattern_detected: bool
    category: str
    patterns: List[str]

class ChatResponse(BaseModel):
    safe_response: str
    original_response: Optional[str] = None
    input_threat_assessment: ThreatScoreResponse
    pii_scrubbed_input: bool
    pii_scrubbed_output: bool
    blocked: bool = False
    block_reason: Optional[str] = None

class LogEntry(BaseModel):
    id: int
    timestamp: str
    event_type: str
    details: str
    hash: str

class AnalyticsResponse(BaseModel):
    event_counts: Dict[str, int]
    threat_history: List[Dict[str, Any]]
    pii_detected_sessions: int
    pii_counts: Dict[str, int]
