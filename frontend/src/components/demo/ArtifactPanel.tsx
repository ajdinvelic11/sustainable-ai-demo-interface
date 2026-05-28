import { Clipboard, Database, HardDrive } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { truncateMiddle } from "../../utils/format";

type ArtifactPanelProps = {
  latestCheckpoint?: string | null;
  finalCheckpoint?: string | null;
  bestModelUri?: string | null;
};

export function ArtifactPanel({ latestCheckpoint, finalCheckpoint, bestModelUri }: ArtifactPanelProps) {
  const copy = async (value?: string | null) => {
    if (value) {
      await navigator.clipboard.writeText(value);
    }
  };
  return (
    <Card title="Model Artifacts">
      <div className="grid gap-3 p-5">
        <ArtifactRow icon={<HardDrive size={17} />} label="latest checkpoint URI" value={latestCheckpoint} onCopy={() => copy(latestCheckpoint)} />
        <ArtifactRow icon={<Database size={17} />} label="final checkpoint URI" value={finalCheckpoint} onCopy={() => copy(finalCheckpoint)} />
        <ArtifactRow icon={<HardDrive size={17} />} label="S3 best model URI" value={bestModelUri} onCopy={() => copy(bestModelUri)} />
      </div>
    </Card>
  );
}

function ArtifactRow({
  icon,
  label,
  value,
  onCopy
}: {
  icon: ReactNode;
  label: string;
  value?: string | null;
  onCopy: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-surface-line bg-surface-panel p-3">
      <div className="min-w-0">
        <p className="mb-1 flex items-center gap-2 text-xs text-slate-400">
          {icon}
          {label}
        </p>
        <p className="truncate font-mono text-sm text-slate-100" title={value ?? "n/a"}>
          {truncateMiddle(value, 82)}
        </p>
      </div>
      <Button variant="secondary" icon={<Clipboard size={16} />} disabled={!value} onClick={onCopy} aria-label={`Copy ${label}`} />
    </div>
  );
}
