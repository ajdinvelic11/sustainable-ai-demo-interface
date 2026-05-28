import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getDemoRun, startDemoRun } from "../api/demo";
import LiveDemoDashboard from "../components/LiveDemoDashboard";
import Card from "../components/ui/card";
import { useDemoStream } from "../hooks/useDemoStream";
import type { DemoRunState } from "../types/api";

export default function RunDashboardPage() {
  const params = useParams();
  const demoRunId = Number(params.demoRunId);
  const navigate = useNavigate();
  const [run, setRun] = useState<DemoRunState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const stream = useDemoStream(true);

  useEffect(() => {
    if (!Number.isFinite(demoRunId)) return;
    getDemoRun(demoRunId)
      .then(setRun)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load run."));
  }, [demoRunId]);

  useEffect(() => {
    const latest = stream.state?.latest;
    if (latest?.demo_run_id === demoRunId) {
      setRun(latest);
    }
  }, [stream.state, demoRunId]);

  const startNew = async () => {
    const response = await startDemoRun();
    navigate(`/runs/${response.demo_run_id}`);
  };

  if (!run) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-10">
        <Card className="h-80 animate-pulse" />
        {error && <p className="mt-4 text-red-300">{error}</p>}
      </div>
    );
  }

  return <LiveDemoDashboard run={run} streamConnected={stream.connected} streamError={stream.error} onStartNew={startNew} />;
}
