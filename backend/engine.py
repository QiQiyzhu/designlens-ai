"""Bounded sequential workflow with durable human approval and honest provider traces."""
from __future__ import annotations

import copy
import difflib
import json
import os
import re
import time

from jsonschema import Draft202012Validator, SchemaError, ValidationError, validate

from .db import now, uid
from .remote_provider import RemoteConfig, RemoteProviderError, call_remote


OUTPUT_SCHEMA = {
    "type": "object", "required": ["claims", "abstained"], "additionalProperties": False,
    "properties": {
        "claims": {"type": "array", "maxItems": 20, "items": {"type": "object", "additionalProperties": False,
            "required": ["text", "evidence_id", "quote"], "properties": {"text": {"type": "string"}, "evidence_id": {"type": "string"}, "quote": {"type": "string", "minLength": 1}}}},
        "abstained": {"type": "boolean"},
    },
}


def tokens(value: str) -> set[str]:
    latin = set(re.findall(r"[a-z0-9]{2,}", value.lower()))
    chinese = re.findall(r"[\u4e00-\u9fff]", value)
    return latin | set(chinese)


def retrieve(sources: list[dict], query: str, limit: int = 5) -> list[dict]:
    words = tokens(query)
    ranked = [(len(words & tokens(s["content"])), index, s) for index, s in enumerate(sources)]
    ranked.sort(key=lambda x: (-x[0], x[1]))
    return [item[2] for item in ranked if item[0] > 0 or not words][:limit]


def extract(sources: list[dict], output_mode: str = "structured") -> dict | str:
    claims = []
    seen = set()
    for source in sources:
        # Source content is never interpreted as commands. Exact excerpts retain provenance.
        quote = source["content"].strip()[:320]
        if quote and quote not in seen:
            claims.append({"text": quote, "quote": quote, "evidence_id": source["id"]})
            seen.add(quote)
    if output_mode == "text":
        return "\n".join(c["text"] for c in claims) if claims else "Insufficient evidence."
    return {"claims": claims[:20], "abstained": not claims}


def grounding_errors(output: object, sources: list[dict]) -> list[str]:
    try:
        validate(output, OUTPUT_SCHEMA)
    except ValidationError as exc:
        return [f"format: {exc.message}"]
    index = {s["id"]: s for s in sources}
    errors = []
    for claim in output["claims"]:
        source = index.get(claim["evidence_id"])
        if not source:
            errors.append(f"unknown evidence: {claim['evidence_id']}")
        elif claim["quote"] not in source["content"]:
            errors.append(f"quote mismatch: {claim['evidence_id']}")
        elif claim["text"] != claim["quote"]:
            # Deliberately narrow MVP: extractive claims only. Interpretation belongs to human review.
            errors.append(f"non-extractive claim requires human review: {claim['evidence_id']}")
    if output["abstained"] and output["claims"]:
        errors.append("abstained cannot contain claims")
    if not output["abstained"] and not output["claims"]:
        errors.append("empty claims must abstain")
    return errors


def provider_call(prompt: dict, user_input: str, sources: list[dict], rendered: str | None = None) -> dict:
    started = time.perf_counter()
    provider = os.environ.get("DESIGNLENS_PROVIDER", "extractive")
    if provider == "extractive":
        return {"output": extract(sources, prompt["output_mode"]), "model": "deterministic-extractor",
                "provider": "extractive", "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                "token_usage": None, "cost_usd": 0, "mode": "DEMO deterministic extraction; no model call"}
    if provider not in ("deepseek", "openai-compatible", "qwen"):
        raise ValueError("DESIGNLENS_PROVIDER must be extractive, deepseek, qwen or openai-compatible")
    RemoteConfig.from_env()
    if any(s.get("is_demo") is not True for s in sources) and os.environ.get("DESIGNLENS_ALLOW_REAL_REMOTE") != "1":
        raise ValueError("Real evidence is local-only; explicit remote data permission is not configured")
    context = json.dumps([{"evidence_id": s["id"], "content": s["content"]} for s in sources], ensure_ascii=False)
    message = rendered or prompt["template"].replace("{{input}}", user_input).replace("{{context}}", context)
    return call_remote(prompt, message, OUTPUT_SCHEMA)


def version_diff(old: dict, new: dict) -> str:
    a = json.dumps(old, ensure_ascii=False, indent=2, sort_keys=True).splitlines()
    b = json.dumps(new, ensure_ascii=False, indent=2, sort_keys=True).splitlines()
    return "\n".join(difflib.unified_diff(a, b, fromfile=f"v{old['version']}", tofile=f"v{new['version']}", lineterm=""))


def validate_nodes(nodes: list[dict]):
    ids = [n["id"] for n in nodes]
    if len(ids) != len(set(ids)):
        raise ValueError("Node IDs must be unique")
    if nodes[0]["type"] != "Input":
        raise ValueError("First node must be Input")
    if sum(n["type"] == "LLM" for n in nodes) != 1:
        raise ValueError("MVP workflow requires exactly one LLM/extractor node")
    if not any(n["type"] == "Structured Output" for n in nodes):
        raise ValueError("Workflow must end in a validated Structured Output")
    if nodes[-1]["type"] != "Structured Output":
        raise ValueError("Last node must be Structured Output")
    llm_at = next(i for i, n in enumerate(nodes) if n["type"] == "LLM")
    for i, node in enumerate(nodes):
        kind, config = node["type"], node["config"]
        if kind == "Human Approval" and i < llm_at:
            raise ValueError("Human Approval must follow the output candidate")
        if kind == "Condition":
            if config.get("field", "context_count") not in ("context_count", "claim_count"):
                raise ValueError("Condition field must be context_count or claim_count")
            if config.get("operator", "gt") not in ("gt", "gte", "eq", "lt"):
                raise ValueError("Unsupported condition operator")
            if not isinstance(config.get("value", 0), (int, float)):
                raise ValueError("Condition value must be a number")
            if config.get("on_false", "abstain") not in ("abstain", "error"):
                raise ValueError("Condition on_false must be abstain or error")
        if kind == "Retrieval" and not isinstance(config.get("limit", 5), int):
            raise ValueError("Retrieval limit must be an integer")
        if kind == "Structured Output" and "schema" in config:
            try:
                Draft202012Validator.check_schema(config["schema"])
            except SchemaError as exc:
                raise ValueError("Invalid output schema: " + exc.message) from None


def new_run(workflow: dict, prompt: dict, user_input: str, sources: list[dict]) -> dict:
    return {"id": uid("run"), "workflow_id": workflow["workflow_id"], "workflow_version": workflow["version"],
            "prompt_id": prompt["prompt_id"], "prompt_version": prompt["version"], "created_at": now(),
            "status": "running", "input": user_input, "output": None, "model": None, "provider": None,
            "latency_ms": 0, "token_usage": None, "cost_usd": None, "retrieved_context": [], "tool_calls": [],
            "trace": [], "error": None, "is_demo": not sources or any(s.get("is_demo", True) for s in sources),
            "human_review": None, "next_node": 0,
            "snapshot": {"workflow": copy.deepcopy(workflow), "prompt": copy.deepcopy(prompt), "sources": copy.deepcopy(sources)}}


def execute_run(run: dict) -> dict:
    started = time.perf_counter()
    snapshot = run["snapshot"]
    nodes = snapshot["workflow"]["nodes"]
    prompt = snapshot["prompt"]
    sources = snapshot["sources"]
    context = run.get("retrieved_context", [])
    rendered = run.get("rendered_prompt")
    try:
        for index in range(run["next_node"], len(nodes)):
            node = nodes[index]
            kind, config = node["type"], node["config"]
            trace = {"node_id": node["id"], "type": kind, "status": "completed"}
            if kind == "Input":
                trace["characters"] = len(run["input"])
            elif kind == "Retrieval":
                context = retrieve(sources, run["input"], min(20, max(1, config.get("limit", 5))))
                run["retrieved_context"] = context
                trace["evidence_ids"] = [s["id"] for s in context]
            elif kind == "Prompt":
                rendered = prompt["template"].replace("{{input}}", run["input"]).replace("{{context}}", json.dumps([{"evidence_id": s["id"], "content": s["content"]} for s in context], ensure_ascii=False))
                run["rendered_prompt"] = rendered
                trace["prompt_version"] = prompt["version"]
            elif kind == "LLM":
                result = provider_call(prompt, run["input"], context, rendered)
                run.update({key: result[key] for key in ("output", "model", "provider", "token_usage", "cost_usd", "mode")})
                trace["provider_latency_ms"] = result["latency_ms"]
                if "provider_trace" in result:
                    run["provider_trace"] = result["provider_trace"]
            elif kind == "Condition":
                count = len(context) if config.get("field", "context_count") == "context_count" else len(run["output"].get("claims", [])) if isinstance(run["output"], dict) else 0
                value = config.get("value", 0)
                passed = {"gt": count > value, "gte": count >= value, "eq": count == value, "lt": count < value}[config.get("operator", "gt")]
                trace.update({"observed": count, "passed": passed})
                if not passed:
                    if config.get("on_false", "abstain") == "error":
                        raise ValueError(f"Condition {node['id']} failed")
                    run["output"] = {"claims": [], "abstained": True}
                    run["status"] = "abstained"
                    run["trace"].append(trace)
                    run["next_node"] = len(nodes)
                    break
            elif kind == "Tool":
                if config.get("name", "evidence_search") != "evidence_search":
                    raise ValueError("Only read-only local evidence_search is enabled")
                context = retrieve(sources, run["input"], 5)
                run["retrieved_context"] = context
                call = {"tool": "evidence_search", "input": run["input"], "evidence_ids": [s["id"] for s in context], "side_effects": False}
                run["tool_calls"].append(call)
                trace["tool"] = call
            elif kind == "MCP":
                raise ValueError("MCP node is a design placeholder; remote MCP execution is not implemented")
            elif kind == "Human Approval":
                trace["status"] = "pending_approval"
                run["status"] = "pending_approval"
                run["trace"].append(trace)
                run["next_node"] = index + 1
                break
            elif kind == "Structured Output":
                errors = grounding_errors(run["output"], context)
                if errors:
                    raise ValueError("; ".join(errors))
                if "schema" in config:
                    validate(run["output"], config["schema"])
                run["status"] = "completed"
            run["trace"].append(trace)
            run["next_node"] = index + 1
        if run["status"] == "running":
            run["status"] = "completed"
    except (ValueError, ValidationError) as exc:
        run["status"] = "failed"
        run["error"] = str(exc)[:1500]
        if isinstance(exc, RemoteProviderError):
            run["provider_trace"] = exc.metadata
            run["token_usage"] = exc.metadata["token_usage"]
            run["provider"] = exc.metadata["provider"]
            run["model"] = exc.metadata["response_model"] or exc.metadata["requested_model"]
        run["trace"].append({"node_id": nodes[run["next_node"]]["id"] if run["next_node"] < len(nodes) else "unknown", "status": "failed", "error": run["error"]})
    run["latency_ms"] += round((time.perf_counter() - started) * 1000, 3)
    return run


def approve_run(run: dict, approved: bool, note: str) -> dict:
    if run["status"] != "pending_approval":
        raise ValueError("Only a pending run can be reviewed; a review cannot be replayed")
    run["human_review"] = {"approved": approved, "note": note, "reviewed_at": now(), "reviewer": "local-owner"}
    run["trace"].append({"type": "Human Decision", **run["human_review"]})
    if not approved:
        run["status"] = "rejected"
        return run
    run["status"] = "running"
    return execute_run(run)
