import clsx from "clsx";

interface StatusPillProps {
  status?: string | null;
}

export default function StatusPill({ status }: StatusPillProps) {
  const normalized = (status || "UNKNOWN").toUpperCase();
  const color =
    normalized === "COMPLETED"
      ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-300"
      : normalized === "FAILED"
        ? "border-red-400/40 bg-red-400/10 text-red-300"
        : normalized === "RUNNING" || normalized === "PICKED_UP"
          ? "border-cyan-400/40 bg-cyan-400/10 text-cyan-300"
          : normalized === "TRANSITION" || normalized === "STARTING"
            ? "border-amber-400/40 bg-amber-400/10 text-amber-300"
            : "border-slate-500/40 bg-slate-700/30 text-slate-300";
  return (
    <span className={clsx("inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-semibold", color)}>
      {(normalized === "RUNNING" || normalized === "PICKED_UP") && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />}
      {normalized}
    </span>
  );
}
