import { useEffect, useState } from "react";
import { useSettings } from "../../context/SettingsContext";

export interface ChartColors {
  series1: string;
  series2: string;
  grid: string;
  axis: string;
  heat: string[];
  surface: string;
  ink: string;
}

function read(): ChartColors {
  const cs = getComputedStyle(document.documentElement);
  const v = (name: string) => cs.getPropertyValue(name).trim();
  return {
    series1: v("--chart-1"),
    series2: v("--chart-2"),
    grid: v("--chart-grid"),
    axis: v("--chart-axis"),
    heat: ["--heat-0", "--heat-1", "--heat-2", "--heat-3", "--heat-4"].map(v),
    surface: `rgb(${v("--surface")})`,
    ink: `rgb(${v("--ink")})`,
  };
}

/** Recharts writes SVG attributes (which can't resolve CSS variables), so resolve them here. */
export function useChartColors(): ChartColors {
  const { settings } = useSettings();
  const [colors, setColors] = useState<ChartColors>(read);
  useEffect(() => {
    const id = requestAnimationFrame(() => setColors(read()));
    return () => cancelAnimationFrame(id);
  }, [settings.theme]);
  return colors;
}

export function ChartTooltip({ active, payload, label, format }: {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string;
  format?: (v: number) => string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-2 text-xs shadow-card">
      {label && <div className="mb-1 font-medium text-ink">{label}</div>}
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2 text-ink2">
          <span className="h-2 w-2 rounded-sm" style={{ background: p.color }} />
          <span>{p.name}</span>
          <span className="ml-auto pl-3 font-semibold tabular-nums text-ink">{format ? format(p.value) : p.value}</span>
        </div>
      ))}
    </div>
  );
}

export const axisProps = (c: ChartColors) => ({
  stroke: c.axis,
  tick: { fill: c.axis, fontSize: 11 },
  tickLine: false,
  axisLine: { stroke: c.grid },
});
