import { CheckCircle2, Clipboard, RotateCcw } from "lucide-react";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { StatusPill } from "../ui/status-pill";
import type { DemoState } from "../../types/api";
import { formatMetric, truncateMiddle } from "../../utils/format";

export function FinalResults({ state, onStartNew }: { state: DemoState; onStartNew: () => void }) {
  const finalUri = state.final_result.final_checkpoint_s3_uri;
  const copyFinal = async () => {
    if (finalUri) {
      await navigator.clipboard.writeText(finalUri);
    }
  };
  return (
    <Card className="overflow-hidden">
      <div className="border-b border-surface-line bg-emerald-400/8 p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-md bg-emerald-400/14 text-emerald-200">
              <CheckCircle2 size={24} />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">Demo completed successfully</h2>
              <p className="mt-1 text-sm text-slate-400">Final run ID: {state.demo_run_id ?? "n/a"}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" icon={<Clipboard size={17} />} disabled={!finalUri} onClick={copyFinal}>
              Copy final S3 URI
            </Button>
            <Button icon={<RotateCcw size={17} />} onClick={onStartNew}>
              Start new demo
            </Button>
          </div>
        </div>
        <div className="mt-5 rounded-md border border-emerald-400/25 bg-slate-950/40 p-4">
          <p className="mb-1 text-xs text-slate-400">final checkpoint S3 URI</p>
          <p className="break-words font-mono text-sm text-emerald-100">{finalUri ?? "n/a"}</p>
        </div>
      </div>

      <div className="p-5">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-surface-line text-xs text-slate-400">
                <th className="py-3 pr-4 font-medium">phase_no</th>
                <th className="py-3 pr-4 font-medium">location_name</th>
                <th className="py-3 pr-4 font-medium">region_code</th>
                <th className="py-3 pr-4 font-medium">target_percent</th>
                <th className="py-3 pr-4 font-medium">command_id</th>
                <th className="py-3 pr-4 font-medium">command_status</th>
                <th className="py-3 pr-4 font-medium">training_run_id</th>
                <th className="py-3 font-medium">output_checkpoint_s3_uri</th>
              </tr>
            </thead>
            <tbody>
              {state.phases.map((phase) => (
                <tr key={phase.phase_no} className="border-b border-surface-line/70">
                  <td className="py-3 pr-4 font-mono text-slate-200">{phase.phase_no}</td>
                  <td className="py-3 pr-4 text-white">{phase.location_name}</td>
                  <td className="py-3 pr-4 font-mono text-slate-300">{phase.region_code}</td>
                  <td className="py-3 pr-4 text-slate-300">{phase.target_percent}%</td>
                  <td className="py-3 pr-4 font-mono text-slate-300">{phase.command_id ?? "n/a"}</td>
                  <td className="py-3 pr-4">
                    <StatusPill status={phase.command_status ?? phase.status} />
                  </td>
                  <td className="py-3 pr-4 font-mono text-slate-300">{phase.training_run_id ?? "n/a"}</td>
                  <td className="py-3 font-mono text-slate-300" title={phase.output_checkpoint_s3_uri ?? "n/a"}>
                    {truncateMiddle(phase.output_checkpoint_s3_uri, 48)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <Metric label="mAP50" value={formatMetric(state.latest_metrics?.mAP50)} />
          <Metric label="precision" value={formatMetric(state.latest_metrics?.precision)} />
          <Metric label="recall" value={formatMetric(state.latest_metrics?.recall)} />
        </div>
      </div>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-surface-line bg-surface-panel p-4">
      <p className="mb-1 text-xs text-slate-400">{label}</p>
      <p className="font-mono text-lg font-semibold text-white">{value}</p>
    </div>
  );
}

