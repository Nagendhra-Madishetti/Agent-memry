"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Clock,
  Database,
  FileText,
  Loader2,
  RotateCcw,
  Sparkles,
  Upload,
} from "lucide-react";
import { toast } from "sonner";
import {
  api,
  confidenceBadgeClass,
  type AnswerResponse,
  type ContextResponse,
  type Health,
  type ServedFact,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";

type Doc = { name: string; created: number; superseded: number };
const fmt = (d: string | null) => (d ? d.slice(0, 10) : "—");

const DEMO = [
  { t: "acme_report_2011", d: "Acme Robotics is headquartered in Calderport.", when: "2011-01-01" },
  { t: "acme_report_2020", d: "Acme Robotics is headquartered in Newhaven.", when: "2020-01-01" },
  { t: "acme_ceo_2014", d: "The CEO of Acme Robotics is Dana Voss.", when: "2014-01-01" },
  { t: "acme_ceo_2021", d: "The CEO of Acme Robotics is Marcus Lund.", when: "2021-01-01" },
];

export default function Playground() {
  const [sid, setSid] = useState<string | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [healthErr, setHealthErr] = useState(false);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  const [query, setQuery] = useState("Where is Acme Robotics headquartered?");
  const [useAsOf, setUseAsOf] = useState(true);
  const [asOf, setAsOf] = useState("2015-01-01");
  const [answer, setAnswer] = useState<AnswerResponse | null>(null);
  const [facts, setFacts] = useState<ServedFact[]>([]);

  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [docDate, setDocDate] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    (async () => {
      try {
        setHealth(await api.health());
      } catch {
        setHealthErr(true);
      }
      try {
        const stored = localStorage.getItem("cf_session");
        const s = stored || (await api.newSession());
        localStorage.setItem("cf_session", s);
        setSid(s);
      } catch {
        setHealthErr(true);
      }
    })();
  }, []);

  const asOfValue = useAsOf ? new Date(asOf).toISOString() : null;
  const down = healthErr || (health && !health.falkordb);

  const loadDemo = useCallback(async () => {
    if (!sid) return;
    setBusy("demo");
    try {
      const added: Doc[] = [];
      for (const x of DEMO) {
        const r = await api.ingestText(sid, x.d, x.t, x.when);
        added.push({ name: x.t, created: r.facts_created, superseded: r.facts_superseded });
      }
      setDocs((d) => [...added, ...d]);
      toast.success("Demo corpus loaded — try the as-of date on 2013 vs now.");
    } catch (e) {
      toast.error(`Ingest failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  }, [sid]);

  const onFile = useCallback(
    async (f: File) => {
      if (!sid) return;
      setBusy("upload");
      try {
        const r = await api.ingestFile(sid, f, docDate ? new Date(docDate).toISOString() : undefined);
        setDocs((d) => [{ name: r.document, created: r.facts_created, superseded: r.facts_superseded }, ...d]);
        toast.success(`${r.document}: ${r.facts_created} facts from ${r.chunks} chunks`);
      } catch (e) {
        toast.error(`Upload failed: ${(e as Error).message}`);
      } finally {
        setBusy(null);
      }
    },
    [sid, docDate],
  );

  const addText = useCallback(async () => {
    if (!sid || !text.trim()) return;
    setBusy("text");
    try {
      const r = await api.ingestText(sid, text, title || "note", docDate ? new Date(docDate).toISOString() : undefined);
      setDocs((d) => [{ name: r.document, created: r.facts_created, superseded: r.facts_superseded }, ...d]);
      setText("");
      setTitle("");
      toast.success(`Added ${r.facts_created} fact(s)`);
    } catch (e) {
      toast.error(`Ingest failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  }, [sid, text, title, docDate]);

  const ask = useCallback(
    async (mode: "answer" | "context") => {
      if (!sid || !query.trim()) return;
      setBusy(mode);
      setAnswer(null);
      try {
        if (mode === "answer") {
          const r = await api.answer(sid, query, asOfValue);
          setAnswer(r);
          setFacts(r.facts);
        } else {
          const r: ContextResponse = await api.context(sid, query, asOfValue);
          setFacts(r.facts);
        }
      } catch (e) {
        toast.error(`${mode} failed: ${(e as Error).message}`);
      } finally {
        setBusy(null);
      }
    },
    [sid, query, asOfValue],
  );

  const reset = useCallback(async () => {
    if (!sid) return;
    await api.reset(sid).catch(() => {});
    setDocs([]);
    setFacts([]);
    setAnswer(null);
    toast.success("Session reset");
  }, [sid]);

  return (
    <div className="mx-auto max-w-6xl px-5 py-12">
      <p className="eyebrow mb-3">Playground</p>
      <h1 className="text-hero mb-3 !text-[clamp(2rem,4vw,3rem)]">Upload real docs. Ask &ldquo;as of when?&rdquo;</h1>
      <p className="text-subhead mb-8 max-w-[62ch]">
        Drop in your own documents (or paste text) with the date each was true. Then ask a
        question and move the <b>as-of</b> date &mdash; watch the answer change with time, cited
        and confidence-labeled. Real ingestion, real temporal store.
      </p>

      {down && (
        <div className="mb-8 flex items-start gap-3 rounded-xl border border-warn/40 bg-warn/10 p-4 text-sm">
          <AlertTriangle className="mt-0.5 size-5 shrink-0 text-warn" />
          <div>
            <div className="font-semibold text-foreground">Backend not reachable</div>
            <p className="mt-1 text-muted-foreground">
              Start FalkorDB and the API, then reload:{" "}
              <code className="rounded bg-secondary px-1.5 py-0.5">python cogniflow-api/main.py</code>{" "}
              (needs a running FalkorDB on :6379 and your <code>.env</code>).
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,380px)_1fr]">
        {/* CORPUS */}
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-5 elev">
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
              <Database className="size-4 text-brand" /> Corpus
            </div>

            <label className="mb-3 block cursor-pointer rounded-lg border border-dashed border-border bg-secondary/40 p-5 text-center transition-colors hover:border-brand/50 hover:bg-secondary">
              <Upload className="mx-auto mb-2 size-5 text-muted-foreground" />
              <div className="text-sm font-medium">Upload a document</div>
              <div className="text-xs text-muted-foreground">PDF, markdown, or text</div>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.md,.markdown,.txt,text/*"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
              />
            </label>

            <div className="mb-2 text-xs text-muted-foreground">Or paste a fact / snippet</div>
            <Input
              placeholder="title (e.g. policy_2020)"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mb-2"
            />
            <Textarea
              placeholder="e.g. Acme Robotics is headquartered in Newhaven."
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={3}
              className="mb-2"
            />
            <div className="mb-2 flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Valid from</span>
              <Input
                type="date"
                value={docDate}
                onChange={(e) => setDocDate(e.target.value)}
                className="h-8 w-auto"
              />
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={addText} disabled={!!busy || !text.trim()}>
                {busy === "text" ? <Loader2 className="size-4 animate-spin" /> : "Add fact"}
              </Button>
              <Button size="sm" variant="outline" onClick={loadDemo} disabled={!!busy}>
                {busy === "demo" ? <Loader2 className="size-4 animate-spin" /> : "Load demo"}
              </Button>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-5 elev">
            <div className="mb-3 flex items-center justify-between text-sm font-semibold">
              <span>Ingested ({docs.length})</span>
              {docs.length > 0 && (
                <button onClick={reset} className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-danger">
                  <RotateCcw className="size-3.5" /> reset
                </button>
              )}
            </div>
            {docs.length === 0 ? (
              <p className="text-xs text-muted-foreground">Nothing yet. Upload a doc or load the demo.</p>
            ) : (
              <ul className="space-y-2">
                {docs.map((d, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm">
                    <FileText className="size-4 shrink-0 text-muted-foreground" />
                    <span className="truncate">{d.name}</span>
                    <span className="ml-auto shrink-0 text-xs text-muted-foreground">
                      +{d.created}
                      {d.superseded > 0 && <span className="text-warn"> · {d.superseded} superseded</span>}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* ASK */}
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-5 elev">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question about your docs…"
              className="mb-3 h-11 text-[15px]"
            />
            <div className="flex flex-wrap items-center gap-3">
              <div className="inline-flex overflow-hidden rounded-lg border border-border">
                <button
                  onClick={() => setUseAsOf(false)}
                  className={`px-3 py-1.5 text-sm ${!useAsOf ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent"}`}
                >
                  Now
                </button>
                <button
                  onClick={() => setUseAsOf(true)}
                  className={`px-3 py-1.5 text-sm ${useAsOf ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent"}`}
                >
                  As of
                </button>
              </div>
              {useAsOf && (
                <Input
                  type="date"
                  value={asOf}
                  onChange={(e) => setAsOf(e.target.value)}
                  className="h-9 w-auto"
                />
              )}
              <div className="ml-auto flex gap-2">
                <Button variant="outline" onClick={() => ask("context")} disabled={!!busy}>
                  {busy === "context" ? <Loader2 className="size-4 animate-spin" /> : "Context"}
                </Button>
                <Button onClick={() => ask("answer")} disabled={!!busy}>
                  {busy === "answer" ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <>
                      <Sparkles className="size-4" /> Answer
                    </>
                  )}
                </Button>
              </div>
            </div>
            <p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
              <Clock className="size-3.5 text-brand" />
              {useAsOf ? `Answering as of ${asOf} — the truth at that moment.` : "Answering as of now."}
            </p>
          </div>

          {answer && (
            <div className="ring-glow rounded-xl border border-border bg-card p-5">
              <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
                <Sparkles className="size-3.5 text-brand" /> Cited answer
                {answer.generator_model && <span>· {answer.generator_model}</span>}
              </div>
              <p className="text-[15px] leading-relaxed">{answer.answer}</p>
              {Object.keys(answer.confidence).length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {Object.entries(answer.confidence).map(([k, v]) => (
                    <Badge key={k} variant="outline" className={confidenceBadgeClass(k)}>
                      {k} ×{v}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="rounded-xl border border-border bg-card p-5 elev">
            <div className="mb-3 text-sm font-semibold">
              {answer ? "Facts it stood on" : "Retrieved context"} ({facts.length})
            </div>
            {facts.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Ask a question to see the temporally-correct facts (and their provenance).
              </p>
            ) : (
              <ul className="space-y-3">
                {facts.map((f) => (
                  <FactCard key={f.belief_id} f={f} />
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function FactCard({ f }: { f: ServedFact }) {
  return (
    <li className="rounded-lg border border-border p-3">
      <div className={`text-sm ${f.invalid_at ? "text-muted-foreground line-through" : "text-foreground"}`}>
        {f.statement}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <Badge variant="outline" className={confidenceBadgeClass(f.valid_at_source)}>
          {f.valid_at_source}
        </Badge>
        <span>
          valid {fmt(f.valid_at)} → {f.invalid_at ? fmt(f.invalid_at) : "present"}
        </span>
        {f.provenance.length > 0 && <span>· source: {f.provenance.join(", ")}</span>}
      </div>
    </li>
  );
}
