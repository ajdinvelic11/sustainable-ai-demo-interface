import { Cloud, Cpu, MapPin } from "lucide-react";
import { Card } from "../ui/card";
import type { SiteInfo } from "../../types/api";

export function SiteCard({ site }: { site: SiteInfo }) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-md bg-signal-cyan/12 text-signal-cyan">
            <MapPin size={20} />
          </div>
          <h3 className="text-base font-semibold text-white">{site.location_name}</h3>
          <p className="mt-1 font-mono text-xs text-slate-400">{site.region_code}</p>
        </div>
        <span className="rounded-full border border-surface-line bg-surface-panel px-2.5 py-1 text-xs text-slate-300">
          training site
        </span>
      </div>
      <div className="mt-5 grid gap-3 text-sm">
        <div className="flex items-center gap-2 text-slate-300">
          <Cpu size={16} className="text-signal-blue" />
          <span>{site.host ?? "configured host"}</span>
        </div>
        <div className="flex items-start gap-2 text-slate-400">
          <Cloud size={16} className="mt-0.5 text-signal-green" />
          <span>{site.role ?? "site role configured in backend"}</span>
        </div>
      </div>
    </Card>
  );
}

