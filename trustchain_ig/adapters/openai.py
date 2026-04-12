"""
TrustChain Adapter for OpenAI Agents SDK

This adapter wraps the OpenAI Agents SDK toolset to route through TrustChain.

Usage:
    from adapters.openai import TrustChainToolset, wrap_agent
    
    # Wrap an OpenAI agent
    agent = wrap_agent(agent, trustchain_url="http://localhost:7070/mcp")
"""
import os
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents import Agent


class TrustChainToolset:
    """
    Wrapper for OpenAI Agents SDK that routes tool calls through TrustChain.
    """
    
    def __init__(
        self,
        trustchain_url: str = "http://localhost:7070/mcp",
        session_id: Optional[str] = None,
        task_id: str = "default"
    ):
        self.trustchain_url = trustchain_url
        self.session_id = session_id or f"sess_{os.urandom(8).hex()}"
        self.task_id = task_id
        self._tokens = {}
    
    def get_session_headers(self) -> Dict[str, str]:
        """Get headers for TrustChain session."""
        return {
            "X-Session-ID": self.session_id,
            "X-Task-ID": self.task_id
        }
    
    def issue_token(
        self,
        agent_id: str,
        tool_name: str,
        max_calls: Optional[int] = None
    ) -> Dict[str, Any]:
        """Issue a capability token for a specific tool."""
        payload = {
            "agent_id": agent_id,
            "tool_name": tool_name,
            "task_id": self.task_id,
            "issued_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
            "max_calls": max_calls
        }
        
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            b"trustchain-secret-key-change-in-production",
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        token_id = f"{agent_id}:{tool_name}"
        self._tokens[token_id] = (payload, signature)
        
        return {
            "payload": payload,
            "signature": signature
        }
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool through TrustChain."""
        import httpx
        
        payload = None
        signature = None
        
        tool_key = f"{self.session_id}:{tool_name}"
        if tool_key in self._tokens:
            payload, signature = self._tokens[tool_key]
        
        request_body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
                "_token_payload": payload,
                "_token_signature": signature,
                "_session_id": self.session_id,
                "_task_id": self.task_id
            }
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.trustchain_url,
                json=request_body,
                headers=self.get_session_headers()
            )
            
            result = response.json()
            
            if "error" in result:
                error_info = result["error"].get("data", {})
                raise Exception(
                    f"TrustChain blocked: {error_info.get('reason', 'Unknown')}"
                )
            
            return result.get("result", {})
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from TrustChain."""
        import httpx
        import asyncio
        
        async def _list():
            async with httpx.AsyncClient(timeout=10) as client:
                request_body = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list"
                }
                response = await client.post(
                    self.trustchain_url,
                    json=request_body,
                    headers=self.get_session_headers()
                )
                result = response.json()
                return result.get("result", {}).get("tools", [])
        
        try:
            return asyncio.run(_list())
        except:
            return []


def wrap_agent(
    agent: "Agent",
    trustchain_url: str = "http://localhost:7070/mcp",
    session_id: Optional[str] = None,
    task_id: str = "default"
) -> "Agent":
    """
    Wrap an OpenAI Agents SDK agent with TrustChain security.
    
    Usage:
        from agents import Agent
        
        agent = Agent(...)
        secure_agent = wrap_agent(
            agent,
            trustchain_url="http://localhost:7070/mcp",
            session_id="my-session",
            task_id="my-task"
        )
    """
    toolset = TrustChainToolset(
        trustchain_url=trustchain_url,
        session_id=session_id,
        task_id=task_id
    )
    
    original_execute = getattr(agent, "execute", None)
    
    async def secure_execute(tool_name: str, arguments: Dict[str, Any]):
        return await toolset.call_tool(tool_name, arguments)
    
    if hasattr(agent, "tools"):
        original_tools = agent.tools
        secure_tools = []
        
        for tool in original_tools:
            async def secure_tool_wrapper(tool_name=tool.name):
                async def wrapper(args):
                    return await toolset.call_tool(tool_name, args)
                return wrapper
            
            secure_tools.append(secure_tool_wrapper)
        
        agent.tools = secure_tools
    
    return agent


__all__ = ["TrustChainToolset", "wrap_agent"]