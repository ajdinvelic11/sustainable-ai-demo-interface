import { MapPin, Server } from "lucide-react";

import type { SiteInfo } from "../types/api";
import StatusPill from "./StatusPill";
import Card from "./ui/Card";

export default function SiteCard({ site }: { site: SiteInfo }) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-lg bg-slate-800 text-cyan-300">
            <MapPin className="h-5 w-5" />
          </span>
          <div>
            <h3 className="font-semibold text-white">{site.location_name}</h3>
            <p className="text-sm text-slate-400">{site.region_code}</p>
          </div>
        </div>
        <StatusPill status={site.status} />
      </div>
      <div className="mt-5 space-y-3 text-sm">
        <div className="flex items-center gap-2 text-slate-300">
          <Server className="h-4 w-4 text-slate-500" />
          {site.host_label}
        </div>
        <p className="leading-6 text-slate-400">{site.role}</p>
      </div>
    </Card>
  );
}
