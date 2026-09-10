# Evaluation report

SYNTHETIC evaluation fixtures; actual executions, not real user or model-quality evidence

Executed: 2026-09-10T04:53:36.168746+00:00
Dataset SHA-256: `71ecece501189fd39ec5cb244485247231a5bb06115d31171452bf0bc72131dc`

| Variant | Passed / cases | Format | Grounding | Mean latency ms | Pending human review |
|---|---:|---:|---:|---:|---:|
| Prompt V1 | 0 / 12 | 0.0% | 0.0% | 0.011 | 0 |
| Prompt V2 | 11 / 12 | 100.0% | 100.0% | 0.007 | 0 |
| RAG | 12 / 12 | 100.0% | 100.0% | 0.089 | 0 |
| Workflow | 12 / 12 | 100.0% | 100.0% | 0.094 | 10 |

- Default provider is deterministic extraction; prompt comparison tests contracts, not LLM reasoning quality.
- Citation/quote checks do not establish semantic insight correctness.
- Workflow candidates may await human approval; rule-check pass does not mean human acceptance.
- Cases are development fixtures, not an independent held-out generalization benchmark.
- Token usage is null without a model call; human ratings remain null until recorded.

Agent: skipped — no demonstrated autonomous tool need.

The extractive provider follows output_mode configuration. It does not understand or optimize prompt prose. Prompt V1 is the plain-text contract baseline; V2 is a structured exact-extract contract. Their difference is not evidence of LLM intelligence or a real user benefit.
