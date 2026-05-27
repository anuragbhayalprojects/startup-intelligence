import { useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowUpDown, Bookmark, BookmarkCheck, Download, Search as SearchIcon } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ScorePill } from "@/components/ScorePill";
import { EmptyState } from "@/components/EmptyState";
import { useSavedStartups } from "@/store/saved-startups";
import { exportToCSV, formatRelativeTime } from "@/lib/csv";
import { toast } from "sonner";
import type { Startup } from "@/types";

type SortKey =
  | "name"
  | "sector"
  | "city"
  | "fundingStage"
  | "bfsiScore"
  | "priorityScore"
  | "lastUpdated";

interface Props {
  data: Startup[];
  pageSize?: number;
  storageKey?: string;
}

const SECTORS_ALL = "All sectors";
const STAGES_ALL = "All stages";

export function StartupTable({ data, pageSize = 10 }: Props) {
  const [query, setQuery] = useState("");
  const [sector, setSector] = useState(SECTORS_ALL);
  const [stage, setStage] = useState(STAGES_ALL);
  const [sortKey, setSortKey] = useState<SortKey>("priorityScore");
  const [sortAsc, setSortAsc] = useState(false);
  const [page, setPage] = useState(1);
  const { isSaved, toggle } = useSavedStartups();

  const sectors = useMemo(() => Array.from(new Set(data.map((s) => s.sector))), [data]);
  const stages = useMemo(() => Array.from(new Set(data.map((s) => s.fundingStage))), [data]);

  const filtered = useMemo(() => {
    return data.filter((s) => {
      if (sector !== SECTORS_ALL && s.sector !== sector) return false;
      if (stage !== STAGES_ALL && s.fundingStage !== stage) return false;
      if (query) {
        const q = query.toLowerCase();
        if (
          !s.name.toLowerCase().includes(q) &&
          !s.subsector.toLowerCase().includes(q) &&
          !s.city.toLowerCase().includes(q) &&
          !s.assignedTeam.toLowerCase().includes(q)
        )
          return false;
      }
      return true;
    });
  }, [data, query, sector, stage]);

  const sorted = useMemo(() => {
    const arr = [...filtered];
    arr.sort((a, b) => {
      const va = a[sortKey];
      const vb = b[sortKey];
      if (typeof va === "number" && typeof vb === "number") return sortAsc ? va - vb : vb - va;
      return sortAsc
        ? String(va).localeCompare(String(vb))
        : String(vb).localeCompare(String(va));
    });
    return arr;
  }, [filtered, sortKey, sortAsc]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const pageRows = sorted.slice((safePage - 1) * pageSize, safePage * pageSize);

  function toggleSort(k: SortKey) {
    if (sortKey === k) setSortAsc((a) => !a);
    else {
      setSortKey(k);
      setSortAsc(false);
    }
  }

  function onExport() {
    exportToCSV(
      sorted,
      `startups-${new Date().toISOString().slice(0, 10)}.csv`,
      [
        { key: "name", label: "Startup Name" },
        { key: "sector", label: "Sector" },
        { key: "subsector", label: "Subsector" },
        { key: "city", label: "City" },
        { key: "fundingStage", label: "Funding Stage" },
        { key: "bfsiScore", label: "BFSI Score" },
        { key: "priorityScore", label: "Priority Score" },
        { key: "assignedTeam", label: "Assigned Team" },
        { key: "source", label: "Source" },
        { key: "lastUpdated", label: "Last Updated" },
      ],
    );
    toast.success(`Exported ${sorted.length} startups to CSV`);
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-col lg:flex-row lg:items-center gap-3">
        <div className="flex-1 relative">
          <SearchIcon className="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name, subsector, city, team…"
            className="pl-9 h-10 bg-card"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          <Select
            value={sector}
            onValueChange={(v) => {
              setSector(v);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[170px] h-10 bg-card">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={SECTORS_ALL}>{SECTORS_ALL}</SelectItem>
              {sectors.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={stage}
            onValueChange={(v) => {
              setStage(v);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[160px] h-10 bg-card">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={STAGES_ALL}>{STAGES_ALL}</SelectItem>
              {stages.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={onExport} className="h-10 gap-1.5">
            <Download className="size-4" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* Table */}
      {pageRows.length === 0 ? (
        <EmptyState
          title="No startups match your filters"
          description="Try clearing filters or adjusting your search query."
        />
      ) : (
        <div className="rounded-xl border border-border bg-card overflow-hidden shadow-card">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <SortableHead label="Startup" k="name" sortKey={sortKey} sortAsc={sortAsc} onSort={toggleSort} />
                  <SortableHead label="Sector" k="sector" sortKey={sortKey} sortAsc={sortAsc} onSort={toggleSort} />
                  <TableHead>Subsector</TableHead>
                  <SortableHead label="City" k="city" sortKey={sortKey} sortAsc={sortAsc} onSort={toggleSort} />
                  <SortableHead label="Stage" k="fundingStage" sortKey={sortKey} sortAsc={sortAsc} onSort={toggleSort} />
                  <SortableHead label="BFSI" k="bfsiScore" sortKey={sortKey} sortAsc={sortAsc} onSort={toggleSort} />
                  <SortableHead label="Priority" k="priorityScore" sortKey={sortKey} sortAsc={sortAsc} onSort={toggleSort} />
                  <TableHead>Team</TableHead>
                  <TableHead>Source</TableHead>
                  <SortableHead label="Updated" k="lastUpdated" sortKey={sortKey} sortAsc={sortAsc} onSort={toggleSort} />
                  <TableHead className="w-10"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pageRows.map((s) => {
                  const saved = isSaved(s.id);
                  return (
                    <TableRow key={s.id} className="group">
                      <TableCell>
                        <Link
                          to="/startups/$id"
                          params={{ id: s.id }}
                          className="font-medium text-foreground hover:text-primary transition-colors"
                        >
                          {s.name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="font-normal">
                          {s.sector}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{s.subsector}</TableCell>
                      <TableCell className="text-muted-foreground">{s.city}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="font-normal">
                          {s.fundingStage}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <ScorePill value={s.bfsiScore} />
                      </TableCell>
                      <TableCell>
                        <ScorePill value={s.priorityScore} />
                      </TableCell>
                      <TableCell className="text-muted-foreground whitespace-nowrap">
                        {s.assignedTeam}
                      </TableCell>
                      <TableCell className="text-muted-foreground">{s.source}</TableCell>
                      <TableCell className="text-muted-foreground whitespace-nowrap">
                        {formatRelativeTime(s.lastUpdated)}
                      </TableCell>
                      <TableCell>
                        <button
                          onClick={() => {
                            toggle(s.id);
                            toast.success(saved ? "Removed from saved" : "Saved startup");
                          }}
                          className="text-muted-foreground hover:text-primary transition-colors"
                          aria-label={saved ? "Unsave" : "Save"}
                        >
                          {saved ? (
                            <BookmarkCheck className="size-4 text-primary" />
                          ) : (
                            <Bookmark className="size-4" />
                          )}
                        </button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
          {/* Pagination */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-border bg-muted/30 text-sm">
            <div className="text-muted-foreground">
              Showing <span className="font-medium text-foreground">{(safePage - 1) * pageSize + 1}</span>–
              <span className="font-medium text-foreground">
                {Math.min(safePage * pageSize, sorted.length)}
              </span>{" "}
              of <span className="font-medium text-foreground">{sorted.length}</span>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                disabled={safePage === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <div className="px-3 text-sm tabular-nums text-muted-foreground">
                Page {safePage} / {totalPages}
              </div>
              <Button
                variant="outline"
                size="sm"
                disabled={safePage === totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SortableHead({
  label,
  k,
  sortKey,
  sortAsc,
  onSort,
}: {
  label: string;
  k: SortKey;
  sortKey: SortKey;
  sortAsc: boolean;
  onSort: (k: SortKey) => void;
}) {
  const active = sortKey === k;
  return (
    <TableHead>
      <button
        onClick={() => onSort(k)}
        className="inline-flex items-center gap-1 hover:text-foreground transition-colors"
      >
        {label}
        <ArrowUpDown
          className={`size-3 ${active ? "opacity-100" : "opacity-40"} ${active && sortAsc ? "rotate-180" : ""} transition-transform`}
        />
      </button>
    </TableHead>
  );
}
