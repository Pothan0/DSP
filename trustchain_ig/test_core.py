import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=== TrustChain Industry-Grade ===")
print()

# Test only non-embedding modules
print("Testing Config...")
from config import get_config
print(f"  OK - Port: {get_config().mcp.port}")

print("Testing Audit...")
from audit import get_audit_store
store = get_audit_store()
store.write("TEST", session_id="x", decision="PASS")
print(f"  OK - Verified: {store.verify_chain()}")

print("Testing Capability Gate...")
from engines.capability import get_capability_gate
gate = get_capability_gate()
token = gate.issue_token("agent1", "read_file", "task1")
print(f"  OK - Token issued")

print("Testing HITL Gate...")
from engines.hitl import get_hitl_gate
hitl = get_hitl_gate()
print(f"  OK - {len(hitl.get_pending())} pending")

print()
print("Core modules verified!")
print()
print("Note: Session manager and injection detector load")
print("embedding model on first use - this may delay startup.")
print()
print("To run server: python run_gateway.py")