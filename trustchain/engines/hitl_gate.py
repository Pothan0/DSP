import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass

import config
from interceptor.envelope import MessageEnvelope


@dataclass
class HITLRequest:
    """Represents a human-in-the-loop review request."""
    message_id: str
    task_id: str
    sender: str
    receiver: str
    content: Any
    risk_score: float
    reason: str
    created_at: datetime
    status: str = "pending"  # pending, approved, rejected


class HITLGate:
    """
    Engine D: Adaptive Human-in-the-Loop Gate
    Computes composite risk score and queues high-risk actions for human review.
    """
    
    def __init__(self):
        self.pending_reviews: Dict[str, HITLRequest] = {}
        self.approval_history: List[HITLRequest] = []
        self.pending_requests: Dict[str, asyncio.Event] = {}
        self.decisions: Dict[str, bool] = {}
    
    def _get_irreversibility_weight(self, content: dict) -> float:
        """Determine irreversibility weight based on action type."""
        if not isinstance(content, dict):
            return config.IRREVERSIBLE_WEIGHTS["default"]
        
        action = content.get("action", "")
        params = content.get("params", {})
        
        if action == "execute":
            action_type = params.get("type", "")
            if action_type in config.IRREVERSIBLE_WEIGHTS:
                return config.IRREVERSIBLE_WEIGHTS[action_type]
        
        if action in ["call_tool"]:
            tool = params.get("tool", "")
            if tool in ["send_email", "http_request"]:
                return config.IRREVERSIBLE_WEIGHTS["http_request"]
        
        return config.IRREVERSIBLE_WEIGHTS["default"]
    
    def compute_risk(
        self,
        trust_score: float,
        anomaly_confidence: float,
        content: dict
    ) -> float:
        """
        Compute composite risk score.
        risk = (1 - trust_score) * 0.4 + anomaly_confidence * 0.4 + irreversibility_weight * 0.2
        """
        irreversibility_weight = self._get_irreversibility_weight(content)
        
        risk = (
            (1 - trust_score) * 0.4 +
            anomaly_confidence * 0.4 +
            irreversibility_weight * 0.2
        )
        
        return min(1.0, max(0.0, risk))
    
    def process(self, envelope: MessageEnvelope) -> dict:
        """Process a message through the HITL gate."""
        content = envelope.original.get("content", {})
        
        trust_score = envelope.trust_score
        anomaly_confidence = 0.0
        if envelope.anomaly_flag:
            anomaly_confidence = 0.7
        
        risk_score = self.compute_risk(trust_score, anomaly_confidence, content)
        
        required = risk_score > config.HITL_RISK_THRESHOLD
        
        result = {
            "required": required,
            "risk_score": risk_score,
            "threshold": config.HITL_RISK_THRESHOLD,
            "irreversibility": self._get_irreversibility_weight(content),
            "factors": {
                "trust_component": (1 - trust_score) * 0.4,
                "anomaly_component": anomaly_confidence * 0.4,
                "irreversibility_component": self._get_irreversibility_weight(content) * 0.2
            }
        }
        
        if required:
            request = HITLRequest(
                message_id=envelope.message_id,
                task_id=envelope.original.get("task_id", ""),
                sender=envelope.trust_meta["sender_id"],
                receiver=envelope.trust_meta["receiver_id"],
                content=content,
                risk_score=risk_score,
                reason=f"Risk score {risk_score:.2f} exceeds threshold {config.HITL_RISK_THRESHOLD}",
                created_at=datetime.utcnow()
            )
            self.pending_reviews[envelope.message_id] = request
            result["review_id"] = envelope.message_id
        
        return result
    
    async def process_async(self, envelope: MessageEnvelope) -> dict:
        """Async wrapper for process."""
        result = self.process(envelope)
        
        if result.get("required") and "review_id" in result:
            review_id = result["review_id"]
            event = asyncio.Event()
            self.pending_requests[review_id] = event
            
            try:
                # Wait for the human to resolve the request (default 60s timeout for demo)
                await asyncio.wait_for(event.wait(), timeout=config.HITL_TIMEOUT if hasattr(config, 'HITL_TIMEOUT') else 60.0)
                
                decision = self.decisions.get(review_id, False)
                if not decision:
                    result["error"] = "Human rejected the request"
                    result["decision"] = "BLOCK"
                else:
                    result["decision"] = "PASS"
                    
            except asyncio.TimeoutError:
                result["error"] = "HITL request timed out"
                result["decision"] = "BLOCK"
                # Remove from pending if timed out
                if review_id in self.pending_requests:
                    del self.pending_requests[review_id]
                if review_id in self.pending_reviews:
                    del self.pending_reviews[review_id]
                    
        return result
    
    async def resolve_request(self, request_id: str, approved: bool) -> bool:
        """Resolve a pending HITL request."""
        if request_id in self.pending_requests:
            self.decisions[request_id] = approved
            self.pending_requests[request_id].set()
            
            # Clean up pending structures
            if approved:
                self.approve(request_id)
            else:
                self.reject(request_id)
                
            return True
        return False
    
    def get_pending_reviews(self) -> List[HITLRequest]:
        """Get all pending HITL reviews."""
        return list(self.pending_reviews.values())
    
    def approve(self, message_id: str) -> bool:
        """Approve a pending review."""
        if message_id in self.pending_reviews:
            request = self.pending_reviews[message_id]
            request.status = "approved"
            self.approval_history.append(request)
            del self.pending_reviews[message_id]
            return True
        return False
    
    def reject(self, message_id: str) -> bool:
        """Reject a pending review."""
        if message_id in self.pending_reviews:
            request = self.pending_reviews[message_id]
            request.status = "rejected"
            self.approval_history.append(request)
            del self.pending_reviews[message_id]
            return True
        return False
    
    def get_review_status(self, message_id: str) -> Optional[str]:
        """Get the status of a review."""
        if message_id in self.pending_reviews:
            return "pending"
        for req in self.approval_history:
            if req.message_id == message_id:
                return req.status
        return None


# Global HITL gate instance
_gate: Optional[HITLGate] = None


def get_hitl_gate() -> HITLGate:
    """Get or create the global HITL gate instance."""
    global _gate
    if _gate is None:
        _gate = HITLGate()
    return _gate


def init_hitl_gate() -> HITLGate:
    """Initialize and return the HITL gate."""
    global _gate
    _gate = HITLGate()
    return _gate