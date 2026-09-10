"""Actual fixture execution; no ground-truth fed to the provider, no fabricated model scores."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from statistics import mean

from .db import now, uid
from .engine import execute_run, grounding_errors, new_run, provider_call, retrieve


DATASET = Path(__file__).resolve().parents[1] / "evals" / "evidence-cases.json"


def run_evaluation(workflow: dict, prompts: list[dict]) -> dict:
    raw = DATASET.read_bytes()
    dataset = json.loads(raw)
    rows = []
    variants = [(f"Prompt V{p['version']}", p, "direct") for p in prompts]
    strongest = max(prompts, key=lambda p: p["version"])
    variants.extend([("RAG", strongest, "retrieval"), ("Workflow", strongest, "workflow")])
    for name, prompt, mode in variants:
        for case in dataset["cases"]:
            started = time.perf_counter()
            sources = case["sources"]
            context = sources if mode == "direct" else retrieve(sources, case["input"], 5)
            error = None
            status = "completed"
            output = None
            trace = []
            usage = None
            provider = "unavailable"
            model = None
            try:
                if mode == "workflow":
                    run = execute_run(new_run(workflow, prompt, case["input"], sources))
                    output, error, status, trace = run["output"], run["error"], run["status"], run["trace"]
                    usage, provider, model = run["token_usage"], run["provider"], run["model"]
                    context = run["retrieved_context"]
                else:
                    response = provider_call(prompt, case["input"], context)
                    output, usage, provider, model = response["output"], response["token_usage"], response["provider"], response["model"]
            except ValueError as exc:
                error, status = str(exc), "failed"
            latency = round((time.perf_counter() - started) * 1000, 3)
            errors = grounding_errors(output, context)
            serialized = json.dumps(output, ensure_ascii=False)
            observed_ids = {c.get("evidence_id") for c in output.get("claims", [])} if isinstance(output, dict) else set()
            abstained = output.get("abstained", False) if isinstance(output, dict) else False
            checks = {
                "format_validity": not any(e.startswith("format:") for e in errors),
                "evidence_grounding": not errors,
                "required_content": all(text in serialized for text in case["must_include"]),
                "forbidden_content": all(text not in serialized for text in case["must_not_include"]),
                "reference_coverage": set(case["reference_evidence"]).issubset(observed_ids),
                "abstention_behavior": abstained == case.get("expect_abstain", False),
                "no_execution_error": error is None,
            }
            rows.append({"case_id": case["case_id"], "category": case["category"], "difficulty": case["difficulty"],
                         "variant": name, "prompt_version": prompt["version"], "input": case["input"], "expected_behavior": case["expected_behavior"],
                         "output": output, "checks": checks, "task_success": all(checks.values()), "unsupported_claims": len([e for e in errors if not e.startswith("format:")]),
                         "grounding_errors": errors, "latency_ms": latency, "token_usage": usage, "human_rating": None,
                         "status": status, "error": error, "trace": trace, "provider": provider, "model": model,
                         "reference_evidence": case["reference_evidence"], "retrieved_evidence": [s["id"] for s in context]})
    comparison = []
    for name, prompt, mode in variants:
        results = [row for row in rows if row["variant"] == name]
        comparison.append({"variant": name, "prompt_version": prompt["version"], "cases": len(results),
                           "passed": sum(row["task_success"] for row in results), "task_success_rate": mean(row["task_success"] for row in results),
                           "format_validity": mean(row["checks"]["format_validity"] for row in results),
                           "evidence_grounding": mean(row["checks"]["evidence_grounding"] for row in results),
                           "unsupported_claims": sum(row["unsupported_claims"] for row in results),
                           "latency_ms_mean": round(mean(row["latency_ms"] for row in results), 3),
                           "token_usage": [row["token_usage"] for row in results] if any(row["token_usage"] is not None for row in results) else None,
                           "human_rating": None, "pending_human_review": sum(row["status"] == "pending_approval" for row in results)})
    return {"id": uid("eval"), "created_at": now(), "workflow_id": workflow["workflow_id"], "workflow_version": workflow["version"],
            "dataset_id": dataset["dataset_id"], "dataset_sha256": hashlib.sha256(raw).hexdigest(), "is_demo": True,
            "data_label": "SYNTHETIC evaluation fixtures; actual executions, not real user or model-quality evidence",
            "comparison": comparison, "results": rows, "skipped": [{"variant": "Agent", "reason": "No task requires autonomous tool selection; not implemented or benchmarked"}],
            "limitations": ["Default provider is deterministic extraction; prompt comparison tests contracts, not LLM reasoning quality.",
                            "Citation/quote checks do not establish semantic insight correctness.",
                            "Workflow candidates may await human approval; rule-check pass does not mean human acceptance.",
                            "Cases are development fixtures, not an independent held-out generalization benchmark.",
                            "Token usage is null without a model call; human ratings remain null until recorded."]}
