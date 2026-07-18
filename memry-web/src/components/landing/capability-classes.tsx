import { Check, Minus, TriangleAlert } from "lucide-react";

type Cell = "yes" | "no" | { warn: string } | { partial: string };

const ROWS: { q: string; plain: Cell; temporal: Cell; bi: Cell }[] = [
  { q: "Where is Acme headquartered?", plain: "yes", temporal: "yes", bi: "yes" },
  { q: "Where was Acme headquartered in 2020?", plain: "no", temporal: "yes", bi: "yes" },
  { q: "What did the system know in 2020?", plain: "no", temporal: { warn: "sometimes" }, bi: "yes" },
  { q: "When did this fact change?", plain: "no", temporal: { warn: "limited" }, bi: "yes" },
  { q: "Replay a belief that was corrected later", plain: "no", temporal: { partial: "rarely" }, bi: "yes" },
];

function CellView({ c }: { c: Cell }) {
  if (c === "yes") {
    return (
      <span className="inline-flex items-center gap-1.5 font-semibold text-win">
        <Check className="size-4" /> Yes
      </span>
    );
  }
  if (c === "no") {
    return (
      <span className="inline-flex items-center gap-1.5 text-miss">
        <Minus className="size-4" /> No
      </span>
    );
  }
  const label = "warn" in c ? c.warn : c.partial;
  return (
    <span className="inline-flex items-center gap-1.5 text-warn">
      <TriangleAlert className="size-4" /> {label}
    </span>
  );
}

export function CapabilityClasses() {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card elev">
      <table className="w-full text-left text-sm">
        <thead className="bg-secondary/60 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-5 py-3 font-semibold">Question</th>
            <th className="px-5 py-3 font-semibold">Plain RAG</th>
            <th className="px-5 py-3 font-semibold">Temporal RAG</th>
            <th className="bg-brand/[0.06] px-5 py-3 font-semibold text-brand">
              Bitemporal RAG
              <span className="ml-1.5 rounded-full border border-brand/30 bg-brand/10 px-1.5 py-0.5 text-[10px] normal-case tracking-normal">Agent Memry</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map((r) => (
            <tr key={r.q} className="border-t border-border">
              <td className="px-5 py-4 text-foreground">{r.q}</td>
              <td className="px-5 py-4"><CellView c={r.plain} /></td>
              <td className="px-5 py-4"><CellView c={r.temporal} /></td>
              <td className="bg-brand/[0.05] px-5 py-4"><CellView c={r.bi} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
