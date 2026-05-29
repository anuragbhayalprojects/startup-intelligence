import { Link } from "react-router-dom";
import {
  Building2,
  DollarSign,
  Target,
  Sparkles,
  ArrowUpRight,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Info,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { PageHeader } from "../components/PageHeader";
import { KpiCard } from "../components/KpiCard";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import {
  startups,
  fundingTrend,
  sectorBreakdown,
  aiInsights,
  opportunities,
} from "../data/mock";
import { formatUSD } from "../lib/format";

const COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--primary)", "var(--muted-foreground)"];

export default function Dashboard() {
  const totalFunding = startups.reduce((s, x) => s + x.totalFunding, 0);
  const avgFit = Math.round(startups.reduce((s, x) => s + x.iciciFitScore, 0) / startups.length);
  const recent = [...startups].sort((a, b) => b.lastRound.date.localeCompare(a.lastRound.date)).slice(0, 5);

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Live BFSI startup intelligence across funding, sectors, and ICICI strategic fit."
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Tracked Startups" value={startups.length.toString()} delta={12} icon={Building2} />
        <KpiCard label="Total Funding (tracked)" value={formatUSD(totalFunding)} delta={8} icon={DollarSign} />
        <KpiCard label="Avg ICICI Fit Score" value={`${avgFit}/100`} delta={4} icon={Target} />
        <KpiCard label="AI Insights this week" value="23" delta={-3} icon={Sparkles} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        <SectionCard title="Funding Trend" description="Total disclosed funding ($M, last 7 months)" className="lg:col-span-2">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={fundingTrend}>
                <defs>
                  <linearGradient id="fund" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="month" stroke="var(--muted-foreground)" fontSize={12} />
                <YAxis stroke="var(--muted-foreground)" fontSize={12} />
                <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
                <Area type="monotone" dataKey="amount" stroke="var(--primary)" strokeWidth={2} fill="url(#fund)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>

        <SectionCard title="Sector Breakdown" description="Share of tracked BFSI startups">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={sectorBreakdown} dataKey="value" nameKey="sector" innerRadius={45} outerRadius={75} paddingAngle={2}>
                  {sectorBreakdown.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        <SectionCard
          title="Recent Startups"
          description="Most recent funding events"
          className="lg:col-span-2"
          action={
            <Link to="/startups" className="text-xs text-primary hover:underline inline-flex items-center gap-1">
              View all <ArrowUpRight className="h-3 w-3" />
            </Link>
          }
        >
          <div className="divide-y divide-border -m-5 mt-0">
            {recent.map((s) => (
              <Link
                key={s.id}
                to={`/startups/${s.id}`}
                className="flex items-center gap-3 px-5 py-3 hover:bg-muted/40 transition-colors"
              >
                <div className="h-9 w-9 rounded-md bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">
                  {s.logo}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{s.name}</div>
                  <div className="text-xs text-muted-foreground truncate">{s.sector} · {s.hq}</div>
                </div>
                <div className="text-right hidden sm:block">
                  <div className="text-sm font-medium">{formatUSD(s.lastRound.amount)}</div>
                  <div className="text-[11px] text-muted-foreground">{s.lastRound.type}</div>
                </div>
                <StatusBadge tone="info">{s.iciciFitScore} fit</StatusBadge>
              </Link>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="AI Insights" description="Generated by Intel OS">
          <div className="space-y-3">
            {aiInsights.map((i) => {
              const Icon = i.severity === "warning" ? AlertCircle : i.severity === "success" ? CheckCircle2 : Info;
              const tone =
                i.severity === "warning" ? "text-warning-foreground bg-warning/20" :
                i.severity === "success" ? "text-success bg-success/15" :
                "text-info bg-info/15";
              return (
                <div key={i.id} className="rounded-md border border-border p-3">
                  <div className="flex items-start gap-2">
                    <div className={`h-7 w-7 rounded-md flex items-center justify-center shrink-0 ${tone}`}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="text-sm font-medium leading-tight">{i.title}</div>
                      <div className="text-xs text-muted-foreground mt-1">{i.body}</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Top Opportunities" description="AI-ranked engagements for the ICICI team" className="mt-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {opportunities.map((o) => (
            <div key={o.id} className="rounded-md border border-border p-4 hover:border-primary/40 transition-colors">
              <div className="flex items-start justify-between">
                <StatusBadge tone="default">{o.owner}</StatusBadge>
                <span className="text-xs font-semibold text-primary">{o.confidence}%</span>
              </div>
              <div className="text-sm font-medium mt-3">{o.title}</div>
              <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                <TrendingUp className="h-3 w-3" /> {o.value}
              </div>
            </div>
          ))}
        </div>
      </SectionCard>
    </>
  );
}
