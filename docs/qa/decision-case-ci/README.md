# Decision-case Linux evidence

Source `29d007bf639d281894131daeeddb11f515b1de96`; [run 34463711921](https://github.com/QiQiyzhu/designlens-ai/actions/runs/34463711921), completed successfully on 2026-09-10.

- `run.json`: actual GitHub run/job metadata; backend and browser succeeded. Browser job log records 6 passed in 11.6 seconds.
- `backend-junit.xml`: exact downloaded `backend-evidence/backend-tests.xml`; 44 tests, zero errors/failures/skips.
- `decision-case-ci.json`: exact downloaded report; 48 newly executed deterministic cases and actual FastAPI/SQLite rejection paths. Human input is scripted QA; real participants and validated product decisions remain zero.

These are fixed first-implementation-run artifacts, not a claim that this SHA contains subsequent documentation changes. The main export additionally records LF-normalized source hashes and original working-tree hashes, so Windows CRLF conversion can be distinguished from a content change; this original CI artifact remains untouched.
