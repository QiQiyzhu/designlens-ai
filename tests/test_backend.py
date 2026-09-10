import copy
import json

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.engine import grounding_errors, provider_call


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DESIGNLENS_PROVIDER", "extractive")
    app = create_app(str(tmp_path / "test.sqlite3"))
    with TestClient(app) as client:
        yield client


def bootstrap(client):
    return client.get("/api/bootstrap").json()


def accepted(client):
    insight = bootstrap(client)["insights"][0]
    response = client.patch(f"/api/insights/{insight['id']}", json={"status": "accepted", "review_note": "Reviewed synthetic excerpt; no real claim"})
    assert response.status_code == 200
    return response.json()


def opportunity(client, confirmed=False):
    insight = accepted(client)
    response = client.post("/api/opportunities", json={"insight_ids": [insight["id"]], "title": "Clarify resonance", "problem": "Synthetic comprehension task", "reach": 10, "impact": 2, "confidence": 0.5, "effort": 2})
    assert response.status_code == 201
    result = response.json()
    if confirmed:
        response = client.patch(f"/api/opportunities/{result['id']}/decision", json={"decision": "confirmed", "reason": "Use only as demonstration hypothesis"})
        result = response.json()
    return result


def test_empty_research_is_not_fake_users(client):
    data = bootstrap(client)
    assert data["project"]["real_participant_count"] == 0
    assert data["meta"]["real_source_count"] == 0
    assert all(s["is_demo"] for s in data["sources"])
    assert all(i["status"] == "suggested" for i in data["insights"])
    assert not data["opportunities"]
    assert data["analytics"]["weekly_validated_decisions"] == 0


@pytest.mark.parametrize("filename,content,count", [
    ("notes.txt", "A task observation", 1), ("notes.md", "# Source\nExact **text**", 1),
    ("notes.csv", 'content,participant\n"First, quoted",P01\nSecond,P02', 2),
    ("notes.json", '[{"content":"One","source_id":"original-1"},{"content":"Two"}]', 2),
])
def test_four_format_import_preserves_provenance(client, filename, content, count):
    result = client.post("/api/sources/import", json={"filename": filename, "content": content})
    assert result.status_code == 201, result.text
    data = result.json()
    assert data["imported"] == count
    for source in data["sources"]:
        assert source["id"] == source["source_id"]
        assert source["metadata"]["import_sha256"]
        assert source["metadata"]["timestamp_basis"] == "import_time"
        assert client.get(f"/api/sources/{source['id']}").json()["content"] == source["content"]


@pytest.mark.parametrize("filename,content", [
    ("invalid.json", "{"), ("empty.csv", "participant\nP01"), ("bad.json", '[{"content":"valid"},{"content":""}]'),
    ("script.py", "print('hi')"), ("empty.txt", "   "),
    ("bad-date.json", '[{"content":"valid","timestamp":"2026-09-10"}]'),
    ("bad-meta.json", '[{"content":"valid","metadata":42}]'),
])
def test_import_rejects_malformed_atomically(client, filename, content):
    before = len(bootstrap(client)["sources"])
    assert client.post("/api/sources/import", json={"filename": filename, "content": content}).status_code == 422
    assert len(bootstrap(client)["sources"]) == before


def test_real_data_requires_consent_and_stays_real(client):
    payload = {"filename": "notes.txt", "content": "Consented redacted local observation", "is_demo": False}
    assert client.post("/api/sources/import", json=payload).status_code == 422
    payload["consent_confirmed"] = True
    payload["privacy_review_digest"] = client.post("/api/sources/preview", json=payload).json()["preview_digest"]
    source = client.post("/api/sources/import", json=payload).json()["sources"][0]
    assert source["is_demo"] is False
    assert bootstrap(client)["meta"]["real_source_count"] == 1
    assert client.get("/api/analytics?is_demo=false").json()["event_count"] == 1


def test_generate_extracts_have_exact_quotes_and_no_model_usage(client):
    source = bootstrap(client)["sources"][0]
    response = client.post("/api/insights/generate", json={"source_ids": [source["id"]]})
    assert response.status_code == 201
    data = response.json()
    assert data["provider"] == "extractive" and data["token_usage"] is None
    insight = data["insights"][0]
    assert insight["evidence"][0]["quote"] in source["content"]
    assert insight["status"] == "suggested" and insight["confidence"] == "Low"


def test_unknown_source_cannot_generate(client):
    assert client.post("/api/insights/generate", json={"source_ids": ["missing"]}).status_code == 404


@pytest.mark.parametrize("output", [
    {"claims": [{"text": "invented", "quote": "invented", "evidence_id": "real"}], "abstained": False},
    {"claims": [{"text": "text", "quote": "text", "evidence_id": "missing"}], "abstained": False},
    {"claims": [{"text": "Everyone agrees", "quote": "text", "evidence_id": "real"}], "abstained": False},
])
def test_unverifiable_claims_fail_grounding(output):
    assert grounding_errors(output, [{"id": "real", "content": "text"}])


def test_human_gate_and_rice_are_explicit(client):
    insight = bootstrap(client)["insights"][0]
    body = {"insight_ids": [insight["id"]], "title": "Potential task", "problem": "Task hypothesis"}
    assert client.post("/api/opportunities", json=body).status_code == 422
    item = opportunity(client)
    assert item["rice"] == 5
    assert item["ice"] == 0.5
    assert item["human_decision"]["decision"] == "pending"
    assert "not a model" in item["recommendation_basis"]


def test_acceptance_denominator_does_not_count_repeated_clicks(client):
    item = accepted(client)
    client.patch(f"/api/insights/{item['id']}", json={"status": "accepted", "review_note": "Reviewed again"})
    metric = bootstrap(client)["analytics"]["insight_acceptance"]
    assert metric["accepted"] == 1 and metric["rate"] == 1
    events = [e for e in bootstrap(client)["analytics"]["recent_events"] if e["name"] == "insight_accepted"]
    assert len(events) == 1


@pytest.mark.parametrize("inputs,expected", [
    ({"task_type": "ui"}, "No AI"), ({"task_type": "rules"}, "Rules"),
    ({"task_type": "lookup"}, "Search"), ({"task_type": "classification", "data_availability": "labeled"}, "Traditional ML"),
    ({"task_type": "language", "privacy": "approved_remote"}, "RAG"),
    ({"task_type": "language", "privacy": "approved_remote", "tool_required": True}, "Agent"),
    ({"task_type": "language", "privacy": "local_only"}, "Search"),
    ({"task_type": "language", "privacy": "approved_remote", "data_availability": "none"}, "No AI"),
])
def test_feasibility_does_not_always_recommend_agent(client, inputs, expected):
    opp = opportunity(client)
    result = client.post("/api/feasibility", json={"opportunity_id": opp["id"], **inputs}).json()
    assert result["recommended_architecture"] == expected
    assert len(result["options"]) == 8
    assert result["non_ai_alternative"]


def test_prompt_version_diff_and_rollback_are_immutable(client):
    original = bootstrap(client)["prompts"][0]["versions"][1]
    body = {k: original[k] for k in ("goal", "template", "variables", "model", "temperature", "output_mode")}
    body["template"] += "\nKeep counterexamples visible."
    result = client.post("/api/prompts/evidence-summary/versions", json=body).json()
    assert result["active_version"] == 3
    assert result["versions"][1]["template"] == original["template"]
    assert "counterexamples" in client.get("/api/prompts/evidence-summary/diff?from_version=2&to_version=3").json()["diff"]
    rollback = client.post("/api/prompts/evidence-summary/rollback", json={"version": 1}).json()
    assert rollback["active_version"] == 4 and len(rollback["versions"]) == 4
    assert rollback["versions"][-1]["template"] == rollback["versions"][0]["template"]
    assert rollback["versions"][-1]["evaluation_result"] is None


def test_workflow_human_review_pins_snapshot(client):
    run = client.post("/api/workflows/evidence-workflow/run", json={"input": "resonance", "source_ids": ["demo-onboarding"]}).json()
    assert run["status"] == "pending_approval" and run["prompt_version"] == 2
    assert run["token_usage"] is None
    client.post("/api/prompts/evidence-summary/rollback", json={"version": 1})
    result = client.post(f"/api/runs/{run['id']}/approval", json={"approved": True, "note": "Exact excerpt checked"}).json()
    assert result["status"] == "completed" and result["prompt_version"] == 2
    assert result["human_review"]["approved"] is True
    assert client.post(f"/api/runs/{run['id']}/approval", json={"approved": True, "note": "Repeated review"}).status_code == 422


def test_rejected_approval_is_not_success(client):
    run = client.post("/api/workflows/evidence-workflow/run", json={"input": "route"}).json()
    result = client.post(f"/api/runs/{run['id']}/approval", json={"approved": False, "note": "Not relevant enough"}).json()
    assert result["status"] == "rejected"
    assert bootstrap(client)["analytics"]["workflow_success"]["rate"] == 0


def test_no_context_abstains_without_call(client):
    result = client.post("/api/workflows/evidence-workflow/run", json={"input": "unmatchedword", "source_ids": []}).json()
    assert result["status"] == "abstained"
    assert result["model"] is None and result["output"]["abstained"] is True


def test_mixed_demo_data_cannot_count_as_real_run(client):
    payload = {"filename": "real.txt", "content": "Consented route task", "is_demo": False, "consent_confirmed": True}
    payload["privacy_review_digest"] = client.post("/api/sources/preview", json=payload).json()["preview_digest"]
    source = client.post("/api/sources/import", json=payload).json()["sources"][0]
    run = client.post("/api/workflows/evidence-workflow/run", json={"input": "route", "source_ids": [source["id"], "demo-route"]}).json()
    assert run["is_demo"] is True


def test_workflow_versions_diff_and_unsupported_mcp_are_real(client):
    original = bootstrap(client)["workflows"][0]["versions"][0]
    body = {k: copy.deepcopy(original[k]) for k in ("name", "description", "nodes", "prompt_id", "prompt_version")}
    body["nodes"].insert(1, {"id": "external", "type": "MCP", "label": "Unavailable connector", "config": {}})
    updated = client.post("/api/workflows/evidence-workflow/versions", json=body)
    assert updated.status_code == 201
    assert "MCP" in client.get("/api/workflows/evidence-workflow/diff").json()["diff"]
    run = client.post("/api/workflows/evidence-workflow/run", json={"input": "route"}).json()
    assert run["status"] == "failed"
    assert "not implemented" in run["error"]


def test_duplicate_workflow_nodes_rejected(client):
    original = bootstrap(client)["workflows"][0]["versions"][0]
    body = {k: copy.deepcopy(original[k]) for k in ("name", "nodes", "prompt_id", "prompt_version")}
    body["nodes"][1]["id"] = body["nodes"][0]["id"]
    assert client.post("/api/workflows", json=body).status_code == 422


def test_evaluation_executes_all_cases_and_preserves_failures(client):
    response = client.post("/api/evaluations/run", json={"workflow_id": "evidence-workflow", "prompt_versions": [1, 2]})
    assert response.status_code == 201, response.text
    report = response.json()
    assert len(report["results"]) == 48
    assert len(report["dataset_sha256"]) == 64
    baseline = next(v for v in report["comparison"] if v["variant"] == "Prompt V1")
    assert baseline["passed"] == 0 and baseline["format_validity"] == 0
    assert all(row["latency_ms"] >= 0 for row in report["results"])
    assert all(row["human_rating"] is None and row["token_usage"] is None for row in report["results"])
    assert report["skipped"][0]["variant"] == "Agent"
    assert next(v for v in report["comparison"] if v["variant"] == "Workflow")["pending_human_review"] > 0


def test_experiment_requires_confirmed_opportunity_and_never_fakes_result(client):
    opp = opportunity(client)
    body = {"opportunity_id": opp["id"], "title": "Route labels pilot", "hypothesis": "Context labels may reduce task confusion", "primary_metric": "Unaided task completion", "decision_rule": "Proceed only if observed critical errors decline without new critical errors"}
    assert client.post("/api/experiments", json=body).status_code == 422
    client.patch(f"/api/opportunities/{opp['id']}/decision", json={"decision": "confirmed", "reason": "Synthetic protocol only"})
    result = client.post("/api/experiments", json=body).json()
    assert result["status"] == "planned" and result["result"] is None
    assert bootstrap(client)["analytics"]["weekly_validated_decisions"] == 0
    assert bootstrap(client)["analytics"]["funnel"][-1]["projects"] == 1


def test_no_denominator_is_null(client):
    data = client.get("/api/analytics?is_demo=false").json()
    assert data["dau"] == 0
    assert data["insight_acceptance"]["rate"] is None
    assert data["workflow_success"]["rate"] is None


def test_remote_provider_does_not_silently_fake_results(monkeypatch):
    monkeypatch.setenv("DESIGNLENS_PROVIDER", "openai-compatible")
    monkeypatch.delenv("DESIGNLENS_API_KEY", raising=False)
    with pytest.raises(ValueError, match="needs"):
        provider_call({"output_mode": "structured"}, "question", [])


def test_export_retains_demo_labels_and_sources(client):
    result = client.get("/api/export").json()
    assert "consent" in result["warning"]
    assert result["sources"][0]["is_demo"] is True


def test_rejected_underlying_evidence_blocks_later_confirmation(client):
    opp = opportunity(client)
    client.patch(f"/api/insights/{opp['insight_ids'][0]}", json={"status": "rejected", "review_note": "Found insufficient support"})
    response = client.patch(f"/api/opportunities/{opp['id']}/decision", json={"decision": "confirmed", "reason": "Attempt stale decision"})
    assert response.status_code == 422
    assert "review changed" in response.text


def test_invalid_custom_output_schema_is_a_validation_error(client):
    original = bootstrap(client)["workflows"][0]["versions"][0]
    body = {k: copy.deepcopy(original[k]) for k in ("name", "nodes", "prompt_id", "prompt_version")}
    body["nodes"][-1]["config"] = {"schema": {"type": "not-a-json-schema-type"}}
    response = client.post("/api/workflows", json=body)
    assert response.status_code == 422
    assert "Invalid output schema" in response.text


def test_sql_file_executes_against_schema(client):
    from pathlib import Path
    from datetime import datetime, timedelta, timezone
    sql = (Path(__file__).parents[1] / "analytics" / "queries.sql").read_text(encoding="utf-8")
    cleaned = "\n".join(line for line in sql.splitlines() if not line.startswith("--"))
    now = datetime.now(timezone.utc)
    with client.app.state.store.connect() as db:
        for query in cleaned.split(";"):
            if query.strip():
                db.execute(query, {"is_demo": 1, "since_day": (now - timedelta(days=1)).isoformat(), "since_week": (now - timedelta(days=7)).isoformat()}).fetchall()
