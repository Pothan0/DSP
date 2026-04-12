import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from config import get_config


class HITLDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


@dataclass
class HITLRequest:
    """Represents a human-in-the-loop review request."""
    request_id: str
    session_id: str
    tool_name: str
    arguments: Dict[str, Any]
    trust_score: float
    flags: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    decision: HITLDecision = HITLDecision.PENDING
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None


class HITLGate:
    """
    Human-in-the-Loop escalation system.
    Holds agent connection open while waiting for human approval.
    """
    
    def __init__(self):
        self._config = get_config()
        self._pending: Dict[str, HITLRequest] = {}
        self._history: List[HITLRequest] = []
        self._waiting: Dict[str, asyncio.Future] = {}
    
    def create_request(
        self,
        session_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        trust_score: float,
        flags: List[str]
    ) -> HITLRequest:
        """Create a new HITL request."""
        request = HITLRequest(
            request_id=f"hitl_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            tool_name=tool_name,
            arguments=arguments,
            trust_score=trust_score,
            flags=flags
        )
        
        self._pending[request.request_id] = request
        
        if self._config.hitl.enabled and self._config.hitl.timeout_seconds > 0:
            asyncio.create_task(self._timeout_request(request.request_id))
        
        return request
    
    async def _timeout_request(self, request_id: str):
        """Auto-expire requests after timeout."""
        await asyncio.sleep(self._config.hitl.timeout_seconds)
        
        if request_id in self._pending:
            request = self._pending[request_id]
            if request.decision == HITLDecision.PENDING:
                if self._config.hitl.timeout_policy == "auto_reject":
                    await self.reject(request_id, "system")
                else:
                    await self.approve(request_id, "system")
    
    async def approve(self, request_id: str, decided_by: str = "human") -> bool:
        """Approve a pending request."""
        if request_id not in self._pending:
            return False
        
        request = self._pending[request_id]
        request.decision = HITLDecision.APPROVED
        request.decided_at = datetime.utcnow()
        request.decided_by = decided_by
        
        self._history.append(request)
        del self._pending[request_id]
        
        if request_id in self._waiting:
            self._waiting[request_id].set_result(True)
            del self._waiting[request_id]
        
        return True
    
    async def reject(self, request_id: str, decided_by: str = "human") -> bool:
        """Reject a pending request."""
        if request_id not in self._pending:
            return False
        
        request = self._pending[request_id]
        request.decision = HITLDecision.REJECTED
        request.decided_at = datetime.utcnow()
        request.decided_by = decided_by
        
        self._history.append(request)
        del self._pending[request_id]
        
        if request_id in self._waiting:
            self._waiting[request_id].set_result(False)
            del self._waiting[request_id]
        
        return True
    
    async def wait_for_decision(self, request_id: str, timeout: int = None) -> bool:
        """Wait for human decision (or timeout)."""
        if request_id not in self._pending:
            request = next((r for r in self._history if r.request_id == request_id), None)
            if request:
                return request.decision == HITLDecision.APPROVED
            return False
        
        timeout = timeout or self._config.hitl.timeout_seconds
        
        future = asyncio.Future()
        self._waiting[request_id] = future
        
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            if request_id in self._pending:
                if self._config.hitl.timeout_policy == "auto_reject":
                    await self.reject(request_id, "timeout")
                else:
                    await self.approve(request_id, "timeout")
            return False
    
    def get_pending(self) -> List[HITLRequest]:
        """Get all pending requests."""
        return list(self._pending.values())
    
    def get_request(self, request_id: str) -> Optional[HITLRequest]:
        """Get a specific request."""
        if request_id in self._pending:
            return self._pending[request_id]
        return next((r for r in self._history if r.request_id == request_id), None)
    
    def get_history(self, limit: int = 50) -> List[HITLRequest]:
        """Get request history."""
        return self._history[-limit:]


_hitl_gate: Optional[HITLGate] = None


def get_hitl_gate() -> HITLGate:
    """Get or create the global HITL gate."""
    global _hitl_gate
    if _hitl_gate is None:
        _hitl_gate = HITLGate()
    return _hitl_gate