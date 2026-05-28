import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Play, Radio, RotateCcw } from "lucide-react";
import { api } from "../api/client";
import { ArtifactPanel } from "../components/demo/ArtifactPanel";
import { EventLog } from "../components/demo/EventLog";
import { FinalResults } from "../components/demo/FinalResults";
import { MetricsPanel } from "../components/demo/MetricsPanel";
import { PhaseTimeline } from "../components/demo/PhaseTimeline";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Progress } from "../components/ui/progress";
import { Skeleton } from "../components/ui/skeleton";
import { StatusPill } from "../components/ui/status-pill";
import { useDemoStream } from "../hooks/useDemoStream";
import type { DemoState } from "../types/api";

export function DashboardPage() {
  const params = useParams();
  const navigate = useNavigate();
  const [initialState, setInitialState] = useState<DemoState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { state: streamState, connected, error: streamError } = useDemoStream(true);

  const requestedRunId = Number(params.demoRunId);
  const state = useMemo(() => {
    if (streamState?.demo_run_id === requestedRunId || !requestedRunId) {
      return streamState ?? initialState;
    }
    return initialState;
  }, [initialState, requestedRunId, streamState]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = requestedRunId ? await api.run(requestedRunId) : await api.currentRun();
        setInitialState(response);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load run.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [requestedRunId]);

  const startNew = async () => {
    const response = await api.startDemo();
    navigate(`/runs/${response.demo_run_id}`);
  };

  if (loading && !state) {
    return (
      <div className="grid gap-5">
        <Skeleton className="h-20" />
        <Skeleton className="h-64" />
        <Skeleton className="h-80" />
      </div>
    );
  }

  if (error || !state) {
    return (
      <Card className="p-6">
        <p className="text-red-100">{error ?? "Demo run not found."}</p>
        <Button className="mt-4" variant="secondary" icon={<ArrowLeft size={17} />} onClick={() => navigate("/")}>
          Back to console
        </Button>
      </Card>
    );
  }

  if (state.status === "COMPLETED") {
    return <FinalResults state={state} onStartNew={startNew} />;
  }

  return (
    <div className="grid gap-5">
      <section className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Button variant="ghost" icon={<ArrowLeft size={17} />} onClick={() => navigate("/")}>
            Back
          </Button>
          <h1 className="mt-3 text-3xl font-semibold text-white">Live Demo Dashboard</h1>
          <p className="mt-2 text-sm text-slate-400">Run {state.demo_run_id ?? "n/a"} / {state.demo_name ?? "Sustainable AI demo"}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-2 rounded-full border border-surface-line bg-surface-raised px-3 py-1.5 text-xs text-slate-300">
            <Radio size={14} className={connected ? "text-signal-green" : "text-signal-amber"} />
            {connected ? "live stream connected" : streamError ?? "connecting"}
          </span>
          <StatusPill status={state.status} />
        </div>
      </section>

      <Card className="p-5">
        <div className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="rounded-md border border-surface-line bg-surface-panel p-5">
            <p className="text-sm text-slate-400">Current training site</p>
            <h2 className="mt-2 text-2xl font-semibold text-white">{state.current_phase?.location_name ?? "Waiting for phase"}</h2>
            <p className="mt-2 font-mono text-sm text-slate-400">{state.current_phase?.region_code ?? "n/a"}</p>
            <div className="mt-5">
              <StatusPill status={state.current_phase?.status ?? state.status} />
            </div>
          </div>
          <div className="rounded-md border border-surface-line bg-surface-panel p-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-sm text-slate-400">Current phase</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">
                  Phase {state.current_phase?.phase_no ?? "n/a"} / {state.current_phase?.target_percent ?? 0}%
                </h2>
              </div>
              <Button variant="secondary" icon={<RotateCcw size={17} />} onClick={() => window.location.reload()}>
                Refresh
              </Button>
            </div>
            <Progress className="mt-6" value={state.overall_progress_percent} label="Overall progress" />
          </div>
        </div>
      </Card>

      <section className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
        <Card title="Phase Timeline">
          <div className="p-5">
            <PhaseTimeline phases={state.phases} />
          </div>
        </Card>
        <MetricsPanel metrics={state.latest_metrics} progress={state.overall_progress_percent} />
      </section>

      <section className="grid gap-5 xl:grid-cols-[1fr_1fr]">
        <ArtifactPanel
          latestCheckpoint={state.latest_checkpoint_s3_uri}
          finalCheckpoint={state.final_result.final_checkpoint_s3_uri}
          bestModelUri={state.final_result.best_model_s3_uri}
        />
        <EventLog events={state.events} />
      </section>

      {state.status === "FAILED" && (
        <Card className="border-red-400/40 bg-red-500/8 p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className="text-red-100">Demo failed. Review the event log and reset stale state from the admin console if needed.</p>
            <Button icon={<Play size={17} />} onClick={startNew}>
              Start Demo Run
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}

