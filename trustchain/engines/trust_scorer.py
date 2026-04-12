import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json

import config
from interceptor.envelope import MessageEnvelope


class TrustScorer:
    """
    Engine A: Trust Score Propagator
    Computes trust score based on hop count, anomaly history, and provenance.
    """
    
    def __init__(self, audit_store: Any = None):
        self.audit_store = audit_store
        self.agent_trust_scores: Dict[str, float] = {
            "orchestrator": 1.0,
            "tool_agent": 1.0,
            "retrieval_agent": 1.0,
            "executor_agent": 1.0,
            "human": 1.0
        }
    
    def _get_anomaly_count(self, agent_id: str) -> int:
        """Get recent anomaly count for an agent from audit log."""
        if not self.audit_store:
            return 0
        
        try:
            logs = self.audit_store.query(
                sender=agent_id,
                event_type="ANOMALY_DETECTED",
                since=datetime.utcnow() - timedelta(minutes=10)
            )
            return len(logs)
        except Exception:
            return 0
    
    def _calculate_hop_decay(self, message: dict) -> float:
        """Calculate trust decay based on hop count."""
        hop_count = message.get("hop_count", 1)
        if hop_count > config.HOP_PENALTY_THRESHOLD:
            excess_hops = hop_count - config.HOP_PENALTY_THRESHOLD
            return excess_hops * config.HOP_DECAY
        return 0.0
    
    def score(
        self,
        message: dict,
        audit_log: Optional[List[dict]] = None
    ) -> float:
        """
        Compute trust score for a message.
        
        Factors:
        - hop_count: decrements trust by 0.1 per hop beyond 2
        - anomaly_count: each recent anomaly decays by 0.15
        - provenance_valid: +0.1 bonus if from authenticated human
        """
        sender = message.get("sender", "")
        
        base_score = self.agent_trust_scores.get(sender, 1.0)
        
        hop_decay = self._calculate_hop_decay(message)
        
        anomaly_count = self._get_anomaly_count(sender)
        anomaly_decay = anomaly_count * config.ANOMALY_DECAY
        
        provenance = message.get("provenance_valid", False)
        provenance_bonus = config.PROVENANCE_BONUS if provenance else 0.0
        
        final_score = base_score - hop_decay - anomaly_decay + provenance_bonus
        
        return max(0.0, min(1.0, final_score))
    
    def process(self, envelope: MessageEnvelope) -> dict:
        """Process a message through the trust scorer."""
        message = envelope.original
        
        trust_score = self.score(message)
        
        is_blocked = trust_score < config.TRUST_THRESHOLD
        
        return {
            "trust_score": trust_score,
            "threshold": config.TRUST_THRESHOLD,
            "blocked": is_blocked,
            "factors": {
                "hop_decay": self._calculate_hop_decay(message),
                "anomaly_decay": self._get_anomaly_count(envelope.trust_meta["sender_id"]) * config.ANOMALY_DECAY,
                "provenance_bonus": config.PROVENANCE_BONUS if message.get("provenance_valid") else 0.0
            }
        }
    
    async def process_async(self, envelope: MessageEnvelope) -> dict:
        """Async wrapper for process."""
        return self.process(envelope)
    
    def update_agent_trust(self, agent_id: str, score: float):
        """Update an agent's base trust score."""
        self.agent_trust_scores[agent_id] = max(0.0, min(1.0, score))


# Global trust scorer instance
_scorer: Optional[TrustScorer] = None


def get_trust_scorer() -> TrustScorer:
    """Get or create the global trust scorer instance."""
    global _scorer
    if _scorer is None:
        _scorer = TrustScorer()
    return _scorer


def init_trust_scorer(audit_store: Any = None) -> TrustScorer:
    """Initialize and return the trust scorer."""
    global _scorer
    _scorer = TrustScorer(audit_store)
    return _scorer