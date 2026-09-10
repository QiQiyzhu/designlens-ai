import json

import pytest

from backend.remote_provider import RemoteProviderError
from scripts import research_ablation as probe


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("DESIGNLENS_PROVIDER", "deepseek")
    monkeypatch.setenv("DESIGNLENS_API_KEY", "test-only-no-real-credential")
    monkeypatch.setenv("DESIGNLENS_API_BASE", "https://api.deepseek.com")


def test_frozen_preflight_is_zero_call_and_bounds_are_explicit(configured, monkeypatch):
    monkeypatch.setattr(probe, "call_remote", lambda *args: pytest.fail("Preflight called model"))
    result = probe.run()
    assert result["planned_rows"] == 36 and result["attempted_calls"] == 0
    assert result["status"] == "ready_not_executed" and result["complete"] is False
    assert result["real_participants"] == result["validated_product_decisions"] == 0
    with pytest.raises(ValueError):
        probe.run(max_calls=121)


def test_budget_stop_preserves_partial_receipt(configured, monkeypatch, tmp_path):
    calls = []
    def response(prompt, message, schema):
        calls.append(message)
        return {"output": {"claims": [], "abstained": True}, "token_usage": {"total_tokens": 11},
                "provider_trace": {"attempts": 1, "response_received": True}, "latency_ms": 1, "model": "mock-transport-test"}
    monkeypatch.setattr(probe, "call_remote", response)
    output = tmp_path / "receipt.json"
    result = probe.run(execute=True, max_calls=2, output=output)
    assert len(calls) == result["attempted_calls"] == 2
    assert result["status"] == "budget_stopped" and not result["complete"]
    assert result["observed_tokens"] == 22
    assert json.loads(output.read_text())["results"] == result["results"]


def test_transport_failure_stops_without_retries_and_usage_is_unknown(configured, monkeypatch):
    calls = []
    def fail(*args):
        calls.append(1)
        raise RemoteProviderError("HTTP 429", {"attempts": 1, "response_received": False, "token_usage": None})
    monkeypatch.setattr(probe, "call_remote", fail)
    result = probe.run(execute=True)
    assert result["status"] == "failed" and len(calls) == 1
    assert result["attempted_calls"] == 1 and not result["usage_complete"]
    assert result["cost_usd"] is None and not result["complete"]
