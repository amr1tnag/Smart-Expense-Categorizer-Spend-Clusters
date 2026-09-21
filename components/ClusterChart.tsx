"use client";

import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TransactionRow } from "@/lib/types";
import { INK, colorForIndex } from "@/lib/palette";

function fmt(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

export default function ClusterChart({
  rows,
  clusterOrder,
}: {
  rows: TransactionRow[];
  clusterOrder: string[];
}) {
  const series = clusterOrder.map((label, i) => ({
    label,
    color: colorForIndex(i),
    points: rows
      .filter((r) => r.cluster_label === label)
      .map((r) => ({
        x: new Date(r.date).getTime(),
        y: r.abs_amount,
        description: r.description,
        category: r.category,
        date: r.date,
      })),
  }));

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-x-4 gap-y-1.5">
        {clusterOrder.map((label, i) => (
          <div key={label} className="flex items-center gap-1.5 text-xs">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ background: colorForIndex(i) }}
            />
            <span style={{ color: INK.secondary }}>{label}</span>
          </div>
        ))}
      </div>
      <div className="h-[340px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
            <CartesianGrid stroke={INK.gridline} />
            <XAxis
              type="number"
              dataKey="x"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(t) =>
                new Date(t).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                })
              }
              stroke={INK.baseline}
              tick={{ fill: INK.muted, fontSize: 12 }}
              tickLine={false}
            />
            <YAxis
              type="number"
              dataKey="y"
              scale="log"
              domain={["auto", "auto"]}
              tickFormatter={fmt}
              stroke={INK.baseline}
              tick={{ fill: INK.muted, fontSize: 12 }}
              tickLine={false}
              width={64}
            />
            <Tooltip
              cursor={{ stroke: INK.baseline }}
              contentStyle={{
                background: "#1a1a19",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                color: INK.primary,
                fontSize: 13,
              }}
              labelStyle={{ color: INK.secondary }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const p = payload[0].payload as {
                  description: string;
                  category: string;
                  date: string;
                  y: number;
                };
                return (
                  <div
                    style={{
                      background: "#1a1a19",
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: 8,
                      padding: "8px 10px",
                      fontSize: 12,
                      color: INK.primary,
                      maxWidth: 220,
                    }}
                  >
                    <div style={{ color: INK.secondary }}>{p.date}</div>
                    <div style={{ margin: "2px 0" }}>{p.description}</div>
                    <div style={{ color: INK.muted }}>
                      {p.category} · {fmt(p.y)}
                    </div>
                  </div>
                );
              }}
            />
            {series.map((s) => (
              <Scatter
                key={s.label}
                name={s.label}
                data={s.points}
                fill={s.color}
                fillOpacity={0.75}
                r={4}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
