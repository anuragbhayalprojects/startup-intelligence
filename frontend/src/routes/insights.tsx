import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Sparkles } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { INSIGHTS } from "@/lib/mock-data";
import { formatRelativeTime } from "@/lib/csv";

export const Route = createFileRoute("/insights")({
  head: () => ({ meta: [{ title: "AI Insights · ICICI SIOS" }] }),
  component: InsightsPage,
});

const TYPES = ["All", "Opportunity", "Risk", "Trend", "Match"] as const;

function InsightsPage() {
  const [filter, setFilter] = useState<(typeof TYPES)[number]>("All");
  const list = filter === "All" ? INSIGHTS : INSIGHTS.filter((i) => i.type === filter);

  return (
    <>
      <PageHeader
        title="AI Insights"
        description="Auto-generated intelligence signals across the tracked startup universe — opportunities, risks, trends and portfolio matches."
        actions={
          <Button className="gap-1.5">
            <Sparkles className="size-4" /> Run intelligence sweep
          </Button>
        }
      />
      <div className="flex gap-2 mb-4 flex-wrap">
        {TYPES.map((t) => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
              filter === t
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-card text-muted-foreground border-border hover:text-foreground"
            }`}
          >
            {t}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {list.map((i) => (
          <Link
            key={i.id}
            to="/startups/$id"
            params={{ id: i.startupId }}
            className="rounded-xl border border-border bg-card p-5 shadow-card hover:border-primary/40 hover:shadow-elegant transition-all"
          >
            <div className="flex items-center justify-between">
              <Badge variant="outline">{i.type}</Badge>
              <span className="text-xs text-muted-foreground">{formatRelativeTime(i.createdAt)}</span>
            </div>
            <h3 className="font-semibold text-sm mt-2">{i.title}</h3>
            <p className="text-xs text-muted-foreground mt-0.5">{i.startupName}</p>
            <p className="text-sm text-muted-foreground mt-3 leading-relaxed line-clamp-3">{i.summary}</p>
            <div className="mt-4 flex items-center gap-2">
              <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                <div className="h-full bg-primary" style={{ width: `${i.confidence}%` }} />
              </div>
              <span className="text-xs font-semibold tabular-nums">{i.confidence}%</span>
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}
