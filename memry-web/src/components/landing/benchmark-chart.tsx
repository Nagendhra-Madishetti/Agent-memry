"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { chartColors } from "@/lib/site";

export type PanelDatum = { panel: string; plain: number; memry: number; n: number };

export function BenchmarkChart({ data }: { data: PanelDatum[] }) {
  const n = data[0]?.n ?? 4;
  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} barGap={10} margin={{ top: 20, right: 8, left: -18, bottom: 4 }}>
          <CartesianGrid vertical={false} stroke={chartColors.grid} strokeDasharray="3 3" />
          <XAxis
            dataKey="panel"
            tick={{ fill: chartColors.text, fontSize: 13 }}
            axisLine={{ stroke: chartColors.grid }}
            tickLine={false}
          />
          <YAxis
            domain={[0, n]}
            ticks={Array.from({ length: n + 1 }, (_, i) => i)}
            tick={{ fill: chartColors.text, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,0.03)" }}
            contentStyle={{
              background: "#ffffff",
              border: `1px solid ${chartColors.grid}`,
              borderRadius: 12,
              color: "#16181d",
              fontSize: 13,
              boxShadow: "0 12px 32px -18px rgba(16,18,29,0.2)",
            }}
            formatter={(value, name) =>
              [
                `${value as number}/${n}`,
                (name as string) === "plain" ? "Plain RAG" : "Agent Memry",
              ] as [string, string]
            }
          />
          <Legend
            formatter={(v) => (v === "plain" ? "Plain RAG" : "Agent Memry")}
            wrapperStyle={{ fontSize: 13, color: chartColors.text }}
          />
          <Bar dataKey="plain" radius={[6, 6, 0, 0]} maxBarSize={64} fill={chartColors.plain}>
            <LabelList dataKey="plain" position="top" fill={chartColors.text} fontSize={12} />
          </Bar>
          <Bar dataKey="memry" radius={[6, 6, 0, 0]} maxBarSize={64} fill={chartColors.brand}>
            <LabelList dataKey="memry" position="top" fill={chartColors.brand} fontSize={12} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
