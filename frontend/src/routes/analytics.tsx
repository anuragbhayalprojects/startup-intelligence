import { createFileRoute } from "@tanstack/react-router";
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Radar, Legend, Line, LineChart,
} from "recharts";
import { PageHeader } from "@/components/PageHeader";
import {
  sectorDistribution, stageTrends, bfsiDistribution, STARTUPS,
} from "@/lib/mock-data";

export const Route = createFileRoute("/analytics")({
  head: () => ({ meta: [{ title: "Analytics · ICICI SIOS" }] }),
  component: AnalyticsPage,
});

const tooltipStyle = {
  background: "var(--popover)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontSize: 12,
  color: "var(--popover-foreground)",
};

function AnalyticsPage() {
  // 12 weeks of "discovery activity"
  const activity = Array.from({ length: 12 }, (_, i) => ({
    week: `W${i + 1}`,
    discovered: 20 + Math.round(Math.sin(i / 2) * 10 + Math.random() * 15),
    scored: 15 + Math.round(Math.cos(i / 2) * 8 + Math.random() * 12),
    engaged: 5 + Math.round(Math.random() * 8),
  }));

  // Radar of sector signals
  const radarData = sectorDistribution().slice(0, 6).map((s) => ({
    sector: s.name,
    coverage: s.value,
    bfsiFit: STARTUPS.filter((x) => x.sector === s.name).reduce((a, b) => a + b.bfsiScore, 0) / s.value,
  }));

  return (
    <>
      <PageHeader
        title="Analytics"
        description="Deep cross-sectional analytics on the tracked startup universe."
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="Discovery & Engagement (12 weeks)">
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={activity}>
              <defs>
                <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--chart-2)" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="var(--chart-2)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="week" stroke="var(--muted-foreground)" fontSize={11} />
              <YAxis stroke="var(--muted-foreground)" fontSize={11} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area type="monotone" dataKey="discovered" stroke="var(--chart-1)" fill="url(#g1)" strokeWidth={2} />
              <Area type="monotone" dataKey="scored" stroke="var(--chart-2)" fill="url(#g2)" strokeWidth={2} />
              <Area type="monotone" dataKey="engaged" stroke="var(--chart-3)" fill="none" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Sector Coverage vs BFSI Fit">
          <ResponsiveContainer width="100%" height={280}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="var(--border)" />
              <PolarAngleAxis dataKey="sector" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
              <PolarRadiusAxis tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
              <Radar name="Coverage" dataKey="coverage" stroke="var(--chart-1)" fill="var(--chart-1)" fillOpacity={0.3} />
              <Radar name="BFSI Fit" dataKey="bfsiFit" stroke="var(--chart-2)" fill="var(--chart-2)" fillOpacity={0.3} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Tooltip contentStyle={tooltipStyle} />
            </RadarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Funding Stage Distribution">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={stageTrends()}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="stage" stroke="var(--muted-foreground)" fontSize={11} />
              <YAxis stroke="var(--muted-foreground)" fontSize={11} />
              <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--muted)" }} />
              <Bar dataKey="count" fill="var(--chart-1)" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="BFSI Score Trajectory">
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={bfsiDistribution()}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="range" stroke="var(--muted-foreground)" fontSize={11} />
              <YAxis stroke="var(--muted-foreground)" fontSize={11} />
              <Tooltip contentStyle={tooltipStyle} />
              <Line type="monotone" dataKey="count" stroke="var(--chart-3)" strokeWidth={2.5} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-card">
      <h3 className="font-semibold text-sm mb-4">{title}</h3>
      {children}
    </div>
  );
}
