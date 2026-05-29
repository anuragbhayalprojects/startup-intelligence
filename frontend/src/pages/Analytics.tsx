import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, LineChart, Line, PieChart, Pie, Cell, Legend } from "recharts";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { fundingTrend, sectorBreakdown, geographyData, stageData } from "../data/mock";

const COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--primary)", "var(--muted-foreground)"];
const tooltipStyle = { background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 };

export default function Analytics() {
  return (
    <>
      <PageHeader title="Analytics" description="Deep cuts across funding, sectors, geography and stage distribution." />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SectionCard title="Funding Trend" description="$M raised per month (tracked)">
          <div className="h-72">
            <ResponsiveContainer>
              <LineChart data={fundingTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="month" stroke="var(--muted-foreground)" fontSize={12} />
                <YAxis stroke="var(--muted-foreground)" fontSize={12} />
                <Tooltip contentStyle={tooltipStyle} />
                <Line type="monotone" dataKey="amount" stroke="var(--primary)" strokeWidth={2} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>

        <SectionCard title="Sector Analytics" description="Share of startups by sector">
          <div className="h-72">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={sectorBreakdown} dataKey="value" nameKey="sector" outerRadius={90}>
                  {sectorBreakdown.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>

        <SectionCard title="Geography" description="Startup count by HQ country">
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={geographyData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis type="number" stroke="var(--muted-foreground)" fontSize={12} />
                <YAxis type="category" dataKey="geo" stroke="var(--muted-foreground)" fontSize={12} width={80} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="value" fill="var(--chart-2)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>

        <SectionCard title="Stage Distribution" description="Startups by funding stage">
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={stageData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="stage" stroke="var(--muted-foreground)" fontSize={12} />
                <YAxis stroke="var(--muted-foreground)" fontSize={12} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="count" fill="var(--primary)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>
      </div>
    </>
  );
}
