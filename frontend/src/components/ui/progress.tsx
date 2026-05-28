import { clsx } from "clsx";
import { formatPercent } from "../../utils/format";

type ProgressProps = {
  value: number;
  label?: string;
  className?: string;
};

export function Progress({ value, label, className }: ProgressProps) {
  const normalized = Math.max(0, Math.min(100, value));
  return (
    <div className={className}>
      <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
        <span>{label ?? "Progress"}</span>
        <span className="font-mono text-slate-200">{formatPercent(normalized)}</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-slate-950 ring-1 ring-surface-line">
        <div
          className={clsx(
            "h-full rounded-full bg-gradient-to-r from-signal-blue via-signal-cyan to-signal-green transition-all duration-500",
            normalized > 0 && normalized < 100 && "animate-pulse"
          )}
          style={{ width: `${normalized}%` }}
        />
      </div>
    </div>
  );
}

