import { ArrowLeft, Clock, Radio, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";

import type { DemoRunState } from "../types/api";
import ArtifactPanel from "./ArtifactPanel";
import CurrentSiteCard from "./CurrentSiteCard";
import EventLogPanel from "./EventLogPanel";
import FinalResultsPanel from "./FinalResultsPanel";
import LiveMetricsPanel from "./LiveMetricsPanel";
import PhaseTimeline from "./PhaseTimeline";
import StatusPill from "./StatusPill";
import Card from "./ui/card";
import Progress from "./ui/progress";

interface LiveDemoDashboardProps {
  run: DemoRunState;
  streamConnected: boolean;
  streamError?: string | null;
  onStartNew: () => void;
}

export default function LiveDemoDashboard({ run, streamConnected, streamError, onStartNew }: LiveDemoDashboardProps) {
  const completed = run.status === "COMPLETED";

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <Link to="/" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-400 hover:text-white">
            <ArrowLeft className="h-4 w-4" />
            Back to overview
          </Link>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <h1 className="text-4xl font-semibold text-white">Live Demo Dashboard</h1>
            <StatusPill status={run.status} />
          </div>
          <p className="mt-2 text-sm text-slate-400">
            Run #{run.demo_run_id} | {run.demo_name}
          </p>
        </div>
        <div className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-300">
          <Radio className={`h-4 w-4 ${streamConnected ? "text-emerald-300" : "text-amber-300"}`} />
          {streamConnected ? "Live stream connected" : "Reconnecting stream"}
        </div>
      </div>

      {streamError && <div className="mb-5 rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100">{streamError}</div>}
      {completed && <FinalResultsPanel run={run} onStartNew={onStartNew} />}

      <section className="mt-6 grid gap-5 lg:grid-cols-[1fr_380px]">
        <Card>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="text-sm uppercase tracking-wide text-slate-500">Overall progress</div>
              <div className="mt-2 text-5xl font-semibold text-white">{run.overall_progress_percent}%</div>
            </div>
            <div className="grid gap-3 sm:grid-cols-3 lg:min-w-[430px]">
              <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
                <Clock className="h-4 w-4 text-slate-500" />
                <div className="mt-2 text-sm text-slate-400">Duration</div>
                <div className="font-semibold text-white">{run.requested_duration_seconds}s</div>
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
                <RefreshCw className="h-4 w-4 text-slate-500" />
                <div className="mt-2 text-sm text-slate-400">Updated</div>
                <div className="font-semibold text-white">{new Date(run.updated_at).toLocaleTimeString()}</div>
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
                <div className="h-4 w-4 rounded-full bg-cyan-300/80" />
                <div className="mt-2 text-sm text-slate-400">Phase</div>
                <div className="font-semibold text-white">{run.current_phase?.phase_no || "n/a"}</div>
              </div>
            </div>
          </div>
          <Progress value={run.overall_progress_percent} className="mt-6" />
        </Card>

        <CurrentSiteCard phase={run.current_phase} />
      </section>

      <section className="mt-6 grid gap-5 lg:grid-cols-[420px_1fr]">
        <Card>
          <h2 className="mb-5 text-lg font-semibold text-white">Phase Timeline</h2>
          <PhaseTimeline phases={run.phases} />
        </Card>
        <LiveMetricsPanel metrics={run.latest_metrics} />
      </section>

      <section className="mt-6 grid gap-5 lg:grid-cols-[1fr_1fr]">
        <ArtifactPanel run={run} />
        <EventLogPanel events={run.events} />
      </section>
    </div>
  );
}
