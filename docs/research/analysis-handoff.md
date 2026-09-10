# When real data arrives

Current state: **PENDING REAL USER RESEARCH**.

1. Verify consent, pseudonymous IDs, session dates, game version and redaction. Keep contact information out of imports and Git.
2. Import TXT/Markdown or rows using the format in examples/import-format.json. Set is_demo=false only for consented real records. An import timestamp is not a session timestamp; provide the latter explicitly when known.
3. Code observed behavior before proposing features. Keep positive/negative examples and non-users of AI. Count independent participants, not source rows.
4. Use extractive drafts to find text, then accept/reject with a review note. Explain why a quote supports an interpretation; a valid source ID alone is not enough.
5. Create an opportunity from accepted insights, record RICE assumptions and the human decision. Mark frequency as “observed in x of n pilot participants” only after deduplicating real participants; avoid population generalization.
6. Choose top three problems based on task severity, recurrence, counterexamples and scope. Compare non-AI solutions, not only architectures involving a model.
7. Choose one MVP and freeze its experiment plan. Fill a baseline, rubric, exclusion rules and decision rule from actual study needs; do not invent a statistically powered A/B design from 8–12 participants.
8. Export a review packet. Replace pending case-study fields only with linked raw evidence and actual results. Preserve the initial hypothesis and what changed.

Evidence confidence rubric: Low = isolated/indirect/unreviewed; Medium = multiple independent relevant observations with acknowledged disagreement; High = convergent independent evidence with triangulation and a documented review. A small convenience pilot often remains Medium. “High” describes confidence in a local finding, not a claim of representative prevalence.
