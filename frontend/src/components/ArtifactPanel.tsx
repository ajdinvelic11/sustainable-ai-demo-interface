import { Copy, Database, PackageCheck } from "lucide-react";

import type { DemoRunState } from "../types/api";
import Button from "./ui/button";
import Card from "./ui/card";

function copy(value?: string | null) {
  if (value) {
    void navigator.clipboard.writeText(value);
  }
}

export default function ArtifactPanel({ run }: { run: DemoRunState }) {
  const latestCheckpoint =
    [...run.phases].reverse().find((phase) => phase.output_checkpoint_s3_uri)?.output_checkpoint_s3_uri ||
    run.final_result.final_checkpoint_s3_uri;

  return (
    <Card>
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Model Artifacts</h2>
          <p className="mt-1 text-sm text-slate-400">Checkpoint transfer and final result</p>
        </div>
        <PackageCheck className="h-5 w-5 text-emerald-300" />
      </div>
      <div className="space-y-3">
        {[
          ["Latest checkpoint URI", latestCheckpoint],
          ["Final checkpoint URI", run.final_result.final_checkpoint_s3_uri],
          ["S3 best model URI", run.final_result.s3_best_model_uri],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2">
                <Database className="h-4 w-4 flex-none text-slate-500" />
                <div className="min-w-0">
                  <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
                  <div className="mt-1 truncate font-mono text-xs text-slate-200">{value || "not available yet"}</div>
                </div>
              </div>
              <Button variant="ghost" className="px-2 py-2" disabled={!value} onClick={() => copy(String(value))}>
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
