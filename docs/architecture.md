# Architecture and operational boundaries

The product is a single-user local prototype. React/TypeScript owns interaction; FastAPI validates actions; SQLite persists evidence, decisions, prompt/workflow versions, traces and activity. It deliberately does not implement multi-tenant access control, arbitrary remote tools or production experiment assignment.

## Data model
users/projects/events/experiments/workflow_runs have explicit SQLite tables. Small product entities use a typed category plus JSON payload so versions and evolving canvas fields remain simple in the MVP. Queries bind values; file contents are never evaluated. Imports support TXT/MD as one source and CSV/JSON as records, validate all rows before writing and retain original external ID, file hash, row and timestamp basis.

The intake preview performs local cleanup without persistence or model calls. Real imports require consent and a digest of the reviewed input and cleanup settings. Only the cleaned copy is retained, with the original file hash and cleaned provenance metadata; raw file bytes and replacement terms are not stored. Retained source content is immutable through the API. Claims must reference this retained source and an exact excerpt. The extractive MVP requires claim text to equal its quote; human interpretation is a separate review task. This protects a narrow provenance contract, not the truth or representativeness of the source itself.

## Workflow and prompt execution
Workflow nodes execute in listed order. Input, Retrieval, Prompt, LLM/extractor, Condition, Tool, Human Approval and Structured Output have real behavior. MCP is a visible unsupported design node and fails explicitly. The only enabled tool is local read-only evidence search. Conditions compare context_count/claim_count to a numeric threshold and either continue, abstain or error.

Each run snapshots workflow, prompt and sources. Human Approval records a pending run; review resumes the pinned snapshot, not whichever version is currently active. Repeated terminal approval is rejected. This MVP is designed for one local user; a multi-worker concurrent deployment would need transactional compare-and-swap state transitions and task queue/idempotency controls.

Prompt edits append immutable versions; rollback creates a new copy and clears evaluation association. Evaluation results reference prompt versions, workflow version and dataset hash. The default extractor uses output_mode configuration, not natural-language reasoning; changing prose alone will not improve its behavior. A real model can be configured with server environment variables and will use the actual prompt text.

## Provider boundary
No key is needed in extractive mode. Remote mode requires a provider URL, model and key. Source text is framed as data, output is parsed, exact source/quote checks run, and remote failures are recorded without silently substituting a successful demo result. Token usage is null if unavailable; cost is unknown without a billing basis. Real evidence needs the global permission AND a reviewed intake AND per-source approval matching the current content hash. Approval changes and their audit event share one SQLite transaction; revoke prevents future calls, not past transfers. Known identifier patterns are checked in source text and the rendered request before transport. These checks remain incomplete local suggestions, not an anonymization or authorization system.

No automatic secret loading or `.env` parsing occurs. Never put keys in frontend bundles, exported packets or Git. The API exposes local source text by design and therefore must not be exposed publicly with confidential research until authentication/authorization and data handling are implemented.

## Evaluation and analytics
The fixture dataset is hand-authored and explicitly synthetic. Expected behavior/reference fields are used only by the evaluator, not passed to the provider. Comparisons execute variants, preserve outputs/errors and report format, grounding, required/forbidden content, reference coverage, abstention, actual duration, available tokens and nullable human review. Workflow candidates may pass rules while still awaiting human approval. Agent is not benchmarked because no autonomous tool task is implemented.

Analytics uses actual recorded local events. Demo and real-data cohorts are explicit; a mixed-source workflow is marked demo so synthetic context cannot become a real-data success claim. The project funnel preserves order, acceptance uses current distinct states, and missing denominators stay null. The North Star is not incremented by a draft experiment.

## Risks before production
Add authentication, ownership checks, tenant isolation, request size/rate budgets, private storage, backup/restore, audit retention, workflow queues and transactional review transitions. Real research and provider evaluation also remain pending. These are concrete release boundaries, not claims that the current code is production-ready.
