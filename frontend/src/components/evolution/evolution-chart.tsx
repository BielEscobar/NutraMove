"use client";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { displayDate, number, type Point } from "@/lib/evolution";
export function EvolutionChart({
  points,
  label,
  unit,
}: {
  points: Point[];
  label: string;
  unit: string;
}) {
  if (!points.length)
    return (
      <p className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground">
        Nenhum registro desta série no período selecionado.
      </p>
    );
  return (
    <div className="min-w-0">
      <p className="mb-4 text-sm font-medium">
        {label} ({unit})
      </p>
      <figure
        className="h-64 w-full min-w-0"
        aria-label={`Gráfico de ${label}`}
      >
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <LineChart
            data={points}
            margin={{ top: 10, right: 16, bottom: 5, left: 0 }}
            accessibilityLayer
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={(value) => displayDate(String(value)).slice(0, 5)}
              minTickGap={28}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              width={50}
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => number(Number(value))}
            />
            <Tooltip
              labelFormatter={(label) => displayDate(String(label))}
              formatter={(value) => [number(Number(value)), unit]}
            />
            <Line
              type="linear"
              dataKey="value"
              name={label}
              stroke="#167D5A"
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </figure>
      <details className="mt-4 border-t pt-2">
        <summary className="min-h-11 cursor-pointer py-3 text-sm font-medium">
          Consultar valores em texto
        </summary>
        <ul className="max-h-64 space-y-2 overflow-y-auto text-sm">
          {points.map((point) => (
            <li key={point.assessment_id}>
              {displayDate(point.date)} — {number(point.value)} {unit}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
