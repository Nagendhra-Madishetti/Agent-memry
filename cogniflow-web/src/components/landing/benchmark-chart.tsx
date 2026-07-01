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

export type PanelDatum = { panel: string; plain: number; cogniflow: number; n: number };

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
              background: "#1a2147",
              border: `1px solid ${chartColors.grid}`,
              borderRadius: 12,
              color: "#eaf0ff",
              fontSize: 13,
            }}
            formatter={(value, name) =>
              [
                `${value as number}/${n}`,
                (name as string) === "plain" ? "Plain RAG" : "Cogniflow",
              ] as [string, string]
            }
          />
          <Legend
            formatter={(v) => (v === "plain" ? "Plain RAG" : "Cogniflow")}
            wrapperStyle={{ fontSize: 13, color: chartColors.text }}
          />
          <Bar dataKey="plain" radius={[6, 6, 0, 0]} maxBarSize={64} fill={chartColors.plain}>
            <LabelList dataKey="plain" position="top" fill={chartColors.text} fontSize={12} />
          </Bar>
          <Bar dataKey="cogniflow" radius={[6, 6, 0, 0]} maxBarSize={64} fill={chartColors.brand}>
            <LabelList dataKey="cogniflow" position="top" fill={chartColors.brand} fontSize={12} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
