import { Activity, BarChart3 } from "lucide-react";
import type { ReactNode } from "react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatDateTime, formatMetric, formatPercent } from "../../utils/format";
import type { LiveMetrics } from "../../types/api";
import { Card } from "../ui/card";
import { StatusPill } from "../ui/status-pill";

type MetricsPanelProps = {
  metrics?: LiveMetrics | null;
  progress: number;
};

export function MetricsPanel({ metrics, progress }: MetricsPanelProps) {
  const chartData = [
    { name: "start", progress: 0 },
    { name: "live", progress: metrics?.progress_percent ?? progress },
    { name: "target", progress: progress }
  ];
  return (
    <Card title="Live Metrics">
      <div className="grid gap-5 p-5 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="h-52 min-h-52 rounded-md border border-surface-line bg-slate-950/50 p-3">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-200">
            <BarChart3 size={17} className="text-signal-cyan" />
            Progress telemetry
          </div>
          <ResponsiveContainer width="100%" height="82%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="progressFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#18d3ff" stopOpacity={0.45} />
                  <stop offset="95%" stopColor="#54e38e" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <XAxis dataKey="name" stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={12} domain={[0, 100]} />
              <Tooltip
                contentStyle={{
                  background: "#101d31",
                  border: "1px solid #22324a",
                  color: "#e7edf7"
                }}
              />
              <Area type="monotone" dataKey="progress" stroke="#18d3ff" fill="url(#progressFill)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <Metric label="command_id" value={metrics?.command_id ?? "n/a"} />
          <Metric label="training_run_id" value={metrics?.training_run_id ?? "n/a"} />
          <div className="rounded-md border border-surface-line bg-surface-panel p-3">
            <p className="mb-2 text-xs text-slate-400">current_status</p>
            <StatusPill status={metrics?.current_status ?? "PENDING"} />
          </div>
          <Metric label="progress_percent" value={formatPercent(metrics?.progress_percent ?? progress)} />
          <Metric label="epoch" value={metrics?.epoch ?? "n/a"} />
          <Metric label="total_epochs" value={metrics?.total_epochs ?? "n/a"} />
          <Metric label="mAP50" value={formatMetric(metrics?.mAP50)} />
          <Metric label="precision" value={formatMetric(metrics?.precision)} />
          <Metric label="recall" value={formatMetric(metrics?.recall)} />
          <Metric label="updated_at" value={formatDateTime(metrics?.updated_at)} />
          <div className="col-span-2 rounded-md border border-surface-line bg-surface-panel p-3">
            <p className="mb-2 flex items-center gap-2 text-xs text-slate-400">
              <Activity size={14} />
              message
            </p>
            <p className="min-h-5 text-slate-200">{metrics?.message ?? "Waiting for live metrics"}</p>
          </div>
        </div>
      </div>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-md border border-surface-line bg-surface-panel p-3">
      <p className="mb-1 text-xs text-slate-400">{label}</p>
      <p className="break-words font-mono text-sm text-slate-100">{value}</p>
    </div>
  );
}
