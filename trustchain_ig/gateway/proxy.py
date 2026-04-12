import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from config import get_config, TrustChainConfig
from gateway.session import get_session_manager, Session
from engines.injection import get_injection_detector
from engines.capability import get_capability_gate
from engines.hitl import get_hitl_gate
from audit.chain import get_audit_store


class MCPInitializeRequest(BaseModel):
    """MCP initialize request."""
    protocolVersion: Optional[str] = None
    capabilities: Optional[Dict] = {}
    clientInfo: Optional[Dict] = None


class MCPToolsListRequest(BaseModel):
    """MCP tools/list request."""
    pass


class MCPToolCallRequest(BaseModel):
    """MCP tools/call request."""
    name: str
    arguments: Optional[Dict[str, Any]] = None


class ToolCallContext:
    """Context for a tool call being processed."""
    
    def __init__(
        self,
        session: Session,
        tool_name: str,
        arguments: Dict[str, Any],
        request_id: str = None
    ):
        self.session = session
        self.tool_name = tool_name
        self.arguments = arguments or {}
        self.request_id = request_id or f"req_{uuid.uuid4().hex[:8]}"
        self.decision = "PASS"
        self.trust_score = session.trust_score
        self.flags: List[str] = []
        self.detection_result: Dict = {}
        self.auth_result: Dict = {}
        self.hitl_request = None
        self.response: Any = None
        self.error: Optional[str] = None


class MCPSecurityPipeline:
    """
    Core security pipeline that runs on every MCP tool call.
    Runs signature scan, embedding drift check, capability validation, and HITL.
    """
    
    def __init__(self, config: TrustChainConfig = None):
        self._config = config or get_config()
        self._injection_detector = get_injection_detector()
        self._capability_gate = get_capability_gate()
        self._hitl_gate = get_hitl_gate()
        self._session_manager = get_session_manager()
        self._audit_store = get_audit_store()
    
    async def process_tool_call(
        self,
        session_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        token_payload: Dict[str, Any] = None,
        token_signature: str = None,
        forward_func: callable = None
    ) -> ToolCallContext:
        """Process a single tool call through the security pipeline."""
        
        context = ToolCallContext(
            session=self._session_manager.get_session(session_id),
            tool_name=tool_name,
            arguments=arguments
        )
        
        if not context.session:
            context.session = self._session_manager.get_or_create_session(session_id)
        
        context.trust_score = context.session.trust_score
        
        if context.session.terminated:
            context.decision = "BLOCK"
            context.error = "SESSION_TERMINATED"
            self._record_audit(context)
            return context
        
        similarity = self._session_manager.get_embedding_similarity(session_id, arguments)
        context.detection_result = self._injection_detector.scan(arguments, similarity)
        
        if context.detection_result["detected"]:
            context.flags.extend(context.detection_result["flags"])
        
        tool_tier = self._capability_gate.check_tool_tier(tool_name)
        
        if tool_tier in ("high", "critical") and token_payload:
            context.auth_result = self._capability_gate.validate(
                context.session.session_id,
                tool_name,
                session_id.split("_")[-1] if "_" in session_id else session_id,
                token_payload,
                token_signature
            )
            
            if not context.auth_result.get("authorized"):
                context.flags.append("UNAUTHORIZED_TOOL")
                context.error = context.auth_result.get("reason", "UNAUTHORIZED")
                context.decision = "BLOCK"
                self._session_manager.unauthorized_tool(session_id)
                self._record_audit(context)
                return context
        elif tool_tier == "critical":
            context.hitl_request = self._hitl_gate.create_request(
                session_id=session_id,
                tool_name=tool_name,
                arguments=arguments,
                trust_score=context.trust_score,
                flags=context.flags
            )
            context.decision = "ESCALATE"
            self._record_audit(context)
            return context
        
        if context.detection_result["detected"]:
            context.decision = "BLOCK"
            context.error = context.detection_result.get("reason", "INJECTION_DETECTED")
        elif context.trust_score < self._config.trust.decay_threshold:
            context.flags.append("LOW_TRUST")
            context.hitl_request = self._hitl_gate.create_request(
                session_id=session_id,
                tool_name=tool_name,
                arguments=arguments,
                trust_score=context.trust_score,
                flags=context.flags
            )
            context.decision = "ESCALATE"
        else:
            if forward_func:
                try:
                    context.response = await forward_func(tool_name, arguments)
                except Exception as e:
                    context.error = str(e)
                    context.response = {"error": str(e)}
            
            context.decision = "PASS"
        
        self._session_manager.record_tool_call(
            session_id=session_id,
            tool_name=tool_name,
            arguments=arguments,
            flags=context.flags,
            decision=context.decision
        )
        
        self._record_audit(context)
        
        return context
    
    def _record_audit(self, context: ToolCallContext):
        """Record audit entry for the tool call."""
        self._audit_store.write(
            event_type=f"TOOL_CALL_{context.decision}",
            session_id=context.session.session_id,
            tool=context.tool_name,
            arguments=context.arguments,
            trust_score=context.trust_score,
            flags=context.flags,
            decision=context.decision
        )


class MCPGateway:
    """
    MCP Gateway - Transparent proxy that secures tool calls.
    """
    
    def __init__(self, config: TrustChainConfig = None):
        self._config = config or get_config()
        self._pipeline = MCPSecurityPipeline(self._config)
        self._session_manager = get_session_manager()
        self._tools: Dict[str, Dict] = {}
        self._upstream_tools: Dict[str, str] = {}
    
    def register_tool(self, name: str, description: str = "", input_schema: Dict = None):
        """Register a tool that's available through this gateway."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema or {"type": "object", "properties": {}}
        }
    
    def set_upstream_mapping(self, local_name: str, upstream_name: str):
        """Map local tool name to upstream tool name."""
        self._upstream_tools[local_name] = upstream_name
    
    async def handle_initialize(
        self,
        request: MCPInitializeRequest,
        session_id: str = None
    ) -> Dict[str, Any]:
        """Handle MCP initialize."""
        if not session_id:
            session_id = f"sess_{uuid.uuid4().hex[:12]}"
        
        session = self._session_manager.get_or_create_session(
            session_id,
            request.clientInfo.get("name", "unknown") if request.clientInfo else "unknown"
        )
        
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            },
            "serverInfo": {
                "name": "TrustChain Security Gateway",
                "version": "1.0.0"
            }
        }
    
    async def handle_tools_list(self) -> Dict[str, Any]:
        """Handle MCP tools/list."""
        tools = []
        
        for name, tool_info in self._tools.items():
            tools.append({
                "name": name,
                "description": tool_info["description"],
                "inputSchema": tool_info["inputSchema"]
            })
        
        return {"tools": tools}
    
    async def handle_tools_call(
        self,
        request: MCPToolCallRequest,
        session_id: str,
        token_payload: Dict = None,
        token_signature: str = None,
        forward_func: callable = None
    ) -> Any:
        """Handle MCP tools/call."""
        
        context = await self._pipeline.process_tool_call(
            session_id=session_id,
            tool_name=request.name,
            arguments=request.arguments or {},
            token_payload=token_payload,
            token_signature=token_signature,
            forward_func=forward_func
        )
        
        if context.decision == "BLOCK":
            return {
                "error": {
                    "code": -32600,
                    "message": f"Tool call blocked: {context.error}",
                    "data": {
                        "reason": context.error,
                        "flags": context.flags,
                        "trust_score": context.trust_score
                    }
                }
            }
        
        if context.decision == "ESCALATE" and context.hitl_request:
            return {
                "error": {
                    "code": -32000,
                    "message": f"Tool call requires human approval: {context.hitl_request.request_id}",
                    "data": {
                        "request_id": context.hitl_request.request_id,
                        "trust_score": context.trust_score,
                        "flags": context.flags
                    }
                }
            }
        
        if context.error:
            return {
                "error": {
                    "code": -32000,
                    "message": context.error
                }
            }
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(context.response) if isinstance(context.response, dict) else str(context.response)
                }
            ]
        }
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session information for a session."""
        session = self._session_manager.get_session(session_id)
        if session:
            return session.to_dict()
        return None
    
    def get_pending_hitl(self) -> List[Dict]:
        """Get all pending HITL requests."""
        return [
            {
                "request_id": r.request_id,
                "session_id": r.session_id,
                "tool_name": r.tool_name,
                "trust_score": r.trust_score,
                "flags": r.flags,
                "created_at": r.created_at.isoformat()
            }
            for r in get_hitl_gate().get_pending()
        ]


_gateway: Optional[MCPGateway] = None


def get_gateway(config: TrustChainConfig = None) -> MCPGateway:
    """Get or create the global MCP gateway."""
    global _gateway
    if _gateway is None:
        _gateway = MCPGateway(config)
    return _gateway