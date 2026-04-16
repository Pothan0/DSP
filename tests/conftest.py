import os
import uuid
import importlib
import pytest


class _DummyRecognizerRegistry:
    def add_recognizer(self, recognizer):
        return None


class _DummyResult:
    def __init__(self, start, end, entity_type):
        self.start = start
        self.end = end
        self.entity_type = entity_type


class _DummyAnalyzerEngine:
    def __init__(self, *args, **kwargs):
        self.registry = _DummyRecognizerRegistry()

    def analyze(self, text, entities=None, language="en"):
        import re

        hits = []
        patterns = [
            (r"\b\d{3}-\d{2}-\d{4}\b", "US_SSN"),
            (r"\bREC-\d{4,8}\b", "INTERNAL_RECORD_ID"),
            (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "EMAIL_ADDRESS"),
            (r"\b\d{4}-\d{4}-\d{4}-\d{4}\b", "CREDIT_CARD"),
            (r"\b(?:Alice Smith|Bob Jones|Charlie Brown|Diana Prince|Dr House|Dr\. House)\b", "PERSON"),
        ]
        for pattern, ent in patterns:
            if entities is not None and ent not in entities:
                continue
            for match in re.finditer(pattern, text):
                hits.append(_DummyResult(match.start(), match.end(), ent))
        return hits


class _DummyAnonymizerEngine:
    pass


@pytest.fixture(autouse=True)
def patch_pii_dependencies(monkeypatch):
    import person2_security

    monkeypatch.setattr(person2_security, "AnalyzerEngine", _DummyAnalyzerEngine)
    monkeypatch.setattr(person2_security, "AnonymizerEngine", _DummyAnonymizerEngine)


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")


@pytest.fixture
def fresh_security_guard():
    from person2_security import SecurityGuard
    return SecurityGuard()


@pytest.fixture
def fresh_threat_scorer(monkeypatch):
    import person3_scorer

    monkeypatch.setattr(person3_scorer, "pipeline", lambda *args, **kwargs: None)
    return person3_scorer.ThreatScorer(threshold=0.75)


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    import database
    import audit_logger

    db_path = tmp_path / f"test_{uuid.uuid4().hex}.db"
    monkeypatch.setattr(database, "DB_FILE", str(db_path))
    monkeypatch.setattr(audit_logger, "DB_FILE", str(db_path))

    database.init_db()
    audit_logger.init_log_table()
    return db_path


@pytest.fixture
def api_client(seeded_db, monkeypatch):
    from fastapi.testclient import TestClient
    import person3_scorer

    monkeypatch.setattr(person3_scorer, "pipeline", lambda *args, **kwargs: None)

    import api
    importlib.reload(api)

    api.guard.vault.clear()
    api.scorer.classifier = None

    def fake_respond(query, user_context=None):
        q = (query or "").lower()
        if "bob" in q and user_context and user_context.get("role") != "admin":
            return "Access Denied: cross-user access blocked"
        if "diagnosis" in q:
            return "Patient diagnosis is Hypertension. SSN is 111-22-3333."
        return "Safe informational response"

    api.agent.respond = fake_respond

    client = TestClient(api.app)
    return client
