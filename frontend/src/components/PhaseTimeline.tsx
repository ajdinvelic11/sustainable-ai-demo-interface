import { CheckCircle2, Circle, Loader2 } from "lucide-react";

import type { DemoPhase } from "../types/api";
import StatusPill from "./StatusPill";

export default function PhaseTimeline({ phases }: { phases: DemoPhase[] }) {
  return (
    <div className="space-y-3">
      {phases.map((phase) => {
        const running = ["RUNNING", "PICKED_UP", "PENDING"].includes((phase.status || "").toUpperCase()) && phase.command_id;
        const complete = phase.status === "COMPLETED";
        return (
          <div
            key={phase.phase_no}
            className={`rounded-xl border p-4 transition ${
              running ? "border-cyan-400/40 bg-cyan-400/10" : "border-slate-800 bg-slate-950/40"
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex gap-3">
                <span className="mt-0.5 text-cyan-300">
                  {complete ? <CheckCircle2 className="h-5 w-5" /> : running ? <Loader2 className="h-5 w-5 animate-spin" /> : <Circle className="h-5 w-5" />}
                </span>
                <div>
                  <div className="font-semibold text-white">
                    Phase {phase.phase_no} | {phase.location_name}
                  </div>
                  <div className="mt-1 text-sm text-slate-400">
                    {phase.region_code} | {phase.target_percent}% | {phase.target_duration_seconds}s
                  </div>
                  {phase.command_id && <div className="mt-2 font-mono text-xs text-slate-500">command #{phase.command_id}</div>}
                </div>
              </div>
              <StatusPill status={phase.command_status || phase.status} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
