import { createFileRoute } from "@tanstack/react-router";
import { CheckCircle2, AlertTriangle, Loader2, Clock } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { WORKFLOWS } from "@/lib/mock-data";
import { StatCard } from "@/components/StatCard";
import { formatRelativeTime } from "@/lib/csv";

export const Route = createFileRoute("/workflow")({
  head: () => ({ meta: [{ title: "Workflow Monitor · ICICI SIOS" }] }),
  component: WorkflowPage,
});

const STATUS_ICON = {
  Success: <CheckCircle2 className="size-4 text-success" />,
  Running: <Loader2 className="size-4 text-info animate-spin" />,
  Failed: <AlertTriangle className="size-4 text-destructive" />,
  Queued: <Clock className="size-4 text-muted-foreground" />,
};

const STATUS_TONE: Record<string, string> = {
  Success: "bg-success/10 text-success border-success/20",
  Running: "bg-info/10 text-info border-info/20",
  Failed: "bg-destructive/10 text-destructive border-destructive/20",
  Queued: "bg-muted text-muted-foreground",
};

function WorkflowPage() {
  const total = WORKFLOWS.length;
  const success = WORKFLOWS.filter((w) => w.status === "Success").length;
  const failed = WORKFLOWS.filter((w) => w.status === "Failed").length;
  const running = WORKFLOWS.filter((w) => w.status === "Running").length;

  return (
    <>
      <PageHeader
        title="Workflow Monitor"
        description="Live monitoring of ingestion, scoring, enrichment and export pipelines."
      />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Runs" value={total} icon={Clock} />
        <StatCard label="Successful" value={success} delta={5} icon={CheckCircle2} />
        <StatCard label="Running" value={running} icon={Loader2} />
        <StatCard label="Failed" value={failed} delta={-12} icon={AlertTriangle} />
      </div>
      <div className="rounded-xl border border-border bg-card overflow-hidden shadow-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Workflow</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Records</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead>Started</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {WORKFLOWS.map((w) => (
              <TableRow key={w.id}>
                <TableCell className="font-medium">{w.name}</TableCell>
                <TableCell><Badge variant="secondary">{w.type}</Badge></TableCell>
                <TableCell>
                  <div className="flex items-center gap-1.5">
                    {STATUS_ICON[w.status]}
                    <Badge variant="outline" className={STATUS_TONE[w.status]}>{w.status}</Badge>
                  </div>
                </TableCell>
                <TableCell className="tabular-nums">{w.recordsProcessed.toLocaleString()}</TableCell>
                <TableCell className="tabular-nums text-muted-foreground">{(w.durationMs / 1000).toFixed(1)}s</TableCell>
                <TableCell className="text-muted-foreground">{formatRelativeTime(w.startedAt)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </>
  );
}
