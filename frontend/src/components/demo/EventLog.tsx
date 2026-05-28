import { AlertTriangle, CheckCircle2, CircleDot, Info } from "lucide-react";
import { clsx } from "clsx";
import type { DemoEvent } from "../../types/api";
import { formatDateTime } from "../../utils/format";
import { Card } from "../ui/card";

export function EventLog({ events }: { events: DemoEvent[] }) {
  const latest = [...events].reverse().slice(0, 18);
  return (
    <Card title="Event Log">
      <div className="max-h-[31rem] overflow-y-auto p-4">
        <div className="grid gap-3">
          {latest.length === 0 && <p className="rounded-md border border-surface-line bg-surface-panel p-4 text-sm text-slate-400">No events yet.</p>}
          {latest.map((event) => (
            <div key={`${event.event_id}-${event.created_at}`} className="grid grid-cols-[1.25rem_1fr] gap-3 rounded-md border border-surface-line bg-surface-panel p-3">
              <EventIcon severity={event.severity} type={event.event_type} />
              <div className="min-w-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-slate-100">{event.event_type.replaceAll("_", " ")}</p>
                  <span className="font-mono text-xs text-slate-500">{formatDateTime(event.created_at)}</span>
                </div>
                <p className="mt-1 text-sm text-slate-300">{event.message}</p>
                <p className="mt-2 font-mono text-xs text-slate-500">
                  phase {event.phase_no ?? "n/a"} / command {event.command_id ?? "n/a"}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

function EventIcon({ severity, type }: { severity: string; type: string }) {
  const isError = severity.toUpperCase() === "ERROR";
  const isWarn = severity.toUpperCase() === "WARN";
  const isDone = type.includes("COMPLETED") || type.includes("UPLOADED");
  return (
    <div
      className={clsx(
        "mt-0.5 flex h-5 w-5 items-center justify-center rounded-full",
        isError && "text-signal-red",
        isWarn && "text-signal-amber",
        isDone && "text-signal-green",
        !isError && !isWarn && !isDone && "text-signal-cyan"
      )}
    >
      {isError || isWarn ? <AlertTriangle size={16} /> : isDone ? <CheckCircle2 size={16} /> : type.includes("STARTED") ? <CircleDot size={16} /> : <Info size={16} />}
    </div>
  );
}

