# Validation and evidence boundaries

The release evidence is machine-readable in [validation.json](../reports/validation.json). These checks are software tests, not research participants or product outcomes.

| Check | Actual result | Artifact |
|---|---|---|
| Backend | 43 passing tests; 0 failures/errors | [JUnit](../reports/backend-tests.xml) |
| Browser | 6 complete user-flow checks with actual FastAPI/SQLite | [Compact browser report](../reports/browser-tests.json) |
| Evaluation | 48 actual executions: 12 synthetic cases × 4 variants | [Case report](../reports/evaluation.json), [readable comparison](../reports/evaluation.md) |
| Frontend | TypeScript check, Vite production build and lint completed | Commands in README / CI |
| Built app smoke | FastAPI serves the built UI; 6 sources/7 workflow nodes; no page errors or failed assets | [Production smoke](../reports/production-smoke.json) |
| Dependency audit | Unused Vitest removed; clean `npm ci`; npm audit reports 0 known vulnerabilities | [npm audit](../reports/npm-audit.json) |
| Analytics | SQL queries executed against schema; demo activity exported | [SQL](../analytics/queries.sql), [demo export](../reports/analytics-demo.json) |
| Visual review | Desktop source/insight, workflow, evaluation and narrow-screen screenshots inspected | [Screenshots](screenshots/) |

Browser coverage: source → original excerpt, Escape/focus containment, malformed import recovery, CSV persistence, extract generation, human insight review, opportunity scoring and confirmation, No-AI comparison, planned protocol, prompt/workflow versions and diff, durable approval, actual evaluation failure inspection, scripted rating, demo/real cohort separation and 390px no-horizontal-overflow.

The browser uses a fresh synthetic SQLite file on port 8002. Its review/rating actions are automated QA input, **not interviews or an actual human-rating study**. The normal demonstration workspace on port 8001 is separate. Screenshot data is labeled synthetic. The default evaluation report keeps human ratings null and token usage null because no model was called.

## Actual fixes discovered during verification
- Invalid import errors preserve the input rather than discarding it; the modal shows the error.
- Filled textarea controls have explicit accessible names, so keyboard and automation can locate them consistently.
- Workflow UI reads the pinned active-version nodes; prompt changes do not silently update saved workflows.
- Evidence review changes prevent a stale opportunity from being confirmed or used to create a protocol.
- A malformed custom output schema returns a validation error.
- Mixed synthetic/real context is excluded from real-data workflow metrics.
- Missing analytics denominators display an empty state instead of a fabricated 0%.

## Known limits
The evidence extractor is deterministic and narrow. Its perfect development-fixture result with retrieval does not establish generalization or model intelligence. The tests do not measure actual PM decision quality, game onboarding, willingness to pay, retention or business impact. Hosted authentication/data isolation, arbitrary MCP/Agent execution and live-provider evaluation remain outside the demonstrated scope. Two environment dependency deprecation warnings occurred in the Python test run; they did not fail the tests.

Real player research, an evidence-selected game intervention, manual Figma work and product experiments remain **PENDING REAL USER RESEARCH / NOT EXECUTED** as applicable.

The GitHub Actions workflow under `.github/workflows/backend.yml` actually passed on Linux: [run 34440912752](https://github.com/QiQiyzhu/designlens-ai/actions/runs/34440912752), commit `6211fe89ba41e95449b52e3f38d82505581e84e6`. The backend and browser jobs completed successfully, including 43 backend tests and 6 browser cases.

The additional [read-only HTTP sample](../reports/performance-readonly.json) records 255 actual local requests at 10/25/50 worker concurrency, with zero errors. It is a short synthetic-data observation, not production capacity. Method, raw samples, percentiles and limits are in the [A–T dossier](interview-dossier.md#m-performance-真实结果).
