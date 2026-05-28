import { useState } from "react";
import { AlertTriangle, RefreshCcw, X } from "lucide-react";

import Button from "./ui/button";

interface ResetStaleStateDialogProps {
  open: boolean;
  loading?: boolean;
  onClose: () => void;
  onConfirm: (failOpenCommands: boolean) => void | Promise<void>;
}

export default function ResetStaleStateDialog({ open, loading = false, onClose, onConfirm }: ResetStaleStateDialogProps) {
  const [failOpenCommands, setFailOpenCommands] = useState(false);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-950 p-6 shadow-2xl shadow-black/40">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="flex h-11 w-11 flex-none items-center justify-center rounded-lg border border-amber-400/30 bg-amber-400/10 text-amber-200">
              <AlertTriangle className="h-5 w-5" />
            </span>
            <div>
              <h2 className="text-xl font-semibold text-white">Reset stale demo state</h2>
              <p className="mt-2 text-sm leading-6 text-slate-400">
                This marks active UI demo runs as FAILED so a new presentation run can start. Historical runs and S3 artifacts are never deleted.
              </p>
            </div>
          </div>
          <button
            aria-label="Close"
            className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-900 hover:text-white"
            type="button"
            onClick={onClose}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <label className="mt-6 flex cursor-pointer items-start gap-3 rounded-xl border border-slate-800 bg-slate-900/70 p-4">
          <input
            checked={failOpenCommands}
            className="mt-1 h-4 w-4 rounded border-slate-600 bg-slate-950 text-cyan-400 focus:ring-cyan-400"
            type="checkbox"
            onChange={(event) => setFailOpenCommands(event.target.checked)}
          />
          <span>
            <span className="block text-sm font-semibold text-slate-100">Also fail open edge commands</span>
            <span className="mt-1 block text-sm leading-6 text-slate-400">
              Marks PENDING, PICKED_UP and RUNNING edge commands as FAILED. Use this only after confirming the training backend is stale.
            </span>
          </span>
        </label>

        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <Button variant="secondary" type="button" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button variant="danger" type="button" onClick={() => onConfirm(failOpenCommands)} disabled={loading}>
            <RefreshCcw className="h-4 w-4" />
            {loading ? "Resetting..." : "Confirm Reset"}
          </Button>
        </div>
      </div>
    </div>
  );
}
