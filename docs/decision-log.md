# Decision log

Actual implementation choices; role labels are a project planning exercise, not named team members.

| ID | Decision | Alternative / tradeoff | Evidence / revisit trigger |
|---|---|---|---|
| D01 | Write discovery assumptions and research plan before core code | More immediate UI output | User explicitly requires product thinking; revisit after real interviews |
| D02 | Default to deterministic extraction | Paid model by default | No provided model credentials or real dataset; makes provenance reproducible |
| D03 | Exact claim text must equal quote | Allow free-form inference with a citation | Citation existence does not prove entailment; broader insight synthesis needs human/semantic evaluation |
| D04 | Keep recommendation and human decision distinct | Auto-prioritize | Human owns the opportunity and uncertainty; override is meaningful data |
| D05 | Sequential bounded workflow | General graph/agent platform | Scope versus deadline; supports actual conditions/approval with understandable traces |
| D06 | No arbitrary MCP execution | Pretend a connector ran | Unimplemented external calls must fail honestly; revisit on observed tool requirement |
| D07 | Pin prompt/workflow/source snapshots per run | Resolve latest versions on resume | Pending human approvals must not silently change after editing |
| D08 | Null unknown metrics, separate demo cohort | Attractive seeded business chart | No real user evidence exists; avoid false outcomes |
| D09 | Compare UI/rules/search before AI | Preselect build advisor | Research might show an information hierarchy problem, not a language problem |
| D10 | One local workspace and SQLite | Multi-tenant hosted service | Limits infrastructure scope; hosted deployment requires auth and data isolation |

Typical future tradeoffs are not claimed as measured: quality versus latency, model quality versus cost, automation versus approval. Record actual provider timing and user task consequences before choosing a bigger model or removing review.
