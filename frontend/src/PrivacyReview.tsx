import { useState } from "react";
import { api, text, type Row } from "./api";

export interface IntakePreview {
  preview_digest: string;
  sources: Row[];
  changes: { row: number; field: string; kind: string; count: number }[];
  record_count: number;
  limitations: string;
}

export function CleanupPreview({ preview, reviewed, onReview }: {
  preview: IntakePreview; reviewed: boolean; onReview: (value: boolean) => void;
}) {
  return <section className="privacy-preview" aria-label="Cleaned source preview">
    <div className="eyebrow">LOCAL PREVIEW · NOTHING SAVED OR SENT TO AI</div>
    <h3>Review the copy that will be retained</h3>
    <p>{preview.record_count} source(s) · {preview.changes.reduce((n, x) => n + x.count, 0)} suggested redactions</p>
    <div className="privacy-copies">{preview.sources.map((source) => <article key={source.id}>
      <strong>{text(source.participant)} · {text(source.segment)}</strong>
      <blockquote>{text(source.content)}</blockquote>
      <details><summary>Retained provenance</summary><pre>{JSON.stringify(source.metadata, null, 2)}</pre></details>
    </article>)}</div>
    {preview.changes.length > 0 && <details><summary>What was replaced?</summary><ul>{preview.changes.map((change, index) =>
      <li key={index}>Row {change.row}: {change.field} · {change.kind} × {change.count}</li>)}</ul></details>}
    <p>{preview.limitations} Editing any input invalidates this review.</p>
    <label className="check"><input type="checkbox" checked={reviewed} onChange={(e) => onReview(e.target.checked)} />
      I reviewed the cleaned content and remaining identifiers
    </label>
  </section>;
}

export function SourcePrivacyReview({ source, onUpdated }: { source: Row; onUpdated: (source: Row) => Promise<void> }) {
  const [note, setNote] = useState(""), [consent, setConsent] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState("");
  const privacy = (source.privacy_review ?? {}) as Record<string, unknown>;
  const sharing = (source.remote_review ?? {}) as Record<string, unknown>;
  const reviewed = privacy.status === "reviewed";
  async function decide(approved: boolean) {
    setBusy(true); setError("");
    try {
      const updated = await api<Row>(`/sources/${source.id}/remote-review`, "POST", {
        approved, content_sha256: privacy.content_sha256, note, consent_confirmed: consent,
      });
      await onUpdated(updated); setNote(""); setConsent(false);
    } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  }
  return <section className="privacy-preview" aria-label="Source sharing review">
    <div className="eyebrow">PER-SOURCE PERMISSION</div>
    <h3>{sharing.approved ? "Reviewed cloud use approved" : "Local-only research source"}</h3>
    <p>{reviewed ? "You are viewing the cleaned, retained source. Original file bytes were not saved." : "This source has no confirmed cleanup preview. Re-import through local review before approving external research use."}</p>
    {reviewed && <>
      <p>Permission is bound to this exact content. Revocation prevents future requests; it cannot undo an earlier transfer. Server-level remote sharing must also be enabled.</p>
      <label>Sharing review note<textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Record purpose, data scope and why sharing is appropriate." /></label>
      {!sharing.approved && <label className="check"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
        I have authorization to share this cleaned source with the configured model service
      </label>}
      <button disabled={busy || note.trim().length < 10 || (!sharing.approved && !consent)} onClick={() => void decide(!sharing.approved)}>
        {busy ? "Saving review…" : sharing.approved ? "Revoke future cloud use" : "Approve this source for cloud use"}
      </button>
      {sharing.reviewed_at && <p>Last reviewed {text(sharing.reviewed_at)} · {text(sharing.note)}</p>}
    </>}
    {error && <p className="error" role="alert">{error}</p>}
  </section>;
}
