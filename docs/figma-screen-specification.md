# Figma-ready screen specification

This is a design handoff and learning reference. **No Figma file has been created by this project.** The author should manually recreate and refine the six key screens in Figma, including components, auto-layout, variants and a clickable prototype.

## Foundation
Desktop reference: 1440×1024. Minimum designed desktop: 1120 px wide. Shipped navigation rail: 240 px (205 px below 1250); header: 76 px. Content margin: 38 px (27 px below 1250). For manual Figma work, use a 12-column grid with 24 px gutters inside this region; shipped split panels use 22–23 px gaps and 23 px internal padding. Detail drawers use 520 px with a 95vw cap; keep evidence text at a comfortable 60–80 character line length. Tables scroll horizontally without clipping actions.

Typography: system sans / Inter fallback; display 30/38 semibold, page heading 24/32, section 18/26, body 14/22, caption 12/18, mono 12/20 for IDs, prompts and diffs. Spacing scale: 4,8,12,16,24,32,48. Radius: 6 inputs, 10 panels, 999 badges. Use restrained shadows only for floating layers.

Shipped token roles: canvas #F5F7F9, surface #FFFFFF, text #182F42, muted #617D8E, border #DEE6EC, primary #1C5276, accepted text #317155 on #E4F3EB, pending text #9D792D on #FBF3E5, rejected text #A05D50 on #FDEEEA. Focus outline #709ABD; inspect contrast while recreating in Figma. Do not use color alone: badges include Suggested/Accepted/Rejected and DEMO text. CSS is the source for final visual values; the grid is a suggested Figma construction method, not a claim that a Figma file already exists.

## Shared components
AppShell; breadcrumb; project switch label; ResearchStatusBanner; Primary/Secondary/Destructive Button with loading/disabled; source-type chip; EvidenceConfidenceBadge; SourceCard; EvidenceQuote; HumanDecisionPanel; ScoreInput with unit; NodeCard; VersionSelector; DiffViewer; RunStatus; MetricCard with denominator; empty/error/loading states; confirmation inline panel; toast with recovery action. Keyboard focus must be visible and all icon-only buttons need accessible names.

## Screen 1 — Research Dashboard
Purpose: understand what evidence exists and what to do next. Header contains workspace title and Import. A persistent banner says “DEMO/SYNTHETIC · Real player research pending”. Summary cards show source count, review state and actual research status, without fake user or impact numbers. Source list supports selection/type labels; adjacent detail shows original content, participant/source, timestamp basis and metadata.

Interaction: Import opens a form for filename/file text and metadata. Validate format/content before submit; preserve entered text on error. A successful import returns new source IDs, then “Draft observations” operates on selected sources. Empty state: “Add consented research or explore the labeled demo.” Loading uses a clear spinner and prevents double submission.

## Screen 2 — Evidence-backed Insight
Two columns: interpretation/draft on left (7 columns); exact quote and original source on right (5). Display Observation / Pain point / Need distinctly; default extractive drafts say human interpretation pending. Source links remain one click away. Confidence is a reviewer selection with a rubric tooltip, not model certainty.

Actions: Accept or Reject requires a note; acceptance does not auto-create a feature. Rejected state remains inspectable. Missing or invalid evidence blocks acceptance and shows a repair message. Long quotes scroll in the detail panel, not truncate the provenance behind an ellipsis.

## Screen 3 — Opportunity Map
Header: business goal and “Create from accepted insights”. Main area links goal → problem → opportunity → solution → experiment. A selected opportunity exposes segment, severity/frequency basis, assumptions, RICE/ICE and MoSCoW. Separate the recommendation card from the human decision card.

Pending state calls for a decision with reason. Confirmed can proceed to experiment; deferred/rejected remains in the map. Score units are visible; zero effort is invalid. Do not animate a higher score as if it proves more demand.

## Screen 4 — AI Feasibility Canvas
Inputs in a left panel: task, data, privacy, latency budget, tools, error cost. The main matrix compares all eight architectures with accuracy/cost marked unmeasured where appropriate. The selected recommendation has reasons, failure modes, non-AI alternative and MVP boundary.

No-AI result is a normal success state. Local-only privacy can restrict remote recommendations. A user can confirm or disagree with rationale; the UI never sends credentials or private source text merely to render the canvas.

## Screen 5 — Workflow Builder
Sequential node canvas with visible numbered order; node palette supports the nine documented types. Selected node opens label/config controls. Prompt panel shows template, variables, model label, temperature, output contract and immutable version. Diff uses added/removed lines with text labels; rollback creates a new version.

Run shows input, context IDs, node trace, output, real duration and unknown token state. Human Approval pauses and presents exact source excerpts; Approve/Reject resumes or terminates the pinned run. MCP node is visibly unavailable in this MVP; do not depict a green successful external call. Conditions show the observed count, operator and branch outcome.

## Screen 6 — Evaluation Dashboard
Top: dataset name/hash, provider, run time and synthetic label. Comparison table shows actual variant cases, passes, format/grounding, latency and pending human review. Selecting a failed case opens input, expected behavior, output, individual rules and evidence. Human rating starts empty and needs a note.

The baseline failure is visible, not hidden to improve a headline. Agent row says skipped with reason. Token usage displays “No model call” in extractive mode; missing real-provider usage says unavailable. Never show a progress bar or percentage before a run is finished.

## Analytics / experiment supporting screen
Display an explicit DEMO/real cohort control, UTC windows and denominators. Null means “No eligible data”, not 0%. Keep validated decisions at pending until real study outcomes exist. Protocol form separates hypothesis, primary metric, secondary metrics, guardrails, variants and decision rule. All new experiments are Planned; no auto-generated uplift.

## Figma practice checklist
Create token variables, use Auto Layout, build button/status variants, use component instances and prototype the import → review → opportunity → feasibility → run → approval → failed-case flow. Include keyboard/focus annotations, narrow-screen overflow, empty/error states and a redline page. Export six frame PNGs and a prototype URL only after you have actually created them; do not claim a generated website is a Figma deliverable.
