import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import {
  ArrowLeft,
  Globe,
  Users,
  Calendar,
  DollarSign,
  Bookmark,
  BookmarkCheck,
  Sparkles,
  FileText,
  TrendingUp,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScorePill } from "@/components/ScorePill";
import { getStartupById, getActivityForStartup, INSIGHTS } from "@/lib/mock-data";
import { formatCurrency, formatRelativeTime } from "@/lib/csv";
import { useSavedStartups } from "@/store/saved-startups";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export const Route = createFileRoute("/startups/$id")({
  head: ({ params }) => ({
    meta: [{ title: `Startup · ${params.id} · ICICI SIOS` }],
  }),
  loader: ({ params }) => {
    const s = getStartupById(params.id);
    if (!s) throw notFound();
    return s as NonNullable<typeof s>;
  },
  component: StartupDetail,
});

function StartupDetail() {
  const s = Route.useLoaderData() as import("@/types").Startup;
  const activity = getActivityForStartup(s.id);
  const insights = INSIGHTS.filter((i) => i.startupId === s.id);
  const { isSaved, toggle } = useSavedStartups();
  const saved = isSaved(s.id);
  const [assignOpen, setAssignOpen] = useState(false);

  return (
    <>
      <Link
        to="/startups"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4"
      >
        <ArrowLeft className="size-4" /> Back to Explorer
      </Link>

      <PageHeader
        title={s.name}
        description={s.description}
        actions={
          <>
            <Button
              variant="outline"
              onClick={() => {
                toggle(s.id);
                toast.success(saved ? "Removed from saved" : "Saved startup");
              }}
              className="gap-1.5"
            >
              {saved ? <BookmarkCheck className="size-4 text-primary" /> : <Bookmark className="size-4" />}
              {saved ? "Saved" : "Save"}
            </Button>
            <Dialog open={assignOpen} onOpenChange={setAssignOpen}>
              <DialogTrigger asChild>
                <Button className="gap-1.5">
                  <Users className="size-4" /> Assign
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Assign {s.name}</DialogTitle>
                  <DialogDescription>
                    Route this startup to a team or individual for review.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-3 py-2">
                  <Select defaultValue="Ventures Team">
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {["Ventures Team", "Innovation Lab", "Corporate Strategy", "Digital Banking", "Wealth Group"].map(t => (
                        <SelectItem key={t} value={t}>{t}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select defaultValue="High">
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {["Low", "Medium", "High", "Critical"].map(p => (
                        <SelectItem key={p} value={p}>{p} priority</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setAssignOpen(false)}>Cancel</Button>
                  <Button onClick={() => { setAssignOpen(false); toast.success("Assignment created"); }}>
                    Create Assignment
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </>
        }
      />

      {/* Meta cards */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3 mb-6">
        <MetaCard icon={Globe} label="Sector" value={s.sector} />
        <MetaCard icon={TrendingUp} label="Stage" value={s.fundingStage} />
        <MetaCard icon={Users} label="Employees" value={s.employees.toString()} />
        <MetaCard icon={Calendar} label="Founded" value={s.founded.toString()} />
        <MetaCard icon={DollarSign} label="Total Funding" value={formatCurrency(s.totalFundingUSD)} />
        <MetaCard icon={Globe} label="HQ" value={s.city} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <Tabs defaultValue="overview">
            <TabsList>
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="insights">AI Insights ({insights.length})</TabsTrigger>
              <TabsTrigger value="activity">Activity</TabsTrigger>
            </TabsList>
            <TabsContent value="overview" className="mt-4">
              <div className="rounded-xl border border-border bg-card p-6 shadow-card space-y-5">
                <Section title="About">
                  <p className="text-sm text-muted-foreground leading-relaxed">{s.description}</p>
                </Section>
                <Section title="Founders">
                  <div className="flex flex-wrap gap-2">
                    {s.founders.map((f) => (
                      <Badge key={f} variant="secondary">{f}</Badge>
                    ))}
                  </div>
                </Section>
                <Section title="Tags">
                  <div className="flex flex-wrap gap-1.5">
                    {s.tags.map((t) => (
                      <Badge key={t} variant="outline">{t}</Badge>
                    ))}
                  </div>
                </Section>
                <Section title="Website">
                  <a href={s.website} className="text-sm text-primary hover:underline">{s.website}</a>
                </Section>
              </div>
            </TabsContent>
            <TabsContent value="insights" className="mt-4 space-y-3">
              {insights.length === 0 ? (
                <div className="rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
                  No AI insights generated yet for this startup.
                </div>
              ) : (
                insights.map((i) => (
                  <div key={i.id} className="rounded-xl border border-border bg-card p-5 shadow-card">
                    <div className="flex items-center justify-between mb-1">
                      <Badge variant="outline">{i.type}</Badge>
                      <span className="text-xs text-muted-foreground">{i.confidence}% confidence</span>
                    </div>
                    <h4 className="font-semibold text-sm mt-1">{i.title}</h4>
                    <p className="text-sm text-muted-foreground mt-1.5">{i.summary}</p>
                  </div>
                ))
              )}
            </TabsContent>
            <TabsContent value="activity" className="mt-4">
              <div className="rounded-xl border border-border bg-card p-5 shadow-card">
                <ol className="relative border-l border-border ml-3 space-y-5">
                  {activity.map((a) => (
                    <li key={a.id} className="ml-5">
                      <span className="absolute -left-1.5 mt-1.5 size-3 rounded-full bg-primary ring-4 ring-card" />
                      <div className="flex items-center justify-between">
                        <div className="text-sm font-medium">{a.actor}</div>
                        <div className="text-xs text-muted-foreground">{formatRelativeTime(a.at)}</div>
                      </div>
                      <p className="text-sm text-muted-foreground mt-0.5">{a.message}</p>
                    </li>
                  ))}
                </ol>
              </div>
            </TabsContent>
          </Tabs>
        </div>

        <aside className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-5 shadow-card">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-1.5">
              <Sparkles className="size-4 text-primary" /> Scoring
            </h3>
            <div className="space-y-3">
              <ScoreRow label="BFSI Relevance" value={s.bfsiScore} />
              <ScoreRow label="Priority Score" value={s.priorityScore} />
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-5 shadow-card">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-1.5">
              <FileText className="size-4 text-primary" /> Workflow
            </h3>
            <dl className="text-sm space-y-2">
              <Row k="Status" v={<Badge variant="secondary">{s.status}</Badge>} />
              <Row k="Assigned Team" v={s.assignedTeam} />
              <Row k="Source" v={s.source} />
              <Row k="Last Updated" v={formatRelativeTime(s.lastUpdated)} />
            </dl>
          </div>
        </aside>
      </div>
    </>
  );
}

function MetaCard({ icon: Icon, label, value }: { icon: typeof Globe; label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-card">
      <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-muted-foreground">
        <Icon className="size-3.5" />
        {label}
      </div>
      <div className="mt-1.5 font-semibold text-sm">{value}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">{title}</div>
      {children}
    </div>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className="font-medium text-right">{v}</dd>
    </div>
  );
}

function ScoreRow({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-muted-foreground">{label}</span>
        <ScorePill value={value} />
      </div>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full bg-primary rounded-full transition-all"
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}
