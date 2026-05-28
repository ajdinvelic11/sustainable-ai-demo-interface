import type { SiteInfo } from "../types/api";
import SiteCard from "./SiteCard";
import Card from "./ui/card";

interface SiteStatusCardsProps {
  sites: SiteInfo[];
  loading?: boolean;
}

export default function SiteStatusCards({ sites, loading = false }: SiteStatusCardsProps) {
  if (loading) {
    return (
      <>
        <Card className="h-48 animate-pulse" />
        <Card className="h-48 animate-pulse" />
        <Card className="h-48 animate-pulse" />
      </>
    );
  }

  return (
    <>
      {sites.map((site) => (
        <SiteCard key={site.region_code} site={site} />
      ))}
    </>
  );
}
