import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { ASSIGNMENTS } from "@/lib/mock-data";
import { formatRelativeTime } from "@/lib/csv";
import { toast } from "sonner";

export const Route = createFileRoute("/assignments")({
  head: () => ({ meta: [{ title: "Assignments · ICICI SIOS" }] }),
  component: AssignmentsPage,
});

const STATUSES = ["All", "Open", "In Progress", "Blocked", "Done"] as const;
const PRIORITY_TONE: Record<string, string> = {
  Low: "bg-muted text-muted-foreground",
  Medium: "bg-info/10 text-info border-info/20",
  High: "bg-warning/10 text-warning border-warning/20",
  Critical: "bg-destructive/10 text-destructive border-destructive/20",
};

const STATUS_TONE: Record<string, string> = {
  Open: "bg-muted text-muted-foreground",
  "In Progress": "bg-info/10 text-info border-info/20",
  Blocked: "bg-destructive/10 text-destructive border-destructive/20",
  Done: "bg-success/10 text-success border-success/20",
};

function AssignmentsPage() {
  const [status, setStatus] = useState<(typeof STATUSES)[number]>("All");
  const rows = status === "All" ? ASSIGNMENTS : ASSIGNMENTS.filter((a) => a.status === status);

  return (
    <>
      <PageHeader
        title="Assignments"
        description="Track ownership and progress on startups under active review across teams."
        actions={
          <>
            <Select value={status} onValueChange={(v) => setStatus(v as typeof status)}>
              <SelectTrigger className="w-[160px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                {STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={() => toast.success("Assignment created")}>+ New Assignment</Button>
          </>
        }
      />
      <div className="rounded-xl border border-border bg-card overflow-hidden shadow-card">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead>Startup</TableHead>
              <TableHead>Assignee</TableHead>
              <TableHead>Team</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Due</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((a) => (
              <TableRow key={a.id}>
                <TableCell>
                  <Link to="/startups/$id" params={{ id: a.startupId }} className="font-medium hover:text-primary">
                    {a.startupName}
                  </Link>
                </TableCell>
                <TableCell className="text-muted-foreground">{a.assignee}</TableCell>
                <TableCell className="text-muted-foreground">{a.team}</TableCell>
                <TableCell>
                  <Badge variant="outline" className={PRIORITY_TONE[a.priority]}>{a.priority}</Badge>
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className={STATUS_TONE[a.status]}>{a.status}</Badge>
                </TableCell>
                <TableCell className="text-muted-foreground whitespace-nowrap">
                  {new Date(a.dueDate).toLocaleDateString()}
                </TableCell>
                <TableCell className="text-muted-foreground whitespace-nowrap">
                  {formatRelativeTime(a.createdAt)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </>
  );
}
