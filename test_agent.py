from person1_agent import CustomerServiceAgent
import database

database.init_db()
agent = CustomerServiceAgent()
print("\n--- AGENT TEST ---")
query = "what is machine learning"
print(f"User: {query}")
response = agent.respond(query)
print(f"Agent: {response}")
print("------------------\n")
