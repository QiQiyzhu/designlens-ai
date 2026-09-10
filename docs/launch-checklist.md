# Launch checklist and honest release boundaries

## Local synthetic prototype
- [x] Product assumptions, competitor sources and research preparation documented.
- [x] Default data is visibly synthetic; no real participant response fabricated.
- [x] Source content and metadata persist; suggestions require human review.
- [x] Prompt/workflow versions and human approval are implemented.
- [x] Agent/MCP unavailable scope is explicit.
- [x] Confirm combined frontend/backend checks in [validation report](validation-report.md): 43 backend tests and 6 browser user flows.
- [ ] Author manually builds six Figma screens; do not mark complete from a web screenshot.

## Before a real study
- [ ] Recruit real participants and obtain consent.
- [ ] Redact and keep raw data private; agree retention/withdrawal.
- [ ] Freeze game version/tasks, record actual participant count and interventions.
- [ ] Compare top problems and non-AI alternatives before choosing an advisor.

## Before a hosted multi-user product
- [ ] Authentication, authorization, tenant isolation and private source storage.
- [ ] Request budgets/rate limits, secrets management and audit retention.
- [ ] Provider/data permission and budget; live provider regression evaluation.
- [ ] Restore/backup and deletion procedures exercised.
- [ ] Real study and experiment outcomes reviewed; claims tied to evidence.

Unchecked items are not hidden behind “production-ready”. An interviewer can assess the functioning local MVP and planning artifacts now; validated product outcomes need real fieldwork.
