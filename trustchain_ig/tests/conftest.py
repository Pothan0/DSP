import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def light_embedding_encoder(monkeypatch):
    from gateway import session as session_module

    class DummyEncoder:
        def encode(self, texts):
            vectors = []
            for text in texts:
                s = str(text)
                length = float(len(s))
                checksum = float(sum(ord(c) for c in s) % 997)
                vectors.append([length, checksum, 1.0])
            return vectors

    monkeypatch.setattr(session_module.SessionManager, "_get_encoder", lambda self: DummyEncoder())


@pytest.fixture
def gateway_env(tmp_path, monkeypatch):
    from config import schema as config_schema
    from audit import chain as audit_chain
    from gateway import proxy as proxy_module
    from gateway import session as session_module
    from engines import capability as capability_module
    from engines import hitl as hitl_module
    from engines import injection as injection_module

    config_path = ROOT / "config" / "defaults.yaml"
    cfg = config_schema.load_config(str(config_path))
    cfg.audit.database_url = str(tmp_path / "trustchain_test_audit.db")
    cfg.hitl.timeout_seconds = 1

    monkeypatch.setattr(config_schema, "_config", cfg)
    monkeypatch.setattr(config_schema, "get_config", lambda: cfg)

    monkeypatch.setattr(audit_chain, "_audit_store", None)
    monkeypatch.setattr(proxy_module, "_gateway", None)
    monkeypatch.setattr(session_module, "_session_manager", None)
    monkeypatch.setattr(capability_module, "_capability_gate", None)
    monkeypatch.setattr(hitl_module, "_hitl_gate", None)
    monkeypatch.setattr(injection_module, "_injection_detector", None)

    return cfg
