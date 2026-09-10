# AI feasibility canvas

**PENDING REAL USER RESEARCH** for user demand. Technical recommendations are explicit heuristics to support human discussion, not measured model guarantees.

| Architecture | Appropriate task | Main dependency / failure | Review and fallback |
|---|---|---|---|
| No AI | Missing labels, unclear layout, fewer choices | Design iteration; may not handle nuanced questions | Usability test; restore prior UI |
| Rules | Known deterministic constraints / small finite catalog | Maintenance and uncovered conditions | Unit tests, transparent rule trace, no-answer |
| Search | Find existing evidence or help | Index coverage, ambiguous query | Show originals; manual browse |
| Traditional ML | Repeated classification with labeled examples | Label volume, drift, subgroup bias | Held-out evaluation, confidence abstention |
| LLM | Language transformation with bounded scope | Unsupported claims and variable latency | Schema + source checks; extractive fallback |
| RAG | Answers must use a changing evidence corpus | Retrieval misses, stale context and citation mismatch | Source snippets; abstain if context insufficient |
| Agent | Task truly requires iterative tool selection | Compounding errors, cost, side effects | Allowlisted tools, budget, approval, manual execution |
| Multimodal | Task cannot be solved without image/audio meaning | Consent, redaction, costly misinterpretation | Human verification; text-only input |

Every canvas compares expected accuracy (unmeasured until evaluation), latency budget, cost basis, data availability, context, personalization, tools, risk, explainability, privacy, human review and fallback. Unknown numbers stay unknown. Output includes reasons, known failure modes, non-AI alternative and MVP boundary.

The current backend chooses No AI for deterministic UI/task fixes; Rules for a finite rule problem; Search when source lookup suffices; and proposes RAG only for evidence-dependent language work with usable data. Sensitive input without permission blocks a remote model recommendation. Agent requires an actual tool need; that condition alone is not approval to build it.

## Candidate ARC//SHIFT advisor — not selected
Only if research supports it: accept weapon/cards/relics/route/HP/resources and return 2–3 options with why, trade-off and alternative. Never choose for the player. Compare static contextual descriptions and rules first. Require catalog-grounded claims, an explicit no-answer state, visible latency and a rule fallback. Read-only context does not justify an autonomous Agent. The feature is **NOT BUILT / PENDING RESEARCH DECISION**.
