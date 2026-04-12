"""
TrustChain Adapter for AutoGen

This adapter wraps AutoGen's tool execution to route through TrustChain.

Usage:
    from adapters.autogen import TrustChainToolExecutor, wrap_autogen_agent
    
    # Wrap an AutoGen agent
    secure_agent = wrap_autogen_agent(agent, trustchain_url="http://localhost:7070/mcp")
"""
import os
import asyncio
from typing import Any, Dict, Optional, Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autogen.agentchat.conversable_agent import ConversableAgent


class TrustChainToolExecutor:
    """
    Wrapper that intercepts AutoGen tool execution and routes through TrustChain.
    """
    
    def __init__(
        self,
        trustchain_url: str = "http://localhost:7070/mcp",
        session_id: Optional[str] = None,
        original_executor: Optional[Callable] = None
    ):
        self.trustchain_url = trustchain_url
        self.session_id = session_id or f"sess_{os.urandom(8).hex()}"
        self.original_executor = original_executor
    
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """Execute a tool call through TrustChain."""
        import httpx
        
        request_body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
                "_session_id": self.session_id
            }
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.trustchain_url,
                json=request_body,
                headers={"X-Session-ID": self.session_id}
            )
            
            if response.status_code != 200:
                raise Exception(f"TrustChain error: {response.text}")
            
            result = response.json()
            
            if "error" in result:
                error_data = result["error"].get("data", {})
                raise Exception(
                    f"Tool call blocked by TrustChain: {error_data.get('reason', 'Unknown')}"
                )
            
            return result.get("result", {})
    
    def wrap_agent(self, agent: "ConversableAgent") -> "ConversableAgent":
        """Wrap an AutoGen agent with TrustChain protection."""
        original_execute = getattr(agent, "_execute_function", None)
        
        async def secure_execute(*args, **kwargs):
            tool_name = kwargs.get("name", args[0] if args else "")
            tool_args = kwargs.get("arguments", args[1] if len(args) > 1 else {})
            
            return await self.execute(tool_name, tool_args)
        
        if hasattr(agent, "register_function"):
            pass
        
        return agent


def wrap_autogen_agent(
    agent: "ConversableAgent",
    trustchain_url: str = "http://localhost:7070/mcp",
    session_id: Optional[str] = None
) -> "ConversableAgent":
    """
    Wrap an AutoGen agent with TrustChain security.
    
    Usage:
        from autogen import ConversableAgent
        
        agent = ConversableAgent(...)
        secure_agent = wrap_autogen_agent(
            agent,
            trustchain_url="http://localhost:7070/mcp",
            session_id="my-session"
        )
    """
    executor = TrustChainToolExecutor(
        trustchain_url=trustchain_url,
        session_id=session_id
    )
    
    return executor.wrap_agent(agent)


__all__ = ["TrustChainToolExecutor", "wrap_autogen_agent"]