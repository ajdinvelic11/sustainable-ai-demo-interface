import { useEffect, useState } from "react";
import { AlertTriangle, Boxes, Cloud, Database, Play, RefreshCcw, Route, ShieldAlert } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { getCurrentDemoRun, getSites, resetStaleDemoState, startDemoRun } from "../api/demo";
import ResetStaleStateDialog from "../components/ResetStaleStateDialog";
import SiteStatusCards from "../components/SiteStatusCards";
import StatusPill from "../components/StatusPill";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Progress from "../components/ui/Progress";
import { useAuth } from "../context/AuthContext";
import type { CurrentDemoResponse, SiteInfo } from "../types/api";

export default function LandingPage() {
  const [sites, setSites] = useState<SiteInfo[]>([]);
  const [current, setCurrent] = useState<CurrentDemoResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<Record<string, unknown> | null>(null);
  const [resetting, setResetting] = useState(false);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const navigate = useNavigate();
  const { user } = useAuth();

  const load = async () => {
    setLoading(true);
    try {
      const [siteData, currentData] = await Promise.all([getSites(), getCurrentDemoRun()]);
      setSites(siteData);
      setCurrent(currentData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load demo state.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const start = async () => {
    setError(null);
    setConflict(null);
    setStarting(true);
    try {
      const response = await startDemoRun();
      navigate(`/runs/${response.demo_run_id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setConflict((err.details as Record<string, unknown>) || { message: err.message });
      } else {
        setError(err instanceof Error ? err.message : "Could not start demo run.");
      }
    } finally {
      setStarting(false);
    }
  };

  const reset = async (failCommands: boolean) => {
    setResetting(true);
    try {
      await resetStaleDemoState(failCommands);
      await load();
      setConflict(null);
      setResetDialogOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed.");
    } finally {
      setResetting(false);
    }
  };

  const latest = current?.latest;

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <section className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1.5 text-xs font-semibold text-cyan-200">
            <Route className="h-3.5 w-3.5" />
            Five-minute orchestration chain
          </div>
          <h1 className="mt-6 max-w-4xl text-5xl font-semibold tracking-normal text-white">Sustainable AI Demo Interface</h1>
          <p className="mt-5 max-w-3xl text-lg leading-8 text-slate-300">
            Multi-site AI training with checkpoint transfer across Wiener Neustadt, Wien and Eisenstadt
          </p>
        </div>
        <Card>
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="text-sm text-slate-400">Current demo state</div>
              <div className="mt-2 flex items-center gap-3">
                <StatusPill status={latest?.status || "IDLE"} />
                {latest && <span className="font-mono text-sm text-slate-400">run #{latest.demo_run_id}</span>}
              </div>
            </div>
            {latest && <div className="text-right text-2xl font-semibold text-cyan-200">{latest.overall_progress_percent}%</div>}
          </div>
          {latest && <Progress value={latest.overall_progress_percent} className="mt-5" />}
        </Card>
      </section>

      {error && (
        <div className="mt-6 flex items-start gap-3 rounded-xl border border-red-400/30 bg-red-400/10 p-4 text-sm text-red-200">
          <AlertTriangle className="mt-0.5 h-5 w-5" />
          {error}
        </div>
      )}

      {conflict !== null && (
        <div className="mt-6 rounded-xl border border-amber-400/30 bg-amber-400/10 p-5">
          <div className="flex items-start gap-3 text-amber-100">
            <ShieldAlert className="mt-0.5 h-5 w-5 flex-none" />
            <div>
              <h2 className="font-semibold">Demo cannot start safely</h2>
              <p className="mt-1 text-sm leading-6 text-amber-100/80">
                There is already an active run or open edge command. Review the state before resetting.
              </p>
            </div>
          </div>
          <pre className="mt-4 max-h-48 overflow-auto rounded-lg bg-slate-950/60 p-3 text-xs text-amber-50">{JSON.stringify(conflict, null, 2) || ""}</pre>
        </div>
      )}

      <div className="mt-8 flex flex-wrap gap-3">
        <Button onClick={start} disabled={starting || current?.active}>
          <Play className="h-4 w-4" />
          Start Demo Run
        </Button>
        {latest && (
          <Button variant="secondary" onClick={() => navigate(`/runs/${latest.demo_run_id}`)}>
            View Current Run
          </Button>
        )}
        <Button variant="danger" onClick={() => setResetDialogOpen(true)} disabled={resetting || !user?.is_admin}>
          <RefreshCcw className="h-4 w-4" />
          Reset Stale Demo State
        </Button>
      </div>
      {!user?.is_admin && <p className="mt-3 text-sm text-slate-500">Reset is admin-only. Configure APP_ADMIN_SUBJECTS to enable it for your credential subject.</p>}

      <section className="mt-10 grid gap-5 lg:grid-cols-3">
        <SiteStatusCards sites={sites} loading={loading} />
      </section>

      <section className="mt-8 grid gap-5 lg:grid-cols-3">
        <Card>
          <Database className="h-6 w-6 text-cyan-300" />
          <h3 className="mt-4 font-semibold text-white">PostgreSQL Control Plane</h3>
          <p className="mt-2 text-sm leading-6 text-slate-400">Commands, live metrics, manual chain metadata and UI audit events are coordinated through ml_ops tables.</p>
        </Card>
        <Card>
          <Cloud className="h-6 w-6 text-emerald-300" />
          <h3 className="mt-4 font-semibold text-white">Amazon S3 Artifacts</h3>
          <p className="mt-2 text-sm leading-6 text-slate-400">Model checkpoints are expected under s3://weather-data-intelligent-ai-training/model-checkpoints/.</p>
        </Card>
        <Card>
          <Boxes className="h-6 w-6 text-blue-300" />
          <h3 className="mt-4 font-semibold text-white">Existing Edge Agents</h3>
          <p className="mt-2 text-sm leading-6 text-slate-400">The UI writes commands and watches PostgreSQL; edge agents continue to run the training containers.</p>
        </Card>
      </section>

      <ResetStaleStateDialog open={resetDialogOpen} loading={resetting} onClose={() => setResetDialogOpen(false)} onConfirm={reset} />
    </div>
  );
}
