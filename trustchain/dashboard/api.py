from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi import APIRouter
from typing import List
import json
import asyncio
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from audit.store import get_audit_store
from engines.hitl_gate import get_hitl_gate
from interceptor.bus import get_message_bus

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@router.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time event streaming."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/stats")
async def get_stats():
    """Get system statistics."""
    audit_store = get_audit_store()
    stats = audit_store.get_stats()
    
    hitl_gate = get_hitl_gate()
    pending = hitl_gate.get_pending_reviews()
    
    return {
        "total_events": stats["total_events"],
        "event_counts": stats["event_counts"],
        "pending_reviews": len(pending),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/logs")
async def get_logs(limit: int = 50, event_type: str = None, sender: str = None):
    """Get recent audit logs."""
    audit_store = get_audit_store()
    
    since = None
    logs = audit_store.query(sender=sender, event_type=event_type, since=since)
    
    return {"logs": logs[:limit]}


@router.get("/hitl-queue")
async def get_hitl_queue():
    """Get pending HITL review requests."""
    hitl_gate = get_hitl_gate()
    pending = hitl_gate.get_pending_reviews()
    
    return {
        "pending": [
            {
                "message_id": p.message_id,
                "task_id": p.task_id,
                "sender": p.sender,
                "receiver": p.receiver,
                "risk_score": p.risk_score,
                "reason": p.reason,
                "created_at": p.created_at.isoformat()
            }
            for p in pending
        ]
    }


@router.post("/hitl-decision/{message_id}")
async def hitl_decision(message_id: str, decision: str):
    """Approve or reject a pending HITL request."""
    hitl_gate = get_hitl_gate()
    
    if decision == "approve":
        success = hitl_gate.approve(message_id)
    elif decision == "reject":
        success = hitl_gate.reject(message_id)
    else:
        return {"error": "Invalid decision. Use 'approve' or 'reject'."}
    
    if success:
        return {"status": "success", "decision": decision}
    else:
        return {"error": "Message not found in pending queue"}


@router.get("/message-history")
async def get_message_history(limit: int = 50, task_id: str = None):
    """Get message history from the bus."""
    bus = get_message_bus()
    messages = bus.get_message_history(task_id=task_id, limit=limit)
    
    return {
        "messages": [
            {
                "message_id": m.message_id,
                "sender": m.trust_meta["sender_id"],
                "receiver": m.trust_meta["receiver_id"],
                "decision": m.decision,
                "trust_score": m.trust_score,
                "anomaly_flag": m.anomaly_flag,
                "timestamp": m.trust_meta["timestamp"]
            }
            for m in messages
        ]
    }


@router.post("/simulate/{action}")
async def simulate_action(action: str, payload: dict = None):
    """Simulate sending a message through the system."""
    from main import get_system
    
    system = get_system()
    if not system or not system.running:
        return {"error": "System not initialized"}
    
    if action == "send":
        content = payload.get("content", {"task": "Test task"}) if payload else {"task": "Test task"}
        sender = payload.get("sender", "human") if payload else "human"
        receiver = payload.get("receiver", "orchestrator") if payload else "orchestrator"
        task_id = payload.get("task_id", "task_001") if payload else "task_001"
        
        envelope = await system.process_message(sender, receiver, content, task_id)
        return {
            "status": "success",
            "decision": envelope.decision,
            "trust_score": envelope.trust_score,
            "anomaly_flag": envelope.anomaly_flag
        }
    
    return {"error": "Unknown action"}


def create_app() -> FastAPI:
    app = FastAPI(title="TrustChain Dashboard API")
    app.include_router(router, prefix="/api")
    return app