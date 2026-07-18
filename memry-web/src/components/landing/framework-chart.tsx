"use client";

import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { chartColors } from "@/lib/site";

export type SysDatum = { name: string; score: number; n: number };

function colorFor(name: string): string {
  if (name.startsWith("Agent Memry")) return chartColors.brand; // orange
  if (name.startsWith("Temporal") || name.startsWith("Graphiti")) return chartColors.brand2; // amber (temporal, no as-of)
  return chartColors.plain; // gray - general RAG systems
}

export function FrameworkChart({ data, n }: { data: SysDatum[]; n: number }) {
  return (
    <div style={{ height: data.length * 46 + 24 }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart layout="vertical" data={data} margin={{ top: 4, right: 30, left: 8, bottom: 4 }}>
          <XAxis
            type="number"
            domain={[0, n]}
            ticks={Array.from({ length: n + 1 }, (_, i) => i)}
            tick={{ fill: chartColors.text, fontSize: 12 }}
            axisLine={{ stroke: chartColors.grid }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={168}
            tick={{ fill: "#16181d", fontSize: 12.5 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(16,18,29,0.04)" }}
            contentStyle={{
              background: "#ffffff",
              border: `1px solid ${chartColors.grid}`,
              borderRadius: 12,
              color: "#16181d",
              fontSize: 13,
              boxShadow: "0 12px 32px -18px rgba(16,18,29,0.2)",
            }}
            formatter={(v) => [`${v as number}/${n}`, "score"] as [string, string]}
          />
          <Bar dataKey="score" radius={[0, 6, 6, 0]} barSize={22}>
            {data.map((d, i) => (
              <Cell key={i} fill={colorFor(d.name)} />
            ))}
            <LabelList dataKey="score" position="right" fill={chartColors.text} fontSize={12} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
