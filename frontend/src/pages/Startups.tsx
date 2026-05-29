import { Link } from "react-router-dom";
import { useMemo, useState } from "react";
import { Download, ArrowUpDown, Search } from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { startups } from "../data/mock";
import { formatUSD, exportToCsv } from "../lib/format";

type SortKey = "name" | "sector" | "stage" | "totalFunding" | "iciciFitScore";
const PAGE_SIZE = 8;

export default function Startups() {
  const [q, setQ] = useState("");
  const [sector, setSector] = useState("All");
  const [stage, setStage] = useState("All");
  const [page, setPage] = useState(1);
  const [sortKey, setSortKey] = useState<SortKey>("iciciFitScore");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const sectors = ["All", ...Array.from(new Set(startups.map((s) => s.sector)))];
  const stages = ["All", ...Array.from(new Set(startups.map((s) => s.stage)))];

  const filtered = useMemo(() => {
    let list = startups.filter((s) => {
      const matchQ = !q || `${s.name} ${s.sector} ${s.hq} ${s.tags.join(" ")}`.toLowerCase().includes(q.toLowerCase());
      const matchS = sector === "All" || s.sector === sector;
      const matchSt = stage === "All" || s.stage === stage;
      return matchQ && matchS && matchSt;
    });
    list = [...list].sort((a, b) => {
      const av = a[sortKey] as number | string;
      const bv = b[sortKey] as number | string;
      if (typeof av === "number" && typeof bv === "number") {
        return sortDir === "asc" ? av - bv : bv - av;
      }
      return sortDir === "asc" ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
    });
    return list;
  }, [q, sector, stage, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageItems = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const toggleSort = (k: SortKey) => {
    if (sortKey === k) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(k); setSortDir("desc"); }
  };

  const handleExport = () => {
    exportToCsv("startups.csv", filtered.map((s) => ({
      name: s.name, sector: s.sector, stage: s.stage, hq: s.hq,
      totalFunding: s.totalFunding, iciciFitScore: s.iciciFitScore, founded: s.founded,
    })));
  };

  return (
    <>
      <PageHeader
        title="Startups"
        description={`${filtered.length} BFSI startups matched`}
        action={
          <button onClick={handleExport} className="inline-flex items-center gap-2 h-9 px-3 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90">
            <Download className="h-4 w-4" /> Export CSV
          </button>
        }
      />

      <SectionCard>
        <div className="flex flex-col md:flex-row gap-2 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              value={q}
              onChange={(e) => { setQ(e.target.value); setPage(1); }}
              placeholder="Search by name, sector, HQ, tag..."
              className="w-full h-9 rounded-md border border-border bg-background pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring/40"
            />
          </div>
          <select value={sector} onChange={(e) => { setSector(e.target.value); setPage(1); }} className="h-9 rounded-md border border-border bg-background px-3 text-sm">
            {sectors.map((s) => <option key={s}>{s}</option>)}
          </select>
          <select value={stage} onChange={(e) => { setStage(e.target.value); setPage(1); }} className="h-9 rounded-md border border-border bg-background px-3 text-sm">
            {stages.map((s) => <option key={s}>{s}</option>)}
          </select>
        </div>

        <div className="overflow-x-auto -mx-5">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-muted-foreground border-b border-border">
                <Th onClick={() => toggleSort("name")}>Startup</Th>
                <Th onClick={() => toggleSort("sector")}>Sector</Th>
                <Th onClick={() => toggleSort("stage")}>Stage</Th>
                <th className="px-5 py-3 font-medium">HQ</th>
                <Th onClick={() => toggleSort("totalFunding")} align="right">Total Funding</Th>
                <Th onClick={() => toggleSort("iciciFitScore")} align="right">ICICI Fit</Th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody>
              {pageItems.map((s) => (
                <tr key={s.id} className="border-b border-border hover:bg-muted/30 transition-colors">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-md bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">{s.logo}</div>
                      <div>
                        <div className="font-medium">{s.name}</div>
                        <div className="text-xs text-muted-foreground truncate max-w-xs">{s.description}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-3">{s.sector}</td>
                  <td className="px-5 py-3"><StatusBadge tone="muted">{s.stage}</StatusBadge></td>
                  <td className="px-5 py-3 text-muted-foreground">{s.hq}</td>
                  <td className="px-5 py-3 text-right font-medium">{formatUSD(s.totalFunding)}</td>
                  <td className="px-5 py-3 text-right">
                    <span className={`font-semibold ${s.iciciFitScore >= 85 ? "text-success" : s.iciciFitScore >= 75 ? "text-info" : "text-muted-foreground"}`}>
                      {s.iciciFitScore}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right">
                    <Link to={`/startups/${s.id}`} className="text-xs text-primary hover:underline">View</Link>
                  </td>
                </tr>
              ))}
              {pageItems.length === 0 && (
                <tr><td colSpan={7} className="px-5 py-12 text-center text-sm text-muted-foreground">No startups match your filters.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between mt-4 text-xs text-muted-foreground">
          <div>Page {safePage} of {totalPages}</div>
          <div className="flex gap-2">
            <button disabled={safePage === 1} onClick={() => setPage((p) => Math.max(1, p - 1))} className="h-8 px-3 rounded-md border border-border disabled:opacity-40 hover:bg-muted">Previous</button>
            <button disabled={safePage === totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))} className="h-8 px-3 rounded-md border border-border disabled:opacity-40 hover:bg-muted">Next</button>
          </div>
        </div>
      </SectionCard>
    </>
  );
}

function Th({ children, onClick, align = "left" }: { children: React.ReactNode; onClick?: () => void; align?: "left" | "right" }) {
  return (
    <th className={`px-5 py-3 font-medium ${align === "right" ? "text-right" : ""}`}>
      <button onClick={onClick} className="inline-flex items-center gap-1 hover:text-foreground">
        {children}
        {onClick && <ArrowUpDown className="h-3 w-3" />}
      </button>
    </th>
  );
}
