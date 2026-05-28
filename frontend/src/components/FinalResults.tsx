import { useState } from "react";
import { CheckCircle2, Copy, FileDown, KeyRound, RotateCcw } from "lucide-react";

import { exportDemoCertificate, exportDemoCertificateJwt } from "../api/demo";
import type { DemoRunState } from "../types/api";
import StatusPill from "./StatusPill";
import Button from "./ui/button";
import Card from "./ui/card";

interface FinalResultsProps {
  run: DemoRunState;
  onStartNew: () => void;
}

export default function FinalResults({ run, onStartNew }: FinalResultsProps) {
  const finalUri = run.final_result.final_checkpoint_s3_uri;
  const [exportingJson, setExportingJson] = useState(false);
  const [exportingJwt, setExportingJwt] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const downloadCertificate = async (kind: "json" | "jwt") => {
    setExportError(null);
    if (kind === "json") {
      setExportingJson(true);
    } else {
      setExportingJwt(true);
    }
    try {
      const { blob, filename } =
        kind === "json" ? await exportDemoCertificate(run.demo_run_id) : await exportDemoCertificateJwt(run.demo_run_id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "Certificate export failed.");
    } finally {
      if (kind === "json") {
        setExportingJson(false);
      } else {
        setExportingJwt(false);
      }
    }
  };

  return (
    <Card className="border-emerald-400/30 bg-emerald-400/10">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-3 text-emerald-200">
            <CheckCircle2 className="h-7 w-7" />
            <h2 className="text-2xl font-semibold">Demo completed successfully</h2>
          </div>
          <p className="mt-2 text-sm text-emerald-100/80">Final run ID #{run.demo_run_id}</p>
          <p className="mt-3 break-all font-mono text-sm text-emerald-50">{finalUri || "Final checkpoint URI not available yet."}</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button variant="secondary" onClick={() => downloadCertificate("json")} disabled={exportingJson || exportingJwt}>
            <FileDown className="h-4 w-4" />
            {exportingJson ? "Exporting..." : "Export Digital Certificate"}
          </Button>
          <Button variant="secondary" onClick={() => downloadCertificate("jwt")} disabled={exportingJson || exportingJwt}>
            <KeyRound className="h-4 w-4" />
            {exportingJwt ? "Exporting..." : "Export JWT Certificate"}
          </Button>
          <Button variant="secondary" disabled={!finalUri} onClick={() => finalUri && navigator.clipboard.writeText(finalUri)}>
            <Copy className="h-4 w-4" />
            Copy final S3 URI
          </Button>
          <Button onClick={onStartNew}>
            <RotateCcw className="h-4 w-4" />
            Start new demo
          </Button>
        </div>
      </div>
      {exportError && (
        <div className="mt-5 rounded-lg border border-red-400/30 bg-red-400/10 p-3 text-sm text-red-100">{exportError}</div>
      )}

      <div className="mt-6 overflow-x-auto">
        <table className="w-full min-w-[860px] text-left text-sm">
          <thead className="text-xs uppercase tracking-wide text-emerald-100/70">
            <tr>
              <th className="py-3">Phase</th>
              <th>Location</th>
              <th>Region</th>
              <th>Target</th>
              <th>Command</th>
              <th>Status</th>
              <th>Training Run</th>
              <th>Output Checkpoint</th>
            </tr>
          </thead>
          <tbody>
            {run.phases.map((phase) => (
              <tr key={phase.phase_no} className="border-t border-emerald-200/10">
                <td className="py-3 font-semibold">#{phase.phase_no}</td>
                <td>{phase.location_name}</td>
                <td>{phase.region_code}</td>
                <td>{phase.target_percent}%</td>
                <td className="font-mono">{phase.command_id || "n/a"}</td>
                <td>
                  <StatusPill status={phase.command_status || phase.status} />
                </td>
                <td className="font-mono">{phase.training_run_id || "n/a"}</td>
                <td className="max-w-[260px] truncate font-mono text-xs">{phase.output_checkpoint_s3_uri || "n/a"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
