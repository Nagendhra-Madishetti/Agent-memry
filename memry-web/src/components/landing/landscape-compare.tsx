import { Check, Minus, TriangleAlert } from "lucide-react";

type Cell = "yes" | "no" | { warn: string };

// Capability comparison against how temporal-RAG systems typically work (a positioning matrix,
// not a measured run). Agent Memry's column reflects shipped features (as-of, bitemporal replay,
// falsification/supersession, provenance + audit).
const ROWS: { cap: string; field: Cell; cf: Cell }[] = [
  { cap: "Time-aware retrieval", field: "yes", cf: "yes" },
  { cap: "“As of” queries", field: "yes", cf: "yes" },
  { cap: "Timeline reasoning", field: { warn: "some" }, cf: "yes" },
  { cap: "Valid time (when a fact was true)", field: { warn: "some" }, cf: "yes" },
  { cap: "Transaction time (when it was learned)", field: { warn: "rare" }, cf: "yes" },
  { cap: "Belief replay (what was known then)", field: { warn: "rare" }, cf: "yes" },
  { cap: "Falsification tracking", field: "no", cf: "yes" },
  { cap: "Self-correcting memory", field: "no", cf: "yes" },
  { cap: "Provenance & audit", field: { warn: "basic" }, cf: "yes" },
];

function CellView({ c }: { c: Cell }) {
  if (c === "yes") return <span className="inline-flex items-center gap-1.5 font-semibold text-win"><Check className="size-4" /> Yes</span>;
  if (c === "no") return <span className="inline-flex items-center gap-1.5 text-miss"><Minus className="size-4" /> No</span>;
  return <span className="inline-flex items-center gap-1.5 text-warn"><TriangleAlert className="size-4" /> {c.warn}</span>;
}

export function LandscapeCompare() {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card elev">
      <table className="w-full text-left text-sm">
        <thead className="bg-secondary/60 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-5 py-3 font-semibold">Capability</th>
            <th className="px-5 py-3 font-semibold">Temporal RAG (the field)</th>
            <th className="bg-brand/[0.06] px-5 py-3 font-semibold text-brand">Agent Memry</th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map((r) => (
            <tr key={r.cap} className="border-t border-border">
              <td className="px-5 py-4 text-foreground">{r.cap}</td>
              <td className="px-5 py-4"><CellView c={r.field} /></td>
              <td className="bg-brand/[0.05] px-5 py-4"><CellView c={r.cf} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
