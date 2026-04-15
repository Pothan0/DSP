# Security Testing Guide

This repository now includes pytest-based security validation for both:

- Root SentriCore pipeline (`api.py`, `person1_agent.py`, `person2_security.py`, `person3_scorer.py`)
- TrustChain industry-grade path (`trustchain_ig/`)

## Test Layout

- `tests/security/`
  - Threat detection classification and adversarial coverage
  - Fuzz-style mutation tests for evasion resistance
  - PII scrub/unmask tokenization tests
  - RBAC behavior tests
  - Regression metrics checks (precision/recall/FPR guardrails)
- `tests/integration/`
  - End-to-end API security pipeline behavior and audit chain checks
- `trustchain_ig/tests/`
  - Injection detector behavior
  - Capability token authorization and abuse controls
  - Gateway security flow (block/escalate behavior)

## Markers

- `security`: adversarial, policy, and regression security tests
- `integration`: cross-module behavior tests

## Commands

Run all tests:

```bash
pytest
```

Run only security tests:

```bash
pytest -m security
```

Run security tests with coverage gate:

```bash
pytest -m security --cov=. --cov-report=term-missing --cov-fail-under=60
```

## Recommended Quality Gates

- All `security` tests pass in CI
- No RBAC bypass regressions
- Threat scorer metrics floor in `test_threat_regression_metrics.py` remains green
- Audit chain verification endpoint remains valid in integration tests

## Extending the Suite

1. Add new attack samples to scorer test parametrizations.
2. Add false-positive safe prompts before introducing new block patterns.
3. For TrustChain, add gateway tests for any new high/critical tools.
4. Keep tests deterministic; use fixtures/mocks for heavyweight dependencies.
