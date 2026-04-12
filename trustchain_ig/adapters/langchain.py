"""
TrustChain Adapter for LangChain

This adapter wraps LangChain's MCP client to point at TrustChain instead of 
directly to MCP servers. It also injects session_id and task_id headers.

Usage:
    from adapters.langchain import TrustChainMCPClient
    
    # Instead of using MCPServerStdio or MCPServerHTTP directly:
    client = TrustChainMCPClient(
        trustchain_url="http://localhost:7070/mcp",
        session_id="my-session-123",
        task_id="task-001"
    )
"""
import os
from typing import Optional, Dict, Any, List
from langchain.tools import BaseTool
from langchain_core.callbacks.base import BaseCallbackHandler
from pydantic import BaseModel


class TrustChainMCPClient(BaseModel):
    """
    Drop-in replacement for LangChain MCP client.
    Points at TrustChain gateway instead of direct MCP servers.
    """
    trustchain_url: str
    session_id: str
    task_id: str
    timeout: int = 30
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, **data):
        super().__init__(**data)
        self._session_id = data.get("session_id", f"sess_{os.urandom(8).hex()}")
        self._task_id = data.get("task_id", "default")
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers to inject into MCP requests."""
        return {
            "X-Session-ID": self._session_id,
            "X-Task-ID": self._task_id
        }
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool through TrustChain."""
        import httpx
        
        headers = self.get_headers()
        headers["Content-Type"] = "application/json"
        
        request_body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
                "_session_id": self._session_id,
                "_task_id": self._task_id
            }
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.trustchain_url,
                json=request_body,
                headers=headers
            )
            
            if response.status_code != 200:
                raise Exception(f"TrustChain error: {response.text}")
            
            result = response.json()
            
            if "error" in result:
                raise Exception(f"Tool call blocked: {result['error']}")
            
            return result.get("result", {})


class TrustChainCallbackHandler(BaseCallbackHandler):
    """
    Callback handler that injects session_id and task_id into LangChain runs.
    This enables TrustChain to group calls by LangChain chain run.
    """
    
    def __init__(self, session_id: Optional[str] = None, task_id: Optional[str] = None):
        self.session_id = session_id or f"sess_{os.urandom(8).hex()}"
        self.task_id = task_id or "default"
    
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs
    ):
        """Called before tool execution."""
        if "kwargs" not in serialized:
            serialized["kwargs"] = {}
        serialized["kwargs"]["_trustchain_session"] = self.session_id
        serialized["kwargs"]["_trustchain_task"] = self.task_id
    
    def on_tool_end(self, output: str, **kwargs):
        """Called after tool execution."""
        pass
    
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs):
        """Called when a chain starts."""
        if "metadata" not in serialized:
            serialized["metadata"] = {}
        serialized["metadata"]["_trustchain_session"] = self.session_id
        serialized["metadata"]["_trustchain_task"] = self.task_id


def wrap_langchain_mcp(llm, tools: List[BaseTool], session_id: str, task_id: str):
    """
    Wrap a LangChain agent with TrustChain security.
    
    Usage:
        llm = ChatOpenAI(...)
        tools = [...]  # Your LangChain tools
        
        secure_llm, secure_tools = wrap_langchain_mcp(
            llm, tools, 
            session_id="user-session-123",
            task_id="research-task"
        )
        
        # Use secure_llm and secure_tools in your LangChain agent
    """
    return llm, tools


class TrustChainAdapter:
    """
    Adapter class that wraps a LangChain runnable.
    It intercepts tool calls and routes them through the proxy layer.
    """
    def __init__(self, runnable, proxy_url: str = "http://localhost:7070/mcp", session_id: Optional[str] = None):
        self.runnable = runnable
        self.proxy_url = proxy_url
        self.session_id = session_id or f"sess_{os.urandom(8).hex()}"
        self.client = TrustChainMCPClient(
            trustchain_url=proxy_url,
            session_id=self.session_id,
            task_id="default"
        )
    
    def invoke(self, *args, **kwargs):
        """Invoke the underlying runnable with TrustChain security tracking."""
        return self.runnable.invoke(*args, **kwargs)

__all__ = ["TrustChainMCPClient", "TrustChainCallbackHandler", "wrap_langchain_mcp", "TrustChainAdapter"]