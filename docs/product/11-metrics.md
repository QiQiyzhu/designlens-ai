# Metric tree and instrumentation

**PENDING REAL USER RESEARCH**. The application can calculate software activity; seeded activity is DEMO/SYNTHETIC and is never a business metric.

## North star: Weekly Validated Product Decisions
Count distinct opportunity decisions in a UTC week only when: (1) accepted real evidence is linked; (2) a named human records an architecture and reason; (3) a completed real evaluation or study is attached; (4) an experiment/review has an observed result; (5) a human records build/revise/stop with limitations. Draft protocols, demo evidence and clicks do not qualify. MVP leaves this **0 / awaiting real studies**, rather than equating experiment creation to validation.

| Metric | Definition / denominator | Why / limitation |
|---|---|---|
| Activation | New projects reaching first accepted insight within 7 days / eligible new projects | Evidence review is early value; immature cohorts excluded |
| Insight acceptance | Accepted / (accepted + rejected) in reviewed cohort | Review usefulness; not accuracy, and selection bias exists |
| Evidence coverage | Valid source-linked accepted insights / accepted insights | Detects broken provenance; not semantic truth |
| Opportunity → experiment | Opportunities with a protocol / confirmed opportunities | Shows follow-through; a draft is not an outcome |
| Workflow success | Completed without error / terminal runs | Reliability; pending approval excluded and shown separately |
| Evaluation pass | All applicable checks passed / executed cases | Dataset-scoped technical behavior; not general model quality |
| Time to decision | Median elapsed from first evidence to human decision | Includes waiting; pair with observed active task time |
| Week-4 retention | Week-0 activated users active days 28–34 / matured activated cohort | Real adoption; not meaningful before cohort matures |

Guardrails: unsupported claim rate (manually audited semantic sample, not citation existence alone); cost/run (provider billing basis, unknown when unavailable); latency P50/P95; override rate (human disagreement / reviewed suggestions); AI failure rate (failed remote runs / remote attempts). A higher acceptance rate can indicate reviewer complacency, so do not optimize it alone.

## Events and units
`project_created → source_uploaded → insight_accepted → opportunity_created → experiment_created` is an **ordered project-level funnel**. Events include UTC timestamp, user_id, project_id, entity_id, is_demo and properties. Reject/review transitions are logged, but use current distinct insight state for acceptance to avoid repeated clicks inflating the rate. Deduplicate retries where possible. Missing denominator returns null, never 0% pretending a measured result.

Tables: users, projects, events, experiments, workflow_runs plus decision entities. SQL and a Python export are in analytics/. Days/weeks are UTC, filters are explicit. Seeded test events validate queries only. A public demo user is a demonstration identity, not an acquired user.
