import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import type { DemoPhase } from "../../types/api";
import { StatusPill } from "../ui/status-pill";

export function PhaseTimeline({ phases }: { phases: DemoPhase[] }) {
  return (
    <div className="grid gap-3">
      {phases.map((phase, index) => {
        const status = phase.status.toUpperCase();
        const active = status === "RUNNING";
        const done = status === "COMPLETED";
        const failed = status === "FAILED";
        return (
          <div key={phase.phase_no} className="grid grid-cols-[2rem_1fr] gap-3">
            <div className="flex flex-col items-center">
              <div
                className={clsx(
                  "flex h-8 w-8 items-center justify-center rounded-full border",
                  done && "border-emerald-400/60 bg-emerald-400/14 text-emerald-200",
                  active && "border-cyan-400/60 bg-cyan-400/14 text-cyan-100",
                  failed && "border-red-400/60 bg-red-400/14 text-red-100",
                  !done && !active && !failed && "border-slate-500/50 bg-slate-700/20 text-slate-300"
                )}
              >
                {done ? <CheckCircle2 size={17} /> : active ? <Loader2 size={17} className="animate-spin" /> : <Circle size={14} />}
              </div>
              {index < phases.length - 1 && <div className="min-h-8 w-px flex-1 bg-surface-line" />}
            </div>
            <div
              className={clsx(
                "rounded-md border p-4",
                active ? "border-cyan-400/40 bg-cyan-400/8" : "border-surface-line bg-surface-panel/70"
              )}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-white">
                    Phase {phase.phase_no} {phase.location_name}
                  </p>
                  <p className="mt-1 font-mono text-xs text-slate-400">
                    {phase.region_code} / {phase.target_percent}% / {phase.target_duration_seconds}s
                  </p>
                </div>
                <StatusPill status={phase.command_status ?? phase.status} />
              </div>
              <div className="mt-3 grid gap-2 text-xs text-slate-400 sm:grid-cols-2">
                <span>command_id: {phase.command_id ?? "n/a"}</span>
                <span>training_run_id: {phase.training_run_id ?? "n/a"}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

