# DesignLens API contract

Backend: `python -m uvicorn backend.app:app --host 127.0.0.1 --port 8001`. JSON API; errors use `detail`, validation errors use HTTP 422. Single local workspace, no auth. Never expose real research on a public unprotected endpoint. `/docs` is the generated OpenAPI contract.

`GET /api/bootstrap` returns `{project,sources,insights,opportunities,feasibility,workflows,prompts,evaluations,experiments,runs,analytics,meta}`. Collections are arrays, snake_case. Seed has six synthetic sources, two **suggested** insights, no pre-confirmed opportunity or experiment. Frontend should explain empty states and guide acceptance first.

| Action | Endpoint and JSON |
|---|---|
| Import | `POST /api/sources/import` `{filename,content,type,participant,segment,is_demo:true,consent_confirmed:false}`; returns `{sources,imported}` |
| Original | `GET /api/sources/{id}` returns immutable content and metadata |
| Draft extracts | `POST /api/insights/generate` `{source_ids,query?}` returns `{insights,provider,token_usage,mode}` |
| Human review | `PATCH /api/insights/{id}` `{status:"accepted"|"rejected",review_note,confidence:"Low"|"Medium"|"High"}` |
| Opportunity | `POST /api/opportunities` `{insight_ids,title,problem,target_segment?,frequency?,severity?,business_impact?,potential_solution?,risks?,reach?,impact?,confidence?,effort?,moscow?}`. Requires accepted insights; scores computed, human_decision.pending |
| Decide | `PATCH /api/opportunities/{id}/decision` `{decision:"confirmed"|"deferred"|"rejected",reason}` |
| Feasibility | `POST /api/feasibility` `{opportunity_id,task_type:"ui"|"rules"|"lookup"|"classification"|"language"|"multimodal",data_availability:"none"|"documents"|"labeled"|"multimodal",privacy:"local_only"|"approved_remote",latency_budget_ms,tool_required,error_cost:"low"|"medium"|"high"}` |
| Canvas review | `PATCH /api/feasibility/{id}/decision` same decision/reason |
| Prompt version | `POST /api/prompts/evidence-summary/versions` `{goal,template,variables:["input","context"],model:"deterministic-extractor",temperature:0,output_mode:"structured"|"text"}` |
| Rollback | `POST /api/prompts/{id}/rollback` `{version:1}` creates a new immutable copy; never deletes history |
| Prompt diff | `GET /api/prompts/{id}/diff?from_version=1&to_version=2` returns `{diff}` |
| Workflow create/version | `POST /api/workflows` or `/api/workflows/{id}/versions` `{name,description?,prompt_id:"evidence-summary",prompt_version:2,nodes:[{id,type,label,config}]}` |
| Workflow diff | `GET /api/workflows/{id}/diff?from_version=1&to_version=2` |
| Run | `POST /api/workflows/evidence-workflow/run` `{input,source_ids?,prompt_version?,workflow_version?}` |
| Human gate | `POST /api/runs/{id}/approval` `{approved:true,note}`. Only pending_approval runs; repeated review fails |
| Evaluate | `POST /api/evaluations/run` `{workflow_id:"evidence-workflow",prompt_versions:[1,2]}` |
| Human eval | `PATCH /api/evaluations/{id}/human-rating` `{case_id,variant,rating:1..5,note}` |
| Protocol | `POST /api/experiments` `{opportunity_id,title,hypothesis,primary_metric,decision_rule,secondary_metrics?,guardrails?,variants?,sample_limitation?}`; requires confirmed opportunity; always planned, result null |
| Analytics | `GET /api/analytics?is_demo=true`; default synthetic cohort, null for no denominator |
| Decision export | `GET /api/export`; includes original source text, consent-sensitive export |

Source fields: `id/source_id,type,participant,timestamp,segment,content,metadata,is_demo`. Insight fields: `id,title,observation,pain_point,need,insight,evidence_ids,evidence:[{evidence_id,quote}],confidence,status,review_note,is_demo,generated_by,created_at`. Opportunities include score assumptions plus `ai_recommendation`, `recommendation_basis`, `human_decision:{decision,reason}`.

Prompt/workflow registry shape: `{id,name?,active_version,versions:[{version,...}]}`; use `versions.find(v=>v.version===active_version)`. Nodes run sequentially, not a free graph. Supported Condition config `{field:"context_count"|"claim_count",operator:"gt"|"gte"|"eq"|"lt",value:0,on_false:"abstain"|"error"}`. Retrieval `{limit:5}`; Tool `{name:"evidence_search"}` is read-only. MCP is an explicitly unsupported design node and fails if run. Human Approval pauses durably and resumes the pinned snapshot. Remote provider credentials are server env only, never a UI field.

Evaluation returns `{id,created_at,dataset_id,dataset_sha256,is_demo,data_label,comparison,results,skipped,limitations}`. Comparison rows expose variant, prompt_version, cases, passed, task_success_rate, format_validity, evidence_grounding, unsupported_claims, latency_ms_mean, token_usage, human_rating and pending_human_review. Run outputs and traces are real; no model key means no LLM call, token usage null. The synthetic case suite cannot justify a business improvement claim.
