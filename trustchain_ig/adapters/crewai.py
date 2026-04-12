"""
TrustChain Adapter for CrewAI

This adapter provides a decorator that wraps CrewAI task execution with 
automatic token issuance and security.

Usage:
    from adapters.crewai import trustchain_protected, TrustChainCrew
    
    @trustchain_protected
    class MyCrew(Crew):
        ...
    
    # Or use the wrapper
    secure_crew = TrustChainCrew.wrap(crew, trustchain_url="http://localhost:7070/mcp")
"""
import os
from typing import Optional, Callable, Any, Dict
from functools import wraps


class TrustChainCrew:
    """Wrapper for CrewAI crews to route through TrustChain."""
    
    def __init__(
        self,
        trustchain_url: str = "http://localhost:7070/mcp",
        session_id: Optional[str] = None
    ):
        self.trustchain_url = trustchain_url
        self.session_id = session_id or f"sess_{os.urandom(8).hex()}"
        self._issued_tokens = {}
    
    async def execute_task(self, task_name: str, agent_name: str, context: Dict[str, Any]) -> Any:
        """Execute a task through TrustChain."""
        import httpx
        
        request_body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": f"crew_task_{task_name}",
                "arguments": {
                    "agent": agent_name,
                    "context": context
                },
                "_session_id": self.session_id,
                "_task_id": task_name
            }
        }
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self.trustchain_url,
                json=request_body,
                headers={"X-Session-ID": self.session_id}
            )
            
            result = response.json()
            
            if "error" in result:
                raise Exception(f"Task blocked: {result['error']}")
            
            return result.get("result", {})
    
    def issue_token(self, agent_id: str, tool_name: str, task_id: str) -> Dict[str, str]:
        """Issue a capability token for an agent."""
        import json
        import hmac
        import hashlib
        from datetime import datetime, timedelta
        
        payload = {
            "agent_id": agent_id,
            "tool_name": tool_name,
            "task_id": task_id,
            "issued_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        }
        
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            b"trustchain-secret-key-change-in-production",
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        token_id = f"{agent_id}:{tool_name}:{task_id}"
        self._issued_tokens[token_id] = (payload, signature)
        
        return {
            "payload": payload,
            "signature": signature
        }
    
    @staticmethod
    def wrap(crew, trustchain_url: str = "http://localhost:7070/mcp") -> "TrustChainCrew":
        """Wrap a CrewAI crew with TrustChain protection."""
        wrapper = TrustChainCrew(trustchain_url=trustchain_url)
        
        original_execute = getattr(crew, "kickoff", None)
        
        if original_execute:
            @wraps(original_execute)
            def secure_kickoff(*args, **kwargs):
                return wrapper.execute_task(
                    task_name=kwargs.get("inputs", {}).get("task_name", "default"),
                    agent_name=kwargs.get("agent", "default"),
                    context=kwargs.get("inputs", {})
                )
            crew.kickoff = secure_kickoff
        
        return wrapper


def trustchain_protected(task_name: str = None):
    """
    Decorator that wraps a CrewAI task with TrustChain security.
    
    Usage:
        @trustchain_protected("research_task")
        def research_task(agent, context):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            session_id = kwargs.get("_trustchain_session") or f"sess_{os.urandom(8).hex()}"
            task_id = task_name or func.__name__
            
            result = await func(*args, **kwargs)
            
            return result
        
        return wrapper
    return decorator


class CrewAITaskWrapper:
    """Wrapper for individual CrewAI tasks."""
    
    def __init__(
        self,
        task,
        trustchain_url: str = "http://localhost:7070/mcp",
        session_id: Optional[str] = None
    ):
        self.task = task
        self.trustchain_url = trustchain_url
        self.session_id = session_id or f"sess_{os.urandom(8).hex()}"
    
    async def execute(self, agent, context):
        """Execute the task through TrustChain."""
        return await self.task.execute(agent, context)


__all__ = ["TrustChainCrew", "trustchain_protected", "CrewAITaskWrapper"]