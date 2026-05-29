import { Database } from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge, statusTone } from "../components/StatusBadge";
import { sources } from "../data/mock";

export default function Sources() {
  return (
    <>
      <PageHeader title="Sources" description="Connected pipelines feeding the Intelligence OS." />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {sources.map((s) => (
          <SectionCard key={s.id}>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-md bg-primary/10 text-primary flex items-center justify-center">
                  <Database className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-sm font-semibold">{s.name}</div>
                  <div className="text-xs text-muted-foreground">{s.type}</div>
                </div>
              </div>
              <StatusBadge tone={statusTone(s.status)}>{s.status}</StatusBadge>
            </div>

            <div className="grid grid-cols-3 gap-2 mt-5 pt-4 border-t border-border">
              <Stat label="Startups" value={s.startupCount.toLocaleString()} />
              <Stat label="Success" value={`${s.successRate}%`} />
              <Stat label="Last scrape" value={s.lastScrape.split(" ")[1]} />
            </div>
          </SectionCard>
        ))}
      </div>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[11px] text-muted-foreground uppercase tracking-wide">{label}</div>
      <div className="text-sm font-medium mt-0.5">{value}</div>
    </div>
  );
}
