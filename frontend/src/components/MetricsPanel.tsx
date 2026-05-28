import { Activity, Gauge, Target } from "lucide-react";

import type { LiveMetrics } from "../types/api";
import Card from "./ui/Card";

function formatMetric(value?: number | null, digits = 3) {
  if (value === null || value === undefined) return "n/a";
  return Number(value).toFixed(digits);
}

export default function MetricsPanel({ metrics }: { metrics?: LiveMetrics | null }) {
  const items = [
    ["command_id", metrics?.command_id ?? "n/a"],
    ["training_run_id", metrics?.training_run_id ?? "n/a"],
    ["current_status", metrics?.current_status ?? "n/a"],
    ["progress_percent", metrics?.progress_percent !== undefined && metrics?.progress_percent !== null ? `${metrics.progress_percent}%` : "n/a"],
    ["epoch", metrics?.epoch ?? "n/a"],
    ["total_epochs", metrics?.total_epochs ?? "n/a"],
    ["mAP50", formatMetric(metrics?.map50)],
    ["precision", formatMetric(metrics?.precision)],
    ["recall", formatMetric(metrics?.recall)],
    ["updated_at", metrics?.updated_at ? new Date(metrics.updated_at).toLocaleTimeString() : "n/a"],
  ];

  return (
    <Card>
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Live Metrics</h2>
          <p className="mt-1 text-sm text-slate-400">Latest PostgreSQL training metrics</p>
        </div>
        <Activity className="h-5 w-5 text-cyan-300" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {items.map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
            <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
            <div className="mt-1 truncate font-mono text-sm text-slate-100">{String(value)}</div>
          </div>
        ))}
      </div>
      {metrics?.message && (
        <div className="mt-4 rounded-lg border border-cyan-400/20 bg-cyan-400/10 p-3 text-sm text-cyan-100">{metrics.message}</div>
      )}
    </Card>
  );
}
