import json

import httpx
import pytest

from backend import engine
from backend.remote_provider import MAX_RESPONSE_BYTES, RemoteConfig, RemoteProviderError, call_remote
from scripts.real_model_smoke import main, smoke


PROMPT = {"output_mode": "structured", "temperature": 0, "template": "Task: {{input}}\nSources: {{context}}"}
ANSWER = {"claims": [], "abstained": True}


@pytest.fixture
def configured(monkeypatch):
    for name in ("DESIGNLENS_TOKEN_PARAMETER", "DESIGNLENS_MAX_OUTPUT_TOKENS", "DESIGNLENS_TIMEOUT_SECONDS", "DESIGNLENS_ALLOW_REAL_REMOTE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("DESIGNLENS_PROVIDER", "deepseek")
    monkeypatch.setenv("DESIGNLENS_MODEL", "deepseek-flash")
    monkeypatch.setenv("DESIGNLENS_API_KEY", "test-only-secret-not-a-real-key")
    monkeypatch.setenv("DESIGNLENS_API_BASE", "https://api.deepseek.com")


def envelope(output=ANSWER, **overrides):
    return {"model": "deepseek-flash-test-snapshot", "choices": [{"message": {"content": json.dumps(output)}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 15, "completion_tokens": 7, "total_tokens": 22}, **overrides}


def install_transport(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(engine, "call_remote", lambda prompt, message, schema: call_remote(prompt, message, schema, transport=transport))


def test_deepseek_wire_contract_and_observed_provenance(configured):
    requests = []
    def handler(request):
        requests.append(request)
        body = json.loads(request.content)
        assert body["thinking"] == {"type": "disabled"} and body["stream"] is False
        assert "enable_thinking" not in body
        assert body["response_format"] == {"type": "json_object"}
        assert body["max_tokens"] == 768 and "extra_body" not in body
        assert "reference_evidence" not in request.content.decode()
        return httpx.Response(200, json=envelope(), headers={"x-request-id": "test-request-1"})
    result = call_remote(PROMPT, "Only synthetic context", engine.OUTPUT_SCHEMA, transport=httpx.MockTransport(handler))
    assert len(requests) == 1 and str(requests[0].url) == "https://api.deepseek.com/chat/completions"
    assert result["model"] == "deepseek-flash-test-snapshot" and result["requested_model"] == "deepseek-flash"
    assert result["token_usage"]["total_tokens"] == 22 and result["cost_usd"] is None
    assert result["provider_trace"]["request_id"] == "test-request-1"
    assert len(result["provider_trace"]["response_sha256"]) == 64
    assert "test-only-secret" not in repr(result) + repr(RemoteConfig.from_env())


def test_deepseek_shared_key_defaults_and_cache_usage(configured, monkeypatch):
    for name in ("DESIGNLENS_API_KEY", "DESIGNLENS_MODEL", "DESIGNLENS_API_BASE"):
        monkeypatch.delenv(name)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-shared-key")
    config = RemoteConfig.from_env()
    assert config.model == "deepseek-flash" and config.base_url == "https://api.deepseek.com"
    assert config.key == "test-only-shared-key" and "test-only-shared-key" not in repr(config)
    result = call_remote(PROMPT, "synthetic", engine.OUTPUT_SCHEMA, transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json=envelope(usage={"prompt_tokens": 30, "completion_tokens": 10,
            "total_tokens": 40, "prompt_cache_hit_tokens": 20, "prompt_cache_miss_tokens": 10, "private_text": "never retain"}))))
    assert result["token_usage"]["prompt_cache_hit_tokens"] == 20
    assert "private_text" not in result["token_usage"]


def test_missing_usage_is_not_fabricated_and_openai_omits_sampling(configured, monkeypatch):
    monkeypatch.setenv("DESIGNLENS_PROVIDER", "openai-compatible")
    monkeypatch.setenv("DESIGNLENS_API_BASE", "https://api.openai.com/v1")
    def handler(request):
        body = json.loads(request.content)
        assert "max_completion_tokens" in body and "max_tokens" not in body
        assert "temperature" not in body and "enable_thinking" not in body
        return httpx.Response(200, json=envelope(usage=None))
    result = call_remote(PROMPT, "synthetic", engine.OUTPUT_SCHEMA, transport=httpx.MockTransport(handler))
    assert result["token_usage"] is None


@pytest.mark.parametrize("name,value", [
    ("DESIGNLENS_API_BASE", "http://example.invalid/v1"),
    ("DESIGNLENS_API_BASE", "https://user:secret@example.invalid/v1"),
    ("DESIGNLENS_API_BASE", "https://example.invalid/v1?key=secret"),
    ("DESIGNLENS_API_BASE", "https://{WorkspaceId}.example.invalid/v1"),
    ("DESIGNLENS_API_BASE", "https://other.invalid/v1"),
    ("DESIGNLENS_TOKEN_PARAMETER", "max_completion_tokens"),
    ("DESIGNLENS_MAX_OUTPUT_TOKENS", "2001"),
    ("DESIGNLENS_TIMEOUT_SECONDS", "nan"),
])
def test_invalid_configuration_never_reaches_network(configured, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    transport = httpx.MockTransport(lambda request: pytest.fail("Invalid configuration reached network"))
    with pytest.raises(ValueError):
        call_remote(PROMPT, "synthetic", engine.OUTPUT_SCHEMA, transport=transport)


def test_unlabelled_or_real_sources_block_before_transport(configured, monkeypatch):
    monkeypatch.setattr(engine, "call_remote", lambda *args: pytest.fail("Real data reached remote provider"))
    for source in ({"id": "e1", "content": "Private source"}, {"id": "e1", "content": "Private source", "is_demo": False}):
        with pytest.raises(ValueError, match="local-only"):
            engine.provider_call(PROMPT, "question", [source])


def test_http_429_and_redirect_never_retry_or_echo_body(configured):
    for status in (429, 307):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(status, text="test-only-secret-not-a-real-key private-research", headers={"location": "https://other.invalid"})
        with pytest.raises(RemoteProviderError) as exc:
            call_remote(PROMPT, "synthetic", engine.OUTPUT_SCHEMA, transport=httpx.MockTransport(handler))
        assert len(calls) == 1
        assert "private-research" not in str(exc.value) and "test-only-secret" not in repr(exc.value.metadata)
        assert exc.value.metadata["http_status"] == status
        assert exc.value.metadata["latency_ms"] >= 0


def test_timeout_redacts_exception_and_keeps_unknown_usage(configured):
    def handler(request):
        raise httpx.ReadTimeout("private-research test-only-secret-not-a-real-key", request=request)
    with pytest.raises(RemoteProviderError) as exc:
        call_remote(PROMPT, "synthetic", engine.OUTPUT_SCHEMA, transport=httpx.MockTransport(handler))
    assert "ReadTimeout" in str(exc.value) and "private-research" not in str(exc.value)
    assert exc.value.metadata["token_usage"] is None and exc.value.metadata["attempts"] == 1


def test_truncated_refused_and_invalid_json_responses_preserve_observed_usage(configured):
    invalid = [
        {"message": {"content": "{broken"}, "finish_reason": "stop"},
        {"message": {"content": json.dumps(ANSWER)}, "finish_reason": "length"},
        {"message": {"content": None, "refusal": "private-refusal"}, "finish_reason": "stop"},
    ]
    for choice in invalid:
        with pytest.raises(RemoteProviderError) as exc:
            call_remote(PROMPT, "synthetic", engine.OUTPUT_SCHEMA,
                        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=envelope(choices=[choice]))))
        assert exc.value.metadata["token_usage"]["total_tokens"] == 22
        assert exc.value.metadata["response_received"] is True and "private-refusal" not in str(exc.value)


def test_input_and_response_size_caps(configured):
    with pytest.raises(ValueError, match="64 KiB"):
        call_remote(PROMPT, "x" * 65536, engine.OUTPUT_SCHEMA, transport=httpx.MockTransport(lambda r: pytest.fail("Oversize request sent")))
    with pytest.raises(RemoteProviderError, match="1 MiB"):
        call_remote(PROMPT, "synthetic", engine.OUTPUT_SCHEMA,
                    transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1))))


def test_preflight_and_missing_key_perform_zero_calls(configured, monkeypatch, tmp_path):
    monkeypatch.setattr(engine, "call_remote", lambda *args: pytest.fail("Preflight called model"))
    result = smoke()
    assert result["status"] == "ready_not_executed" and result["attempted_calls"] == 0
    monkeypatch.delenv("DESIGNLENS_API_KEY")
    path = tmp_path / "missing-key.json"
    assert main(["--execute", "--output", str(path)]) == 2
    missing = json.loads(path.read_text())
    assert missing["status"] == "not_configured" and missing["results"] == []
    assert missing["real_participants"] == missing["validated_product_decisions"] == 0


def test_smoke_enforces_call_cap_and_stops_on_transport_failure(configured, monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(429, text="Never persist this body")
    install_transport(monkeypatch, handler)
    result = smoke(execute=True, max_calls=3)
    assert len(calls) == result["attempted_calls"] == 1
    assert result["status"] == "failed" and len(result["results"]) == 1
    assert "Never persist" not in json.dumps(result)
    for limit in (0, 4, True):
        with pytest.raises(ValueError):
            smoke(execute=True, max_calls=limit)


def test_smoke_distinguishes_valid_citation_from_relevance(configured, monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        content = json.loads(request.content)["messages"][-1]["content"]
        if "invoice" in content:
            quote, source = "SYNTHETIC: The invoice export arrived on Tuesday.", "e2"
        else:
            quote, source = "SYNTHETIC: The route legend is difficult to find.", "e1"
        return httpx.Response(200, json=envelope({"claims": [{"text": quote, "quote": quote, "evidence_id": source}], "abstained": False}))
    install_transport(monkeypatch, handler)
    result = smoke(execute=True, max_calls=2)
    assert len(calls) == result["attempted_calls"] == 2
    first, irrelevant = result["results"]
    assert first["task_success"] is True
    assert irrelevant["checks"]["evidence_grounding"] is True
    assert irrelevant["checks"]["abstention_behavior"] is False and irrelevant["task_success"] is False
    assert result["real_participants"] == result["validated_product_decisions"] == 0
    assert all(row["human_review"] == "pending" for row in result["results"])
