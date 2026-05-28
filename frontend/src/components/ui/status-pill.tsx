import { clsx } from "clsx";

const statusStyles: Record<string, string> = {
  PENDING: "border-slate-500/40 bg-slate-500/12 text-slate-200",
  STARTING: "border-amber-400/40 bg-amber-400/12 text-amber-200",
  RUNNING: "border-cyan-400/40 bg-cyan-400/12 text-cyan-100",
  PICKED_UP: "border-blue-400/40 bg-blue-400/12 text-blue-100",
  COMPLETED: "border-emerald-400/40 bg-emerald-400/12 text-emerald-100",
  SUCCEEDED: "border-emerald-400/40 bg-emerald-400/12 text-emerald-100",
  FAILED: "border-red-400/50 bg-red-500/14 text-red-100",
  ERROR: "border-red-400/50 bg-red-500/14 text-red-100",
  TRANSITION: "border-amber-400/40 bg-amber-400/12 text-amber-200",
  NOT_STARTED: "border-slate-500/40 bg-slate-500/12 text-slate-200"
};

export function StatusPill({ status, pulse = false }: { status?: string | null; pulse?: boolean }) {
  const normalized = (status ?? "UNKNOWN").toUpperCase();
  return (
    <span
      className={clsx(
        "inline-flex min-h-7 items-center rounded-full border px-2.5 py-1 text-xs font-semibold",
        statusStyles[normalized] ?? "border-slate-500/40 bg-slate-500/12 text-slate-200",
        (pulse || normalized === "RUNNING") && "animate-pulse"
      )}
    >
      {normalized.replaceAll("_", " ")}
    </span>
  );
}

