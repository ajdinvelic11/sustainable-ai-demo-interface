import type { LiveMetrics } from "../types/api";
import MetricsPanel from "./MetricsPanel";

export default function LiveMetricsPanel({ metrics }: { metrics?: LiveMetrics | null }) {
  return <MetricsPanel metrics={metrics} />;
}
