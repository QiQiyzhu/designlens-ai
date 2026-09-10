import copy
import json

import pytest
from fastapi.testclient import TestClient

from backend import engine
from backend.app import create_app
from backend.privacy import clean_text, content_hash, ensure_remote_sources


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    monkeypatch.setenv("DESIGNLENS_PROVIDER", "extractive")
    app = create_app(str(tmp_path / "research.sqlite3"))
    with TestClient(app) as client:
        yield app, client


def payload():
    return {"filename": "review.txt", "content": "SYNTHETIC QA: Alex Demo finds the route unclear. Contact alex@example.invalid or +1 (415) 555-0100.",
            "participant": "Alex Demo", "segment": "Privacy QA", "redaction_terms": ["Alex Demo"],
            "is_demo": False, "consent_confirmed": True}


def imported(client):
    body = payload()
    body["privacy_review_digest"] = client.post("/api/sources/preview", json=body).json()["preview_digest"]
    response = client.post("/api/sources/import", json=body)
    assert response.status_code == 201
    return response.json()["sources"][0]


def test_local_cleanup_preserves_task_dates_and_handles_overlaps():
    value = "Route on 2026-09-10: Alex Demo, alex@example.invalid, +86 13800138000. Build 1.0.0."
    cleaned, findings = clean_text(value, ["Alex Demo", "alex@example.invalid"])
    assert "2026-09-10" in cleaned and "Build 1.0.0" in cleaned and "Route" in cleaned
    assert "Alex Demo" not in cleaned and "example.invalid" not in cleaned and "13800138000" not in cleaned
    assert sum(x["count"] for x in findings) == 3
    assert clean_text("合成：小雨觉得路线图例难找。", ["小雨"])[0] == "合成：[CUSTOM]觉得路线图例难找。"


def test_preview_makes_no_database_or_provider_change(app_client, monkeypatch):
    app, client = app_client
    monkeypatch.setattr(engine, "call_remote", lambda *args: pytest.fail("Preview called a model"))
    before = client.get("/api/bootstrap").json()
    body = payload(); body["consent_confirmed"] = False
    response = client.post("/api/sources/preview", json=body)
    assert response.status_code == 200
    preview = response.json()
    assert preview["network_calls"] == 0 and preview["persisted"] is False
    assert preview["sources"][0]["participant"] == "[CUSTOM]"
    assert "example.invalid" not in json.dumps(preview)
    body["filename"] = "metadata.json"
    body["content"] = json.dumps([{"content": "SYNTHETIC route observation", "metadata": {
        "alex@example.invalid": "first", "other@example.invalid": "second"}}])
    metadata_preview = client.post("/api/sources/preview", json=body).json()
    assert "example.invalid" not in json.dumps(metadata_preview)
    assert {"first", "second"} <= set(metadata_preview["sources"][0]["metadata"].values())
    after = client.get("/api/bootstrap").json()
    assert after["sources"] == before["sources"]
    assert after["analytics"]["event_count"] == before["analytics"]["event_count"]
    assert client.post("/api/sources/import", json=body).status_code == 422


@pytest.mark.parametrize("field,value", [("content", "Changed route"), ("redaction_terms", []), ("participant", "Changed"), ("consent_confirmed", False)])
def test_review_digest_rejects_changed_inputs_without_partial_import(app_client, field, value):
    app, client = app_client
    body = payload()
    body["privacy_review_digest"] = client.post("/api/sources/preview", json=body).json()["preview_digest"]
    body[field] = value
    before = app.state.store.all("sources")
    assert client.post("/api/sources/import", json=body).status_code == 422
    assert app.state.store.all("sources") == before


def test_only_clean_copy_and_hashes_are_persisted(app_client):
    app, client = app_client
    source = imported(client)
    with app.state.store.connect() as db:
        retained = " ".join(row[0] for row in db.execute("SELECT data FROM entities"))
    assert "alex@example.invalid" not in retained and "Alex Demo" not in retained and "555-0100" not in retained
    assert source["privacy_review"]["status"] == "reviewed" and source["remote_review"]["approved"] is False
    assert source["privacy_review"]["content_sha256"] == content_hash(source["content"])
    assert source["is_demo"] is False
    assert client.get("/api/analytics?is_demo=false").json()["weekly_validated_decisions"] == 0


def test_global_flag_alone_cannot_send_unreviewed_real_source(app_client):
    app, client = app_client
    source = imported(client)
    with pytest.raises(ValueError, match="local-only"):
        ensure_remote_sources([source], True)
    forged = {"content": "Private source", "is_demo": False, "metadata": {"remote_review": {"approved": True}}}
    with pytest.raises(ValueError, match="local-only"):
        ensure_remote_sources([forged], True)


def test_approval_revoke_and_content_change_close_the_remote_boundary(app_client):
    app, client = app_client
    source = imported(client)
    url = f"/api/sources/{source['id']}/remote-review"
    body = {"approved": True, "content_sha256": source["privacy_review"]["content_sha256"], "note": "Scripted QA permission, not real research consent", "consent_confirmed": True}
    assert client.post(url, json={**body, "content_sha256": "0" * 64}).status_code == 409
    assert client.post(url, json={**body, "consent_confirmed": False}).status_code == 422
    source = client.post(url, json=body).json()
    ensure_remote_sources([source], True)
    with pytest.raises(ValueError):
        ensure_remote_sources([source], False)
    changed = copy.deepcopy(source); changed["content"] += " Later material."
    with pytest.raises(ValueError):
        ensure_remote_sources([changed], True)
    app.state.store.put("sources", changed)
    assert client.post(url, json=body).status_code == 409
    assert client.post(url, json={**body, "content_sha256": content_hash(changed["content"])}).status_code == 422
    app.state.store.put("sources", source)
    revoked = client.post(url, json={**body, "approved": False}).json()
    with pytest.raises(ValueError, match="local-only"):
        ensure_remote_sources([revoked], True)
    with app.state.store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE name='source_remote_reviewed' AND entity_id=?", (source["id"],)).fetchone()[0] == 2


def test_remote_generation_checks_rendered_input_and_synthetic_identifiers(monkeypatch):
    monkeypatch.setenv("DESIGNLENS_PROVIDER", "deepseek")
    monkeypatch.setenv("DESIGNLENS_API_KEY", "local-test-only-not-a-real-credential")
    monkeypatch.setenv("DESIGNLENS_API_BASE", "https://api.deepseek.com")
    monkeypatch.setattr(engine, "call_remote", lambda *args: pytest.fail("Unreviewed identifier reached remote transport"))
    prompt = {"output_mode": "structured", "template": "Task: {{input}} Sources: {{context}}"}
    with pytest.raises(ValueError, match="identifier"):
        engine.provider_call(prompt, "email alex@example.invalid", [{"id": "e1", "content": "SYNTHETIC route", "is_demo": True}])
    with pytest.raises(ValueError, match="identifier"):
        engine.provider_call(prompt, "route", [{"id": "e1", "content": "SYNTHETIC alex@example.invalid", "is_demo": True}])
