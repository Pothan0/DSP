#!/usr/bin/env python3
"""
TrustChain CLI Entry Point

Usage:
    trustchain start              # Start the MCP gateway
    trustchain verify             # Verify audit chain
    trustchain status             # Show system status
"""
import sys
import argparse
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import get_config, reload_config
from gateway.app import run_server
from audit import get_audit_store
from gateway.session import get_session_manager
from engines import get_hitl_gate


def cmd_start(args):
    """Start the TrustChain MCP Gateway."""
    print("=" * 60)
    print("TrustChain MCP Security Gateway")
    print("=" * 60)
    
    config = get_config()
    print(f"\nConfiguration:")
    print(f"  MCP Server: {config.mcp.host}:{config.mcp.port}")
    print(f"  Transport: {config.mcp.transport}")
    print(f"  Tools configured: {len(config.tools)}")
    print(f"  Trust threshold: {config.trust.decay_threshold}")
    print(f"  HITL enabled: {config.hitl.enabled}")
    print(f"  OTEL enabled: {config.telemetry.otel_enabled}")
    print(f"  Prometheus enabled: {config.telemetry.prometheus_enabled}")
    
    audit_store = get_audit_store()
    chain_valid = audit_store.verify_chain()
    
    print(f"\nAudit Chain: {'VALID' if chain_valid else 'TAMPERED - ABORTING!'}")
    
    if not chain_valid and not args.allow_invalid:
        print("ERROR: Audit chain verification failed!")
        print("Use --allow-invalid to start anyway (not recommended)")
        sys.exit(1)
    
    print(f"\nStarting server on {config.mcp.host}:{config.mcp.port}...")
    run_server()


def cmd_verify(args):
    """Verify the audit chain integrity."""
    print("Verifying audit chain...")
    
    audit_store = get_audit_store()
    valid = audit_store.verify_chain()
    
    if valid:
        print("OK: Audit chain is valid")
        sys.exit(0)
    else:
        print("ERROR: Audit chain has been tampered with!")
        sys.exit(1)


def cmd_status(args):
    """Show system status."""
    config = get_config()
    audit_store = get_audit_store()
    session_manager = get_session_manager()
    hitl_gate = get_hitl_gate()
    
    print("=" * 60)
    print("TrustChain System Status")
    print("=" * 60)
    
    print(f"\nConfiguration:")
    print(f"  Version: 1.0.0")
    print(f"  MCP Port: {config.mcp.port}")
    print(f"  Tools: {len(config.tools)}")
    
    print(f"\nAudit Store:")
    stats = audit_store.get_stats()
    print(f"  Total events: {stats['total_events']}")
    print(f"  Chain valid: {audit_store.verify_chain()}")
    print(f"  Events by type: {stats['event_counts']}")
    
    print(f"\nSessions:")
    active = session_manager.get_active_sessions()
    print(f"  Active: {len(active)}")
    print(f"  Total: {len(session_manager._sessions)}")
    
    print(f"\nHITL Queue:")
    pending = hitl_gate.get_pending()
    print(f"  Pending: {len(pending)}")
    print(f"  History: {len(hitl_gate.get_history())}")
    
    print(f"\nTools by tier:")
    tiers = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for name, tool in config.tools.items():
        tiers[tool.tier] = tiers.get(tool.tier, 0) + 1
    for tier, count in tiers.items():
        print(f"  {tier}: {count}")


def main():
    parser = argparse.ArgumentParser(description="TrustChain MCP Security Gateway")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    start_parser = subparsers.add_parser("start", help="Start the gateway")
    start_parser.add_argument("--allow-invalid", action="store_true", 
                             help="Allow starting even if audit chain is invalid")
    
    subparsers.add_parser("verify", help="Verify audit chain")
    subparsers.add_parser("status", help="Show system status")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "start":
        cmd_start(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "status":
        cmd_status(args)


if __name__ == "__main__":
    main()