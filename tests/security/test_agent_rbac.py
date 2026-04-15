import pytest


@pytest.mark.security
def test_patient_can_access_own_record(seeded_db):
    import person1_agent
    from person2_security import SecurityGuard

    person1_agent.security_guard = SecurityGuard()
    result = person1_agent.fetch_patient_data.func(
        "Alice Smith",
        {"configurable": {"user_context": {"user_id": 1, "name": "Alice Smith", "role": "patient"}}},
    )
    assert "Access Denied" not in result


@pytest.mark.security
def test_patient_cannot_access_other_record(seeded_db):
    import person1_agent
    from person2_security import SecurityGuard

    person1_agent.security_guard = SecurityGuard()
    result = person1_agent.fetch_patient_data.func(
        "Bob Jones",
        {"configurable": {"user_context": {"user_id": 1, "name": "Alice Smith", "role": "patient"}}},
    )
    assert "Access Denied" in result


@pytest.mark.security
def test_admin_can_access_any_record(seeded_db):
    import person1_agent
    from person2_security import SecurityGuard

    person1_agent.security_guard = SecurityGuard()
    result = person1_agent.fetch_patient_data.func(
        "Bob Jones",
        {"configurable": {"user_context": {"user_id": 99, "name": "Admin", "role": "admin"}}},
    )
    assert "Access Denied" not in result


@pytest.mark.security
def test_missing_user_context_denied(seeded_db):
    import person1_agent
    from person2_security import SecurityGuard

    person1_agent.security_guard = SecurityGuard()
    result = person1_agent.fetch_patient_data.func("Alice Smith", {"configurable": {}})
    assert "Access Denied" in result
