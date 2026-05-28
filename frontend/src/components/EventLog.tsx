import { TerminalSquare } from "lucide-react";

import type { DemoEvent } from "../types/api";
import Card from "./ui/card";
import StatusPill from "./StatusPill";

export default function EventLog({ events }: { events: DemoEvent[] }) {
  return (
    <Card className="max-h-[520px] overflow-hidden">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Event Log</h2>
          <p className="mt-1 text-sm text-slate-400">Orchestration and edge-agent updates</p>
        </div>
        <TerminalSquare className="h-5 w-5 text-cyan-300" />
      </div>
      <div className="max-h-[420px] space-y-3 overflow-y-auto pr-1">
        {events.length === 0 && <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 text-sm text-slate-400">No events yet.</div>}
        {[...events].reverse().map((event) => (
          <div key={event.event_id} className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
            <div className="flex items-center justify-between gap-3">
              <div className="font-mono text-xs text-slate-500">{new Date(event.created_at).toLocaleTimeString()}</div>
              <StatusPill status={event.severity === "ERROR" ? "FAILED" : event.event_type.includes("COMPLETED") ? "COMPLETED" : "TRANSITION"} />
            </div>
            <div className="mt-2 text-sm font-semibold text-slate-100">{event.event_type}</div>
            <div className="mt-1 text-sm leading-6 text-slate-400">{event.message}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}
