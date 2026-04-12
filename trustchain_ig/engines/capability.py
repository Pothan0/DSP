import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from config import get_config


class CapabilityToken:
    """HMAC-signed capability token."""
    
    def __init__(
        self,
        agent_id: str,
        tool_name: str,
        task_id: str,
        issued_at: datetime,
        expires_at: datetime,
        max_calls: Optional[int] = None,
        signature: str = None
    ):
        self.agent_id = agent_id
        self.tool_name = tool_name
        self.task_id = task_id
        self.issued_at = issued_at
        self.expires_at = expires_at
        self.max_calls = max_calls
        self.signature = signature
    
    def is_valid(self) -> bool:
        """Check if token is still valid."""
        if datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def to_payload(self) -> Dict[str, Any]:
        """Get token payload for serialization."""
        return {
            "agent_id": self.agent_id,
            "tool_name": self.tool_name,
            "task_id": self.task_id,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "max_calls": self.max_calls
        }
    
    @classmethod
    def from_payload(cls, payload: Dict[str, Any], signature: str) -> "CapabilityToken":
        """Create token from deserialized payload."""
        return cls(
            agent_id=payload["agent_id"],
            tool_name=payload["tool_name"],
            task_id=payload["task_id"],
            issued_at=datetime.fromisoformat(payload["issued_at"]),
            expires_at=datetime.fromisoformat(payload["expires_at"]),
            max_calls=payload.get("max_calls"),
            signature=signature
        )


class CapabilityGate:
    """
    Zero-Trust Tool Authorization with HMAC-signed capability tokens.
    No database lookup needed - just verify signature and check claims.
    """
    
    def __init__(self, secret_key: str = "trustchain-secret-key-change-in-production"):
        self._secret = secret_key.encode()
        self._config = get_config()
        self._call_counts: Dict[str, int] = {}
    
    def _make_key(self, agent_id: str, tool_name: str, task_id: str) -> str:
        return f"{agent_id}:{tool_name}:{task_id}"
    
    def _sign(self, payload: Dict[str, Any]) -> str:
        """Generate HMAC signature for payload."""
        payload_str = json.dumps(payload, sort_keys=True)
        return hmac.new(self._secret, payload_str.encode(), hashlib.sha256).hexdigest()
    
    def _verify(self, payload: Dict[str, Any], signature: str) -> bool:
        """Verify HMAC signature."""
        expected = self._sign(payload)
        return hmac.compare_digest(expected, signature)
    
    def issue_token(
        self,
        agent_id: str,
        tool_name: str,
        task_id: str,
        max_calls: Optional[int] = None
    ) -> CapabilityToken:
        """Issue a new capability token."""
        tool_config = self._config.tools.get(tool_name)
        if tool_config and tool_config.max_calls:
            max_calls = tool_config.max_calls
        
        ttl = 600
        now = datetime.utcnow()
        
        token = CapabilityToken(
            agent_id=agent_id,
            tool_name=tool_name,
            task_id=task_id,
            issued_at=now,
            expires_at=now + timedelta(seconds=ttl),
            max_calls=max_calls
        )
        
        token.signature = self._sign(token.to_payload())
        
        return token
    
    def validate(
        self,
        agent_id: str,
        tool_name: str,
        task_id: str,
        token_payload: Dict[str, Any],
        token_signature: str
    ) -> Dict[str, Any]:
        """
        Validate a token and return authorization result.
        No DB lookup - just verify HMAC and check claims.
        """
        if not self._verify(token_payload, token_signature):
            return {
                "authorized": False,
                "reason": "INVALID_SIGNATURE",
                "tool": tool_name
            }
        
        token = CapabilityToken.from_payload(token_payload, token_signature)
        
        if not token.is_valid():
            return {
                "authorized": False,
                "reason": "TOKEN_EXPIRED",
                "tool": tool_name
            }
        
        if token.agent_id != agent_id:
            return {
                "authorized": False,
                "reason": "AGENT_MISMATCH",
                "tool": tool_name
            }
        
        if token.tool_name != tool_name:
            return {
                "authorized": False,
                "reason": "TOOL_MISMATCH",
                "tool": tool_name
            }
        
        tool_config = self._config.tools.get(tool_name)
        tier = tool_config.tier if tool_config else "medium"
        
        if tier == "critical":
            return {
                "authorized": False,
                "reason": "REQUIRES_HITL",
                "tool": tool_name,
                "tier": tier
            }
        
        if tier in ("high", "medium"):
            if token.task_id != task_id:
                return {
                    "authorized": False,
                    "reason": "TASK_MISMATCH",
                    "tool": tool_name
                }
            
            call_key = self._make_key(agent_id, tool_name, task_id)
            current_calls = self._call_counts.get(call_key, 0)
            
            if token.max_calls and current_calls >= token.max_calls:
                return {
                    "authorized": False,
                    "reason": "MAX_CALLS_EXCEEDED",
                    "tool": tool_name
                }
            
            self._call_counts[call_key] = current_calls + 1
        
        return {
            "authorized": True,
            "reason": "OK",
            "tool": tool_name,
            "tier": tier
        }
    
    def check_tool_tier(self, tool_name: str) -> str:
        """Get the risk tier for a tool."""
        tool_config = self._config.tools.get(tool_name)
        return tool_config.tier if tool_config else "medium"


_capability_gate: Optional[CapabilityGate] = None


def get_capability_gate(secret_key: str = None) -> CapabilityGate:
    """Get or create the global capability gate."""
    global _capability_gate
    if _capability_gate is None:
        _capability_gate = CapabilityGate(secret_key or "trustchain-secret-key-change-in-production")
    return _capability_gate