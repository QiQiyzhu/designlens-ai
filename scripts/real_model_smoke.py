"""Opt-in, at most three remote calls on committed SYNTHETIC fixtures; default is offline preflight."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import tempfile
from pathlib import Path

from backend.db import Store, now
from backend.engine import grounding_errors, provider_call
from backend.evaluation import DATASET
from backend.remote_provider import RemoteConfig, RemoteProviderError
from backend.seed import seed


ROOT = Path(__file__).resolve().parents[1]
CASE_IDS = ("citation", "irrelevant", "instruction-data")


def git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def smoke(*, execute: bool = False, max_calls: int = 1) -> dict:
    if isinstance(max_calls, bool) or not isinstance(max_calls, int) or not 1 <= max_calls <= 3:
        raise ValueError("max_calls must be 1..3")
    raw = DATASET.read_bytes()
    dataset = json.loads(raw)
    report = {"schema_version": 1, "created_at": now(), "status": "not_configured",
              "source_commit": git_value("rev-parse", "HEAD"), "source_worktree_dirty": bool(git_value("status", "--porcelain", "--untracked-files=no")),
              "environment": {"python": platform.python_version(), "platform": platform.platform()},
              "source_hash_convention": "SHA256 of actual working-tree file bytes at execution, including local line endings",
              "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
                                ("backend/engine.py", "backend/remote_provider.py", "scripts/real_model_smoke.py", "backend/seed.py")},
              "dataset_sha256": hashlib.sha256(raw).hexdigest(), "dataset_id": dataset["dataset_id"],
              "data_label": "SYNTHETIC development fixtures; no real participants or validated product decisions",
              "execution_requested": execute, "max_calls": max_calls, "attempted_calls": 0, "received_responses": 0,
              "provider": None, "results": [], "error": None, "human_ratings": None,
              "real_participants": 0, "validated_product_decisions": 0, "cost_usd": None,
              "limitations": ["A smoke test is not a held-out model benchmark or a product outcome.",
                              "At most three calls, no automatic retries; an HTTP or protocol failure stops the batch.",
                              "Direct-source mode intentionally probes relevance and instruction resistance without a retrieval gate.",
                              "Exact quote validity does not prove relevance or semantic insight quality.",
                              "Missing token usage and price remain null; a timeout may still be billable.",
                              "Human review is pending even when all automated fixture checks pass."]}
    try:
        config = RemoteConfig.from_env()
        report["provider"] = config.public()
    except ValueError as exc:
        report["error"] = str(exc)
        return report
    report["status"] = "ready_not_executed"
    if not execute:
        return report
    with tempfile.TemporaryDirectory() as directory:
        store = Store(str(Path(directory) / "smoke.sqlite3"))
        seed(store)
        prompt = store.get("prompts", "evidence-summary")["versions"][-1]
    report["prompt_version"] = prompt["version"]
    report["prompt_sha256"] = hashlib.sha256(json.dumps({k: v for k, v in prompt.items() if k != "created_at"}, sort_keys=True).encode()).hexdigest()
    cases = {c["case_id"]: c for c in dataset["cases"]}
    for case_id in CASE_IDS[:max_calls]:
        case = cases[case_id]
        if any(s.get("is_demo") is not True for s in case["sources"]):
            raise ValueError("Smoke fixtures must explicitly be synthetic")
        row = {"case_id": case_id, "input": case["input"], "status": "failed", "output": None, "error": None,
               "checks": None, "task_success": False, "token_usage": None, "cost_usd": None,
               "provider_trace": None, "human_review": "pending", "is_demo": True}
        try:
            result = provider_call(prompt, case["input"], case["sources"])
            row.update({k: result[k] for k in ("output", "token_usage", "cost_usd", "provider_trace", "latency_ms", "model")})
            output = result["output"]
            errors = grounding_errors(output, case["sources"])
            serialized = json.dumps(output, ensure_ascii=False)
            observed = {c.get("evidence_id") for c in output.get("claims", []) if isinstance(c, dict)} if isinstance(output, dict) and isinstance(output.get("claims"), list) else set()
            abstained = output.get("abstained", False) if isinstance(output, dict) else False
            checks = {"format_validity": not any(e.startswith("format:") for e in errors), "evidence_grounding": not errors,
                      "required_content": all(s in serialized for s in case["must_include"]),
                      "forbidden_content": all(s not in serialized for s in case["must_not_include"]),
                      "reference_coverage": set(case["reference_evidence"]).issubset(observed),
                      "abstention_behavior": abstained == case.get("expect_abstain", False)}
            row.update(status="completed", checks=checks, task_success=all(checks.values()), grounding_errors=errors)
        except RemoteProviderError as exc:
            row.update(error=str(exc), provider_trace=exc.metadata, token_usage=exc.metadata["token_usage"], latency_ms=exc.metadata["latency_ms"])
        except ValueError as exc:
            row["error"] = str(exc)
        trace = row["provider_trace"] or {}
        report["attempted_calls"] += trace.get("attempts", 0)
        report["received_responses"] += int(trace.get("response_received", False))
        report["results"].append(row)
        if row["status"] == "failed":
            report["status"] = "failed"
            break
    else:
        report["status"] = "completed"
    report["automated_checks_passed"] = sum(row["task_success"] for row in report["results"])
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Opt in to real API requests, possibly billable")
    parser.add_argument("--max-calls", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--output", default="outputs/real-model-smoke.json")
    args = parser.parse_args(argv)
    report = smoke(execute=args.execute, max_calls=args.max_calls)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # The receipt contains synthetic outputs. Console output deliberately excludes raw model text and configuration.
    print(json.dumps({"report": str(path), "status": report["status"], "attempted_calls": report["attempted_calls"],
                      "received_responses": report["received_responses"], "real_participants": 0, "validated_product_decisions": 0}))
    return 2 if report["status"] in ("not_configured", "failed") else 1 if args.execute and not all(r["task_success"] for r in report["results"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
