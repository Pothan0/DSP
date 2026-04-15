import pytest


@pytest.mark.security
def test_high_tier_valid_token_authorized(gateway_env):
    from engines.capability import get_capability_gate

    gate = get_capability_gate()
    token = gate.issue_token("agent-a", "write_file", "task-1")

    result = gate.validate("agent-a", "write_file", "task-1", token.to_payload(), token.signature)
    assert result["authorized"] is True


@pytest.mark.security
def test_token_tamper_rejected(gateway_env):
    from engines.capability import get_capability_gate

    gate = get_capability_gate()
    token = gate.issue_token("agent-a", "write_file", "task-1")
    payload = token.to_payload()
    payload["tool_name"] = "delete_resource"

    result = gate.validate("agent-a", "delete_resource", "task-1", payload, token.signature)
    assert result["authorized"] is False
    assert result["reason"] in {"INVALID_SIGNATURE", "TOOL_MISMATCH"}


@pytest.mark.security
def test_max_calls_enforced(gateway_env):
    from engines.capability import get_capability_gate
    from config import get_config

    gate = get_capability_gate()
    cfg = get_config()
    cfg.tools["search_database"].max_calls = 1
    token = gate.issue_token("agent-a", "search_database", "task-1", max_calls=1)

    first = gate.validate("agent-a", "search_database", "task-1", token.to_payload(), token.signature)
    second = gate.validate("agent-a", "search_database", "task-1", token.to_payload(), token.signature)

    assert first["authorized"] is True
    assert second["authorized"] is False
    assert second["reason"] == "MAX_CALLS_EXCEEDED"
