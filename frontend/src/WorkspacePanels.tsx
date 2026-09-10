import { useEffect, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  Check,
  ChevronRight,
  GitCompareArrows,
  Play,
  Plus,
  RotateCcw,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-react";
import { api, rows, text, type Bootstrap, type Row } from "./api";

type Obj = Record<string, unknown>;
export const object = (value: unknown): Obj =>
  value && typeof value === "object" && !Array.isArray(value)
    ? (value as Obj)
    : {};
const list = (value: unknown): string[] =>
  Array.isArray(value) ? value.map(String) : [];
const numeric = (value: unknown): number =>
  typeof value === "number" ? value : 0;
const percent = (value: unknown) =>
  typeof value === "number"
    ? `${(value * 100).toFixed(0)}%`
    : "No eligible data";
const activeVersion = (registry: Row | undefined): Obj =>
  rows(registry?.versions).find(
    (v) => v.version === registry?.active_version,
  ) || {};
const pretty = (value: unknown) => JSON.stringify(value, null, 2);

function useAction(refresh: () => Promise<void>) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const act = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await action();
      await refresh();
      setNotice(success);
      return result;
    } catch (e) {
      setError(String(e));
      return undefined;
    } finally {
      setBusy(false);
    }
  };
  return {
    busy,
    act,
    feedback: (
      <>
        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        {notice && (
          <div className="success" role="status">
            <Check size={15} />
            {notice}
          </div>
        )}
      </>
    ),
  };
}

export function FeasibilityResult({
  value,
  onReview,
}: {
  value: unknown;
  onReview: (id: string) => void;
}) {
  const item = object(value);
  if (!item.id)
    return (
      <div className="empty">
        <h3>“No AI” is a valid conclusion.</h3>
        <p>Select a reviewed opportunity and compare the constraints.</p>
      </div>
    );
  return (
    <div className="feasibility-result">
      <div className="recommendation">
        <span className="eyebrow">
          PLANNING RECOMMENDATION · HUMAN REVIEW REQUIRED
        </span>
        <h2>{text(item.recommended_architecture)}</h2>
        {list(item.reasons).map((reason, i) => (
          <p key={i}>{reason}</p>
        ))}
      </div>
      <div className="alternative">
        <strong>Non-AI alternative</strong>
        <p>{text(item.non_ai_alternative)}</p>
        <strong>MVP boundary</strong>
        <p>{text(item.mvp_scope)}</p>
      </div>
      <div className="human-decision">
        <small>HUMAN ARCHITECTURE DECISION</small>
        <strong>
          {text(object(item.human_decision).decision || "pending")}
        </strong>
        <p>
          {text(
            object(item.human_decision).reason ||
              "Inspect the alternatives and record your judgment.",
          )}
        </p>
        <button onClick={() => onReview(text(item.id))}>
          Review architecture
        </button>
      </div>
      <h3>Eight approaches, one decision</h3>
      <div className="architecture-cards">
        {rows(item.options).map((option) => (
          <details
            key={text(option.architecture)}
            className={option.recommended ? "recommended" : ""}
          >
            <summary>
              {text(option.architecture)}
              {option.recommended ? (
                <span className="tag accepted">Recommended</span>
              ) : (
                <span className="tag">Compare</span>
              )}
            </summary>
            <p>{text(option.appropriate_for)}</p>
            <dl className="fact-list">
              {[
                "expected_accuracy",
                "latency",
                "cost",
                "data_availability",
                "context_requirement",
                "personalization",
                "tool_requirement",
                "risk",
                "explainability",
                "privacy",
                "human_review",
                "fallback",
              ].map((key) => (
                <div key={key}>
                  <dt>{key.replaceAll("_", " ")}</dt>
                  <dd>{text(option[key])}</dd>
                </div>
              ))}
            </dl>
          </details>
        ))}
      </div>
      <h3>Known failure modes</h3>
      <ul className="plain-list">
        {list(item.known_failure_modes).map((x) => (
          <li key={x}>{x}</li>
        ))}
      </ul>
    </div>
  );
}

export function WorkflowStudio({
  data,
  refresh,
  sourceIds,
  onEvidence,
}: {
  data: Bootstrap;
  refresh: () => Promise<void>;
  sourceIds: string[];
  onEvidence: (id: string) => void;
}) {
  const { busy, act, feedback } = useAction(refresh);
  const [workflowId, setWorkflowId] = useState("evidence-workflow");
  const registry = data.workflows.find((w) => w.id === workflowId),
    current = activeVersion(registry);
  const [draft, setDraft] = useState<Obj>({}),
    [nodes, setNodes] = useState<Obj[]>([]),
    [selectedNode, setSelectedNode] = useState(0);
  const [input, setInput] = useState(
    "What does the evidence say about resonance?",
  );
  const [run, setRun] = useState<Obj | null>(null),
    [reviewNote, setReviewNote] = useState(""),
    [diff, setDiff] = useState("");
  const [diffKind, setDiffKind] = useState<"workflow" | "prompt">("workflow"),
    [fromVersion, setFromVersion] = useState(1),
    [toVersion, setToVersion] = useState(2);
  const [promptOpen, setPromptOpen] = useState(false),
    [promptDraft, setPromptDraft] = useState<Obj>({}),
    [promptVersion, setPromptVersion] = useState(2);
  const promptRegistry = data.prompts.find(
    (p) => p.id === text(draft.prompt_id || "evidence-summary"),
  );
  const versions = rows(promptRegistry?.versions);
  useEffect(() => {
    setDraft(current);
    setNodes(rows(current.nodes));
    setSelectedNode(0);
  }, [registry?.id, registry?.active_version]);
  useEffect(() => {
    const chosen =
      versions.find((v) => v.version === promptVersion) ||
      activeVersion(promptRegistry);
    setPromptDraft(chosen);
  }, [promptRegistry, promptVersion]);
  const nodeTypes = [
    "Input",
    "Retrieval",
    "Prompt",
    "LLM",
    "Condition",
    "Tool",
    "MCP",
    "Human Approval",
    "Structured Output",
  ];
  const node = nodes[selectedNode],
    config = object(node?.config);
  const setNode = (key: string, value: unknown) =>
    setNodes((all) =>
      all.map((n, i) => (i === selectedNode ? { ...n, [key]: value } : n)),
    );
  const setConfig = (key: string, value: unknown) =>
    setNode("config", { ...config, [key]: value });
  const move = (direction: number) => {
    const target = selectedNode + direction;
    if (target < 0 || target >= nodes.length) return;
    const next = [...nodes];
    [next[selectedNode], next[target]] = [next[target], next[selectedNode]];
    setNodes(next);
    setSelectedNode(target);
  };
  const saveWorkflow = () =>
    void act(
      async () =>
        api(`/workflows/${workflowId}/versions`, "POST", {
          name: draft.name,
          description: draft.description || "",
          nodes,
          prompt_id: draft.prompt_id || "evidence-summary",
          prompt_version: numeric(draft.prompt_version) || 2,
        }),
      "New immutable workflow version saved.",
    );
  const inspectDiff = () =>
    void act(async () => {
      const path =
        diffKind === "workflow"
          ? `/workflows/${workflowId}`
          : `/prompts/${promptRegistry?.id}`;
      const result = await api<{ diff: string }>(
        `${path}/diff?from_version=${fromVersion}&to_version=${toVersion}`,
      );
      setDiff(result.diff);
    }, "Version difference loaded.");
  return (
    <>
      {feedback}
      <div className="workflow-toolbar">
        <select
          aria-label="Workflow"
          value={workflowId}
          onChange={(e) => setWorkflowId(e.target.value)}
        >
          {data.workflows.map((w) => (
            <option key={w.id} value={w.id}>
              {text(w.name)}
            </option>
          ))}
        </select>
        <span className="tag">Saved v{numeric(registry?.active_version)}</span>
        <button onClick={() => setPromptOpen((v) => !v)}>
          <GitCompareArrows size={15} /> Prompt registry
        </button>
        <button
          className="primary"
          disabled={busy || !nodes.length}
          onClick={saveWorkflow}
        >
          <Plus size={15} /> Save workflow version
        </button>
      </div>
      <section className="workflow-canvas">
        <div className="workflow-caption">
          SEQUENTIAL EXECUTION · SELECT A NODE TO EDIT · UNSAVED CHANGES APPLY
          AFTER SAVING
        </div>
        <div className="workflow-nodes">
          {nodes.map((n, i) => (
            <div className="node-wrap" key={text(n.id)}>
              <button
                className={`node ${selectedNode === i ? "selected" : ""}`}
                onClick={() => setSelectedNode(i)}
              >
                <span className="node-number">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <ShieldCheck size={19} />
                <strong>{text(n.label || n.type)}</strong>
                <small>
                  {text(n.type)}
                  {n.type === "MCP" ? " · unavailable" : ""}
                </small>
              </button>
              <ChevronRight size={18} />
            </div>
          ))}
        </div>
      </section>
      <div className="split">
        <section className="panel">
          <h2>Node settings</h2>
          {node ? (
            <>
              <label>
                Node label
                <input
                  value={text(node.label)}
                  onChange={(e) => setNode("label", e.target.value)}
                />
              </label>
              <label>
                Node type
                <select
                  value={text(node.type)}
                  onChange={(e) => {
                    setNode("type", e.target.value);
                  }}
                >
                  {nodeTypes.map((type) => (
                    <option key={type}>{type}</option>
                  ))}
                </select>
              </label>
              {node.type === "Retrieval" && (
                <label>
                  Maximum retrieved sources
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={numeric(config.limit) || 5}
                    onChange={(e) => setConfig("limit", Number(e.target.value))}
                  />
                </label>
              )}
              {node.type === "Condition" && (
                <>
                  <label>
                    Observed field
                    <select
                      value={text(config.field || "context_count")}
                      onChange={(e) => setConfig("field", e.target.value)}
                    >
                      <option>context_count</option>
                      <option>claim_count</option>
                    </select>
                  </label>
                  <div className="form-grid">
                    <label>
                      Operator
                      <select
                        value={text(config.operator || "gt")}
                        onChange={(e) => setConfig("operator", e.target.value)}
                      >
                        {["gt", "gte", "eq", "lt"].map((x) => (
                          <option key={x}>{x}</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Threshold
                      <input
                        type="number"
                        value={numeric(config.value)}
                        onChange={(e) =>
                          setConfig("value", Number(e.target.value))
                        }
                      />
                    </label>
                  </div>
                  <label>
                    When false
                    <select
                      value={text(config.on_false || "abstain")}
                      onChange={(e) => setConfig("on_false", e.target.value)}
                    >
                      <option>abstain</option>
                      <option>error</option>
                    </select>
                  </label>
                </>
              )}
              {node.type === "Tool" && (
                <p className="caution">
                  Only read-only local evidence_search is implemented. No
                  external side effects.
                </p>
              )}
              {node.type === "MCP" && (
                <p className="caution">
                  Design placeholder. Running this node fails explicitly; it
                  does not simulate a connection.
                </p>
              )}
              {node.type === "Human Approval" && (
                <p>
                  Execution pauses durably here. An explicit approval resumes
                  the saved prompt, workflow and evidence snapshot.
                </p>
              )}
              {node.type === "LLM" && (
                <p className="caution">
                  Current server: {text(data.meta.provider)}. In extractive
                  mode, this node performs deterministic extraction with no
                  model call.
                </p>
              )}
              <div className="actions">
                <button
                  aria-label="Move node earlier"
                  disabled={selectedNode === 0}
                  onClick={() => move(-1)}
                >
                  <ArrowUp size={14} /> Earlier
                </button>
                <button
                  aria-label="Move node later"
                  disabled={selectedNode === nodes.length - 1}
                  onClick={() => move(1)}
                >
                  <ArrowDown size={14} /> Later
                </button>
                <button
                  onClick={() => {
                    setNodes((all) => all.filter((_, i) => i !== selectedNode));
                    setSelectedNode(Math.max(0, selectedNode - 1));
                  }}
                >
                  <Trash2 size={14} /> Remove node
                </button>
              </div>
            </>
          ) : (
            <p>No node selected.</p>
          )}
          <label>
            Add a node
            <select
              aria-label="Add node type"
              defaultValue=""
              onChange={(e) => {
                if (!e.target.value) return;
                const type = e.target.value;
                setNodes((all) => [
                  ...all.slice(0, -1),
                  { id: `node-${Date.now()}`, type, label: type, config: {} },
                  ...all.slice(-1),
                ]);
                setSelectedNode(Math.max(0, nodes.length - 1));
                e.target.value = "";
              }}
            >
              <option value="">Choose type…</option>
              {nodeTypes.map((type) => (
                <option key={type}>{type}</option>
              ))}
            </select>
          </label>
        </section>
        <section className="panel">
          <h2>Workflow configuration</h2>
          <label>
            Workflow name
            <input
              value={text(draft.name || "")}
              onChange={(e) =>
                setDraft((d) => ({ ...d, name: e.target.value }))
              }
            />
          </label>
          <label>
            Prompt version pinned to this workflow
            <select
              value={numeric(draft.prompt_version) || 2}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  prompt_version: Number(e.target.value),
                }))
              }
            >
              {versions.map((p) => (
                <option key={numeric(p.version)} value={numeric(p.version)}>
                  v{numeric(p.version)} · {text(p.goal)}
                </option>
              ))}
            </select>
          </label>
          <p>
            Prompt edits do not silently change saved workflows. Choose a
            version, then save a workflow version.
          </p>
          <div className="version-compare">
            <label>
              Compare
              <select
                value={diffKind}
                onChange={(e) =>
                  setDiffKind(e.target.value as "workflow" | "prompt")
                }
              >
                <option value="workflow">Workflow</option>
                <option value="prompt">Prompt</option>
              </select>
            </label>
            <label>
              From
              <input
                type="number"
                min={1}
                value={fromVersion}
                onChange={(e) => setFromVersion(Number(e.target.value))}
              />
            </label>
            <label>
              To
              <input
                type="number"
                min={1}
                value={toVersion}
                onChange={(e) => setToVersion(Number(e.target.value))}
              />
            </label>
            <button disabled={busy} onClick={inspectDiff}>
              Show diff
            </button>
          </div>
          {diff && (
            <pre className="diff" aria-label="Version diff">
              {diff}
            </pre>
          )}
        </section>
      </div>
      {promptOpen && (
        <section className="panel prompt-registry">
          <div className="panel-title">
            <div>
              <h2>Prompt registry</h2>
              <p>
                Changing prose in extractive mode does not tune a model. Compare
                actual versions before claiming improvement.
              </p>
            </div>
            <button
              aria-label="Close prompt registry"
              onClick={() => setPromptOpen(false)}
            >
              <X size={16} />
            </button>
          </div>
          <div className="split">
            <div>
              <label>
                Inspect prompt version
                <select
                  value={promptVersion}
                  onChange={(e) => setPromptVersion(Number(e.target.value))}
                >
                  {versions.map((p) => (
                    <option key={numeric(p.version)} value={numeric(p.version)}>
                      v{numeric(p.version)} · {text(p.goal)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Prompt goal
                <input
                  value={text(promptDraft.goal || "")}
                  onChange={(e) =>
                    setPromptDraft((p) => ({ ...p, goal: e.target.value }))
                  }
                />
              </label>
              <label>
                Output contract
                <select
                  value={text(promptDraft.output_mode || "structured")}
                  onChange={(e) =>
                    setPromptDraft((p) => ({
                      ...p,
                      output_mode: e.target.value,
                    }))
                  }
                >
                  <option>structured</option>
                  <option>text</option>
                </select>
              </label>
              <label>
                Temperature · remote provider only
                <input
                  type="number"
                  min={0}
                  max={2}
                  step={0.1}
                  value={numeric(promptDraft.temperature)}
                  onChange={(e) =>
                    setPromptDraft((p) => ({
                      ...p,
                      temperature: Number(e.target.value),
                    }))
                  }
                />
              </label>
              <p>
                Model is configured on the server. Secrets never enter the
                browser.
              </p>
              <p>
                Evaluation association:{" "}
                {object(promptDraft.evaluation_result).evaluation_id
                  ? text(object(promptDraft.evaluation_result).evaluation_id)
                  : "Not evaluated"}
              </p>
            </div>
            <div>
              <label>
                Prompt template
                <textarea
                  aria-label="Prompt template"
                  rows={10}
                  value={text(promptDraft.template || "")}
                  onChange={(e) =>
                    setPromptDraft((p) => ({ ...p, template: e.target.value }))
                  }
                />
              </label>
              <p>
                Variables: {"{{input}}"} and {"{{context}}"}. Sources remain
                untrusted data.
              </p>
              <div className="actions">
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() =>
                    void act(async () => {
                      const r = await api<Row>(
                        `/prompts/${promptRegistry?.id}/versions`,
                        "POST",
                        {
                          goal: promptDraft.goal,
                          template: promptDraft.template,
                          variables: ["input", "context"],
                          model: promptDraft.model || "deterministic-extractor",
                          temperature: numeric(promptDraft.temperature),
                          output_mode: promptDraft.output_mode,
                        },
                      );
                      setPromptVersion(numeric(r.active_version));
                    }, "Prompt version saved; evaluation is now required.")
                  }
                >
                  <Plus size={14} /> Save prompt version
                </button>
                <button
                  disabled={busy}
                  onClick={() =>
                    void act(async () => {
                      const r = await api<Row>(
                        `/prompts/${promptRegistry?.id}/rollback`,
                        "POST",
                        { version: promptVersion },
                      );
                      setPromptVersion(numeric(r.active_version));
                    }, "Rollback created a new immutable version.")
                  }
                >
                  <RotateCcw size={14} /> Restore this version
                </button>
              </div>
            </div>
          </div>
        </section>
      )}
      <div className="split">
        <section className="panel">
          <h2>Run saved workflow</h2>
          <label>
            Research question
            <textarea
              aria-label="Research question"
              rows={4}
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
          </label>
          <p>
            {sourceIds.length
              ? `${sourceIds.length} selected sources`
              : "All workspace sources"}
            . The latest saved workflow version runs; draft node changes do not.
          </p>
          <button
            className="primary"
            disabled={busy || !input.trim()}
            onClick={() =>
              void act(async () => {
                const r = await api<Obj>(
                  `/workflows/${workflowId}/run`,
                  "POST",
                  {
                    input,
                    ...(sourceIds.length ? { source_ids: sourceIds } : {}),
                  },
                );
                setRun(r);
                setReviewNote("");
              }, "Run recorded. Inspect status before accepting an output.")
            }
          >
            <Play size={16} /> Run workflow
          </button>
          <h3>Recent saved runs</h3>
          {rows(data.runs)
            .slice(0, 6)
            .map((r) => (
              <button
                className="run-history"
                key={r.id}
                onClick={() => {
                  setRun(r);
                  setReviewNote("");
                }}
              >
                <span>{text(r.input).slice(0, 52)}</span>
                <span className={`tag ${text(r.status)}`}>
                  {text(r.status)}
                </span>
              </button>
            ))}
        </section>
        <section className="panel">
          <h2>Execution trace</h2>
          {!run ? (
            <div className="empty">
              <h3>No run selected.</h3>
              <p>
                Run a saved version to inspect evidence and each node's actual
                state.
              </p>
            </div>
          ) : (
            <>
              <div className="run-summary">
                <span className={`tag ${text(run.status)}`}>
                  {text(run.status)}
                </span>
                <span>
                  Workflow v{numeric(run.workflow_version)} · Prompt v
                  {numeric(run.prompt_version)}
                </span>
                <span>{numeric(run.latency_ms).toFixed(2)} ms</span>
              </div>
              <p>{text(run.mode || "No model call was needed.")}</p>
              {run.error != null && (
                <div className="error">{text(run.error)}</div>
              )}
              <ol className="trace-list">
                {rows(run.trace).map((step, i) => (
                  <li key={i}>
                    <span className="trace-dot" />
                    <strong>{text(step.type || step.node_id)}</strong>
                    <span>{text(step.status || "recorded")}</span>
                    {typeof step.passed === "boolean" && (
                      <small>
                        Observed {numeric(step.observed)} ·{" "}
                        {step.passed ? "continue" : "false branch"}
                      </small>
                    )}
                  </li>
                ))}
              </ol>
              <h3>Retrieved evidence</h3>
              <div className="evidence-links">
                {rows(run.retrieved_context).map((s) => (
                  <button key={s.id} onClick={() => onEvidence(s.id)}>
                    {s.id}
                  </button>
                ))}
              </div>
              <Output value={run.output} />
              {run.status === "pending_approval" && (
                <div className="approval-box">
                  <h3>
                    <ShieldCheck size={16} /> Human approval required
                  </h3>
                  <p>
                    Check the original extracts and their limits. Approval does
                    not establish a real product outcome.
                  </p>
                  <label>
                    Approval review note
                    <textarea
                      aria-label="Approval review note"
                      rows={3}
                      value={reviewNote}
                      onChange={(e) => setReviewNote(e.target.value)}
                    />
                  </label>
                  <div className="actions">
                    {[true, false].map((approved) => (
                      <button
                        key={String(approved)}
                        className={approved ? "primary" : ""}
                        disabled={busy || reviewNote.trim().length < 3}
                        onClick={() =>
                          void act(
                            async () => {
                              setRun(
                                await api<Obj>(
                                  `/runs/${run.id}/approval`,
                                  "POST",
                                  { approved, note: reviewNote },
                                ),
                              );
                            },
                            approved
                              ? "Human decision recorded; validation resumed."
                              : "Run rejected; no success recorded.",
                          )
                        }
                      >
                        {approved ? "Approve & continue" : "Reject output"}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <details>
                <summary>Technical trace / token usage</summary>
                <pre>{pretty(run)}</pre>
              </details>
            </>
          )}
        </section>
      </div>
    </>
  );
}

function Output({ value }: { value: unknown }) {
  if (value == null) return <p>No output candidate.</p>;
  if (typeof value === "string")
    return <blockquote className="excerpt">{value}</blockquote>;
  const item = object(value);
  return (
    <div className="output-claims">
      {item.abstained === true && (
        <div className="caution">
          Abstained · Insufficient relevant evidence.
        </div>
      )}
      {rows(item.claims).map((claim, i) => (
        <blockquote className="excerpt" key={i}>
          {text(claim.text)}
          <cite>{text(claim.evidence_id)}</cite>
        </blockquote>
      ))}
    </div>
  );
}

export function EvaluationLab({
  data,
  refresh,
}: {
  data: Bootstrap;
  refresh: () => Promise<void>;
}) {
  const { busy, act, feedback } = useAction(refresh);
  const [reportId, setReportId] = useState(""),
    [caseKey, setCaseKey] = useState(""),
    [failuresOnly, setFailuresOnly] = useState(false);
  const [versionsInput, setVersionsInput] = useState("1,2"),
    [rating, setRating] = useState(3),
    [note, setNote] = useState("");
  const report =
    data.evaluations.find((r) => r.id === reportId) || data.evaluations.at(-1);
  const results = rows(report?.results),
    comparison = rows(report?.comparison);
  const currentCase =
    results.find((r) => `${r.variant}:${r.case_id}` === caseKey) ||
    results.find((r) => !r.task_success) ||
    results[0];
  return (
    <>
      {feedback}
      <section className="panel evaluation-intro">
        <div>
          <span className="eyebrow">
            DEVELOPMENT FIXTURES · ACTUAL EXECUTIONS
          </span>
          <h2>Evidence-grounding regression</h2>
          <p>
            Compare a plain-text baseline, structured contract, retrieval and
            workflow. The deterministic provider tests contracts, not LLM
            reasoning or real user impact.
          </p>
        </div>
        <div>
          <label>
            Prompt versions to compare
            <input
              aria-label="Evaluation prompt versions"
              value={versionsInput}
              onChange={(e) => setVersionsInput(e.target.value)}
            />
          </label>
          <button
            className="primary"
            disabled={busy}
            onClick={() =>
              void act(async () => {
                const versions = versionsInput
                  .split(",")
                  .map((x) => Number(x.trim()));
                const result = await api<Row>("/evaluations/run", "POST", {
                  workflow_id: "evidence-workflow",
                  prompt_versions: versions,
                });
                setReportId(result.id);
                setCaseKey("");
              }, "Comparison executed and saved, including failures.")
            }
          >
            <Play size={16} />
            {busy ? "Running cases…" : "Run comparison"}
          </button>
        </div>
      </section>
      {!report ? (
        <section className="panel empty">
          <h3>No comparison has run yet.</h3>
          <p>
            Start an actual run. This screen does not invent scores while
            waiting.
          </p>
        </section>
      ) : (
        <>
          <section className="panel">
            <div className="panel-title">
              <h2>Variant comparison</h2>
              <select
                aria-label="Evaluation history"
                value={report.id}
                onChange={(e) => {
                  setReportId(e.target.value);
                  setCaseKey("");
                }}
              >
                {data.evaluations.map((r) => (
                  <option key={r.id} value={r.id}>
                    {new Date(text(r.created_at)).toLocaleString()} ·{" "}
                    {text(r.dataset_id)}
                  </option>
                ))}
              </select>
            </div>
            <p className="data-note">{text(report.data_label)}</p>
            <p>
              Dataset: <b>{text(report.dataset_id)}</b> · {results.length}{" "}
              executed cases across variants
            </p>
            <div className="table-wrap">
              <table className="comparison-table">
                <thead>
                  <tr>
                    <th>Variant</th>
                    <th>Task checks</th>
                    <th>Format</th>
                    <th>Grounding</th>
                    <th>Mean ms</th>
                    <th>Human gate</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.map((r) => (
                    <tr key={text(r.variant)}>
                      <td>
                        <strong>{text(r.variant)}</strong>
                        <small>Prompt v{numeric(r.prompt_version)}</small>
                      </td>
                      <td>
                        <b>
                          {numeric(r.passed)} / {numeric(r.cases)}
                        </b>
                      </td>
                      <td>{percent(r.format_validity)}</td>
                      <td>{percent(r.evidence_grounding)}</td>
                      <td>{numeric(r.latency_ms_mean).toFixed(3)}</td>
                      <td>
                        {numeric(r.pending_human_review)
                          ? `${numeric(r.pending_human_review)} pending`
                          : "No approval step"}
                      </td>
                    </tr>
                  ))}
                  {rows(report.skipped).map((r) => (
                    <tr key={text(r.variant)}>
                      <td>{text(r.variant)}</td>
                      <td colSpan={5}>Skipped · {text(r.reason)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              Token usage:{" "}
              {results.some((r) => r.token_usage != null)
                ? "Provider-reported; inspect individual cases"
                : "No model call / unavailable · never estimated"}
              . Human ratings are separate from rule checks.
            </p>
            <details>
              <summary>Dataset hash and limitations</summary>
              <code>{text(report.dataset_sha256)}</code>
              <ul className="plain-list">
                {list(report.limitations).map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </details>
          </section>
          <div className="split evaluation-cases">
            <section className="panel">
              <div className="panel-title">
                <h2>Case explorer</h2>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={failuresOnly}
                    onChange={(e) => setFailuresOnly(e.target.checked)}
                  />{" "}
                  Failed only
                </label>
              </div>
              <div className="case-list">
                {results
                  .filter((r) => !failuresOnly || !r.task_success)
                  .map((r) => (
                    <button
                      key={`${r.variant}:${r.case_id}`}
                      className={`${currentCase === r ? "selected" : ""}`}
                      onClick={() => {
                        setCaseKey(`${r.variant}:${r.case_id}`);
                        setNote("");
                      }}
                    >
                      <span
                        className={`case-state ${r.task_success ? "passed" : "failed"}`}
                      >
                        {r.task_success ? <Check size={13} /> : <X size={13} />}
                      </span>
                      <span>
                        <strong>{text(r.case_id)}</strong>
                        <small>
                          {text(r.variant)} · {text(r.category)}
                        </small>
                      </span>
                      <ChevronRight size={14} />
                    </button>
                  ))}
              </div>
            </section>
            <section className="panel">
              {currentCase && (
                <>
                  <div className="panel-title">
                    <h2>{text(currentCase.case_id)}</h2>
                    <span
                      className={`tag ${currentCase.task_success ? "accepted" : "rejected"}`}
                    >
                      {currentCase.task_success
                        ? "Rules passed"
                        : "Rules failed"}
                    </span>
                  </div>
                  <span className="eyebrow">
                    {text(currentCase.variant)} · {text(currentCase.difficulty)}{" "}
                    · {numeric(currentCase.latency_ms).toFixed(3)} MS
                  </span>
                  <h3>Input</h3>
                  <p>{text(currentCase.input)}</p>
                  <h3>Expected behavior</h3>
                  <p>{text(currentCase.expected_behavior)}</p>
                  <h3>Actual output</h3>
                  <Output value={currentCase.output} />
                  <div className="check-grid">
                    {Object.entries(object(currentCase.checks)).map(
                      ([key, passed]) => (
                        <span
                          key={key}
                          className={passed ? "passed" : "failed"}
                        >
                          {passed ? <Check size={13} /> : <X size={13} />}{" "}
                          {key.replaceAll("_", " ")}
                        </span>
                      ),
                    )}
                  </div>
                  {currentCase.error != null && (
                    <div className="error">{text(currentCase.error)}</div>
                  )}
                  <h3>Human evaluation</h3>
                  <p>
                    {currentCase.human_rating
                      ? `Reviewed: ${text(object(currentCase.human_rating).rating)} / 5 · ${text(object(currentCase.human_rating).note)}`
                      : "Not rated. Programmatic checks do not judge whether this is a useful product insight."}
                  </p>
                  <label>
                    Usefulness rating
                    <select
                      value={rating}
                      onChange={(e) => setRating(Number(e.target.value))}
                    >
                      {[1, 2, 3, 4, 5].map((n) => (
                        <option key={n} value={n}>
                          {n} / 5
                          {n === 1
                            ? " · misleading/unusable"
                            : n === 3
                              ? " · useful with revision"
                              : n === 5
                                ? " · clear, useful, appropriately scoped"
                                : ""}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Human rating rationale
                    <textarea
                      aria-label="Human rating rationale"
                      rows={3}
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                    />
                  </label>
                  <button
                    disabled={busy || note.trim().length < 3}
                    onClick={() =>
                      void act(
                        () =>
                          api(
                            `/evaluations/${report.id}/human-rating`,
                            "PATCH",
                            {
                              case_id: currentCase.case_id,
                              variant: currentCase.variant,
                              rating,
                              note,
                            },
                          ),
                        "Human rating recorded with reviewer and timestamp.",
                      )
                    }
                  >
                    Save human rating
                  </button>
                </>
              )}
            </section>
          </div>
        </>
      )}
    </>
  );
}

export function AnalyticsPanel({ data }: { data: Bootstrap }) {
  const [cohort, setCohort] = useState("demo"),
    [real, setReal] = useState<Obj | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    if (cohort === "real")
      void api<Obj>("/analytics?is_demo=false")
        .then(setReal)
        .catch((e) => setError(String(e)));
  }, [cohort]);
  const analytics = cohort === "demo" ? object(data.analytics) : real || {};
  const acceptance = object(analytics.insight_acceptance),
    success = object(analytics.workflow_success),
    coverage = object(analytics.evidence_coverage),
    activation = object(analytics.activation);
  return (
    <>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      <section className="metric-tree">
        <div>
          <small>NORTH STAR · REAL STUDY OUTCOMES REQUIRED</small>
          <h2>Weekly validated product decisions</h2>
          <p>
            Real evidence + actual study or evaluation outcome + an explicit
            human build / revise / stop decision. A planned experiment does not
            qualify.
          </p>
          <span className="tag">PENDING REAL USER RESEARCH</span>
        </div>
        <strong className="northstar-value">
          0<small>validated outcomes</small>
        </strong>
      </section>
      <section className="panel">
        <div className="panel-title">
          <div>
            <h2>Workspace activity</h2>
            <p>{text(analytics.data_label || "Loading selected cohort…")}</p>
          </div>
          <label className="cohort-label">
            Cohort
            <select
              aria-label="Cohort"
              value={cohort}
              onChange={(e) => setCohort(e.target.value)}
            >
              <option value="demo">DEMO / synthetic</option>
              <option value="real">Real-data activity</option>
            </select>
          </label>
        </div>
        <div className="stats analytics-stats">
          <article>
            <span>DAU / WAU</span>
            <strong>
              {numeric(analytics.dau)} / {numeric(analytics.wau)}
            </strong>
            <p>Distinct local identities · UTC</p>
          </article>
          <article>
            <span>Insight acceptance</span>
            <strong>{percent(acceptance.rate)}</strong>
            <p>
              {numeric(acceptance.accepted)} accepted /{" "}
              {numeric(acceptance.accepted) + numeric(acceptance.rejected)}{" "}
              reviewed
            </p>
          </article>
          <article>
            <span>Workflow success</span>
            <strong>{percent(success.rate)}</strong>
            <p>
              {numeric(success.successful)} / {numeric(success.terminal)}{" "}
              terminal · {numeric(success.pending_approval)} awaiting review
            </p>
          </article>
        </div>
        <h3>Ordered decision funnel</h3>
        <p>{text(analytics.funnel_unit)}</p>
        <div className="funnel">
          {rows(analytics.funnel).map((stage, i) => (
            <div key={text(stage.event)}>
              <small>0{i + 1}</small>
              <strong>{text(stage.event).replaceAll("_", " ")}</strong>
              <b>{numeric(stage.projects)}</b>
              {i < 4 && <ChevronRight size={16} />}
            </div>
          ))}
        </div>
        <div className="metric-details">
          <div>
            <strong>{percent(coverage.rate)}</strong>
            <span>Evidence coverage · source links, not semantic truth</span>
          </div>
          <div>
            <strong>{percent(activation.rate)}</strong>
            <span>
              7-day activation · {numeric(activation.denominator)} matured
              projects
            </span>
          </div>
          <div>
            <strong>Not measured</strong>
            <span>Week-4 retention · no matured real cohort</span>
          </div>
        </div>
      </section>
      <div className="split">
        <section className="panel">
          <h2>Feature adoption</h2>
          <p>Distinct projects in the selected cohort, not feature clicks.</p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Feature event</th>
                  <th>Projects</th>
                  <th>Rate</th>
                </tr>
              </thead>
              <tbody>
                {rows(analytics.feature_adoption).map((row) => (
                  <tr key={text(row.feature)}>
                    <td>{text(row.feature)}</td>
                    <td>{numeric(row.projects)}</td>
                    <td>{percent(row.rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <section className="panel">
          <h2>Event ledger</h2>
          <p>
            {numeric(analytics.event_count)} actual local events · UTC
            timestamps
          </p>
          <div className="event-ledger">
            {rows(analytics.recent_events).length ? (
              rows(analytics.recent_events).map((event) => (
                <div key={event.id}>
                  <span className="trace-dot" />
                  <div>
                    <strong>{text(event.name)}</strong>
                    <small>{text(event.timestamp)}</small>
                  </div>
                  <span className="tag">
                    {event.is_demo ? "Demo" : "Local real data"}
                  </span>
                </div>
              ))
            ) : (
              <div className="empty">
                <h3>No events in this cohort.</h3>
                <p>
                  Do not substitute synthetic events for real user behavior.
                </p>
              </div>
            )}
          </div>
        </section>
      </div>
    </>
  );
}
