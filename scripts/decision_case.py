"""Reproduce evidence boundaries with deterministic execution and isolated SQLite."""
import argparse
import hashlib
import json
import os
import platform
import subprocess
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.db import Store, now
from backend.engine import grounding_errors
from backend.evaluation import run_evaluation
from backend.seed import seed

ROOT = Path(__file__).resolve().parents[1]


def execute_boundary(directory):
    if os.environ.get("DESIGNLENS_PROVIDER", "extractive") != "extractive":
        raise ValueError("This decision case requires DESIGNLENS_PROVIDER=extractive; it never calls a paid model")
    store = Store(str(Path(directory) / "evaluation.sqlite3"))
    seed(store)
    evaluation = run_evaluation(store.get("workflows", "evidence-workflow")["versions"][0], store.get("prompts", "evidence-summary")["versions"])
    assert len(evaluation["results"]) == 48
    irrelevant = next(r for r in evaluation["results"] if r["case_id"] == "irrelevant" and r["variant"] == "Prompt V2")
    stopped = next(r for r in evaluation["results"] if r["case_id"] == "irrelevant" and r["variant"] == "Workflow")
    assert irrelevant["checks"]["evidence_grounding"] and not irrelevant["checks"]["abstention_behavior"]
    assert stopped["status"] == "abstained" and all(t["type"] != "LLM" for t in stopped["trace"])

    # Mutation is an explicitly constructed validator probe, not a generated model response.
    mutation = {"claims": [{"text": "Observed improvement is 100%", "quote": "Observed improvement is 100%", "evidence_id": "e2"}], "abstained": False}
    source = {"id": "e2", "content": "SYNTHETIC: The invoice export arrived on Tuesday."}
    mutation_errors = grounding_errors(mutation, [source])
    assert mutation_errors
    with TestClient(create_app(str(Path(directory) / "boundary.sqlite3"))) as client:
        initial = client.get("/api/bootstrap").json()
        insight = initial["insights"][0]
        body = {"insight_ids": [insight["id"]], "title": "Synthetic decision boundary", "problem": "Need task evidence before feature selection", "reach": 10, "impact": 2, "confidence": .5, "effort": 2}
        unreviewed = client.post("/api/opportunities", json=body)
        assert unreviewed.status_code == 422
        assert client.patch(f"/api/insights/{insight['id']}", json={"status": "accepted", "review_note": "Scripted review of synthetic evidence only"}).status_code == 200
        response = client.post("/api/opportunities", json=body)
        assert response.status_code == 201
        opp = response.json()
        assert client.patch(f"/api/opportunities/{opp['id']}/decision", json={"decision": "confirmed", "reason": "Synthetic hypothesis only"}).status_code == 200
        assert client.patch(f"/api/insights/{insight['id']}", json={"status": "rejected", "review_note": "Counterevidence invalidates this support; scripted QA"}).status_code == 200
        protocol = client.post("/api/experiments", json={"opportunity_id": opp["id"], "title": "Stale evidence protocol", "hypothesis": "Unvalidated task hypothesis", "primary_metric": "Unaided task understanding", "decision_rule": "Stop if supporting evidence is rejected"})
        assert protocol.status_code == 422 and "Underlying insight was rejected" in protocol.text
        run = client.post("/api/workflows/evidence-workflow/run", json={"input": "route"}).json()
        assert run["status"] == "pending_approval"
        rejected = client.post(f"/api/runs/{run['id']}/approval", json={"approved": False, "note": "Scripted rejection; relevance not established"}).json()
        assert rejected["status"] == "rejected"
        final = client.get("/api/bootstrap").json()
        assert final["project"]["real_participant_count"] == 0
        assert final["analytics"]["weekly_validated_decisions"] == 0
        assert final["analytics"]["workflow_success"]["rate"] == 0
        steps = [
            {"id": "unreviewed", "title": "未审观察不能成为机会", "status_code": unreviewed.status_code, "response": unreviewed.json()},
            {"id": "stale", "title": "已确认机会的证据被否决后，不能创建实验", "status_code": protocol.status_code, "response": protocol.json()},
            {"id": "human-rejection", "title": "技术规则通过仍可被否决", "run_id": run["id"], "before_status": run["status"], "after_status": rejected["status"], "human_review": rejected["human_review"]},
            {"id": "no-outcome", "title": "没有真实参与者或有效产品结论", "real_participants": final["project"]["real_participant_count"], "weekly_validated_decisions": final["analytics"]["weekly_validated_decisions"], "workflow_success_rate": final["analytics"]["workflow_success"]["rate"]}]
    return {"executed_at": now(), "environment": {"python": platform.python_version(), "platform": platform.platform(), "database": "Actual isolated SQLite via FastAPI TestClient; no TCP/browser in this probe"},
            "method": "48 actual deterministic extractions/workflows plus HTTP application boundary checks; scripted review is QA, not user research",
            "evaluation": evaluation, "validator_probe": {"kind": "explicitly constructed quote mutation, not model output", "source": source, "output": mutation, "errors": mutation_errors},
            "steps": steps, "checks": {"valid_quote_can_be_irrelevant": True, "zero_context_stops_before_provider": True, "quote_mutation_rejected": True,
                                       "unreviewed_opportunity_denied": True, "stale_evidence_protocol_denied": True, "human_rejection_not_success": True, "real_participants": 0, "validated_product_decisions": 0}}


def build_export(boundary):
    paths = ["reports/evaluation.json", "evals/evidence-cases.json", "backend/engine.py", "backend/app.py", "backend/evaluation.py", "scripts/decision_case.py", "docs/research/arc-shift-plan.md"]
    original = json.loads((ROOT / paths[0]).read_text(encoding="utf-8"))
    dataset = json.loads((ROOT / paths[1]).read_text(encoding="utf-8"))
    selected = {"citation": "能看见文字，不等于存在合格引用", "irrelevant": "原文引用成立，相关性仍失败", "empty": "没有证据，停止在模型之前", "counterexample": "保留不同意见，不能自行宣布优先级", "no-ai": "标签规则仍是可选方案", "metadata-not-outcome": "招募计划不是已完成访谈"}
    return {"schema_version": 1, "project": "designlens", "title": "证据不够时，停止决策而不是补写结论",
            "provenance": {"source_head_before_change": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "data": "DEMO/SYNTHETIC, 12 development cases × 4 variants", "provider": "extractive / deterministic-extractor; no LLM calls", "human_review": "Scripted QA only; PENDING REAL USER RESEARCH; real participants=0"},
            "sources": [{"path": p, "sha256": hashlib.sha256((ROOT / p).read_bytes()).hexdigest()} for p in paths],
            "summary": {"historical_executed_at": original["created_at"], "dataset_sha256": original["dataset_sha256"], "executions": len(original["results"]), "variants": original["comparison"], "human_ratings": None},
            "cases": [{"case_id": cid, "title": title, "input": next(c for c in dataset["cases"] if c["case_id"] == cid), "variants": [r for r in original["results"] if r["case_id"] == cid]} for cid, title in selected.items()],
            "all_cases": original["results"], "boundary_execution": boundary,
            "decision": {"chosen": "Keep evidence presence, relevance, source validity, human priority judgment and observed product outcome as separate gates.", "rejected": ["Treat a valid citation as proof of relevant insight", "Treat 12/12 fixture checks as a validated product decision", "Select an AI build advisor before observing player problems"], "limits": ["Keyword retrieval can miss paraphrases or accept accidental overlap", "Exact quote checks cannot validate semantic interpretations", "Single-user SQLite prototype has no hosted authentication or tenant isolation"]},
            "next_experiment": {"status": "PENDING REAL USER RESEARCH / NOT EXECUTED", "sample": "4–6 exploratory PM interviews, then 8–12 adult first-time ARC players spanning low/high roguelite familiarity; targets, not achieved counts", "stop_rules": ["Missing consent or withdrawn data: stop collection/use", "No repeated task problem with traceable unique-participant observations: keep opportunity undecided, recruit a focused second round", "Observed contradiction or rejected source: reopen decision before protocol", "Compare a non-AI label/rule intervention first; AI feature selection remains pending", "Small qualitative pilot reports raw counts and negative cases, never population percentages or significance"], "conversion": "Consent → versioned observation → exact quote/source ID → separate interpretation and counterexample → human-reviewed opportunity → non-AI comparison → preregistered pilot; outcome stays null until observed"}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="reports/decision-case.json")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="designlens-decision-") as directory:
        report = build_export(execute_boundary(directory))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(path), "checks": report["boundary_execution"]["checks"]}))


if __name__ == "__main__":
    main()
