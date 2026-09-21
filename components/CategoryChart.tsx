"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CategoryTotal } from "@/lib/types";
import { INK, SEQUENTIAL_BLUE } from "@/lib/palette";

function fmt(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

export default function CategoryChart({ data }: { data: CategoryTotal[] }) {
  return (
    <div className="h-[280px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 24, bottom: 4, left: 8 }}
          barCategoryGap={10}
        >
          <CartesianGrid
            horizontal={false}
            stroke={INK.gridline}
            strokeDasharray="0"
          />
          <XAxis
            type="number"
            tickFormatter={fmt}
            stroke={INK.baseline}
            tick={{ fill: INK.muted, fontSize: 12 }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="category"
            stroke={INK.baseline}
            tick={{ fill: INK.secondary, fontSize: 13 }}
            tickLine={false}
            width={100}
          />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
            contentStyle={{
              background: "#1a1a19",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 8,
              color: INK.primary,
              fontSize: 13,
            }}
            formatter={(value: number) => [fmt(value), "Total spend"]}
            labelStyle={{ color: INK.secondary }}
          />
          <Bar dataKey="total" radius={[0, 4, 4, 0]} maxBarSize={22}>
            {data.map((entry) => (
              <Cell key={entry.category} fill={SEQUENTIAL_BLUE} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
