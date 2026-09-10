# Retrospective — implementation stage

**PENDING REAL USER RESEARCH**. This retrospective concerns actual product and implementation choices, not user outcomes.

## What changed
The initial brief spans discovery, AI workflows, evaluation and experimentation. We chose one bounded decision chain rather than a general chat interface. The phase-0 documents were written before the main backend implementation. Default examples and model-free runs are explicitly labeled; real research remains blank. Competitor research showed that source-linked synthesis and integrated AI already exist, especially in Dovetail and Productboard, so “we have evidence links” is insufficient differentiation.

## Trade-offs
SQLite and one workspace keep a local demonstration reproducible, but do not solve hosted team permissions. Extractive default behavior makes provenance auditable without credentials, but cannot validate the quality of a language model. A bounded workflow supports conditions and human gates while deferring arbitrary MCP and autonomous tools. These are deliberate scope limits, not hidden completed features.

## Current largest failure risk
The software could make an unvalidated product hypothesis look convincing. An attractive dashboard, many sources and a perfect fixture score can all be mistaken for real value. We therefore keep raw evidence reachable, empty research artifacts visible and dataset/provider labels on reports. Product usefulness still requires real users and a comparison with their existing process.

## What we would do next
Recruit the PM interviews and ARC//SHIFT pilot, then remove fields that do not help a real decision. Freeze a user-provided dataset before changing prompts. Run real-provider variants only after data permission and budget are explicit. Ask someone unfamiliar with the implementation to reconstruct a decision and report missing links. Do not add a game advisor until observed player behavior supports it.

## What has not been learned
No validated pain prevalence, willingness to pay, time savings, retention gain, conversion gain or statistically significant product effect. The implementation's test report is evidence about code behavior only. Maintain that distinction in interviews and in the résumé.
