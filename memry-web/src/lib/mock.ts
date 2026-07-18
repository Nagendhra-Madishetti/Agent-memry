// In-browser demo engine: lets the playground run with no backend (browser demo mode).
// It mirrors the temporal as-of behavior on pasted facts + the demo corpus, so a visitor
// experiences the core magic without running the API. Real PDF ingestion needs the backend.
import type { AnswerResponse, ContextResponse, ServedFact } from "./api";

export type MockFact = { id: string; statement: string; valid_from: string; title: string };

const STOP = new Set([
  "the", "is", "in", "of", "a", "an", "was", "were", "where", "when", "what", "did", "does",
  "this", "that", "to", "as", "on", "at", "and", "for", "its", "it", "are", "how",
]);

function toks(s: string): string[] {
  return s.toLowerCase().replace(/[^a-z0-9 ]/g, " ").split(/\s+/).filter((w) => w && !STOP.has(w));
}

function retrieve(facts: MockFact[], query: string, asOf: string | null): ServedFact[] {
  const q = new Set(toks(query));
  let m = facts.filter((f) => toks(f.statement).some((t) => q.has(t)));
  if (m.length === 0) m = facts.slice(); // fall back to everything if no keyword overlap
  const t = asOf ? Date.parse(asOf) : Number.POSITIVE_INFINITY;
  const valid = m.filter((f) => Date.parse(f.valid_from) <= t);
  valid.sort((a, b) => Date.parse(b.valid_from) - Date.parse(a.valid_from));
  return valid.slice(0, 4).map((f, i) => ({
    belief_id: f.id,
    statement: f.statement,
    valid_at: f.valid_from,
    invalid_at: null,
    valid_at_source: "provided",
    valid_at_source_raw: "provided",
    provenance: [f.title],
    superseded_by: null,
    score: 1 - i * 0.1,
  }));
}

export function mockContext(facts: MockFact[], query: string, asOf: string | null): ContextResponse {
  return { query, as_of: asOf, facts: retrieve(facts, query, asOf), notes: [] };
}

export function mockAnswer(facts: MockFact[], query: string, asOf: string | null): AnswerResponse {
  const f = retrieve(facts, query, asOf);
  const when = asOf ? asOf.slice(0, 10) : "now";
  const top = f[0];
  const answer = top
    ? `As of ${when}, ${top.statement.replace(/\.$/, "")}.`
    : "I don't have that in the loaded facts. Paste a fact or load the demo.";
  return {
    answer,
    as_of: asOf,
    generator_model: "in-browser demo",
    confidence: top ? { derived: f.length } : {},
    facts: f,
  };
}
