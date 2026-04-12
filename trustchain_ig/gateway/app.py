import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import json
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from config import get_config, TrustChainConfig
from gateway.proxy import get_gateway, MCPGateway, MCPInitializeRequest, MCPToolsListRequest, MCPToolCallRequest
from gateway.session import get_session_manager
from engines import get_hitl_gate
from audit import get_audit_store
from telemetry.metrics import setup_metrics


app = FastAPI(title="TrustChain MCP Gateway", version="1.0.0")


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request format."""
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    method: str
    params: Optional[Dict] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response format."""
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    result: Optional[Any] = None
    error: Optional[Dict] = None


def get_client_session_id(request: Request) -> str:
    """Extract or generate session ID from request."""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        client_ip = request.client.host if request.client else "unknown"
        session_id = f"sess_{hash(client_ip) % 1000000:06d}"
    return session_id


@app.post("/mcp")
async def handle_mcp(request: Request):
    """Handle MCP JSON-RPC requests."""
    
    try:
        body = await request.body()
        raw_request = json.loads(body.decode())
        
        if isinstance(raw_request, list):
            responses = []
            for req in raw_request:
                response = await _handle_single_jsonrpc(req, request)
                responses.append(response)
            return JSONResponse(content=responses)
        else:
            return await _handle_single_jsonrpc(raw_request, request)
    
    except json.JSONDecodeError as e:
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error", "data": str(e)}}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"jsonrpc": "2.0", "error": {"code": -32603, "message": "Internal error", "data": str(e)}}
        )


async def _handle_single_jsonrpc(req: Dict, request: Request) -> Dict:
    """Handle a single JSON-RPC request."""
    method = req.get("method")
    params = req.get("params", {})
    req_id = req.get("id")
    session_id = get_client_session_id(request)
    
    gateway = get_gateway()
    
    try:
        if method == "initialize":
            init_req = MCPInitializeRequest(**params) if params else MCPInitializeRequest()
            result = await gateway.handle_initialize(init_req, session_id)
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        
        elif method == "tools/list":
            result = await gateway.handle_tools_list()
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            token_payload = params.get("_token_payload")
            token_signature = params.get("_token_signature")
            
            result = await gateway.handle_tools_call(
                request=MCPToolCallRequest(name=tool_name, arguments=tool_args),
                session_id=session_id,
                token_payload=token_payload,
                token_signature=token_signature
            )
            
            if "error" in result:
                return {"jsonrpc": "2.0", "id": req_id, "error": result["error"]}
            
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        
        elif method == "resources/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": []}}
        
        elif method == "prompts/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": []}}
        
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"pong": True}}
        
        else:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}
    
    except Exception as e:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    config = get_config()
    audit_store = get_audit_store()
    session_manager = get_session_manager()
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "audit_chain_valid": audit_store.verify_chain(),
        "active_sessions": len(session_manager.get_active_sessions()),
        "pending_hitl": len(get_hitl_gate().get_pending())
    }


@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    audit_store = get_audit_store()
    session_manager = get_session_manager()
    hitl_gate = get_hitl_gate()
    
    stats = audit_store.get_stats()
    
    return {
        "audit": stats,
        "sessions": {
            "active": len(session_manager.get_active_sessions()),
            "total": len([s for s in session_manager._sessions.values()])
        },
        "hitl": {
            "pending": len(hitl_gate.get_pending()),
            "history_size": len(hitl_gate.get_history())
        }
    }


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details."""
    gateway = get_gateway()
    session_info = gateway.get_session_info(session_id)
    
    if not session_info:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session_info


@app.get("/hitl-queue")
async def get_hitl_queue():
    """Get pending HITL requests."""
    gateway = get_gateway()
    return {"pending": gateway.get_pending_hitl()}


@app.post("/hitl-decision/{request_id}")
async def hitl_decision(request_id: str, decision: str, decided_by: str = "human"):
    """Approve or reject a HITL request."""
    hitl_gate = get_hitl_gate()
    
    if decision == "approve":
        success = await hitl_gate.approve(request_id, decided_by)
    elif decision == "reject":
        success = await hitl_gate.reject(request_id, decided_by)
    else:
        raise HTTPException(status_code=400, detail="Invalid decision")
    
    if success:
        return {"status": "success", "decision": decision}
    else:
        raise HTTPException(status_code=404, detail="Request not found")


@app.get("/audit")
async def get_audit_logs(
    session_id: str = None,
    event_type: str = None,
    tool: str = None,
    limit: int = 50
):
    """Query audit logs."""
    audit_store = get_audit_store()
    logs = audit_store.query(
        session_id=session_id,
        event_type=event_type,
        tool=tool,
        limit=limit
    )
    return {"logs": logs}


@app.get("/verify-chain")
async def verify_chain():
    """Verify audit chain integrity."""
    audit_store = get_audit_store()
    valid = audit_store.verify_chain()
    return {"valid": valid, "status": "OK" if valid else "TAMPERED"}


setup_metrics(app)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    return app


def run_server(host: str = "0.0.0.0", port: int = 7070):
    """Run the MCP gateway server."""
    config = get_config()
    
    if config.mcp.host:
        host = config.mcp.host
    if config.mcp.port:
        port = config.mcp.port
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()