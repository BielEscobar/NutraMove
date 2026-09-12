"use client";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { displayDate } from "@/lib/evolution";
import { type HydrationHistory, volume } from "@/lib/hydration";

export function HydrationChart({ data }: { data: HydrationHistory }) {
  return (
    <div className="min-w-0">
      <figure
        aria-label="Consumo diário de água em mililitros"
        className="h-64 w-full min-w-0"
      >
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <BarChart
            data={data.items}
            accessibilityLayer
            margin={{ top: 10, right: 10, bottom: 5, left: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={(value) => displayDate(String(value)).slice(0, 5)}
              minTickGap={28}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              width={55}
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => volume(Number(value))}
            />
            <Tooltip
              labelFormatter={(label) => displayDate(String(label))}
              formatter={(value) => [volume(Number(value)), "Consumo"]}
            />
            <Bar
              dataKey="consumed_ml"
              name="Consumo"
              fill="#176B78"
              radius={[4, 4, 0, 0]}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </figure>
      <details className="mt-4 border-t pt-2">
        <summary className="min-h-11 cursor-pointer py-3 text-sm font-medium">
          Consultar valores em texto
        </summary>
        <ul className="max-h-64 space-y-2 overflow-y-auto text-sm">
          {data.items.map((item) => (
            <li key={item.date}>
              {displayDate(item.date)} — {volume(item.consumed_ml)}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
