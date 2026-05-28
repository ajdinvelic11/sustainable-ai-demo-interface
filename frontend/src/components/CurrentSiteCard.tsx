import { MapPin, Play } from "lucide-react";

import type { DemoPhase } from "../types/api";
import StatusPill from "./StatusPill";
import Card from "./ui/Card";

export default function CurrentSiteCard({ phase }: { phase?: DemoPhase | null }) {
  return (
    <Card>
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Current Training Site</h2>
          <p className="mt-1 text-sm text-slate-400">Active phase target and edge command</p>
        </div>
        <span className="flex h-11 w-11 items-center justify-center rounded-lg border border-cyan-400/30 bg-cyan-400/10 text-cyan-200">
          <MapPin className="h-5 w-5" />
        </span>
      </div>

      {phase ? (
        <div className="mt-6 space-y-4">
          <div>
            <div className="text-3xl font-semibold text-white">{phase.location_name}</div>
            <div className="mt-1 text-sm text-slate-400">
              {phase.region_code} | phase {phase.phase_no} | {phase.target_percent}% target
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
              <div className="text-xs uppercase tracking-wide text-slate-500">command_id</div>
              <div className="mt-1 font-mono text-sm text-slate-100">{phase.command_id || "n/a"}</div>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
              <div className="text-xs uppercase tracking-wide text-slate-500">training_run_id</div>
              <div className="mt-1 font-mono text-sm text-slate-100">{phase.training_run_id || "n/a"}</div>
            </div>
          </div>
          <div className="flex items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-950/40 p-3">
            <div className="flex items-center gap-2 text-sm text-slate-300">
              <Play className="h-4 w-4 text-slate-500" />
              {phase.target_duration_seconds}s target window
            </div>
            <StatusPill status={phase.command_status || phase.status} />
          </div>
        </div>
      ) : (
        <div className="mt-6 rounded-lg border border-slate-800 bg-slate-950/40 p-4 text-sm text-slate-400">No active phase.</div>
      )}
    </Card>
  );
}
