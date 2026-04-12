import asyncio
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

from config import get_config


@dataclass
class Session:
    """Represents an agent session with trust state."""
    session_id: str
    agent_framework: str = "unknown"
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    trust_score: float = 1.0
    embeddings_history: List[np.ndarray] = field(default_factory=list)
    call_history: List[Dict] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    terminated: bool = False

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "agent_framework": self.agent_framework,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "trust_score": self.trust_score,
            "flags": self.flags,
            "terminated": self.terminated
        }


class SessionManager:
    """
    Manages agent sessions, trust scores, and embedding history.
    """
    
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._encoder = None
        self._config = get_config()
        
    def _get_encoder(self):
        """Lazy-load sentence encoder."""
        if self._encoder is None:
            self._encoder = SentenceTransformer(self._config.injection.embedding_model)
        return self._encoder
    
    def create_session(self, session_id: str = None, framework: str = "unknown") -> Session:
        """Create a new session."""
        if session_id is None:
            session_id = f"sess_{uuid.uuid4().hex[:12]}"
        
        session = Session(
            session_id=session_id,
            agent_framework=framework,
            trust_score=self._config.trust.initial_score
        )
        self._sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get an existing session."""
        return self._sessions.get(session_id)
    
    def get_or_create_session(self, session_id: str = None, framework: str = "unknown") -> Session:
        """Get existing session or create new one."""
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        return self.create_session(session_id, framework)
    
    def record_tool_call(
        self,
        session_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        flags: List[str],
        decision: str
    ):
        """Record a tool call and update trust score."""
        session = self.get_session(session_id)
        if not session:
            return
        
        session.last_activity = datetime.utcnow()
        
        arguments_str = json.dumps(arguments, sort_keys=True)
        args_hash = hashlib.sha256(arguments_str.encode()).hexdigest()[:16]
        
        call_record = {
            "tool": tool_name,
            "args_hash": args_hash,
            "flags": flags,
            "decision": decision,
            "timestamp": datetime.utcnow().isoformat()
        }
        session.call_history.append(call_record)
        
        if len(session.call_history) > 100:
            session.call_history = session.call_history[-100:]
        
        delta = self._config.trust.clean_call_delta
        
        if "SIGNATURE_MATCH" in flags:
            delta += self._config.trust.signature_match_delta
            session.flags.append("SIGNATURE_MATCH")
        
        if "EMBEDDING_DRIFT" in flags:
            delta += self._config.trust.embedding_drift_delta
            session.flags.append("EMBEDDING_DRIFT")
        
        if decision == "BLOCK":
            session.flags.append(f"BLOCKED_{tool_name}")
        
        embedding = self._get_encoder().encode([arguments_str])[0]
        session.embeddings_history.append(embedding)
        
        if len(session.embeddings_history) > self._config.injection.embedding_window_size:
            session.embeddings_history = session.embeddings_history[-self._config.injection.embedding_window_size:]
        
        session.trust_score = max(0.0, min(1.0, session.trust_score + delta))
        
        self._check_threshold(session)
    
    def hitl_approved(self, session_id: str):
        """Apply trust score change for HITL approval."""
        session = self.get_session(session_id)
        if session:
            session.trust_score = max(0.0, min(1.0, 
                session.trust_score + self._config.trust.hitl_approve_delta))
    
    def hitl_rejected(self, session_id: str):
        """Apply trust score change for HITL rejection."""
        session = self.get_session(session_id)
        if session:
            session.trust_score = max(0.0, min(1.0, 
                session.trust_score + self._config.trust.hitl_reject_delta))
            session.flags.append("HITL_REJECTED")
            self._check_threshold(session)
    
    def unauthorized_tool(self, session_id: str):
        """Apply trust score penalty for unauthorized tool attempt."""
        session = self.get_session(session_id)
        if session:
            session.trust_score = max(0.0, min(1.0, 
                session.trust_score + self._config.trust.unauthorized_tool_delta))
            session.flags.append("UNAUTHORIZED_TOOL")
            self._check_threshold(session)
    
    def _check_threshold(self, session: Session):
        """Check trust score thresholds."""
        if session.trust_score < self._config.trust.termination_threshold:
            session.terminated = True
            session.flags.append("SESSION_TERMINATED")
        elif session.trust_score < self._config.trust.decay_threshold:
            session.flags.append("AUTO_ESCALATE")
    
    def get_embedding_similarity(self, session_id: str, arguments: Dict[str, Any]) -> float:
        """Calculate similarity to session's embedding history."""
        session = self.get_session(session_id)
        if not session or not session.embeddings_history:
            return 1.0
        
        arguments_str = json.dumps(arguments, sort_keys=True)
        new_embedding = self._get_encoder().encode([arguments_str])[0]
        
        from sklearn.metrics.pairwise import cosine_similarity
        history_embeddings = np.array(session.embeddings_history)
        similarities = cosine_similarity(new_embedding.reshape(1, -1), history_embeddings)[0]
        
        return float(np.mean(similarities))
    
    def decay_all_sessions(self):
        """Apply natural decay to all active sessions."""
        for session in self._sessions.values():
            if not session.terminated:
                session.trust_score = max(
                    0.5,
                    session.trust_score - self._config.trust.decay_rate_per_minute
                )
    
    def get_active_sessions(self) -> List[Session]:
        """Get all active (non-terminated) sessions."""
        return [s for s in self._sessions.values() if not s.terminated]
    
    def terminate_session(self, session_id: str):
        """Terminate a session."""
        session = self.get_session(session_id)
        if session:
            session.terminated = True
            session.flags.append("SESSION_REVOKED")


_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create the global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager