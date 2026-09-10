from __future__ import annotations

import copy
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .analytics import analyze
from .db import Store, now, uid
from .engine import approve_run, execute_run, grounding_errors, new_run, provider_call, validate_nodes, version_diff
from .evaluation import run_evaluation
from .feasibility import assess
from .importer import parse_import
from .models import (ApprovalRequest, DecisionRequest, EvaluationRequest, ExperimentRequest, FeasibilityRequest,
                     GenerateRequest, HumanRatingRequest, ImportRequest, InsightReview, OpportunityRequest,
                     PromptRequest, RollbackRequest, RunRequest, WorkflowRequest)
from .seed import seed


def create_app(db_path: str | None = None, seed_demo: bool = True) -> FastAPI:
    store = Store(db_path)
    if seed_demo:
        seed(store)
    app = FastAPI(title="DesignLens AI", version="0.1.0", description="Single-user local MVP. DEMO data is never real research.")
    app.state.store = store
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5175", "http://127.0.0.1:5175", "http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST", "PATCH"], allow_headers=["Content-Type"])

    @app.exception_handler(ValueError)
    async def invalid_value(request: Request, exc: ValueError):
        return JSONResponse(status_code=422, content={"detail": str(exc)[:1500]})

    def require(kind: str, entity_id: str):
        item = store.get(kind, entity_id)
        if item is None:
            raise HTTPException(404, f"{kind} not found")
        return item

    def version(item: dict, number: int | None = None):
        number = number or item["active_version"]
        found = next((v for v in item["versions"] if v["version"] == number), None)
        if found is None:
            raise HTTPException(404, "Version not found")
        return found

    def public_run(run: dict):
        return {k: v for k, v in run.items() if k != "snapshot"}

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.1.0", "provider": os.environ.get("DESIGNLENS_PROVIDER", "extractive"), "research_status": "PENDING REAL USER RESEARCH"}

    @app.get("/api/bootstrap")
    def bootstrap():
        return {"project": store.all("projects")[0] if store.all("projects") else None,
                **{key: store.all(key) for key in ("sources", "insights", "opportunities", "feasibility", "workflows", "prompts", "evaluations", "experiments")},
                "runs": [public_run(r) for r in store.runs()], "analytics": analyze(store),
                "meta": {"research_status": "PENDING REAL USER RESEARCH", "data_label": "DEMO/SYNTHETIC examples — not real interviews",
                         "provider": os.environ.get("DESIGNLENS_PROVIDER", "extractive"), "model_mode": "Deterministic evidence extraction; no LLM call" if os.environ.get("DESIGNLENS_PROVIDER", "extractive") == "extractive" else "Remote model configured; inspect individual execution traces",
                         "real_source_count": sum(not s["is_demo"] for s in store.all("sources")), "real_participant_count": None,
                         "scope": "Single-user local workspace; no auth or arbitrary MCP execution"}}

    @app.post("/api/sources/import", status_code=201)
    def import_sources(request: ImportRequest):
        sources = parse_import(request)
        # Validation completes before persistence: a malformed row cannot partially import a file.
        with store.connect() as db:
            import json
            for source in sources:
                db.execute("INSERT INTO entities VALUES(?,?,?)", (source["id"], "sources", json.dumps(source, ensure_ascii=False)))
        for source in sources:
            store.event("source_uploaded", source["id"], source["is_demo"])
        return {"sources": sources, "imported": len(sources)}

    @app.get("/api/sources/{source_id}")
    def source_detail(source_id: str):
        return require("sources", source_id)

    @app.post("/api/insights/generate", status_code=201)
    def generate_insights(request: GenerateRequest):
        sources = [require("sources", sid) for sid in dict.fromkeys(request.source_ids)]
        prompt = version(require("prompts", "evidence-summary"))
        result = provider_call(prompt, request.query, sources)
        errors = grounding_errors(result["output"], sources)
        if errors:
            raise ValueError("Draft rejected: " + "; ".join(errors))
        created = []
        for claim in result["output"]["claims"]:
            source = next(s for s in sources if s["id"] == claim["evidence_id"])
            item = {"id": uid("ins"), "title": "Observation · " + source["segment"], "observation": claim["text"],
                    "pain_point": "Human interpretation pending", "need": "Human interpretation pending", "insight": claim["text"],
                    "evidence_ids": [source["id"]], "evidence": [{"evidence_id": source["id"], "quote": claim["quote"]}],
                    "confidence": "Low", "status": "suggested", "review_note": None, "is_demo": source["is_demo"],
                    "generated_by": result["model"], "prompt_version": prompt["version"], "created_at": now()}
            store.put("insights", item)
            store.event("insight_generated", item["id"], item["is_demo"])
            created.append(item)
        return {"insights": created, "provider": result["provider"], "token_usage": result["token_usage"], "mode": result["mode"]}

    @app.patch("/api/insights/{insight_id}")
    def review_insight(insight_id: str, request: InsightReview):
        item = require("insights", insight_id)
        for quote in item["evidence"]:
            source = require("sources", quote["evidence_id"])
            if quote["quote"] not in source["content"]:
                raise ValueError("Cannot accept an insight with broken provenance")
        prior = item["status"]
        item.update(request.model_dump())
        item["reviewed_at"] = now()
        item["reviewer"] = "local-owner"
        store.put("insights", item)
        if prior != request.status:
            store.event("insight_" + request.status, item["id"], item["is_demo"], {"previous_status": prior})
        return item

    @app.post("/api/opportunities", status_code=201)
    def create_opportunity(request: OpportunityRequest):
        insights = [require("insights", iid) for iid in dict.fromkeys(request.insight_ids)]
        if any(i["status"] != "accepted" for i in insights):
            raise ValueError("Human-accepted insights are required before creating an opportunity")
        item = {**request.model_dump(), "id": uid("opp"), "created_at": now(), "is_demo": any(i["is_demo"] for i in insights),
                "evidence_ids": list(dict.fromkeys(sid for i in insights for sid in i["evidence_ids"])),
                "evidence_confidence": "Low" if any(i["confidence"] == "Low" for i in insights) else "Medium",
                "rice": round(request.reach * request.impact * request.confidence / request.effort, 3),
                "ice": round(request.impact * request.confidence / request.effort, 3),
                "score_basis": "Owner-entered estimates; not measured reach. ICE ease=1/effort.",
                "ai_recommendation": "Investigate this task with a small pilot; compare a non-AI solution first.",
                "recommendation_basis": "Deterministic planning suggestion, not a model finding", "human_decision": {"decision": "pending", "reason": None}}
        store.put("opportunities", item)
        store.event("opportunity_created", item["id"], item["is_demo"])
        return item

    @app.patch("/api/opportunities/{opportunity_id}/decision")
    def decide(opportunity_id: str, request: DecisionRequest):
        item = require("opportunities", opportunity_id)
        if request.decision == "confirmed" and any(require("insights", iid)["status"] != "accepted" for iid in item["insight_ids"]):
            raise ValueError("Evidence review changed. Re-review underlying insights before confirming this opportunity")
        item["human_decision"] = {**request.model_dump(), "reviewer": "local-owner", "at": now()}
        store.put("opportunities", item)
        store.event("opportunity_decided", item["id"], item["is_demo"], request.model_dump())
        return item

    @app.post("/api/feasibility", status_code=201)
    def feasibility(request: FeasibilityRequest):
        item = assess(request, require("opportunities", request.opportunity_id))
        return store.put("feasibility", item)

    @app.patch("/api/feasibility/{feasibility_id}/decision")
    def decide_feasibility(feasibility_id: str, request: DecisionRequest):
        item = require("feasibility", feasibility_id)
        item["human_decision"] = {**request.model_dump(), "reviewer": "local-owner", "at": now()}
        return store.put("feasibility", item)

    @app.post("/api/prompts/{prompt_id}/versions", status_code=201)
    def add_prompt_version(prompt_id: str, request: PromptRequest):
        item = require("prompts", prompt_id)
        if any(v not in ("input", "context") for v in request.variables):
            raise ValueError("Supported template variables: input, context")
        unknown = __import__("re").findall(r"\{\{(.*?)\}\}", request.template)
        if any(v not in request.variables for v in unknown):
            raise ValueError("Template contains undeclared variables")
        n = max(v["version"] for v in item["versions"]) + 1
        item["versions"].append({**request.model_dump(), "prompt_id": prompt_id, "version": n, "created_at": now(), "evaluation_result": None})
        item["active_version"] = n
        return store.put("prompts", item)

    @app.post("/api/prompts/{prompt_id}/rollback")
    def rollback(prompt_id: str, request: RollbackRequest):
        item = require("prompts", prompt_id)
        previous = copy.deepcopy(version(item, request.version))
        previous.update({"version": max(v["version"] for v in item["versions"]) + 1, "created_at": now(), "rolled_back_from": request.version, "evaluation_result": None})
        item["versions"].append(previous)
        item["active_version"] = previous["version"]
        return store.put("prompts", item)

    @app.get("/api/prompts/{prompt_id}/diff")
    def prompt_diff(prompt_id: str, from_version: int = 1, to_version: int = 2):
        item = require("prompts", prompt_id)
        return {"diff": version_diff(version(item, from_version), version(item, to_version))}

    def workflow_payload(request: WorkflowRequest, workflow_id: str, n: int):
        require("prompts", request.prompt_id)
        version(require("prompts", request.prompt_id), request.prompt_version)
        payload = {**request.model_dump(), "workflow_id": workflow_id, "version": n, "created_at": now()}
        validate_nodes(payload["nodes"])
        return payload

    @app.post("/api/workflows", status_code=201)
    def create_workflow(request: WorkflowRequest):
        workflow_id = uid("wf")
        item = {"id": workflow_id, "name": request.name, "active_version": 1, "versions": [workflow_payload(request, workflow_id, 1)]}
        store.put("workflows", item)
        store.event("workflow_created", workflow_id)
        return item

    @app.post("/api/workflows/{workflow_id}/versions", status_code=201)
    def edit_workflow(workflow_id: str, request: WorkflowRequest):
        item = require("workflows", workflow_id)
        n = max(v["version"] for v in item["versions"]) + 1
        item["versions"].append(workflow_payload(request, workflow_id, n))
        item["active_version"] = n
        item["name"] = request.name
        store.put("workflows", item)
        store.event("workflow_edited", workflow_id)
        return item

    @app.get("/api/workflows/{workflow_id}/diff")
    def workflow_diff(workflow_id: str, from_version: int = 1, to_version: int = 2):
        item = require("workflows", workflow_id)
        return {"diff": version_diff(version(item, from_version), version(item, to_version))}

    @app.post("/api/workflows/{workflow_id}/run", status_code=201)
    def run_workflow(workflow_id: str, request: RunRequest):
        selected = version(require("workflows", workflow_id), request.workflow_version)
        prompt = version(require("prompts", selected["prompt_id"]), request.prompt_version or selected["prompt_version"])
        sources = [require("sources", s) for s in dict.fromkeys(request.source_ids)] if request.source_ids is not None else store.all("sources")
        run = execute_run(new_run(selected, prompt, request.input, sources))
        store.save_run(run)
        store.event("workflow_run", run["id"], run["is_demo"], {"status": run["status"]})
        if run["status"] in ("completed", "abstained"):
            store.event("workflow_success", run["id"], run["is_demo"])
        return public_run(run)

    @app.post("/api/runs/{run_id}/approval")
    def approve(run_id: str, request: ApprovalRequest):
        run = store.get_run(run_id)
        if not run:
            raise HTTPException(404, "Run not found")
        run = approve_run(run, request.approved, request.note)
        store.save_run(run)
        if run["status"] in ("completed", "abstained"):
            store.event("workflow_success", run["id"], run["is_demo"])
        return public_run(run)

    @app.post("/api/evaluations/run", status_code=201)
    def evaluate(request: EvaluationRequest):
        workflow = version(require("workflows", request.workflow_id))
        registry = require("prompts", workflow["prompt_id"])
        prompts = [version(registry, number) for number in dict.fromkeys(request.prompt_versions)]
        report = run_evaluation(workflow, prompts)
        store.put("evaluations", report)
        store.event("evaluation_run", report["id"])
        for p in registry["versions"]:
            if p["version"] in request.prompt_versions:
                p["evaluation_result"] = {"evaluation_id": report["id"], "dataset_sha256": report["dataset_sha256"], "at": report["created_at"]}
        store.put("prompts", registry)
        return report

    @app.patch("/api/evaluations/{evaluation_id}/human-rating")
    def human_rating(evaluation_id: str, request: HumanRatingRequest):
        report = require("evaluations", evaluation_id)
        row = next((r for r in report["results"] if r["case_id"] == request.case_id and r["variant"] == request.variant), None)
        if row is None:
            raise HTTPException(404, "Evaluation case/variant not found")
        row["human_rating"] = {"rating": request.rating, "note": request.note, "reviewer": "local-owner", "at": now()}
        return store.put("evaluations", report)

    @app.post("/api/experiments", status_code=201)
    def experiment(request: ExperimentRequest):
        opportunity = require("opportunities", request.opportunity_id)
        if opportunity["human_decision"]["decision"] != "confirmed":
            raise ValueError("Confirm the opportunity before designing an experiment")
        if any(require("insights", iid)["status"] != "accepted" for iid in opportunity["insight_ids"]):
            raise ValueError("Underlying insight was rejected; update the decision before creating a protocol")
        item = {**request.model_dump(), "id": uid("exp"), "created_at": now(), "status": "planned", "result": None,
                "is_demo": opportunity["is_demo"], "research_status": "PENDING REAL USER RESEARCH"}
        store.save_experiment(item)
        store.event("experiment_created", item["id"], item["is_demo"])
        return item

    @app.get("/api/analytics")
    def analytics(is_demo: bool = True):
        return analyze(store, is_demo)

    @app.get("/api/export")
    def export_packet():
        return {"exported_at": now(), "warning": "Contains source text. Review consent before sharing; DEMO records are not real research.",
                **{k: store.all(k) for k in ("projects", "sources", "insights", "opportunities", "feasibility", "prompts", "workflows", "evaluations", "experiments")}}

    frontend = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    if frontend.exists():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


app = create_app()
