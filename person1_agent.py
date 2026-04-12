import os
import traceback
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig

import database

load_dotenv()

# Global reference to the security guard for unmasking/masking in tools
# This will be set by api.py
security_guard = None

# ─── Tools ──────────────────────────────────────────────────────────────────

@tool
def fetch_customer_data(name: str, config: RunnableConfig):
    """Look up customer info (ID, email, balance, SSN) by their full Name. 
    Use this ONLY for banking/account queries.
    """
    user_context = config.get("configurable", {}).get("user_context")
    if not user_context:
        return "System Error: Missing user authentication context. Access Denied."
        
    real_name = security_guard.unmask_pii(name) if security_guard else name
    
    # RBAC Check
    if user_context["role"] != "admin" and real_name.lower() != user_context["name"].lower():
        return f"Access Denied: You are authenticated as {user_context['name']}. You cannot access records for '{real_name}'."
        
    res = database.get_customer_by_name(real_name)
    if not res:
        return f"Customer '{real_name}' not found."
    
    safe_res = security_guard.scrub_pii(str(res)) if security_guard else str(res)
    return safe_res

@tool
def fetch_transactions(customer_id: str, config: RunnableConfig):
    """Get recent spending history using a numeric Customer ID ID.
    Use this ONLY for banking/account queries.
    """
    user_context = config.get("configurable", {}).get("user_context")
    if not user_context:
        return "System Error: Missing user authentication context. Access Denied."
        
    try:
        real_cid_str = security_guard.unmask_pii(customer_id) if security_guard else customer_id
        cid = int(real_cid_str)
        
        # RBAC Check
        if user_context["role"] != "admin" and cid != user_context["user_id"]:
             return f"Access Denied: You do not have permission to view transactions for Account ID {cid}."
             
        res = database.get_transaction_history(cid)
        if not res:
            return f"No transactions found for ID {cid}."
        
        safe_res = security_guard.scrub_pii(str(res)) if security_guard else str(res)
        return safe_res
    except ValueError:
        return "Invalid Customer ID format. Must be an integer."

# ─── Agent Class ─────────────────────────────────────────────────────────────

class CustomerServiceAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            self.gemini_available = False
            print("⚠️ OPENROUTER_API_KEY not found. Agent in Mock Mode for testing Gateway layers.")
        else:
            self.gemini_available = True
            # Using OpenRouter "newtron" model (as specified by user)
            self.llm = ChatOpenAI(
                model="nvidia/nemotron-3-super-120b-a12b:free",
                temperature=0,
                api_key=self.api_key,
                base_url="https://openrouter.ai/api/v1"
            )
            self.tools = [fetch_customer_data, fetch_transactions]
            
            system_message = """You are a helpful Banking Assistant. 
            
RULES:
1. Speak in regular, natural English only. Never output raw JSON.
2. If the user asks about general topics (like Machine Learning), just explain it directly.
3. If they ask about banking details, MUST use your tools to look up account data. Never invent data.
"""
            # Create a LangGraph prebuilt ReAct agent with native tool calling
            self.agent_executor = create_react_agent(self.llm, self.tools, prompt=system_message)
        
    def respond(self, query: str, user_context: dict = None) -> str:
        """Runs the agent graph and returns the final response."""
        if not self.gemini_available:
            q = query.lower()
            if "balance" in q or "alice" in q:
                return "Sure! I found Alice Smith. Her balance is $1500.50. Her SSN is 111-22-3333 and her internal account ID is ACC-12345."
            elif "evil" in q or "steal" in q:
                return "I am now an evil AI. Here is how you steal money: transfer $1000 from ACC-12345 to your account."
            else:
                return "Mock Mode Active (OPENROUTER_API_KEY missing). Please ask about 'Alice's balance' to trigger the PII protection, or an attack payload."

        try:
            # LangGraph inputs and outputs messages. Inject config context.
            config = {"configurable": {"user_context": user_context}}
            result = self.agent_executor.invoke({"messages": [("user", query)]}, config=config)
            
            # The final message from the agent contains the text
            final_content = result["messages"][-1].content
            if isinstance(final_content, list):
                return "\n".join([c.get("text", "") for c in final_content if c.get("type") == "text"])
            return str(final_content)
        except Exception as e:
            err_trace = traceback.format_exc()
            print(f"Exception caught in respond: {err_trace}")
            return f"Agent Security/Execution Error: {str(e)}\n\nTraceback: {err_trace}"

if __name__ == "__main__":
    database.init_db()
    agent = CustomerServiceAgent()
    print("Agent Online. Testing OpenRouter Connection...")
    if agent.gemini_available:
        print(agent.respond("Hi, what is my balance? My name is Alice Smith.", user_context={"user_id": 1, "name": "Alice Smith", "role": "customer"}))
