import sqlite3
import asyncio
import json
import threading
import uuid
from datetime import datetime
from typing import Callable, Optional, List, Dict, Any
from queue import Queue
from dataclasses import dataclass, field
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from interceptor.envelope import MessageEnvelope, create_message


@dataclass
class Message:
    id: str
    sender: str
    receiver: str
    content: Any
    task_id: str
    message_type: str
    timestamp: str
    envelope: Optional[MessageEnvelope] = None
    processed: bool = False


class MessageBus:
    """
    SQLite-backed message queue with interceptor middleware.
    Every message passes through security engines before reaching the target agent.
    """
    
    def __init__(self, db_file: str = None):
        self.db_file = db_file or config.DB_FILE
        self._lock = threading.RLock()
        self._subscribers: Dict[str, List[Callable]] = {}
        self._engines = []
        self._engine_results = {}
        
        self._init_db()
    
    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(self.db_file)
            cur = conn.cursor()
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {config.MESSAGE_QUEUE_TABLE} (
                    id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    receiver TEXT NOT NULL,
                    content TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    envelope_json TEXT,
                    processed INTEGER DEFAULT 0
                )
            """)
            conn.commit()
            conn.close()
    
    def register_engine(self, engine):
        """Register a security engine to run on every message."""
        self._engines.append(engine)
    
    async def run_engines(self, envelope: MessageEnvelope) -> Dict[str, Any]:
        """
        Run all registered security engines in parallel using asyncio.gather.
        Returns a dict of engine_name -> result.
        """
        import asyncio
        
        tasks = []
        engine_names = []
        
        for engine in self._engines:
            if hasattr(engine, 'process_async'):
                tasks.append(engine.process_async(envelope))
                engine_names.append(engine.__class__.__name__)
            elif hasattr(engine, 'process'):
                # Wrap sync process in async
                async def run_sync(e, eng=engine):
                    return eng.process(e)
                tasks.append(run_sync(envelope))
                engine_names.append(engine.__class__.__name__)
        
        if not tasks:
            return {}
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        engine_results = {}
        for name, result in zip(engine_names, results):
            if isinstance(result, Exception):
                engine_results[name] = {"error": str(result)}
            else:
                engine_results[name] = result
        
        return engine_results
    
    def _update_envelope_from_engines(self, envelope: MessageEnvelope, results: Dict[str, Any]):
        """Merge engine results into envelope metadata."""
        
        # Trust Scorer result
        if "TrustScorer" in results:
            score_data = results["TrustScorer"]
            if isinstance(score_data, dict) and "trust_score" in score_data:
                envelope.trust_score = score_data["trust_score"]
        
        # Anomaly Detector result
        if "AnomalyDetector" in results:
            anomaly_data = results["AnomalyDetector"]
            if isinstance(anomaly_data, dict):
                envelope.anomaly_flag = anomaly_data.get("flag", False)
        
        # Capability Gate result
        if "CapabilityGate" in results:
            cap_data = results["CapabilityGate"]
            if isinstance(cap_data, dict):
                envelope.capability_valid = cap_data.get("valid", True)
        
        # HITL Gate result
        if "HITLGate" in results:
            hitl_data = results["HITLGate"]
            if isinstance(hitl_data, dict):
                envelope.hitl_required = hitl_data.get("required", False)
        
        # Determine final decision
        if not envelope.capability_valid:
            envelope.decision = "BLOCK"
        elif envelope.trust_score < config.TRUST_THRESHOLD:
            envelope.decision = "BLOCK"
        elif envelope.anomaly_flag:
            envelope.decision = "BLOCK"
        elif envelope.hitl_required:
            envelope.decision = "ESCALATE"
        else:
            envelope.decision = "PASS"
    
    async def send(
        self,
        sender: str,
        receiver: str,
        content: Any,
        task_id: str,
        message_type: str = "agent_message"
    ) -> MessageEnvelope:
        """
        Send a message through the interceptor. All security engines run before
        the message is queued for delivery.
        """
        # Create raw message
        raw_message = create_message(sender, receiver, content, task_id, message_type)
        
        # Create envelope with initial metadata
        envelope = MessageEnvelope(
            original=raw_message,
            sender_id=sender,
            receiver_id=receiver
        )
        
        # Run all security engines
        if self._engines:
            engine_results = await self.run_engines(envelope)
            self._engine_results[envelope.message_id] = engine_results
            self._update_envelope_from_engines(envelope, engine_results)
        
        # Write to database
        with self._lock:
            conn = sqlite3.connect(self.db_file)
            cur = conn.cursor()
            cur.execute(f"""
                INSERT INTO {config.MESSAGE_QUEUE_TABLE}
                (id, sender, receiver, content, task_id, message_type, timestamp, envelope_json, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                envelope.message_id,
                sender,
                receiver,
                json.dumps(content) if not isinstance(content, str) else content,
                task_id,
                message_type,
                envelope.trust_meta["timestamp"],
                json.dumps(envelope.to_dict()),
                1 if envelope.decision == "PASS" else 0
            ))
            conn.commit()
            conn.close()
        
        # Notify subscribers
        self._notify_subscribers(receiver, envelope)
        
        return envelope
    
    def send_sync(
        self,
        sender: str,
        receiver: str,
        content: Any,
        task_id: str,
        message_type: str = "agent_message"
    ) -> MessageEnvelope:
        """Synchronous wrapper for send."""
        return asyncio.run(self.send(sender, receiver, content, task_id, message_type))
    
    def _notify_subscribers(self, receiver: str, envelope: MessageEnvelope):
        if receiver in self._subscribers:
            for callback in self._subscribers[receiver]:
                try:
                    callback(envelope)
                except Exception as e:
                    print(f"Subscriber error: {e}")
    
    def subscribe(self, agent_id: str, callback: Callable):
        """Subscribe an agent to receive messages."""
        if agent_id not in self._subscribers:
            self._subscribers[agent_id] = []
        self._subscribers[agent_id].append(callback)
    
    def get_pending_messages(self, receiver: str) -> List[MessageEnvelope]:
        """Retrieve unprocessed messages for an agent."""
        with self._lock:
            conn = sqlite3.connect(self.db_file)
            cur = conn.cursor()
            cur.execute(f"""
                SELECT envelope_json FROM {config.MESSAGE_QUEUE_TABLE}
                WHERE receiver = ? AND processed = 0
                ORDER BY timestamp ASC
            """, (receiver,))
            rows = cur.fetchall()
            conn.close()
            
            envelopes = []
            for row in rows:
                data = json.loads(row[0])
                envelopes.append(MessageEnvelope.from_dict(data))
            
            return envelopes
    
    def mark_processed(self, message_id: str):
        """Mark a message as processed."""
        with self._lock:
            conn = sqlite3.connect(self.db_file)
            cur = conn.cursor()
            cur.execute(f"""
                UPDATE {config.MESSAGE_QUEUE_TABLE}
                SET processed = 1 WHERE id = ?
            """, (message_id,))
            conn.commit()
            conn.close()
    
    def get_message_history(self, task_id: str = None, limit: int = 50) -> List[MessageEnvelope]:
        """Get recent messages, optionally filtered by task_id."""
        with self._lock:
            conn = sqlite3.connect(self.db_file)
            cur = conn.cursor()
            
            if task_id:
                cur.execute(f"""
                    SELECT envelope_json FROM {config.MESSAGE_QUEUE_TABLE}
                    WHERE task_id = ?
                    ORDER BY timestamp DESC LIMIT ?
                """, (task_id, limit))
            else:
                cur.execute(f"""
                    SELECT envelope_json FROM {config.MESSAGE_QUEUE_TABLE}
                    ORDER BY timestamp DESC LIMIT ?
                """, (limit,))
            
            rows = cur.fetchall()
            conn.close()
            
            envelopes = []
            for row in rows:
                data = json.loads(row[0])
                envelopes.append(MessageEnvelope.from_dict(data))
            
            return envelopes
    
    def get_engine_results(self, message_id: str) -> Dict[str, Any]:
        """Get the engine results for a specific message."""
        return self._engine_results.get(message_id, {})


# Global message bus instance
_bus: Optional[MessageBus] = None


def get_message_bus() -> MessageBus:
    """Get or create the global message bus instance."""
    global _bus
    if _bus is None:
        _bus = MessageBus()
    return _bus


def init_message_bus() -> MessageBus:
    """Initialize and return the message bus."""
    global _bus
    _bus = MessageBus()
    return _bus