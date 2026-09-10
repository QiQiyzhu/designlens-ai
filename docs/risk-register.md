# Risk register

Planning exercise, reviewed 2026-09-10.

| Risk | Likelihood / impact | Early signal | Mitigation / owner role |
|---|---|---|---|
| No meaningful unmet need | Unknown / high | Manual stack completes tasks just as well | Recruit actual PMs; kill/pivot criterion / PM |
| Synthetic results mistaken for business data | Medium / high | Portfolio headline says “users improved” | Labels in UI, reports, README and claim ledger / PM, Data |
| Valid citation but invalid inference | High / high | Quote supports only part of claim | Exact-extract MVP + human interpretation review / AI |
| Privacy leakage | Medium / high | Raw notes committed or remote model receives real data | Ignored private directory, consent gate, env remote gate / Backend |
| Model latency/cost degrades task | Unknown / medium | P95 exceeds task budget | Measure first, narrow context, rules/search fallback / AI, PM |
| Workflow feature creep | High / medium | Arbitrary tools requested before task evidence | Read-only allowlist; explicit unsupported MCP / PM |
| One researcher confirmation bias | Medium / high | Positive quotes only, no counterexamples | Negative-case log, external reviewer if available / Research |
| Unprotected demo treated as hosted team product | Medium / high | Real external users submit confidential data | Local-only default, no enterprise claims / Backend |
| Eval overfit | High / medium | Perfect development cases but unseen failures | Frozen future held-out user-derived cases; report fixture limits / AI |
| Figma skill overstated | Medium / medium | Website presented as manual design work | Explicit manual learning deliverable still pending / Design |
