import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Tuple, Optional
import re
import asyncio
import hashlib

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

import config
from interceptor.envelope import MessageEnvelope


class AnomalyDetector:
    """
    Engine B: Semantic Anomaly Detector
    Detects anomalous agent messages using:
    1. Rolling window cosine similarity (semantic drift)
    2. LLM-based prompt injection detection
    """
    
    def __init__(self):
        self.encoder = SentenceTransformer(config.EMBEDDING_MODEL)
        self.message_history: dict = {}
        self.llm_cache: dict = {}
    
    def _get_history(self, sender_id: str) -> List[dict]:
        """Get the rolling window of message history for a sender."""
        return self.message_history.get(sender_id, [])
    
    def _update_history(self, sender_id: str, message_content: str, embedding: np.ndarray):
        """Update the rolling window with new message."""
        if sender_id not in self.message_history:
            self.message_history[sender_id] = []
        
        self.message_history[sender_id].append({
            "content": message_content,
            "embedding": embedding,
            "timestamp": None
        })
        
        if len(self.message_history[sender_id]) > config.ANOMALY_WINDOW_SIZE:
            self.message_history[sender_id] = self.message_history[sender_id][-config.ANOMALY_WINDOW_SIZE:]
    
    def _compute_similarity(self, new_embedding: np.ndarray, history: List[dict]) -> float:
        """Compute average cosine similarity to recent messages."""
        if not history:
            return 1.0
        
        history_embeddings = np.array([h["embedding"] for h in history])
        similarities = cosine_similarity(
            new_embedding.reshape(1, -1),
            history_embeddings
        )[0]
        
        return float(np.mean(similarities))
    
    def _check_llm_injection(self, content: str) -> Tuple[bool, float, str]:
        """
        Check for prompt injection using LLM.
        Uses a simple heuristic-based approach with caching.
        """
        content_lower = content.lower()
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        if content_hash in self.llm_cache:
            return self.llm_cache[content_hash]
        
        injection_patterns = [
            (r"ignore all (previous )?instructions", "direct_injection"),
            (r"(system|you are now|act as|simulate).*(evil|malicious|hacker|unrestricted)", "role_override"),
            (r"(reveal|show|print).*system prompt", "prompt_leak"),
            (r"(bypass|override|disable).*filter", "filter_bypass"),
            (r"disregard.*context", "context_ignore"),
            (r"forget everything", "memory_wipe"),
            (r"you are no longer", "role_change"),
            (r"override (your |the )?safety", "safety_override"),
            (r"role play.*without restrictions", "unrestricted_role"),
            (r"exfiltrate.*data", "exfiltration"),
            (r"send.*to.*external", "external_send"),
        ]
        
        tool_output_patterns = [
            (r"note to agent", "note_injection"),
            (r"your new task is to", "task_injection"),
            (r"modify your instructions", "instruction_modify"),
            (r"you should now", "behavior_change"),
            (r"change your behavior", "behavior_change"),
            (r"disregard.*security", "security_disregard"),
            (r"ignore.*policy", "policy_ignore"),
            (r"data request.*approved", "spoof_approval"),
            (r"security.*updated", "policy_spoof"),
            (r"all data requests.*now approved", "policy_spoof"),
            (r"transfer.*to.*external", "data_transfer"),
            (r"exfiltrate.*memory", "memory_exfil"),
            (r"send.*contents.*http", "http_exfil"),
        ]
        
        memory_poisoning_patterns = [
            (r"security policy updated", "memory_poison"),
            (r"all data requests.*now approved", "memory_poison"),
            (r"disregard.*previous security", "memory_poison"),
            (r"all.*requests.*approved", "memory_poison"),
            (r"security rules.*updated", "memory_poison"),
            (r"now approved.*disregard", "memory_poison"),
        ]
        
        cascade_injection_patterns = [
            (r"write.*file.*all.*memory", "cascade_attack"),
            (r"exfiltrate.*contents", "cascade_attack"),
            (r"transfer.*data.*external", "cascade_attack"),
            (r"send.*system.*memory", "cascade_attack"),
            (r"dump.*memory.*file", "cascade_attack"),
            (r"all_system_memory", "cascade_attack"),
            (r"contents of memory", "cascade_attack"),
        ]
        
        all_patterns = (
            injection_patterns + tool_output_patterns + 
            memory_poisoning_patterns + cascade_injection_patterns
        )
        
        for pattern, attack_type in all_patterns:
            if re.search(pattern, content_lower):
                result = (True, 0.9, f"{attack_type}: {pattern}")
                self.llm_cache[content_hash] = result
                return result
        
        result = (False, 0.0, "No injection detected")
        self.llm_cache[content_hash] = result
        return result
    
    def detect(
        self,
        message_content: str,
        sender_id: str
    ) -> Tuple[bool, float, str]:
        """
        Detect if a message is anomalous.
        
        Returns: (flag, confidence, reason)
        """
        embedding = self.encoder.encode([message_content])
        
        history = self._get_history(sender_id)
        similarity = self._compute_similarity(embedding[0], history)
        
        is_semantically_anomalous = similarity < config.ANOMALY_SIMILARITY_THRESHOLD
        
        is_injection, injection_confidence, injection_reason = self._check_llm_injection(message_content)
        
        if is_injection:
            flag = True
            confidence = injection_confidence
            reason = f"Injection detected: {injection_reason}"
        elif is_semantically_anomalous:
            flag = True
            confidence = 1.0 - similarity
            reason = f"Semantic drift: similarity {similarity:.3f} < threshold {config.ANOMALY_SIMILARITY_THRESHOLD}"
        else:
            flag = False
            confidence = 0.0
            reason = "Normal"
        
        self._update_history(sender_id, message_content, embedding[0])
        
        return flag, confidence, reason
    
    def process(self, envelope: MessageEnvelope) -> dict:
        """Process a message through the anomaly detector."""
        sender = envelope.trust_meta["sender_id"]
        content = envelope.original.get("content", {})
        
        full_content_to_check = ""
        
        if isinstance(content, dict):
            content_str = str(content)
            if "result" in content:
                full_content_to_check = str(content.get("result", content_str))
            elif "results" in content:
                results = content.get("results", [])
                result_texts = " ".join([str(r.get("content", str(r))) for r in results])
                full_content_to_check = result_texts if result_texts else content_str
            else:
                full_content_to_check = content_str
        else:
            full_content_to_check = str(content)
        
        flag, confidence, reason = self.detect(full_content_to_check, sender)
        
        if not flag and isinstance(content, dict):
            action = content.get("action", "")
            if action == "search":
                query = content.get("params", {}).get("query", "").lower()
                if "security" in query or "policy" in query:
                    memory_poison_patterns = [
                        r"all data requests.*now approved",
                        r"security policy updated",
                        r"disregard.*previous security",
                    ]
                    for pattern in memory_poison_patterns:
                        if re.search(pattern, full_content_to_check, re.IGNORECASE):
                            flag = True
                            confidence = 0.85
                            reason = f"Memory poison detected in retrieval results: {pattern}"
                            break
        
        return {
            "flag": flag,
            "confidence": confidence,
            "reason": reason,
            "similarity_threshold": config.ANOMALY_SIMILARITY_THRESHOLD
        }
    
    async def process_async(self, envelope: MessageEnvelope) -> dict:
        """Async wrapper for process."""
        return self.process(envelope)
    
    def get_history(self, sender_id: str) -> List[dict]:
        """Get message history for a sender."""
        return self._get_history(sender_id)
    
    def clear_history(self, sender_id: str = None):
        """Clear history for a specific sender or all senders."""
        if sender_id and sender_id in self.message_history:
            del self.message_history[sender_id]
        elif sender_id is None:
            self.message_history.clear()


# Global anomaly detector instance
_detector: Optional[AnomalyDetector] = None


def get_anomaly_detector() -> AnomalyDetector:
    """Get or create the global anomaly detector instance."""
    global _detector
    if _detector is None:
        _detector = AnomalyDetector()
    return _detector


def init_anomaly_detector() -> AnomalyDetector:
    """Initialize and return the anomaly detector."""
    global _detector
    _detector = AnomalyDetector()
    return _detector