# PRD — Evidence-to-decision MVP

Version 0.1 · 2026-09-10 · Owner: project author, with AI-assisted implementation. **PENDING REAL USER RESEARCH**.

## Background, users and evidence
The product hypothesis is that fragmented artifacts make decisions hard to reconstruct. Primary user: an individual PM; reviewer: a designer/engineer/PM lead. Desk research establishes strong existing tools but does not establish unmet demand. JTBD: inspect why a feature is worth testing, including an option not to use AI.

## Goals and non-goals
Enable one complete, auditable decision packet. Expose original evidence, uncertainty, human choice, workflow version and evaluation cases. Do not automate prioritization, run a real customer experiment, replace Amplitude, or claim business results from seed data.

## Journey and wireframe
Research Hub: left navigation, source list and selected source → Insight detail: interpretation next to exact excerpt and review action → Opportunity: goal/problem/solution/experiment chain with recommendation and human decision → Feasibility: eight alternatives with a selected rationale → Workflow: nodes, settings, version diff and run trace → Evaluation: variant comparison and failed cases → Analytics: labeled event cohort and experiment protocol. See [screen specification](../figma-screen-specification.md).

## Requirements and acceptance
| ID / priority | User behavior | Acceptance |
|---|---|---|
| R1 Must | Import TXT/MD/CSV/JSON | Malformed, oversize and empty files fail explicitly; each row keeps ID, type, source, timestamp, segment, content and metadata |
| R2 Must | Review an insight | Every quote resolves to a source and exact substring; unknown source or fabricated quotation rejected; accept/reject recorded |
| R3 Must | Decide an opportunity | Requires accepted evidence; RICE/ICE assumptions shown; reason required for human decision |
| R4 Must | Compare architectures | Includes all eight categories, privacy/fallback, unknown accuracy/cost, and a valid No AI result |
| R5 Must | Change and run a workflow | Immutable versions, diff, actual input/output/latency/context/tool trace; bounded nodes and human approval supported |
| R6 Must | Change a prompt | Versioned template and settings; rollback creates a new version; comparison uses actual executions |
| R7 Must | Inspect evaluation | Case-level checks, actual timing, token usage only when provider supplies it; no judge-only verdict |
| R8 Must | View analysis | DEMO and real cohorts separated; denominator and zero-data state explicit; ordered funnel |
| R9 Should | Create an experiment | Links confirmed opportunity, hypothesis, control/non-AI/AI candidates, metrics and preregistered decision rule |
| R10 Later | Multi-user hosted workspace / connectors | Not required to validate the MVP task; unavailable capabilities clearly labeled |

## AI architecture and boundary
Default mode is deterministic extractive evidence selection, not a language model. An optional configured remote provider can return schema-constrained evidence claims; every citation and quotation is validated. Human acceptance remains separate. Source text is untrusted data, never a tool instruction. Bounded workflow tools are read-only local evidence search; arbitrary MCP nodes fail with an explicit unsupported error rather than simulate execution.

Failure cases: no sources, unrelated sources, duplicate claims, invalid JSON, timeout, unknown model usage, failed schema, rejected approval and stale prompt. Preserve error traces; never mark a failed run successful or invent token counts. A rule fallback is labeled as such and must not conceal a model failure.

## Metrics, evaluation and experiment
Instrument project/source/insight/opportunity/workflow/evaluation/experiment lifecycle events with pseudonymous user, project, UTC time and demo flag. Primary product metric is a verified decision, not button clicks. Automated checks validate format/provenance and required behavior; human rating is nullable until reviewed. Run a usability pilot before powered A/B experimentation. See documents 11 and 12.

## Rollout, risks and dependencies
Release local synthetic demo first. Before raw data use: consent, redaction, backup/retention agreement and private storage. Before hosted production: authentication, authorization, isolation and deployment controls; these are not implemented in this single-user MVP. Before paid inference: configure provider, model, privacy permission and actual budget.

Open questions: Does the chain reduce missing assumptions? Is the reviewer willing to use another tool? Which fields can be removed? Will users maintain the evidence record after shipping? These require observation, not more generated documentation.
