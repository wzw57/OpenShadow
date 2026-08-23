from __future__ import annotations

import pytest
from shadow_application import DeterministicPeripheralAdapter, InteractionRequest


def _request(**overrides: object) -> InteractionRequest:
    values: dict[str, object] = {
        "operation": "shadow.device.observe",
        "principal_ref": "principal-device",
        "space_id": "space-personal",
        "endpoint_ref": "endpoint-local-web",
        "capability_ref": "capability.device.observe",
        "consent_ref": "consent-device-1",
        "data_classification": "personal",
        # Keep the replay fixture byte-identical across calls; expiry semantics
        # are covered separately by the explicit expired request below.
        "expires_at": "2099-01-01T00:00:00Z",
        "idempotency_key": "device-1",
        "typed_input": {"device_ref": "device-local"},
    }
    values.update(overrides)
    return InteractionRequest(**values)


def test_deterministic_adapter_enforces_capability_and_replay() -> None:
    adapter = DeterministicPeripheralAdapter(supported_capabilities={"capability.device.observe"})
    first = adapter.execute(_request())
    replay = adapter.execute(_request())
    assert first.status == "succeeded"
    assert replay.replayed is True
    assert adapter.calls == 1


def test_expired_or_inline_secret_requests_are_rejected() -> None:
    adapter = DeterministicPeripheralAdapter(supported_capabilities={"capability.device.observe"})
    with pytest.raises(ValueError, match="expired"):
        adapter.execute(_request(expires_at="2000-01-01T00:00:00Z"))
    with pytest.raises(ValueError, match="inline Secret"):
        adapter.execute(_request(typed_input={"api_key": "inline"}))


def test_unknown_provider_result_is_not_retried() -> None:
    adapter = DeterministicPeripheralAdapter(supported_capabilities={"capability.device.observe"}, outcome="unknown")
    first = adapter.execute(_request())
    replay = adapter.execute(_request())
    assert first.status == "unknown"
    assert replay.replayed is True
    assert adapter.calls == 1
