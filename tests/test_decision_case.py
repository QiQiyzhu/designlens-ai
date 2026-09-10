from scripts.decision_case import execute_boundary


def test_confirmed_opportunity_loses_protocol_eligibility_after_source_rejection(tmp_path, monkeypatch):
    monkeypatch.setenv("DESIGNLENS_PROVIDER", "extractive")
    report = execute_boundary(tmp_path)
    assert report["checks"]["stale_evidence_protocol_denied"]
    stale = next(s for s in report["steps"] if s["id"] == "stale")
    assert stale["status_code"] == 422
    assert report["checks"]["validated_product_decisions"] == 0
