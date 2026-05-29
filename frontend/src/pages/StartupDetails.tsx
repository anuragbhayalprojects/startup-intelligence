import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Globe, Users, Calendar, MapPin, DollarSign, Linkedin, Sparkles } from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { startups } from "../data/mock";
import { formatUSD } from "../lib/format";

export default function StartupDetails() {
  const { id } = useParams<{ id: string }>();
  const s = startups.find((x) => x.id === id);

  if (!s) {
    return (
      <div className="text-center py-20">
        <h2 className="text-lg font-semibold">Startup not found</h2>
        <Link to="/startups" className="text-sm text-primary mt-2 inline-block">← Back to startups</Link>
      </div>
    );
  }

  return (
    <>
      <Link to="/startups" className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1 mb-4">
        <ArrowLeft className="h-3 w-3" /> Back to startups
      </Link>

      <PageHeader
        title={s.name}
        description={s.description}
        action={
          <div className="flex items-center gap-2">
            <StatusBadge tone="muted">{s.stage}</StatusBadge>
            <a href={s.website} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 h-9 px-3 rounded-md border border-border text-sm hover:bg-muted">
              <Globe className="h-4 w-4" /> Website
            </a>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <SectionCard className="lg:col-span-2">
          <div className="flex items-center gap-4">
            <div className="h-16 w-16 rounded-lg bg-primary/10 text-primary text-xl font-bold flex items-center justify-center">{s.logo}</div>
            <div className="flex-1">
              <div className="text-lg font-semibold">{s.name}</div>
              <div className="text-sm text-muted-foreground">{s.sector} · {s.subSector}</div>
              <div className="flex flex-wrap gap-1 mt-2">
                {s.tags.map((t) => <StatusBadge key={t} tone="muted">{t}</StatusBadge>)}
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-border">
            <Stat icon={MapPin} label="HQ" value={`${s.hq}, ${s.country}`} />
            <Stat icon={Calendar} label="Founded" value={s.founded.toString()} />
            <Stat icon={Users} label="Employees" value={s.employees.toString()} />
            <Stat icon={DollarSign} label="Total Funding" value={formatUSD(s.totalFunding)} />
          </div>
        </SectionCard>

        <SectionCard title="ICICI Relevance">
          <div className="space-y-4">
            <Meter label="BFSI Relevance" value={s.bfsiRelevance} />
            <Meter label="ICICI Fit Score" value={s.iciciFitScore} />
            <div className="rounded-md bg-accent/40 p-3">
              <div className="flex items-start gap-2">
                <Sparkles className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <p className="text-xs text-foreground/80">{s.aiInsight}</p>
              </div>
            </div>
          </div>
        </SectionCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        <SectionCard title="BFSI Analysis" className="lg:col-span-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {s.useCases.map((u) => (
              <div key={u} className="rounded-md border border-border p-3">
                <div className="text-xs text-muted-foreground">Use case</div>
                <div className="text-sm font-medium mt-1">{u}</div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Funding Details">
          <div className="text-xs text-muted-foreground">Last round</div>
          <div className="text-lg font-semibold mt-1">{formatUSD(s.lastRound.amount)} <span className="text-sm font-normal text-muted-foreground">· {s.lastRound.type}</span></div>
          <div className="text-xs text-muted-foreground mt-1">{s.lastRound.date} · Led by {s.lastRound.leadInvestor}</div>
          <div className="mt-4 pt-4 border-t border-border">
            <div className="text-xs text-muted-foreground mb-2">Investors</div>
            <div className="flex flex-wrap gap-1">
              {s.investors.map((inv) => <StatusBadge key={inv} tone="info">{inv}</StatusBadge>)}
            </div>
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Founders" className="mt-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {s.founders.map((f) => (
            <div key={f.name} className="flex items-center gap-3 rounded-md border border-border p-3">
              <div className="h-10 w-10 rounded-full bg-primary/10 text-primary text-xs font-semibold flex items-center justify-center">
                {f.name.split(" ").map((n) => n[0]).join("")}
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium">{f.name}</div>
                <div className="text-xs text-muted-foreground">{f.role}</div>
              </div>
              <a href={f.linkedin} className="text-muted-foreground hover:text-primary"><Linkedin className="h-4 w-4" /></a>
            </div>
          ))}
        </div>
      </SectionCard>
    </>
  );
}

function Stat({ icon: Icon, label, value }: { icon: typeof Globe; label: string; value: string }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground"><Icon className="h-3 w-3" /> {label}</div>
      <div className="text-sm font-medium mt-1">{value}</div>
    </div>
  );
}

function Meter({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-semibold">{value}/100</span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div className="h-full bg-primary" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}
