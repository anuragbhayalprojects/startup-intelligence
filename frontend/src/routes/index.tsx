import { createFileRoute } from "@tanstack/react-router";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Legend,
  FunnelChart,
  Funnel,
  LabelList,
} from "recharts";
import {
  Building2,
  TrendingUp,
  Users,
  Sparkles,
  ArrowUpRight,
} from "lucide-react";
import { Link } from "@tanstack/react-router";
import { PageHeader } from "@/components/PageHeader";
import { StatCard } from "@/components/StatCard";
import {
  STARTUPS,
  sectorDistribution,
  cityDistribution,
  stageTrends,
  bfsiDistribution,
  pipelineFunnel,
  INSIGHTS,
} from "@/lib/mock-data";
import { Button } from "@/components/ui/button";
import { ScorePill } from "@/components/ScorePill";
import { formatRelativeTime } from "@/lib/csv";
import { Badge } from "@/components/ui/badge";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [{ title: "Executive Dashboard · ICICI SIOS" }],
  }),
  component: Dashboard,
});

const CHART_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "var(--primary)",
  "var(--info)",
];

const tooltipStyle = {
  background: "var(--popover)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontSize: 12,
  color: "var(--popover-foreground)",
};

function Dashboard() {
  const totalStartups = STARTUPS.length;
  const highBfsi = STARTUPS.filter((s) => s.bfsiScore >= 75).length;
  const inPipeline = STARTUPS.filter((s) => s.status === "Pipeline" || s.status === "Engaged").length;
  const topInsights = INSIGHTS.slice(0, 5);
  const recentStartups = [...STARTUPS]
    .sort((a, b) => new Date(b.lastUpdated).getTime() - new Date(a.lastUpdated).getTime())
    .slice(0, 6);

  return (
    <>
      <PageHeader
        title="Executive Dashboard"
        description="Real-time intelligence on the startup ecosystem across BFSI, SaaS, AI, ClimateTech and more — curated for ICICI Group leadership."
        actions={
          <>
            <Button variant="outline">Last 30 days</Button>
            <Button className="gap-1.5">
              <Sparkles className="size-4" />
              Generate Brief
            </Button>
          </>
        }
      />

      {/* KPI cards */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Tracked Startups" value={totalStartups} delta={12} icon={Building2} hint="vs last month" />
        <StatCard label="High BFSI Relevance" value={highBfsi} delta={8} icon={TrendingUp} hint="score ≥ 75" />
        <StatCard label="Active in Pipeline" value={inPipeline} delta={-3} icon={Users} hint="engaged + pipeline" />
        <StatCard label="AI Insights (week)" value={INSIGHTS.length} delta={24} icon={Sparkles} hint="auto-generated" />
      </div>

      {/* Charts row 1 */}
      <div className="grid gap-4 grid-cols-1 lg:grid-cols-3 mt-4">
        <ChartCard title="Sector Distribution" subtitle="Across the tracked universe">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={sectorDistribution()}
                dataKey="value"
                nameKey="name"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={2}
              >
                {sectorDistribution().map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Top Cities" subtitle="Geographic concentration">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={cityDistribution().slice(0, 8)} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis type="number" stroke="var(--muted-foreground)" fontSize={11} />
              <YAxis dataKey="name" type="category" stroke="var(--muted-foreground)" fontSize={11} width={80} />
              <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--muted)" }} />
              <Bar dataKey="value" fill="var(--chart-1)" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="BFSI Relevance Distribution" subtitle="Scoring buckets">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={bfsiDistribution()}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="range" stroke="var(--muted-foreground)" fontSize={11} />
              <YAxis stroke="var(--muted-foreground)" fontSize={11} />
              <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--muted)" }} />
              <Bar dataKey="count" fill="var(--chart-3)" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Charts row 2 */}
      <div className="grid gap-4 grid-cols-1 lg:grid-cols-3 mt-4">
        <ChartCard
          title="Funding Stage Trends"
          subtitle="Count & avg funding by stage"
          className="lg:col-span-2"
        >
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={stageTrends()}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="stage" stroke="var(--muted-foreground)" fontSize={11} />
              <YAxis yAxisId="left" stroke="var(--muted-foreground)" fontSize={11} />
              <YAxis yAxisId="right" orientation="right" stroke="var(--muted-foreground)" fontSize={11} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line yAxisId="left" type="monotone" dataKey="count" stroke="var(--chart-1)" strokeWidth={2} dot={{ r: 4 }} />
              <Line yAxisId="right" type="monotone" dataKey="avgFunding" name="Avg Funding ($M)" stroke="var(--chart-2)" strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Pipeline Funnel" subtitle="Conversion across stages">
          <ResponsiveContainer width="100%" height={280}>
            <FunnelChart>
              <Tooltip contentStyle={tooltipStyle} />
              <Funnel dataKey="count" data={pipelineFunnel()} isAnimationActive>
                {pipelineFunnel().map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
                <LabelList position="right" fill="var(--foreground)" stroke="none" dataKey="stage" style={{ fontSize: 11 }} />
              </Funnel>
            </FunnelChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Below grids: AI Insights + recent activity */}
      <div className="grid gap-4 grid-cols-1 lg:grid-cols-5 mt-4">
        <div className="rounded-xl border border-border bg-card p-5 shadow-card lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold">Top AI Insights</h3>
              <p className="text-xs text-muted-foreground">Highest-confidence signals this week</p>
            </div>
            <Link to="/insights" className="text-xs text-primary hover:underline inline-flex items-center gap-0.5">
              View all <ArrowUpRight className="size-3" />
            </Link>
          </div>
          <div className="space-y-3">
            {topInsights.map((i) => (
              <Link
                key={i.id}
                to="/startups/$id"
                params={{ id: i.startupId }}
                className="block rounded-lg border border-border p-3 hover:border-primary/40 hover:bg-accent/40 transition-colors"
              >
                <div className="flex items-center justify-between gap-2">
                  <Badge variant="outline" className="text-[10px]">
                    {i.type}
                  </Badge>
                  <span className="text-[11px] text-muted-foreground">{i.confidence}% conf.</span>
                </div>
                <div className="font-medium text-sm mt-1.5">{i.title}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{i.startupName}</div>
              </Link>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-5 shadow-card lg:col-span-3">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold">Recently Updated</h3>
              <p className="text-xs text-muted-foreground">Fresh signals across the universe</p>
            </div>
            <Link to="/startups" className="text-xs text-primary hover:underline inline-flex items-center gap-0.5">
              Explore all <ArrowUpRight className="size-3" />
            </Link>
          </div>
          <div className="divide-y divide-border">
            {recentStartups.map((s) => (
              <Link
                key={s.id}
                to="/startups/$id"
                params={{ id: s.id }}
                className="grid grid-cols-12 gap-2 items-center py-3 hover:bg-accent/30 rounded-md px-2 -mx-2 transition-colors"
              >
                <div className="col-span-4 font-medium text-sm truncate">{s.name}</div>
                <div className="col-span-3 text-xs text-muted-foreground truncate">{s.sector} · {s.subsector}</div>
                <div className="col-span-2 text-xs text-muted-foreground">{s.city}</div>
                <div className="col-span-1"><ScorePill value={s.bfsiScore} /></div>
                <div className="col-span-2 text-xs text-muted-foreground text-right">
                  {formatRelativeTime(s.lastUpdated)}
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

function ChartCard({
  title,
  subtitle,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-xl border border-border bg-card p-5 shadow-card ${className}`}>
      <div className="mb-3">
        <h3 className="font-semibold text-sm">{title}</h3>
        {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}
