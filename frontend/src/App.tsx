import {
  AnalyticsPanel,
  EvaluationLab,
  FeasibilityResult,
  WorkflowStudio,
  object,
} from "./WorkspacePanels";
import { useEffect, useState, useCallback, useRef } from "react";
import {
  Layers,
  Library,
  GitFork,
  Compass,
  Workflow,
  FlaskConical,
  ChartNoAxesCombined,
  Plus,
  ArrowUpRight,
  ArrowRight,
  Check,
  Upload,
  Search,
  Link,
  Quote,
  RefreshCw,
  X,
  ChevronDown,
} from "lucide-react";
import { api, text, type Bootstrap, type Row } from "./api";
import { CleanupPreview, SourcePrivacyReview, type IntakePreview } from "./PrivacyReview";
const nav = [
  ["Research", Library],
  ["Opportunities", GitFork],
  ["AI feasibility", Compass],
  ["Workflows", Workflow],
  ["Evaluation", FlaskConical],
  ["Analytics", ChartNoAxesCombined],
] as const;
function Json({ value }: { value: unknown }) {
  return <pre>{JSON.stringify(value, null, 2)}</pre>;
}
const empty = {
  sources: [],
  insights: [],
  opportunities: [],
  feasibility: [],
  workflows: [],
  prompts: [],
  evaluations: [],
  experiments: [],
  analytics: null,
  meta: {},
  project: { id: "arc-study" },
} as Bootstrap;
export default function App() {
  const [privacyPreview, setPrivacyPreview] = useState<IntakePreview | null>(null);
  const [cleanupReviewed, setCleanupReviewed] = useState(false);
  const intakeRevision = useRef(0);
  const [data, setData] = useState(empty),
    [screen, setScreen] = useState("Research"),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [selected, setSelected] = useState<string[]>([]),
    [evidence, setEvidence] = useState<Row | null>(null),
    [search, setSearch] = useState(""),
    [dialog, setDialog] = useState<string | null>(null),
    [form, setForm] = useState<Record<string, string>>({}),
    [opportunity, setOpportunity] = useState(""),
    [result, setResult] = useState<unknown>(null),
    [workflow] = useState("evidence-workflow"),
    [run, setRun] = useState<Row | null>(null);
  const reload = useCallback(async () => {
    try {
      setData(await api<Bootstrap>("/bootstrap"));
      setError("");
    } catch (e) {
      setError(String(e));
    }
  }, []);
  useEffect(() => {
    void reload();
  }, [reload]);
  const act = async (fn: () => Promise<unknown>, success = "Saved") => {
    setBusy(true);
    setError("");
    try {
      const value = await fn();
      setMessage(success);
      await reload();
      return value;
    } catch (e) {
      setError(String(e));
      return undefined;
    } finally {
      setBusy(false);
    }
  };
  const update = (key: string, value: string) => {
    intakeRevision.current++;
    setForm((f) => ({ ...f, [key]: value }));
    setPrivacyPreview(null); setCleanupReviewed(false);
  };
  function field(
    label: string,
    key: string,
    placeholder = "",
    multiline = false,
  ) {
    return (
      <label>
        {label}
        {multiline ? (
          <textarea
            aria-label={label}
            rows={5}
            value={form[key] || ""}
            onChange={(e) => update(key, e.target.value)}
            placeholder={placeholder}
          />
        ) : (
          <input
            aria-label={label}
            value={form[key] || ""}
            onChange={(e) => update(key, e.target.value)}
            placeholder={placeholder}
          />
        )}
      </label>
    );
  }
  function show(name: string) {
    intakeRevision.current++;
    setDialog(name);
    setForm({});
    setPrivacyPreview(null); setCleanupReviewed(false);
    setMessage("");
    setError("");
  }
  useEffect(() => {
    if (!dialog && !evidence) return;
    const previous = document.activeElement as HTMLElement | null;
    const panel = document.querySelector<HTMLElement>("[role=dialog]");
    const focusables = () =>
      Array.from(
        panel?.querySelectorAll<HTMLElement>(
          "button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href]",
        ) || [],
      );
    focusables()[0]?.focus();
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setDialog(null);
        setEvidence(null);
      }
      if (event.key === "Tab") {
        const items = focusables();
        const first = items[0],
          last = items.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", handler);
    return () => {
      document.removeEventListener("keydown", handler);
      previous?.focus();
    };
  }, [dialog, evidence]);
  const accepted = data.insights.filter((i) => i.status === "accepted");
  const intakePayload = () => ({
    filename: form.filename || "feedback.txt", content: form.content,
    type: form.type || "User Feedback", participant: form.participant || "Demo source",
    segment: form.segment || "New players", is_demo: form.real !== "yes",
    consent_confirmed: form.consent === "yes",
    redaction_terms: (form.redactions || "").split("\n").map((x) => x.trim()).filter(Boolean),
  });
  async function submit() {
    if (dialog === "Import evidence" && !privacyPreview) {
      const revision = intakeRevision.current;
      await act(async () => {
        const preview = await api<IntakePreview>("/sources/preview", "POST", intakePayload());
        if (revision !== intakeRevision.current) throw Error("Input changed while preparing preview. Preview the current input again.");
        setPrivacyPreview(preview);
        setCleanupReviewed(false);
      }, "Preview ready. Nothing has been saved or sent to a model.");
      return;
    }
    await act(async () => {
      let value: unknown;
      if (dialog === "Import evidence") {
        value = await api("/sources/import", "POST", {
          ...intakePayload(), privacy_review_digest: privacyPreview?.preview_digest,
        });
      } else if (dialog === "Review insight") {
        value = await api("/insights/" + form.id, "PATCH", {
          status: form.status,
          review_note: form.note,
          confidence: form.confidence || "Low",
        });
      } else if (dialog === "New opportunity") {
        value = await api("/opportunities", "POST", {
          insight_ids: form.insight
            ? [form.insight]
            : accepted.slice(0, 1).map((i) => i.id),
          title: form.title,
          problem: form.problem,
          target_segment: form.segment || "New players",
          reach: Number(form.reach || 1),
          impact: Number(form.impact || 1),
          confidence: Number(form.confidence || 0.5),
          effort: Number(form.effort || 1),
          moscow: form.moscow || "Could",
          frequency: form.frequency || "Not measured; qualitative hypothesis",
          severity: form.severity || "Needs human assessment",
          business_impact: form.business || "Unknown; no product experiment",
          potential_solution:
            form.solution || "Compare clearer UI and rules before AI",
        });
      } else if (
        dialog === "Priority decision" ||
        dialog === "Architecture decision"
      ) {
        value = await api(
          (dialog === "Priority decision"
            ? "/opportunities/"
            : "/feasibility/") +
            form.id +
            "/decision",
          "PATCH",
          { decision: form.decision || "confirmed", reason: form.note },
        );
        if (dialog === "Architecture decision") setResult(value);
      } else if (dialog === "Plan experiment") {
        value = await api("/experiments", "POST", {
          opportunity_id: form.id || opportunity,
          title: form.title,
          hypothesis: form.hypothesis,
          primary_metric: form.metric,
          decision_rule: form.rule,
        });
      } else if (dialog === "Edit workflow") {
        const current = data.workflows.find((w) => w.id === workflow);
        value = await api("/workflows/" + workflow + "/versions", "POST", {
          name: form.name || text(current?.name),
          nodes: JSON.parse(form.nodes || "[]"),
          prompt_id: form.prompt || "evidence-summary",
          prompt_version: Number(form.version || 2),
          description: form.description || "",
        });
      } else if (dialog === "Edit prompt") {
        value = await api(
          "/prompts/" + (form.id || "evidence-summary") + "/versions",
          "POST",
          {
            goal: form.goal,
            template: form.template,
            model: "deterministic-extractor",
            variables: ["input", "context"],
            output_mode: "structured",
            temperature: 0,
          },
        );
      } else if (dialog === "Approve run") {
        value = await api<Row>("/runs/" + run?.id + "/approval", "POST", {
          approved: form.decision !== "reject",
          note: form.note,
        });
        setRun(value as Row);
      }
      setDialog(null);
      return value;
    });
  }
  return (
    <div className="app">
      <aside>
        <a href="/" className="brand">
          <span>
            <Layers size={23} />
          </span>
          DesignLens<i>AI</i>
        </a>
        <div className="project-switch">
          <div className="project-avatar">A</div>
          <div>
            ARC//SHIFT<small>Discovery workspace</small>
          </div>
          <ChevronDown size={15} />
        </div>
        <div className="nav-label">DECISION WORKSPACE</div>
        <nav>
          {nav.map(([name, Icon], i) => (
            <button
              className={screen === name ? "active" : ""}
              key={name}
              onClick={() => {
                setScreen(name);
                setResult(null);
                setMessage("");
              }}
            >
              <Icon size={18} />
              {name}
              <small>0{i + 1}</small>
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <div className="circle-icon">
            <Link size={17} />
          </div>
          <strong>Keep the evidence close.</strong>
          <p>Every recommendation starts with a source you can inspect.</p>
        </div>
        <div className="user">
          <span>Y</span>
          <div>
            Local researcher<small>Personal workspace</small>
          </div>
        </div>
      </aside>
      <main>
        <header>
          <div>
            <span>Workspace</span>
            <ArrowRight size={13} />
            <b>{screen}</b>
          </div>
          <div>
            <span className="mode">DEMO / SYNTHETIC</span>
            <button
              aria-label="Refresh workspace"
              className="icon-button"
              onClick={() => void reload()}
            >
              <RefreshCw size={17} />
            </button>
          </div>
        </header>
        <div className="page">
          <div className="title-row">
            <div>
              <div className="eyebrow">ARC//SHIFT · PRODUCT DISCOVERY</div>
              <h1>
                {screen === "Research"
                  ? "From signals to understanding."
                  : screen === "Opportunities"
                    ? "Choose what matters next."
                    : screen === "AI feasibility"
                      ? "Start with the simplest solution."
                      : screen === "Workflows"
                        ? "Make decisions repeatable."
                        : screen === "Evaluation"
                          ? "Test the claim. Keep the evidence."
                          : "See the path to a decision."}
              </h1>
              <p>
                {screen === "Research"
                  ? "Collect sources, inspect evidence and decide which insights deserve attention."
                  : screen === "Opportunities"
                    ? "Separate suggested priorities from decisions you have confirmed."
                    : screen === "AI feasibility"
                      ? "Compare rules, search and AI against the same product constraints."
                      : screen === "Workflows"
                        ? "Version the prompt, review its context and approve the output."
                        : screen === "Evaluation"
                          ? "Programmatic checks ground the result; human review judges usefulness."
                          : "Local workspace events, with synthetic activity kept separate from real research."}
              </p>
            </div>
            {screen === "Research" && (
              <button
                className="primary"
                onClick={() => show("Import evidence")}
              >
                <Plus size={17} /> Add evidence
              </button>
            )}
            {screen === "Opportunities" && (
              <button
                className="primary"
                onClick={() => show("New opportunity")}
                disabled={!accepted.length}
              >
                <Plus size={17} /> New opportunity
              </button>
            )}
          </div>
          <div className="research-status">
            <FlaskConical size={17} />
            <span>
              <strong>Research in preparation.</strong> No real player
              interviews have been collected. Demo sources validate the workflow
              only.
            </span>
            <span className="status-pill">PENDING REAL USER RESEARCH</span>
          </div>
          {error && (
            <div className="error" role="alert">
              {error}
              <small>
                Local service: port 8001. An unavailable service produces no
                invented result.
              </small>
            </div>
          )}
          {message && (
            <div className="success" role="status">
              <Check size={15} />
              {message}
              <button
                aria-label="Dismiss message"
                onClick={() => setMessage("")}
              >
                <X size={13} />
              </button>
            </div>
          )}
          {screen === "Research" && (
            <>
              <div className="stats">
                <article>
                  <span>Source library</span>
                  <strong>
                    {data.sources.length}
                    <small>sources</small>
                  </strong>
                  <p>Retained source stays inspectable</p>
                </article>
                <article>
                  <span>Suggested insights</span>
                  <strong>
                    {
                      data.insights.filter((i) => i.status === "suggested")
                        .length
                    }
                    <small>to review</small>
                  </strong>
                  <p>Human confirmation required</p>
                </article>
                <article>
                  <span>Reviewed & accepted</span>
                  <strong>
                    {accepted.length}
                    <small>insights</small>
                  </strong>
                  <p>Ready for opportunity mapping</p>
                </article>
                <article className="northstar">
                  <span>RESEARCH STANDARD</span>
                  <h3>A conclusion is only as useful as its evidence.</h3>
                  <p>Trace it. Challenge it. Decide.</p>
                </article>
              </div>
              <div className="research-grid">
                <section className="panel">
                  <div className="panel-title">
                    <h2>
                      Evidence library <span>{data.sources.length}</span>
                    </h2>
                    <button
                      className="quiet"
                      disabled={busy || !selected.length}
                      onClick={() =>
                        void act(
                          () =>
                            api("/insights/generate", "POST", {
                              source_ids: selected,
                            }),
                          "Evidence-backed suggestions generated",
                        )
                      }
                    >
                      <Layers size={15} /> Find signals
                    </button>
                  </div>
                  <label className="search">
                    <Search size={17} />
                    <input
                      aria-label="Search evidence"
                      placeholder="Search sources, participants or segments"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </label>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>
                            <input
                              aria-label="Select all sources"
                              type="checkbox"
                              checked={
                                selected.length > 0 &&
                                selected.length === data.sources.length
                              }
                              onChange={(e) =>
                                setSelected(
                                  e.target.checked
                                    ? data.sources.map((s) => s.id)
                                    : [],
                                )
                              }
                            />
                          </th>
                          <th>Source</th>
                          <th>Segment</th>
                          <th>Evidence</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.sources
                          .filter((s) =>
                            JSON.stringify(s)
                              .toLowerCase()
                              .includes(search.toLowerCase()),
                          )
                          .map((s) => (
                            <tr key={s.id}>
                              <td>
                                <input
                                  aria-label={"Select " + s.id}
                                  type="checkbox"
                                  checked={selected.includes(s.id)}
                                  onChange={(e) =>
                                    setSelected(
                                      e.target.checked
                                        ? [...selected, s.id]
                                        : selected.filter((id) => id !== s.id),
                                    )
                                  }
                                />
                              </td>
                              <td>
                                <button
                                  className="source-name"
                                  onClick={() => setEvidence(s)}
                                >
                                  {text(s.segment || s.id)}
                                  <small>
                                    {text(s.type)} · {text(s.participant)}
                                  </small>
                                </button>
                              </td>
                              <td>{text(s.segment)}</td>
                              <td>
                                <span className="tag">
                                  {s.is_demo ? "Synthetic" : "Real source"}
                                </span>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                    {!data.sources.length && (
                      <div className="empty">
                        <Upload size={28} />
                        <h3>Add your first source</h3>
                        <p>Import TXT, Markdown, CSV or JSON.</p>
                      </div>
                    )}
                  </div>
                  <div className="panel-foot">
                    {selected.length} selected · Retained sources are never
                    rewritten by suggestions.
                  </div>
                </section>
                <section className="panel insight-panel">
                  <div className="panel-title">
                    <h2>Signals to review</h2>
                    <Quote size={18} />
                  </div>
                  {!data.insights.length ? (
                    <div className="empty">
                      <h3>Listen before drawing conclusions.</h3>
                      <p>
                        Select evidence and find signals. Every suggestion links
                        back to its retained sources.
                      </p>
                    </div>
                  ) : (
                    data.insights.map((i) => (
                      <article className="insight" key={i.id}>
                        <div>
                          <span className="tag">{text(i.status)}</span>
                          <span className="confidence">
                            {text(i.confidence || "Low")} confidence
                          </span>
                        </div>
                        <h3>{text(i.title || i.observation || i.insight)}</h3>
                        <blockquote className="excerpt">
                          {text(i.observation || i.insight)}
                        </blockquote>
                        <p>
                          {text(i.pain_point)} · {text(i.need)}
                        </p>
                        {i.review_note != null && (
                          <p className="review-note">
                            <strong>Human review:</strong> {text(i.review_note)}
                          </p>
                        )}
                        <div className="evidence-links">
                          {(Array.isArray(i.evidence_ids)
                            ? i.evidence_ids
                            : []
                          ).map((id) => (
                            <button
                              key={String(id)}
                              onClick={() =>
                                setEvidence(
                                  data.sources.find((s) => s.id === id) || null,
                                )
                              }
                            >
                              <Link size={12} />
                              {String(id)}
                            </button>
                          ))}
                        </div>
                        <div className="review-actions">
                          <button
                            onClick={() => {
                              show("Review insight");
                              setForm({ id: i.id, status: "accepted" });
                            }}
                          >
                            <Check size={14} /> Accept
                          </button>
                          <button
                            className="quiet"
                            onClick={() => {
                              show("Review insight");
                              setForm({ id: i.id, status: "rejected" });
                            }}
                          >
                            Reject
                          </button>
                        </div>
                      </article>
                    ))
                  )}
                </section>
              </div>
            </>
          )}
          {screen === "Opportunities" && (
            <>
              <div className="goal-line">
                <Compass />
                <div>
                  <small>BUSINESS GOAL · HYPOTHESIS</small>
                  <h2>Help new players make informed build decisions</h2>
                </div>
                <span>Research → Opportunity → Experiment</span>
              </div>
              <div className="opportunities">
                {data.opportunities.length ? (
                  data.opportunities.map((o) => (
                    <article className="panel opportunity" key={o.id}>
                      <div className="panel-title">
                        <span className="tag">{text(o.moscow)}</span>
                        <span className="confidence">
                          {text(
                            object(o.human_decision).decision ||
                              "Awaiting decision",
                          )}
                        </span>
                      </div>
                      <h2>{text(o.title)}</h2>
                      <p>{text(o.problem)}</p>
                      <dl>
                        <div>
                          <dt>Target segment</dt>
                          <dd>{text(o.target_segment)}</dd>
                        </div>
                        <div>
                          <dt>RICE · suggested</dt>
                          <dd>{text(o.rice_score || o.rice)}</dd>
                        </div>
                        <div>
                          <dt>Evidence confidence</dt>
                          <dd>{text(o.evidence_confidence || o.confidence)}</dd>
                        </div>
                      </dl>
                      <div className="recommendation">
                        <small>PLANNING SUGGESTION</small>
                        <p>{text(o.ai_recommendation)}</p>
                      </div>
                      <div className="human-decision">
                        <small>HUMAN DECISION</small>
                        <strong>
                          {text(object(o.human_decision).decision)}
                        </strong>
                        <p>
                          {text(
                            object(o.human_decision).reason ||
                              "A reviewer must record a decision and rationale.",
                          )}
                        </p>
                      </div>
                      <p>
                        <strong>Potential solution:</strong>{" "}
                        {text(o.potential_solution)}
                      </p>
                      <p>
                        <strong>Frequency:</strong> {text(o.frequency)}
                      </p>
                      <p>
                        <strong>Severity:</strong> {text(o.severity)}
                      </p>
                      <p className="caution">{text(o.business_impact)}</p>
                      <div className="evidence-links">
                        {(Array.isArray(o.evidence_ids)
                          ? o.evidence_ids
                          : []
                        ).map((id) => (
                          <button
                            key={String(id)}
                            onClick={() =>
                              setEvidence(
                                data.sources.find((s) => s.id === id) || null,
                              )
                            }
                          >
                            <Link size={12} />
                            {String(id)}
                          </button>
                        ))}
                      </div>
                      <div className="actions">
                        <button
                          onClick={() => {
                            show("Priority decision");
                            setForm({ id: o.id });
                          }}
                        >
                          Review priority
                        </button>
                        <button
                          onClick={() => {
                            setOpportunity(o.id);
                            setScreen("AI feasibility");
                          }}
                        >
                          Compare approaches <ArrowUpRight size={15} />
                        </button>
                        <button
                          disabled={
                            object(o.human_decision).decision !== "confirmed"
                          }
                          title={
                            object(o.human_decision).decision !== "confirmed"
                              ? "Confirm a priority decision first"
                              : ""
                          }
                          onClick={() => {
                            show("Plan experiment");
                            setForm({ id: o.id });
                          }}
                        >
                          Plan experiment
                        </button>
                      </div>
                    </article>
                  ))
                ) : (
                  <section className="panel empty">
                    <GitFork size={36} />
                    <h2>Start with an accepted insight.</h2>
                    <p>
                      Review a signal in Research, then create an opportunity
                      with a stated problem and assumptions.
                    </p>
                    <button onClick={() => setScreen("Research")}>
                      Review evidence <ArrowRight size={15} />
                    </button>
                  </section>
                )}
              </div>
              {data.experiments.length > 0 && (
                <section className="panel">
                  <h2>Planned experiments</h2>
                  {data.experiments.map((e) => (
                    <details key={e.id}>
                      <summary>
                        {text(e.title)} · {text(e.status)}
                      </summary>
                      <p>
                        <strong>Hypothesis:</strong> {text(e.hypothesis)}
                      </p>
                      <p>
                        <strong>Primary metric:</strong>{" "}
                        {text(e.primary_metric)}
                      </p>
                      <p>
                        <strong>Decision rule:</strong> {text(e.decision_rule)}
                      </p>
                      <p>
                        <strong>Variants:</strong>{" "}
                        {Array.isArray(e.variants)
                          ? e.variants.join(" / ")
                          : "Not specified"}
                      </p>
                      <p className="caution">
                        {text(e.sample_limitation)} · No result has been
                        recorded.
                      </p>
                    </details>
                  ))}
                </section>
              )}
            </>
          )}
          {screen === "AI feasibility" && (
            <div className="split">
              <section className="panel">
                <h2>Feasibility canvas</h2>
                <p>
                  Numbers here are constraints you choose, not measured model
                  guarantees.
                </p>
                <label>
                  Opportunity
                  <select
                    value={opportunity}
                    onChange={(e) => setOpportunity(e.target.value)}
                  >
                    <option value="">Select an opportunity</option>
                    {data.opportunities.map((o) => (
                      <option key={o.id} value={o.id}>
                        {text(o.title)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Primary job
                  <select
                    value={form.task_type || "ui"}
                    onChange={(e) => update("task_type", e.target.value)}
                  >
                    {[
                      "ui",
                      "rules",
                      "lookup",
                      "classification",
                      "language",
                      "multimodal",
                    ].map((x) => (
                      <option key={x}>{x}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Available data
                  <select
                    value={form.data || "documents"}
                    onChange={(e) => update("data", e.target.value)}
                  >
                    {["none", "documents", "labeled", "multimodal"].map((x) => (
                      <option key={x}>{x}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Privacy boundary
                  <select
                    value={form.privacy || "local_only"}
                    onChange={(e) => update("privacy", e.target.value)}
                  >
                    <option>local_only</option>
                    <option>approved_remote</option>
                  </select>
                </label>
                {field("Latency budget (ms)", "latency", "1000")}
                <label className="check">
                  <input
                    type="checkbox"
                    checked={form.tool === "yes"}
                    onChange={(e) =>
                      update("tool", e.target.checked ? "yes" : "no")
                    }
                  />{" "}
                  External tools are necessary
                </label>
                <button
                  className="primary"
                  disabled={!opportunity || busy}
                  onClick={() =>
                    void act(async () => {
                      const v = await api("/feasibility", "POST", {
                        opportunity_id: opportunity,
                        task_type: form.task_type || "ui",
                        data_availability: form.data || "documents",
                        privacy: form.privacy || "local_only",
                        latency_budget_ms: Number(form.latency || 1000),
                        tool_required: form.tool === "yes",
                        error_cost: "medium",
                      });
                      setResult(v);
                      return v;
                    }, "Approaches compared")
                  }
                >
                  <Compass size={16} /> Compare approaches
                </button>
              </section>
              <section className="panel">
                <h2>Architecture recommendation</h2>
                <div className="approach-list">
                  {[
                    "No AI",
                    "Rules",
                    "Search",
                    "Traditional ML",
                    "LLM",
                    "RAG",
                    "Agent",
                    "Multimodal",
                  ].map((x) => (
                    <span key={x}>{x}</span>
                  ))}
                </div>
                <FeasibilityResult
                  value={result || data.feasibility.at(-1)}
                  onReview={(id) => {
                    show("Architecture decision");
                    setForm({ id });
                  }}
                />
              </section>
            </div>
          )}
          {screen === "Workflows" && (
            <WorkflowStudio
              data={data}
              refresh={reload}
              sourceIds={selected}
              onEvidence={(id) =>
                setEvidence(data.sources.find((s) => s.id === id) || null)
              }
            />
          )}
          {screen === "Evaluation" && (
            <EvaluationLab data={data} refresh={reload} />
          )}
          {screen === "Analytics" && <AnalyticsPanel data={data} />}
        </div>
      </main>
      {evidence && (
        <div className="scrim" onClick={() => setEvidence(null)}>
          <section
            className="evidence-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Original evidence"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="close"
              aria-label="Close evidence"
              onClick={() => setEvidence(null)}
            >
              <X size={18} />
            </button>
            <div className="eyebrow">RETAINED SOURCE · EXACT CITATION BASIS</div>
            <h2>{text(evidence.participant || evidence.id)}</h2>
            <p>
              {text(evidence.type)} · {text(evidence.segment)}
            </p>
            <span className="tag">
              {evidence.is_demo ? "DEMO / SYNTHETIC" : "Real source"}
            </span>
            <blockquote>{text(evidence.content)}</blockquote>
            <SourcePrivacyReview key={evidence.id} source={evidence} onUpdated={async (source) => { setEvidence(source); await reload(); }} />
            <h3>Provenance</h3>
            <Json value={evidence} />
          </section>
        </div>
      )}
      {dialog && (
        <div className="scrim">
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label={dialog}
          >
            <div className="panel-title">
              <h2>{dialog}</h2>
              <button aria-label="Close dialog" onClick={() => setDialog(null)}>
                <X size={18} />
              </button>
            </div>
            {dialog === "Import evidence" ? (
              <>
                <label className="upload">
                  Choose TXT / MD / CSV / JSON
                  <input
                    type="file"
                    accept=".txt,.md,.csv,.json"
                    onChange={async (e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        if (file.size > 1000000) {
                          setError("Import must be at most 1 MB.");
                          return;
                        }
                        update("filename", file.name);
                        update("content", await file.text());
                      }
                    }}
                  />
                </label>
                {field("Filename", "filename", "feedback.txt")}
                {field("Source / participant", "participant", "Demo source")}
                {field("Segment", "segment", "New players")}
                <label>
                  Source type
                  <select
                    value={form.type || "User Feedback"}
                    onChange={(e) => update("type", e.target.value)}
                  >
                    {[
                      "User Interview",
                      "Survey",
                      "User Feedback",
                      "Support Ticket",
                      "App Review",
                      "Product Document",
                      "Competitor Note",
                      "Behavior/Event Data",
                    ].map((x) => (
                      <option key={x}>{x}</option>
                    ))}
                  </select>
                </label>
                {field(
                  "Content",
                  "content",
                  "Paste source text or choose a file",
                  true,
                )}
                {field("Names or phrases to remove · one per line", "redactions", "Add names, addresses or identifiers the local patterns cannot recognize.", true)}
                <p>Cleanup runs locally. Email, phone and common token patterns are suggestions; names and indirect identifiers need your review. Only the reviewed copy is retained.</p>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={form.real === "yes"}
                    onChange={(e) =>
                      update("real", e.target.checked ? "yes" : "no")
                    }
                  />{" "}
                  This is real research data
                </label>
                {form.real === "yes" && (
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={form.consent === "yes"}
                      onChange={(e) =>
                        update("consent", e.target.checked ? "yes" : "no")
                      }
                    />{" "}
                    Consent to collect and retain this research has been confirmed
                  </label>
                )}
                {privacyPreview && <CleanupPreview preview={privacyPreview} reviewed={cleanupReviewed} onReview={setCleanupReviewed} />}
              </>
            ) : dialog === "Review insight" ? (
              <>
                <p>
                  Record why the evidence does or does not support this
                  interpretation.
                </p>
                {field(
                  "Review note",
                  "note",
                  "Describe support, uncertainty and scope.",
                  true,
                )}
                <label>
                  Confidence
                  <select
                    value={form.confidence || "Low"}
                    onChange={(e) => update("confidence", e.target.value)}
                  >
                    {["Low", "Medium", "High"].map((x) => (
                      <option key={x}>{x}</option>
                    ))}
                  </select>
                </label>
              </>
            ) : dialog === "New opportunity" ? (
              <>
                <label>
                  Accepted insight
                  <select
                    value={form.insight || accepted[0]?.id || ""}
                    onChange={(e) => update("insight", e.target.value)}
                  >
                    {accepted.map((i) => (
                      <option key={i.id} value={i.id}>
                        {text(i.title || i.id)}
                      </option>
                    ))}
                  </select>
                </label>
                {field("Title", "title")}
                {field("Problem to solve", "problem", "", true)}
                {field("Target segment", "segment", "New players")}
                <div className="form-grid">
                  {field("Reach · assumption", "reach", "1")}
                  {field("Impact · assumption", "impact", "1")}
                  {field("Confidence (0–1)", "confidence", "0.5")}
                  {field("Effort", "effort", "1")}
                </div>
                <label>
                  MoSCoW priority
                  <select
                    value={form.moscow || "Could"}
                    onChange={(e) => update("moscow", e.target.value)}
                  >
                    {["Must", "Should", "Could", "Won't"].map((x) => (
                      <option key={x}>{x}</option>
                    ))}
                  </select>
                </label>
                {field(
                  "Frequency · evidence basis",
                  "frequency",
                  "Not measured; qualitative hypothesis",
                )}
                {field(
                  "Severity · task consequence",
                  "severity",
                  "Needs human assessment",
                )}
                {field(
                  "Business impact · hypothesis",
                  "business",
                  "Unknown; no product experiment",
                )}
                {field(
                  "Potential solution",
                  "solution",
                  "Compare clearer UI and rules before AI",
                )}
                <p>
                  RICE inputs are assumptions until supported by research.
                  Effort is person-weeks; ICE uses ease = 1 / effort.
                </p>
              </>
            ) : dialog === "Priority decision" ||
              dialog === "Architecture decision" ? (
              <>
                <label>
                  Human decision
                  <select
                    value={form.decision || "confirmed"}
                    onChange={(e) => update("decision", e.target.value)}
                  >
                    {["confirmed", "deferred", "rejected"].map((x) => (
                      <option key={x}>{x}</option>
                    ))}
                  </select>
                </label>
                {field("Reason", "note", "", true)}
              </>
            ) : dialog === "Plan experiment" ? (
              <>
                {field("Experiment title", "title")}
                {field("Hypothesis", "hypothesis", "", true)}
                {field("Primary metric", "metric")}
                {field("Decision rule and limitations", "rule", "", true)}
                <p>
                  This saves a plan. It does not create experiment outcomes or
                  statistical significance.
                </p>
              </>
            ) : dialog === "Edit workflow" ? (
              <>
                {field("Name", "name")}
                {field("Prompt version", "version", "2")}
                {field(
                  "Nodes (JSON) · order is execution order",
                  "nodes",
                  "",
                  true,
                )}
                <p>
                  Supported: Input, Prompt, Retrieval, LLM, Condition, Tool,
                  MCP, Human Approval, Structured Output. Saving creates a new
                  validated version.
                </p>
              </>
            ) : dialog === "Edit prompt" ? (
              <>
                {field("Prompt ID", "id", "evidence-summary")}
                {field("Goal", "goal")}
                {field(
                  "Template",
                  "template",
                  "Use {{input}} and {{context}}.",
                  true,
                )}
                <p>
                  Saved changes need a new evaluation before you can claim
                  improvement.
                </p>
              </>
            ) : (
              <>
                {field(
                  "Review note",
                  "note",
                  "Check grounding and any risks before approving.",
                  true,
                )}
                <label>
                  Decision
                  <select
                    value={form.decision || "approve"}
                    onChange={(e) => update("decision", e.target.value)}
                  >
                    <option>approve</option>
                    <option>reject</option>
                  </select>
                </label>
                <Json value={run} />
              </>
            )}
            {error && (
              <div className="error" role="alert">
                {error}
              </div>
            )}
            <div className="modal-actions">
              <button onClick={() => setDialog(null)}>Cancel</button>
              <button
                className="primary"
                disabled={busy || (dialog === "Import evidence" && privacyPreview !== null && !cleanupReviewed)}
                onClick={() => void submit()}
              >
                {busy ? "Working…" : dialog === "Import evidence" ? privacyPreview ? "Import reviewed copy" : "Preview local cleanup" : "Save decision"}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
