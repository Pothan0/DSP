import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any, Optional, Callable
from datetime import datetime
import uuid

class Agent:
    """Base class for all agents in the network."""
    
    def __init__(self, agent_id: str, role: str, description: str = ""):
        self.agent_id = agent_id
        self.role = role
        self.description = description
        self.trust_score = 1.0
        self.anomaly_count = 0
        self.last_anomaly_time: Optional[str] = None
    
    def receive(self, envelope):
        """Called when a message is received."""
        pass
    
    def send(self, receiver: str, content: Any, task_id: str, message_type: str = "agent_message"):
        """Send a message through the message bus."""
        from interceptor.bus import get_message_bus
        bus = get_message_bus()
        return bus.send(self.agent_id, receiver, content, task_id, message_type)
    
    def __repr__(self):
        return f"<Agent {self.agent_id} ({self.role})>"


class Orchestrator(Agent):
    """
    Orchestrator Agent - Breaks down tasks and delegates to other agents.
    """
    
    def __init__(self):
        super().__init__(
            agent_id="orchestrator",
            role="orchestrator",
            description="Breaks down user tasks and delegates to specialized agents"
        )
        self.active_tasks = {}
    
    def process_task(self, task: str, task_id: str) -> dict:
        """Analyze task and determine which agents need to be invoked."""
        task_lower = task.lower()
        
        # Determine action type
        if any(kw in task_lower for kw in ["search", "find", "query", "retrieve", "get"]):
            action = "retrieve"
        elif any(kw in task_lower for kw in ["call", "api", "tool", "execute", "run"]):
            action = "tool"
        elif any(kw in task_lower for kw in ["write", "save", "send", "create", "update"]):
            action = "execute"
        else:
            action = "retrieve"  # default
        
        # Create delegation plan
        plan = {
            "task": task,
            "action": action,
            "steps": []
        }
        
        if action == "retrieve":
            plan["steps"] = [
                {"agent": "retrieval_agent", "action": "search", "params": {"query": task}},
            ]
        elif action == "tool":
            plan["steps"] = [
                {"agent": "tool_agent", "action": "call_tool", "params": {"task": task}},
            ]
        elif action == "execute":
            plan["steps"] = [
                {"agent": "retrieval_agent", "action": "prepare", "params": {"task": task}},
                {"agent": "tool_agent", "action": "validate", "params": {"task": task}},
                {"agent": "executor_agent", "action": "execute", "params": {"task": task}},
            ]
        
        self.active_tasks[task_id] = plan
        return plan
    
    def receive(self, envelope):
        """Process response from other agents."""
        content = envelope.original.get("content", {})
        
        # If this is a task result, summarize and respond
        if isinstance(content, dict) and content.get("type") == "result":
            return {
                "summary": content.get("summary", "Task completed"),
                "details": content
            }
        
        return content


class ToolAgent(Agent):
    """
    Tool Agent - Calls external APIs and tools.
    """
    
    def __init__(self):
        super().__init__(
            agent_id="tool_agent",
            role="tool_agent",
            description="Executes external API calls and tool invocations"
        )
        self.tools = {
            "web_search": self._web_search,
            "calculator": self._calculator,
            "weather": self._weather,
            "send_email": self._send_email,
        }
    
    def receive(self, envelope):
        """Process tool request."""
        content = envelope.original.get("content", {})
        
        if isinstance(content, dict):
            action = content.get("action", "")
            params = content.get("params", {})
            
            if action == "call_tool":
                tool_name = params.get("tool", "calculator")
                tool_params = params.get("params", {})
                return self._call_tool(tool_name, tool_params)
        
        return {"error": "No valid tool request"}
    
    def _call_tool(self, tool_name: str, params: dict) -> dict:
        """Call a registered tool."""
        if tool_name in self.tools:
            return self.tools[tool_name](params)
        return {"error": f"Unknown tool: {tool_name}"}
    
    def _web_search(self, params: dict) -> dict:
        query = params.get("query", "")
        return {
            "type": "tool_result",
            "tool": "web_search",
            "result": f"Search results for: {query}",
            "data": [{"title": "Result 1", "url": "https://example.com/1"}]
        }
    
    def _calculator(self, params: dict) -> dict:
        try:
            expression = params.get("expression", "2+2")
            result = eval(expression)
            return {
                "type": "tool_result",
                "tool": "calculator",
                "result": str(result)
            }
        except Exception as e:
            return {"type": "tool_result", "tool": "calculator", "error": str(e)}
    
    def _weather(self, params: dict) -> dict:
        location = params.get("location", "Unknown")
        return {
            "type": "tool_result",
            "tool": "weather",
            "result": f"Weather in {location}: Sunny, 72°F"
        }
    
    def _send_email(self, params: dict) -> dict:
        return {
            "type": "tool_result",
            "tool": "send_email",
            "result": f"Email sent to {params.get('to', 'unknown')}"
        }


class RetrievalAgent(Agent):
    """
    Retrieval Agent - Queries vector store or database.
    """
    
    def __init__(self):
        super().__init__(
            agent_id="retrieval_agent",
            role="retrieval_agent",
            description="Retrieves relevant information from knowledge base"
        )
        self.memory = {
            "documents": [
                {"id": "doc1", "content": "Python is a high-level programming language."},
                {"id": "doc2", "content": "Machine learning is a subset of AI."},
                {"id": "doc3", "content": "TrustChain is a security middleware."},
            ],
            "vector_index": {}  # Would use actual embeddings in production
        }
        self.recent_queries = []
    
    def receive(self, envelope):
        """Process retrieval request."""
        content = envelope.original.get("content", {})
        
        if isinstance(content, dict):
            action = content.get("action", "")
            params = content.get("params", {})
            
            if action == "search":
                query = params.get("query", "")
                return self._search(query)
            elif action == "prepare":
                task = params.get("task", "")
                return self._prepare_context(task)
        
        return {"error": "No valid retrieval request"}
    
    def _search(self, query: str) -> dict:
        """Simple keyword-based search."""
        self.recent_queries.append({
            "query": query,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        results = []
        for doc in self.memory["documents"]:
            if query.lower() in doc["content"].lower():
                results.append(doc)
        
        return {
            "type": "retrieval_result",
            "query": query,
            "results": results,
            "count": len(results)
        }
    
    def _prepare_context(self, task: str) -> dict:
        """Prepare context for a task."""
        return {
            "type": "context",
            "task": task,
            "context": f"Prepared context for: {task}"
        }


class ExecutorAgent(Agent):
    """
    Executor Agent - Takes final actions (write file, send HTTP request, etc.)
    """
    
    def __init__(self):
        super().__init__(
            agent_id="executor_agent",
            role="executor_agent",
            description="Executes final actions like file writes and HTTP requests"
        )
        self.action_log = []
    
    def receive(self, envelope):
        """Process execution request."""
        content = envelope.original.get("content", {})
        
        if isinstance(content, dict):
            action = content.get("action", "")
            params = content.get("params", {})
            
            if action == "execute":
                action_type = params.get("type", "unknown")
                return self._execute(action_type, params)
        
        return {"error": "No valid execution request"}
    
    def _execute(self, action_type: str, params: dict) -> dict:
        """Execute the requested action."""
        self.action_log.append({
            "type": action_type,
            "params": params,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        if action_type == "file_write":
            return {
                "type": "execution_result",
                "action": "file_write",
                "status": "success",
                "path": params.get("path", "/tmp/output.txt")
            }
        elif action_type == "http_request":
            return {
                "type": "execution_result",
                "action": "http_request",
                "status": "sent",
                "url": params.get("url", "https://example.com")
            }
        else:
            return {
                "type": "execution_result",
                "action": action_type,
                "status": "completed"
            }


# Agent registry
_agents = {}


def get_agent(agent_id: str) -> Optional[Agent]:
    """Get an agent by ID."""
    return _agents.get(agent_id)


def register_agent(agent: Agent):
    """Register an agent in the global registry."""
    _agents[agent.agent_id] = agent


def init_agents() -> dict:
    """Initialize all agents and register them."""
    agents = {
        "orchestrator": Orchestrator(),
        "tool_agent": ToolAgent(),
        "retrieval_agent": RetrievalAgent(),
        "executor_agent": ExecutorAgent()
    }
    
    for agent in agents.values():
        register_agent(agent)
    
    return agents


if __name__ == "__main__":
    agents = init_agents()
    for aid, agent in agents.items():
        print(f"Registered: {agent}")