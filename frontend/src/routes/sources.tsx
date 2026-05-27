import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Radio, RefreshCw } from "lucide-react";
import { SOURCES_LIST } from "@/lib/mock-data";
import { formatRelativeTime } from "@/lib/csv";
import { toast } from "sonner";

export const Route = createFileRoute("/sources")({
  head: () => ({ meta: [{ title: "Sources Monitor · ICICI SIOS" }] }),
  component: SourcesPage,
});

const TONE: Record<string, string> = {
  Healthy: "bg-success/10 text-success border-success/20",
  Degraded: "bg-warning/10 text-warning border-warning/20",
  Down: "bg-destructive/10 text-destructive border-destructive/20",
};

function SourcesPage() {
  return (
    <>
      <PageHeader
        title="Sources Monitor"
        description="Health, freshness and throughput of all data feeds powering the intelligence platform."
        actions={
          <Button variant="outline" onClick={() => toast.success("Health check triggered")} className="gap-1.5">
            <RefreshCw className="size-4" /> Run Health Check
          </Button>
        }
      />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {SOURCES_LIST.map((s) => (
          <div key={s.id} className="rounded-xl border border-border bg-card p-5 shadow-card">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="size-10 rounded-lg bg-accent grid place-items-center text-accent-foreground">
                  <Radio className="size-4" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm">{s.name}</h3>
                  <p className="text-xs text-muted-foreground">{s.type}</p>
                </div>
              </div>
              <Badge variant="outline" className={TONE[s.status]}>{s.status}</Badge>
            </div>
            <dl className="grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-border">
              <Stat label="Records (today)" value={s.recordsToday.toLocaleString()} />
              <Stat label="Uptime" value={`${s.uptime.toFixed(2)}%`} />
              <Stat label="Last sync" value={formatRelativeTime(s.lastSync)} />
            </dl>
          </div>
        ))}
      </div>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm font-semibold mt-0.5 tabular-nums">{value}</dd>
    </div>
  );
}
