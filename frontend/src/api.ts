export type Row = { id: string; [key: string]: unknown };
export interface Bootstrap {
  sources: Row[];
  insights: Row[];
  opportunities: Row[];
  feasibility: Row[];
  workflows: Row[];
  prompts: Row[];
  evaluations: Row[];
  experiments: Row[];
  runs?: Row[];
  analytics: unknown;
  meta: Record<string, unknown>;
  project: Row;
}
export const text = (value: unknown) =>
  typeof value === "string"
    ? value
    : value == null
      ? "—"
      : JSON.stringify(value);
export const rows = (value: unknown): Row[] =>
  Array.isArray(value) ? value : [];
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const options: RequestInit = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body !== undefined) options.body = JSON.stringify(body);
  const r = await fetch("/api" + path, options);
  if (!r.ok) {
    const error = await r
      .json()
      .catch(() => ({ detail: `Request failed (${r.status})` }));
    throw Error(
      typeof error.detail === "string"
        ? error.detail
        : JSON.stringify(error.detail),
    );
  }
  return r.json();
}
