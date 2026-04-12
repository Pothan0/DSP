from datetime import datetime, timedelta
from typing import Optional, Dict
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from interceptor.envelope import MessageEnvelope


class CapabilityToken:
    """Represents a capability token issued to an agent."""
    
    def __init__(
        self,
        agent_id: str,
        tool_name: str,
        task_id: str,
        issued_at: datetime,
        ttl: int = None
    ):
        self.agent_id = agent_id
        self.tool_name = tool_name
        self.task_id = task_id
        self.issued_at = issued_at
        self.ttl = ttl or config.CAPABILITY_TOKEN_TTL
    
    def is_valid(self) -> bool:
        """Check if token is still valid (not expired)."""
        elapsed = (datetime.utcnow() - self.issued_at).total_seconds()
        return elapsed < self.ttl
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "tool_name": self.tool_name,
            "task_id": self.task_id,
            "issued_at": self.issued_at.isoformat(),
            "ttl": self.ttl,
            "valid": self.is_valid()
        }


class CapabilityGate:
    """
    Engine C: Capability Token Gate
    Validates that agents have proper tokens before executing actions.
    """
    
    def __init__(self):
        self._tokens: Dict[str, CapabilityToken] = {}
    
    def issue_token(
        self,
        agent_id: str,
        tool_name: str,
        task_id: str,
        ttl: int = None
    ) -> CapabilityToken:
        """Issue a new capability token to an agent."""
        token = CapabilityToken(
            agent_id=agent_id,
            tool_name=tool_name,
            task_id=task_id,
            issued_at=datetime.utcnow(),
            ttl=ttl
        )
        
        key = self._make_key(agent_id, tool_name, task_id)
        self._tokens[key] = token
        return token
    
    def validate(
        self,
        agent_id: str,
        tool_name: str,
        task_id: str
    ) -> bool:
        """Validate that a valid token exists for the agent/tool/task combination."""
        key = self._make_key(agent_id, tool_name, task_id)
        
        if key not in self._tokens:
            return False
        
        token = self._tokens[key]
        return token.is_valid()
    
    def revoke_token(
        self,
        agent_id: str,
        tool_name: str,
        task_id: str
    ) -> bool:
        """Revoke a token (e.g., after task completion)."""
        key = self._make_key(agent_id, tool_name, task_id)
        if key in self._tokens:
            del self._tokens[key]
            return True
        return False
    
    def revoke_all_task_tokens(self, task_id: str):
        """Revoke all tokens associated with a task."""
        keys_to_remove = [
            k for k, v in self._tokens.items()
            if v.task_id == task_id
        ]
        for key in keys_to_remove:
            del self._tokens[key]
    
    def get_tokens_for_agent(self, agent_id: str) -> list:
        """Get all valid tokens for an agent."""
        return [
            t.to_dict() for t in self._tokens.values()
            if t.agent_id == agent_id and t.is_valid()
        ]
    
    def _make_key(self, agent_id: str, tool_name: str, task_id: str) -> str:
        """Generate unique key for token lookup."""
        return f"{agent_id}:{tool_name}:{task_id}"
    
    def process(self, envelope: MessageEnvelope) -> dict:
        """
        Process a message through the capability gate.
        Checks if the sender has valid tokens for any tool actions in the message.
        """
        sender = envelope.trust_meta["sender_id"]
        content = envelope.original.get("content", {})
        
        result = {"valid": True, "reason": "OK", "required_tokens": []}
        
        if isinstance(content, dict):
            action = content.get("action", "")
            
            if action in ["call_tool", "execute"]:
                tool_name = content.get("params", {}).get("tool", "unknown")
                if not tool_name:
                    tool_name = content.get("params", {}).get("type", "unknown")
                
                task_id = envelope.original.get("task_id", "")
                
                if not self.validate(sender, tool_name, task_id):
                    result = {
                        "valid": False,
                        "reason": f"No valid token for {tool_name}",
                        "required_tokens": [tool_name]
                    }
        
        return result
    
    async def process_async(self, envelope: MessageEnvelope) -> dict:
        """Async wrapper for process."""
        return self.process(envelope)


# Global capability gate instance
_gate: Optional[CapabilityGate] = None


def get_capability_gate() -> CapabilityGate:
    """Get or create the global capability gate instance."""
    global _gate
    if _gate is None:
        _gate = CapabilityGate()
    return _gate


def init_capability_gate() -> CapabilityGate:
    """Initialize and return the capability gate."""
    global _gate
    _gate = CapabilityGate()
    return _gate