import pytest


@pytest.mark.security
def test_pii_scrub_and_unmask_roundtrip(fresh_security_guard):
    text = "My name is Alice Smith and my SSN is 111-22-3333 with ID REC-12345"
    scrubbed = fresh_security_guard.scrub_pii(text)

    assert scrubbed != text
    assert "111-22-3333" not in scrubbed
    assert "REC-12345" not in scrubbed

    restored = fresh_security_guard.unmask_pii(scrubbed)
    assert restored == text


@pytest.mark.security
def test_generated_tokens_are_unique(fresh_security_guard):
    text = "Alice Smith Alice Smith"
    scrubbed = fresh_security_guard.scrub_pii(text)

    tokens = [token for token in fresh_security_guard.vault.keys() if token in scrubbed]
    assert len(tokens) >= 2
    assert len(tokens) == len(set(tokens))


@pytest.mark.security
def test_unmask_on_unknown_token_is_noop(fresh_security_guard):
    text = "No secret here <US_SSN_deadbeef>"
    restored = fresh_security_guard.unmask_pii(text)
    assert restored == text
