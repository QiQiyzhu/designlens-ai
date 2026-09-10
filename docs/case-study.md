# DesignLens — product case study at the preparation stage

## Context
I wanted a portfolio that demonstrates how an AI PM makes a decision, not only how a model can draft a PRD. The first application context is ARC//SHIFT, an existing action roguelite with several systems a new player must understand. The owner has not yet supplied real player data.

## Research
**PENDING REAL USER RESEARCH.** I prepared recruitment, consent, task observation, a 5–10 minute post-play interview and a survey for an 8–12 person qualitative pilot. Public competitor review covered ChatPRD, Dovetail, Productboard, Amplitude, Notion AI, Linear, ChatGPT and Claude with dated official sources. This is desk research, not customer validation.

## Insight
The current product hypothesis is that source evidence becomes detached from architecture and experiment decisions. It is not a finding from interviews. Competitor documentation already includes evidence linking and AI synthesis; therefore “another summarizer with citations” is not a defensible differentiation claim. The proposed difference is the typed decision chain and its review gates.

## Decision
Build a local MVP that can carry one reviewable packet across the chain. Use deterministic exact extraction by default, keep AI suggestions separate from human decisions, compare non-AI alternatives, and require actual executions for evaluation tables. Defer real game advice, autonomous tools and enterprise features.

## Design
Six principal screens expose the user's next action, source context and decision state. Source detail remains one click from an insight; architecture has a normal No-AI result; runs visibly stop for approval; failed evaluation cases are inspectable. A Figma-ready specification is provided, but manual Figma work remains the author's learning task.

## Build
The functioning prototype imports four formats, preserves provenance, supports human insight/opportunity review, compares eight architecture categories, versions prompts/workflows, executes a bounded pipeline and writes experiment protocols. Optional real-provider execution is configured through server environment variables; the default mode is clearly labeled as no-model extraction.

## Evaluation
The [recorded report](../reports/evaluation.md) contains actual executions on synthetic development cases. It tests format/provenance and required behavior. It cannot establish LLM quality, real player comprehension, time savings or product-market fit. A human rating remains missing until someone actually reviews that output.

## Experiment
No product experiment has been run. A prepared plan compares current UI, a traditional explanation and an AI option only if real evidence justifies it. The small proposed sample supports a qualitative usability pilot, not a statistically significant retention claim. All in-app experiment records begin as Planned with no result.

## Learning and next decision
The key implementation learning is that trustworthy product artifacts need state and evidence constraints, not confident prose. The key unknown is whether that structure helps an actual PM enough to justify another tool. Next: collect real notes, derive the top three problems, select one intervention and update this case study with raw evidence, disagreements and observed outcomes.

## Safe portfolio statement
“Built an evidence-to-decision AI product prototype with source traceability, explicit human review, architecture alternatives and reproducible evaluation; prepared a qualitative ARC//SHIFT research study. Real-user validation is pending.” Do not change this to a claim that the product improved player retention or that interviews have already happened.
