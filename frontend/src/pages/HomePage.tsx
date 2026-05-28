import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, Database, Eye, Network, Play, RotateCcw } from "lucide-react";
import { api, ApiError } from "../api/client";
import { SiteCard } from "../components/demo/SiteCard";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Progress } from "../components/ui/progress";
import { Skeleton } from "../components/ui/skeleton";
import { StatusPill } from "../components/ui/status-pill";
import type { DemoState, SiteInfo, SessionUser } from "../types/api";

export function HomePage({ user }: { user: SessionUser | null }) {
  const navigate = useNavigate();
  const [sites, setSites] = useState<SiteInfo[]>([]);
  const [currentRun, setCurrentRun] = useState<DemoState | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [siteRows, run] = await Promise.all([api.sites(), api.currentRun()]);
      setSites(siteRows);
      setCurrentRun(run);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load demo state.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const startDemo = async () => {
    setStarting(true);
    setConflict(null);
    setError(null);
    try {
      const response = await api.startDemo();
      navigate(`/runs/${response.demo_run_id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setConflict(err.message);
      } else {
        setError(err instanceof Error ? err.message : "Could not start demo run.");
      }
    } finally {
      setStarting(false);
      void load();
    }
  };

  const resetStale = async () => {
    const confirmed = window.confirm("Mark stale demo UI runs as FAILED? Open edge commands can also be marked FAILED.");
    if (!confirmed) {
      return;
    }
    const markCommands = window.confirm("Also mark open edge training commands as FAILED?");
    setResetting(true);
    setError(null);
    try {
      await api.resetStale(markCommands, "Reset from Sustainable AI Demo Interface");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reset stale state.");
    } finally {
      setResetting(false);
    }
  };

  const activeRun = currentRun?.demo_run_id && ["STARTING", "RUNNING"].includes(currentRun.status);

  return (
    <div className="grid gap-6">
      <section className="grid gap-5 lg:grid-cols-[1.25fr_0.75fr]">
        <div>
          <h1 className="text-3xl font-semibold text-white">Sustainable AI Demo Interface</h1>
          <p className="mt-3 max-w-3xl text-base leading-7 text-slate-300">
            Multi-site AI training with checkpoint transfer across Wiener Neustadt, Wien and Eisenstadt.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button icon={<Play size={18} />} disabled={starting || Boolean(activeRun) || currentRun?.setup_required} onClick={startDemo}>
              {starting ? "Starting..." : "Start Demo Run"}
            </Button>
            {currentRun?.demo_run_id && (
              <Button variant="secondary" icon={<Eye size={18} />} onClick={() => navigate(`/runs/${currentRun.demo_run_id}`)}>
                View Current Run
              </Button>
            )}
            {user?.is_admin && (
              <Button variant="danger" icon={<RotateCcw size={18} />} disabled={resetting} onClick={resetStale}>
                Reset Stale Demo State
              </Button>
            )}
          </div>
        </div>
        <Card className="p-5">
          {loading ? (
            <div className="grid gap-3">
              <Skeleton className="h-6 w-32" />
              <Skeleton className="h-14 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm text-slate-400">Current run</p>
                  <p className="mt-1 font-mono text-lg font-semibold text-white">{currentRun?.demo_run_id ?? "n/a"}</p>
                </div>
                <StatusPill status={currentRun?.status ?? "NOT_STARTED"} />
              </div>
              <Progress className="mt-5" value={currentRun?.overall_progress_percent ?? 0} label="Overall demo progress" />
              {currentRun?.warning && <p className="mt-4 text-sm text-amber-200">{currentRun.warning}</p>}
            </div>
          )}
        </Card>
      </section>

      {(error || conflict) && (
        <div className="flex items-start gap-3 rounded-md border border-amber-400/40 bg-amber-400/12 p-4 text-sm text-amber-100">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <span>{conflict ?? error}</span>
        </div>
      )}

      <section className="grid gap-4 md:grid-cols-3">
        {loading
          ? [1, 2, 3].map((item) => <Skeleton key={item} className="h-48" />)
          : sites.map((site) => <SiteCard key={site.region_code} site={site} />)}
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card title="PostgreSQL Coordination">
          <div className="grid gap-4 p-5 text-sm text-slate-300">
            <div className="flex items-center gap-3">
              <Database size={18} className="text-signal-green" />
              <span>ml_ops.edge_training_commands</span>
            </div>
            <div className="flex items-center gap-3">
              <Network size={18} className="text-signal-cyan" />
              <span>manual chain phases and live metrics views</span>
            </div>
          </div>
        </Card>
        <Card title="S3 Artifact Store">
          <div className="grid gap-4 p-5 text-sm text-slate-300">
            <div className="font-mono text-slate-200">s3://weather-data-intelligent-ai-training/model-checkpoints/</div>
            <div className="text-slate-400">model_id sustainable-ai-model-v1 / model_version v1.0</div>
          </div>
        </Card>
      </section>
    </div>
  );
}
