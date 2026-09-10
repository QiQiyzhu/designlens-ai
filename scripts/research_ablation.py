"""Frozen synthetic component comparison; no remote calls without --execute. Not user research."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time

from backend.db import now
from backend.engine import OUTPUT_SCHEMA, grounding_errors, retrieve
from backend.privacy import clean_text
from backend.remote_provider import RemoteConfig, RemoteProviderError, call_remote

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evals/research-intake-dev-v2.json"
VARIANTS = ("direct-synthetic", "local-cleanup", "cleanup-and-context-gate")
PROMPT = {"output_mode": "structured", "temperature": 0}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def write_report(path: Path | None, report: dict) -> None:
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".partial")
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)


def run(*, execute: bool = False, repeats: int = 1, max_calls: int = 36,
        max_observed_tokens: int = 25000, max_seconds: int = 300, output: Path | None = None) -> dict:
    if not 1 <= repeats <= 3 or not 1 <= max_calls <= 120 or not 1000 <= max_observed_tokens <= 100000 or not 10 <= max_seconds <= 900:
        raise ValueError("Bounds: repeats 1..3, calls 1..120, observed tokens 1000..100000, seconds 10..900")
    raw = DATASET.read_bytes(); dataset = json.loads(raw)
    if any(s.get("is_demo") is not True for c in dataset["cases"] for s in c["sources"]):
        raise ValueError("Only the committed, explicitly synthetic fixtures are allowed")
    report = {"schema_version": 1, "created_at": now(), "status": "preflight", "execution_requested": execute,
              "source_commit": git_value("rev-parse", "HEAD"), "source_worktree_dirty": bool(git_value("status", "--porcelain", "--untracked-files=no")),
              "source_sha256_lf": {p: digest((ROOT / p).read_bytes().replace(b"\r\n", b"\n")) for p in
                  ("scripts/research_ablation.py", "backend/remote_provider.py", "backend/privacy.py", "backend/engine.py")},
              "dataset_id": dataset["dataset_id"], "dataset_sha256": digest(raw), "prompt_sha256": digest(json.dumps(PROMPT, sort_keys=True).encode()),
              "environment": {"python": platform.python_version(), "platform": platform.platform()},
              "variants": list(VARIANTS), "repeats": repeats, "planned_rows": len(dataset["cases"]) * len(VARIANTS) * repeats,
              "limits": {"max_calls": max_calls, "max_observed_tokens": max_observed_tokens, "max_seconds": max_seconds, "retries": 0},
              "provider": None, "attempted_calls": 0, "received_responses": 0, "observed_tokens": 0, "usage_complete": True,
              "results": [], "complete": False, "cost_usd": None, "real_participants": 0, "validated_product_decisions": 0,
              "limitations": ["Authored development cases, not held out. No human usefulness rating or real research.",
                  "Direct synthetic variant intentionally bypasses the application privacy gate using only fictional identifiers from the committed dataset.",
                  "Clean/direct isolates local cleanup; clean+gate/clean isolates lexical retrieval and its empty-context stop.",
                  "Names and addresses require manual terms; local patterns can over-redact legitimate numeric data.",
                  "Token/time limits stop between calls; a single in-flight call may exceed the observed budget or be billable with unknown usage.",
                  "The old three-call smoke remains unchanged; v2 separately declares that attack-only material without an observation should abstain."]}
    try:
        report["provider"] = RemoteConfig.from_env().public()
    except ValueError as exc:
        report.update(status="not_configured", error=str(exc))
        write_report(output, report); return report
    if not execute:
        report["status"] = "ready_not_executed"
        write_report(output, report); return report
    report["status"] = "running"
    started = time.perf_counter()
    for repeat in range(1, repeats + 1):
        for case_index, case in enumerate(dataset["cases"]):
            # Rotate ordering to make any repeated comparison's order visible rather than always favoring one variant.
            order = list(VARIANTS)
            shift = (case_index + repeat - 1) % len(order)
            order = order[shift:] + order[:shift]
            for variant in order:
                if report["attempted_calls"] >= max_calls or report["observed_tokens"] >= max_observed_tokens or time.perf_counter() - started >= max_seconds:
                    report["status"] = "budget_stopped"; write_report(output, report); return report
                query, sources = case["query"], copy.deepcopy(case["sources"])
                if variant != "direct-synthetic":
                    query = clean_text(query, case["manual_terms"])[0]
                    for source in sources:
                        source["content"] = clean_text(source["content"], case["manual_terms"])[0]
                context = retrieve(sources, query, 5) if variant == "cleanup-and-context-gate" else sources
                message = "Task: " + query + "\nSources: " + json.dumps([{"evidence_id": s["id"], "content": s["content"]} for s in context], ensure_ascii=False)
                row = {"case_id": case["id"], "category": case["category"], "variant": variant, "repeat": repeat,
                       "status": "failed", "output": None, "provider_trace": None, "token_usage": None,
                       "human_review": "pending", "task_success": False, "model_called": False,
                       "transport_input_contains_identifiers": any(value in message for value in case["identifiers"]),
                       "context_ids": [s["id"] for s in context], "input_sha256": digest(message.encode()), "error": None}
                try:
                    if variant == "cleanup-and-context-gate" and not context:
                        row.update(output={"claims": [], "abstained": True}, status="abstained_before_model", latency_ms=0)
                    else:
                        result = call_remote(PROMPT, message, OUTPUT_SCHEMA)
                        row.update({k: result[k] for k in ("output", "provider_trace", "token_usage", "latency_ms", "model")})
                        row.update(status="completed", model_called=True)
                    output_value = row["output"]
                    errors = grounding_errors(output_value, context)
                    rendered = json.dumps(output_value, ensure_ascii=False)
                    observed = {c.get("evidence_id") for c in output_value.get("claims", []) if isinstance(c, dict)} if isinstance(output_value, dict) and isinstance(output_value.get("claims"), list) else set()
                    abstained = output_value.get("abstained", False) if isinstance(output_value, dict) else False
                    checks = {"format_validity": not any(x.startswith("format:") for x in errors), "exact_grounding": not errors,
                              "required_content": all(t in rendered for t in case["required_terms"]),
                              "reference_coverage": set(case["required_evidence"]) <= observed,
                              "abstention_behavior": abstained == case["expect_abstain"],
                              "no_identifier_output": not any(value in rendered for value in case["identifiers"])}
                    row.update(checks=checks, task_success=all(checks.values()), grounding_errors=errors)
                except RemoteProviderError as exc:
                    row.update(error=str(exc), provider_trace=exc.metadata, token_usage=exc.metadata["token_usage"], model_called=True)
                except ValueError as exc:
                    row["error"] = str(exc)
                trace = row["provider_trace"] or {}
                report["attempted_calls"] += trace.get("attempts", 0)
                report["received_responses"] += int(trace.get("response_received", False))
                usage = row["token_usage"] or {}
                if row["model_called"] and "total_tokens" not in usage:
                    report["usage_complete"] = False
                report["observed_tokens"] += usage.get("total_tokens", 0)
                report["results"].append(row)
                if row["status"] == "failed":
                    report["status"] = "failed"; write_report(output, report); return report
                write_report(output, report)
    report.update(status="completed", complete=True)
    report["summary"] = [{"variant": variant, "rows": len(items := [r for r in report["results"] if r["variant"] == variant]),
                          "task_passes": sum(r["task_success"] for r in items),
                          "identifier_input_rows": sum(r["transport_input_contains_identifiers"] and r["model_called"] for r in items),
                          "identifier_output_rows": sum(not r["checks"]["no_identifier_output"] for r in items),
                          "stopped_before_model": sum(r["status"] == "abstained_before_model" for r in items)} for variant in VARIANTS]
    write_report(output, report); return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--max-calls", type=int, default=36)
    parser.add_argument("--max-observed-tokens", type=int, default=25000)
    parser.add_argument("--max-seconds", type=int, default=300)
    parser.add_argument("--output", type=Path, default=Path("outputs/research-ablation.json"))
    args = parser.parse_args()
    report = run(execute=args.execute, repeats=args.repeats, max_calls=args.max_calls, max_observed_tokens=args.max_observed_tokens, max_seconds=args.max_seconds, output=args.output)
    print(json.dumps({k: report[k] for k in ("status", "attempted_calls", "received_responses", "observed_tokens", "complete", "real_participants")}))
    return 2 if report["status"] in ("not_configured", "failed", "budget_stopped") else 1 if args.execute and not all(r["task_success"] for r in report["results"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
