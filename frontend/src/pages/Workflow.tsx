import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge, statusTone } from "../components/StatusBadge";
import { workflowJobs } from "../data/mock";
import { Activity, CheckCircle2, Loader2, AlertTriangle, Clock } from "lucide-react";

const icons = {
  Running: Loader2,
  Completed: CheckCircle2,
  Queued: Clock,
  Failed: AlertTriangle,
};

export default function Workflow() {
  const summary = {
    running: workflowJobs.filter((j) => j.status === "Running").length,
    queued: workflowJobs.filter((j) => j.status === "Queued").length,
    completed: workflowJobs.filter((j) => j.status === "Completed").length,
    failed: workflowJobs.filter((j) => j.status === "Failed").length,
  };

  return (
    <>
      <PageHeader title="Workflow" description="AI processing queue and pipeline automation." />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <SummaryCard label="Running" value={summary.running} tone="default" icon={Loader2} />
        <SummaryCard label="Queued" value={summary.queued} tone="info" icon={Clock} />
        <SummaryCard label="Completed" value={summary.completed} tone="success" icon={CheckCircle2} />
        <SummaryCard label="Failed" value={summary.failed} tone="destructive" icon={AlertTriangle} />
      </div>

      <SectionCard title="Active Jobs" description="Real-time pipeline activity">
        <div className="space-y-3">
          {workflowJobs.map((j) => {
            const Icon = icons[j.status];
            return (
              <div key={j.id} className="rounded-md border border-border p-4">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-md bg-muted text-muted-foreground flex items-center justify-center">
                    <Icon className={`h-4 w-4 ${j.status === "Running" ? "animate-spin text-primary" : ""}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <div className="text-sm font-medium truncate">{j.name}</div>
                      <StatusBadge tone="muted">{j.stage}</StatusBadge>
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">Started {j.startedAt}</div>
                  </div>
                  <StatusBadge tone={statusTone(j.status)}>{j.status}</StatusBadge>
                </div>
                <div className="mt-3 h-1.5 rounded-full bg-muted overflow-hidden">
                  <div
                    className={`h-full ${j.status === "Failed" ? "bg-destructive" : "bg-primary"}`}
                    style={{ width: `${j.progress}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </SectionCard>

      <SectionCard title="Automation Monitor" description="Pipeline health (24h)" className="mt-4">
        <div className="flex items-center gap-3 text-sm">
          <Activity className="h-4 w-4 text-success" />
          All pipelines operational · 98.4% success rate · avg latency 412ms
        </div>
      </SectionCard>
    </>
  );
}

function SummaryCard({ label, value, tone, icon: Icon }: { label: string; value: number; tone: "default" | "success" | "info" | "destructive"; icon: typeof Loader2 }) {
  const toneClass = {
    default: "bg-primary/10 text-primary",
    success: "bg-success/15 text-success",
    info: "bg-info/15 text-info",
    destructive: "bg-destructive/15 text-destructive",
  }[tone];
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs text-muted-foreground uppercase tracking-wide">{label}</div>
          <div className="text-2xl font-semibold mt-1">{value}</div>
        </div>
        <div className={`h-8 w-8 rounded-md flex items-center justify-center ${toneClass}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
    </div>
  );
}
