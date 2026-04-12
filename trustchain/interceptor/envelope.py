from datetime import datetime
from typing import Optional, Any
import uuid

class MessageEnvelope:
    """
    Metadata envelope added to every message passing through the interceptor.
    """
    
    def __init__(
        self,
        original: dict,
        sender_id: str,
        receiver_id: str,
        trust_score: float = 0.0,
        anomaly_flag: bool = False,
        capability_valid: bool = True,
        hitl_required: bool = False,
        chain_hash: Optional[str] = None,
        decision: str = "PASS"
    ):
        self.original = original
        self.trust_meta = {
            "message_id": str(uuid.uuid4()),
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "timestamp": datetime.utcnow().isoformat(),
            "trust_score": trust_score,
            "anomaly_flag": anomaly_flag,
            "capability_valid": capability_valid,
            "hitl_required": hitl_required,
            "chain_hash": chain_hash,
            "decision": decision
        }
    
    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "trust_meta": self.trust_meta
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MessageEnvelope":
        envelope = cls(
            original=data.get("original", {}),
            sender_id=data.get("trust_meta", {}).get("sender_id", ""),
            receiver_id=data.get("trust_meta", {}).get("receiver_id", ""),
            trust_score=data.get("trust_meta", {}).get("trust_score", 0.0),
            anomaly_flag=data.get("trust_meta", {}).get("anomaly_flag", False),
            capability_valid=data.get("trust_meta", {}).get("capability_valid", True),
            hitl_required=data.get("trust_meta", {}).get("hitl_required", False),
            chain_hash=data.get("trust_meta", {}).get("chain_hash"),
            decision=data.get("trust_meta", {}).get("decision", "PASS")
        )
        return envelope
    
    @property
    def message_id(self) -> str:
        return self.trust_meta["message_id"]
    
    @property
    def decision(self) -> str:
        return self.trust_meta["decision"]
    
    @decision.setter
    def decision(self, value: str):
        self.trust_meta["decision"] = value
    
    @property
    def trust_score(self) -> float:
        return self.trust_meta["trust_score"]
    
    @trust_score.setter
    def trust_score(self, value: float):
        self.trust_meta["trust_score"] = value
    
    @property
    def anomaly_flag(self) -> bool:
        return self.trust_meta["anomaly_flag"]
    
    @anomaly_flag.setter
    def anomaly_flag(self, value: bool):
        self.trust_meta["anomaly_flag"] = value
    
    @property
    def hitl_required(self) -> bool:
        return self.trust_meta["hitl_required"]
    
    @hitl_required.setter
    def hitl_required(self, value: bool):
        self.trust_meta["hitl_required"] = value
    
    @property
    def capability_valid(self) -> bool:
        return self.trust_meta["capability_valid"]
    
    @capability_valid.setter
    def capability_valid(self, value: bool):
        self.trust_meta["capability_valid"] = value
    
    @property
    def chain_hash(self) -> Optional[str]:
        return self.trust_meta["chain_hash"]
    
    @chain_hash.setter
    def chain_hash(self, value: str):
        self.trust_meta["chain_hash"] = value


def create_message(
    sender: str,
    receiver: str,
    content: Any,
    task_id: str,
    message_type: str = "agent_message"
) -> dict:
    """
    Factory function to create a raw message dict before envelope is added.
    """
    return {
        "sender": sender,
        "receiver": receiver,
        "content": content,
        "task_id": task_id,
        "message_type": message_type,
        "timestamp": datetime.utcnow().isoformat()
    }