// Client for the Cogniflow Playground API (cogniflow-api/main.py).
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ServedFact = {
  belief_id: string;
  statement: string;
  valid_at: string | null;
  invalid_at: string | null;
  valid_at_source: string;
  valid_at_source_raw: string | null;
  provenance: string[];
  superseded_by: string | null;
  score: number | null;
};

export type ContextResponse = {
  query: string;
  as_of: string | null;
  facts: ServedFact[];
  notes: string[];
};

export type AnswerResponse = {
  answer: string;
  as_of: string | null;
  generator_model: string | null;
  confidence: Record<string, number>;
  facts: ServedFact[];
};

export type Health = {
  status: string;
  falkordb: boolean;
  llm: boolean;
  embedder: string;
};

async function jpost<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error((await r.text()) || `${r.status}`);
  return r.json();
}

async function jget<T>(path: string): Promise<T> {
  const r = await fetch(`${API_URL}${path}`);
  if (!r.ok) throw new Error((await r.text()) || `${r.status}`);
  return r.json();
}

export const api = {
  health: () => jget<Health>("/api/health"),
  plugins: () =>
    jget<{ embedders: string[]; rerankers: string[]; generators: string[]; backends: string[]; defaults: Record<string, string> }>(
      "/api/plugins",
    ),
  newSession: () => jpost<{ session_id: string }>("/api/session", {}).then((r) => r.session_id),
  setConfig: (session_id: string, cfg: { embedder?: string; reranker?: string }) =>
    jpost<{ ok: boolean }>("/api/config", { session_id, ...cfg }),
  ingestText: (session_id: string, text: string, title: string, reference_time?: string) =>
    jpost<{ document: string; facts_created: number; facts_superseded: number }>("/api/ingest-text", {
      session_id,
      text,
      title,
      reference_time,
    }),
  ingestFile: async (session_id: string, file: File, reference_time?: string) => {
    const fd = new FormData();
    fd.append("session_id", session_id);
    fd.append("file", file);
    if (reference_time) fd.append("reference_time", reference_time);
    const r = await fetch(`${API_URL}/api/ingest`, { method: "POST", body: fd });
    if (!r.ok) throw new Error((await r.text()) || `${r.status}`);
    return r.json() as Promise<{
      document: string;
      chunks: number;
      facts_created: number;
      facts_superseded: number;
    }>;
  },
  context: (session_id: string, query: string, as_of: string | null, top_k = 6) =>
    jpost<ContextResponse>("/api/context", { session_id, query, as_of, top_k }),
  answer: (session_id: string, query: string, as_of: string | null, top_k = 6) =>
    jpost<AnswerResponse>("/api/answer", { session_id, query, as_of, top_k }),
  reset: (session_id: string) => jpost<{ ok: boolean }>(`/api/reset?session_id=${session_id}`, {}),
};

export function confidenceBadgeClass(src: string): string {
  if (src === "authoritative") return "bg-win/12 text-win border-win/30";
  if (src === "derived") return "bg-warn/12 text-warn border-warn/30";
  return "bg-muted text-muted-foreground border-border";
}
