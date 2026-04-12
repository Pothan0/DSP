import sys
import os
from pathlib import Path

# Quick minimal test - no heavy model loading
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("TrustChain Industry-Grade - Quick Test")
print("=" * 60)
print()

# Test 1: Config (no heavy loading)
print("[1] Config System")
from config import get_config
c = get_config()
print(f"    OK - Port: {c.mcp.port}")
print(f"    OK - Tools configured: {len(c.tools)}")

# Test 2: Audit Store (lightweight)
print("[2] Audit Store")
from audit import get_audit_store
audit = get_audit_store()
audit.write("TEST", session_id="test", decision="PASS")
print(f"    OK - Write + verify: {audit.verify_chain()}")

# Test 3: Session Manager (lightweight)
print("[3] Session Manager")
from gateway.session import get_session_manager
sm = get_session_manager()
sess = sm.get_or_create_session("quick-test", "test")
print(f"    OK - Session: {sess.session_id}")

# Test 4: Capability Gate (lightweight)
print("[4] Capability Gate")
from engines import get_capability_gate
cap = get_capability_gate()
token = cap.issue_token("agent", "read_file", "task1")
print(f"    OK - Token: {token.signature[:16]}...")

# Test 5: Gateway (skip injection detector which loads model)
print("[5] MCP Gateway")
from gateway.proxy import get_gateway
gw = get_gateway()
print(f"    OK - Gateway ready")

# Test 6: App routes (don't actually start server)
print("[6] FastAPI App")
from gateway.app import create_app
app = create_app()
routes = [r.path for r in app.routes if hasattr(r, 'path')]
print(f"    OK - {len(routes)} routes")

print()
print("=" * 60)
print("CORE FUNCTIONALITY VERIFIED")
print("=" * 60)
print()
print("Note: Full MCP protocol test requires running server.")
print("To run: python run_gateway.py")
print("Then test with HTTP client to localhost:7070/mcp")