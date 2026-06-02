import React, { useState, useMemo } from "react";
import {
  Search,
  Filter,
  Plus,
  Upload,
  Globe,
  Sparkles,
  RefreshCcw,
  ExternalLink,
  ChevronRight,
  PlusCircle,
  X,
  MapPin,
  Flame,
  CheckCircle2
} from "lucide-react";
import { Startup, UserRole } from "../types";

interface RepositoryProps {
  startups: Startup[];
  currentUser: UserRole;
  onAddStartup: (startupData: any) => Promise<any>;
  onUploadCSV: (csvText: string) => Promise<any>;
  onSelectStartup: (startup: Startup) => void;
  onSemanticSearch: (query: string) => Promise<any[]>;
  onResetDB: () => Promise<void>;
}

const SECTORS = ["All Sectors", "InsurTech", "WealthTech", "LendingTech", "AI Ops"];
const STAGES = ["All Stages", "Seed", "Series A", "Series B", "Series C", "Series D", "Series E", "Growth", "Public"];
const ENTITIES = [
  "All Entities",
  "ICICI Bank",
  "ICICI Lombard",
  "ICICI Securities",
  "ICICI Prudential AMC",
  "ICICI Prudential Life Insurance",
  "ICICI Housing Finance"
];

export default function Repository({
  startups,
  currentUser,
  onAddStartup,
  onUploadCSV,
  onSelectStartup,
  onSemanticSearch,
  onResetDB
}: RepositoryProps) {
  // Filters State
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSector, setSelectedSector] = useState("All Sectors");
  const [selectedStage, setSelectedStage] = useState("All Stages");
  const [selectedEntity, setSelectedEntity] = useState("All Entities");
  const [minPriorityScore, setMinPriorityScore] = useState(0);

  // Semantic Match state
  const [semanticActive, setSemanticActive] = useState(false);
  const [semanticQuery, setSemanticQuery] = useState("");
  const [semanticMatches, setSemanticMatches] = useState<any[]>([]); // Array of { id, explanation }
  const [searchLoading, setSearchLoading] = useState(false);

  // Modal Toggles
  const [showAddModal, setShowAddModal] = useState(false);
  const [showCSVModal, setShowCSVModal] = useState(false);

  // Resizable columns state
  const [colWidths, setColWidths] = useState<Record<string, number>>({
    startup: 220,
    industrySector: 200,
    funding: 135,
    businessModelTags: 220,
    relevance: 250,
    priority: 80,
    teamAssignment: 140,
    trialStatus: 120
  });
  const [resizingCol, setResizingCol] = useState<string | null>(null);
  const [startX, setStartX] = useState<number>(0);
  const [startWidth, setStartWidth] = useState<number>(0);

  const startResize = (colKey: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setResizingCol(colKey);
    setStartX(e.clientX);
    setStartWidth(colWidths[colKey]);
  };

  React.useEffect(() => {
    if (!resizingCol) return;

    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = e.clientX - startX;
      const newWidth = Math.max(70, startWidth + deltaX);
      setColWidths((prev) => ({
        ...prev,
        [resizingCol]: newWidth
      }));
    };

    const handleMouseUp = () => {
      setResizingCol(null);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [resizingCol, startX, startWidth]);

  // Manual Form State
  const [newStartup, setNewStartup] = useState({
    name: "",
    website: "",
    description: "",
    sector: "LendingTech",
    funding_stage: "Seed",
    funding_amount: "$1M"
  });
  const [formError, setFormError] = useState("");
  const [formLoading, setFormLoading] = useState(false);

  // CSV State
  const [csvText, setCsvText] = useState("");
  const [csvStatus, setCsvStatus] = useState("");
  const [csvDuplicates, setCsvDuplicates] = useState<string[]>([]);
  const [csvLoading, setCsvLoading] = useState(false);

  const sampleCSVTemplate = `Name,Description,Website,Funding Stage,Funding Amount
FinMinds,Algorithmic tax harvest and personal tax assistant for Securities investors.,https://finminds.io,Series A,$3.2M
ClaimSentry,Automated mobile photo analysis checks for instant car crash estimates.,https://claimsentry.com,Seed,$1.5M
HansaCredit,Prepaid payroll card issuance layer for building SME credit buffers.,https://hansacredit.in,Series B,$8M`;

  // Filter Logic
  const filteredRepository = useMemo(() => {
    let list = startups;

    // Apply Semantic match filtering if active
    if (semanticActive && semanticMatches.length > 0) {
      const matchIds = semanticMatches.map((m) => String(m.id));
      list = list.filter((s) => matchIds.includes(String(s.id)));
    } else {
      // Normal Query Matching
      if (searchQuery.trim().length > 0) {
        const query = searchQuery.toLowerCase();
        list = list.filter(
          (s) =>
            s.startup_name.toLowerCase().includes(query) ||
            s.description.toLowerCase().includes(query) ||
            s.sector.toLowerCase().includes(query) ||
            (s.subsector && s.subsector.toLowerCase().includes(query)) ||
            (s.industry && s.industry.toLowerCase().includes(query)) ||
            (s.business_models && s.business_models.some((bm) => bm.toLowerCase().includes(query))) ||
            (s.tags && s.tags.some((t) => t.toLowerCase().includes(query)))
        );
      }
    }

    // Apply structured controls
    if (selectedSector !== "All Sectors") {
      list = list.filter((s) => s.sector === selectedSector);
    }
    if (selectedStage !== "All Stages") {
      list = list.filter((s) => s.funding_stage.includes(selectedStage));
    }
    if (selectedEntity !== "All Entities") {
      list = list.filter(
        (s) =>
          s.entity_relevance?.toLowerCase().includes(selectedEntity.toLowerCase()) ||
          (s.relevance_mapping && s.relevance_mapping[selectedEntity] !== undefined)
      );
    }
    if (minPriorityScore > 0) {
      list = list.filter((s) => (s.priority_score || 0) >= minPriorityScore);
    }

    return list;
  }, [startups, searchQuery, selectedSector, selectedStage, selectedEntity, minPriorityScore, semanticActive, semanticMatches]);

  // Handle Manual Create
  const handleCreateStartup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newStartup.name || !newStartup.description) {
      setFormError("Name and Description are required.");
      return;
    }
    setFormLoading(true);
    setFormError("");
    try {
      const result = await onAddStartup(newStartup);
      if (result && result.error) {
        setFormError(result.error);
      } else {
        setShowAddModal(false);
        setNewStartup({
          name: "",
          website: "",
          description: "",
          sector: "LendingTech",
          funding_stage: "Seed",
          funding_amount: "$1M"
        });
      }
    } catch (err: any) {
      setFormError("Platform error. Please check backend connection.");
    } finally {
      setFormLoading(false);
    }
  };

  // Handle CSV Submit
  const handleCSVSubmit = async () => {
    if (!csvText.trim()) {
      setCsvStatus("Please supply CSV dataset content.");
      return;
    }
    setCsvLoading(true);
    setCsvStatus("");
    try {
      const result = await onUploadCSV(csvText);
      if (result.error) {
        setCsvStatus(result.error);
      } else {
        setCsvStatus(`Import success! Added ${result.added} startups.`);
        setCsvDuplicates(result.duplicates || []);
        setCsvText("");
      }
    } catch (err) {
      setCsvStatus("Failed parsing CSV data on servers.");
    } finally {
      setCsvLoading(false);
    }
  };

  // Run Semantic Search Desk
  const triggerSemanticSearch = async () => {
    if (!semanticQuery.trim()) {
      setSemanticActive(false);
      setSemanticMatches([]);
      return;
    }
    setSearchLoading(true);
    try {
      const matches = await onSemanticSearch(semanticQuery);
      setSemanticMatches(matches || []);
      setSemanticActive(true);
    } catch (e) {
      console.error(e);
    } finally {
      setSearchLoading(false);
    }
  };

  // Reset search modes
  const clearSearch = () => {
    setSearchQuery("");
    setSemanticQuery("");
    setSemanticActive(false);
    setSemanticMatches([]);
  };

  return (
    <div className="space-y-6" id="startup-repository-panel">
      {/* Search & Intelligence Controls */}
      <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4 text-left" id="search-desk">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h3 className="font-bold text-slate-900 text-base">Group Intelligence Search Desk</h3>
            <p className="text-slate-500 text-xs mt-1">
              Search by simple keyword or toggle semantic neural search to correlate claims, AI underwriting, or robo-advisory context.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 w-full md:w-auto">
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 shadow-sm transition-all text-center flex-1 md:flex-none justify-center border-0 cursor-pointer"
              id="add-startup-btn"
            >
              <Plus size={15} /> Add Startup
            </button>
            <button
              onClick={() => setShowCSVModal(true)}
              className="bg-slate-100 border border-slate-200 text-slate-700 hover:bg-slate-200 text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 transition-all text-center flex-1 md:flex-none justify-center cursor-pointer"
              id="import-csv-btn"
            >
              <Upload size={15} /> CSV Import
            </button>
            <button
              onClick={onResetDB}
              className="border border-red-200 text-red-650 bg-red-50/20 hover:bg-red-50 text-xs font-semibold px-3 py-2 rounded-lg flex items-center gap-1 transition-all cursor-pointer"
              title="Reset Database"
            >
              <RefreshCcw size={14} /> Reset Seed
            </button>
          </div>
        </div>

        {/* Action search bars */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Natural Search */}
          <div className="relative">
            <Search className="absolute left-3.5 top-3.5 text-slate-400" size={16} />
            <input
              type="text"
              placeholder="Search startup name, use cases..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                if (semanticActive) setSemanticActive(false);
              }}
              className="w-full bg-slate-50 text-slate-800 border border-slate-200 rounded-lg py-2.5 pl-10 pr-4 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          {/* Semantic Search Panel */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Sparkles className="absolute left-3.5 top-3.5 text-amber-500" size={16} />
              <input
                type="text"
                placeholder="Ask Gemini semantic query e.g. 'Show claims automation motor validation'..."
                value={semanticQuery}
                onChange={(e) => setSemanticQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && triggerSemanticSearch()}
                className="w-full bg-amber-500/5 text-slate-800 border-2 border-amber-500/20 rounded-lg py-2 pl-10 pr-4 text-xs focus:ring-2 focus:ring-amber-500/50 focus:outline-none"
              />
            </div>
            <button
              id="toggle-semantic-search"
              onClick={triggerSemanticSearch}
              disabled={searchLoading}
              className="bg-amber-500 text-slate-900 border-0 hover:bg-amber-600 text-xs font-bold px-4 py-2.5 rounded-lg shadow-md transition-all flex items-center gap-1 cursor-pointer"
            >
              {searchLoading ? (
                <RefreshCcw className="animate-spin" size={14} />
              ) : (
                <Sparkles size={14} />
              )}
              Match
            </button>
          </div>
        </div>

        {/* Semantic Status Bar */}
        {(semanticActive || searchQuery.trim().length > 0) && (
          <div className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-xs text-slate-600">
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${semanticActive ? "bg-amber-500 animate-pulse" : "bg-blue-500"}`}></span>
              <span>
                {semanticActive
                  ? `Gemini Vector Search Active matching "${semanticQuery}" (${filteredRepository.length} results grouped)`
                  : `Structured Keyword filter applied (${filteredRepository.length} results)`}
              </span>
            </div>
            <button
              onClick={clearSearch}
              className="text-xs text-blue-600 hover:underline font-bold bg-transparent border-0 cursor-pointer"
            >
              Clear filters
            </button>
          </div>
        )}
      </div>

      {/* Multi-Tier Filters */}
      <div className="bg-slate-50 border border-slate-200/80 p-4 rounded-xl flex flex-wrap gap-4 items-center" id="filter-tier">
        <div className="flex items-center gap-2 text-xs text-slate-550 font-bold">
          <Filter size={14} />
          <span>Filters:</span>
        </div>

        {/* Sector */}
        <div className="space-y-1">
          <select
            value={selectedSector}
            onChange={(e) => setSelectedSector(e.target.value)}
            className="bg-white border border-slate-200 text-slate-700 text-xs rounded-lg p-1.5 focus:outline-none"
          >
            {SECTORS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {/* Stages */}
        <div className="space-y-1">
          <select
            value={selectedStage}
            onChange={(e) => setSelectedStage(e.target.value)}
            className="bg-white border border-slate-200 text-slate-700 text-xs rounded-lg p-1.5 focus:outline-none"
          >
            {STAGES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {/* Entity Relevance */}
        <div className="space-y-1">
          <select
            value={selectedEntity}
            onChange={(e) => setSelectedEntity(e.target.value)}
            className="bg-white border border-slate-200 text-slate-700 text-xs rounded-lg p-1.5 focus:outline-none"
          >
            {ENTITIES.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>
        </div>

        {/* Priority slider */}
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-[11px] text-slate-500 font-bold whitespace-nowrap">Priority Score ≥</span>
          <input
            type="range"
            min="0"
            max="100"
            step="5"
            value={minPriorityScore}
            onChange={(e) => setMinPriorityScore(Number(e.target.value))}
            className="w-24 accent-blue-600 cursor-pointer"
          />
          <span className="text-xs bg-slate-200 font-mono text-slate-705 px-1.5 py-0.5 rounded font-bold">
            {minPriorityScore}
          </span>
        </div>
      </div>

      {/* Main Grid View */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden" id="repository-grid-section">
        <div className="p-4 border-b border-indigo-600 bg-slate-900 flex justify-between items-center text-white">
          <h4 className="font-bold text-xs uppercase tracking-wider">
            Supabase Registry ({filteredRepository.length} Active Startups)
          </h4>
          <span className="text-[10px] bg-indigo-500/20 text-indigo-300 font-mono py-0.5 px-2 rounded-full border border-indigo-500/30">
            Real-time table logs
          </span>
        </div>

        {/* Enterprise Table */}
        <div className="overflow-x-auto">
          <table 
            className="text-left border-collapse"
            style={{
              tableLayout: "fixed",
              width: Object.values(colWidths).reduce((a, b) => a + b, 0) + "px",
              minWidth: "100%"
            }}
          >
            <colgroup>
              <col style={{ width: `${colWidths.startup}px` }} />
              <col style={{ width: `${colWidths.industrySector}px` }} />
              <col style={{ width: `${colWidths.funding}px` }} />
              <col style={{ width: `${colWidths.businessModelTags}px` }} />
              <col style={{ width: `${colWidths.relevance}px` }} />
              <col style={{ width: `${colWidths.priority}px` }} />
              <col style={{ width: `${colWidths.teamAssignment}px` }} />
              <col style={{ width: `${colWidths.trialStatus}px` }} />
            </colgroup>
            <thead>
              <tr className="bg-slate-50 text-slate-500 text-[10.5px] uppercase font-bold border-b border-slate-100 select-none">
                <th className="py-3 px-4 relative group">
                  <span className="truncate block">Startup</span>
                  <div 
                    onMouseDown={(e) => startResize("startup", e)}
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-indigo-500/80 hover:w-1.5 transition-all select-none z-10"
                    style={{ borderRight: "2px solid #cbd5e1" }}
                  />
                </th>
                <th className="py-3 px-4 relative group">
                  <span className="truncate block">Industry & Sector</span>
                  <div 
                    onMouseDown={(e) => startResize("industrySector", e)}
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-indigo-500/80 hover:w-1.5 transition-all select-none z-10"
                    style={{ borderRight: "2px solid #cbd5e1" }}
                  />
                </th>
                <th className="py-3 px-4 relative group">
                  <span className="truncate block">Funding Stage</span>
                  <div 
                    onMouseDown={(e) => startResize("funding", e)}
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-indigo-500/80 hover:w-1.5 transition-all select-none z-10"
                    style={{ borderRight: "2px solid #cbd5e1" }}
                  />
                </th>
                <th className="py-3 px-4 relative group">
                  <span className="truncate block">Business Model & Tags</span>
                  <div 
                    onMouseDown={(e) => startResize("businessModelTags", e)}
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-indigo-500/80 hover:w-1.5 transition-all select-none z-10"
                    style={{ borderRight: "2px solid #cbd5e1" }}
                  />
                </th>
                <th className="py-3 px-4 relative group">
                  <span className="truncate block">Relevance to ICICI</span>
                  <div 
                    onMouseDown={(e) => startResize("relevance", e)}
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-indigo-500/80 hover:w-1.5 transition-all select-none z-10"
                    style={{ borderRight: "2px solid #cbd5e1" }}
                  />
                </th>
                <th className="py-3 px-4 text-center relative group">
                  <span className="truncate block">Priority</span>
                  <div 
                    onMouseDown={(e) => startResize("priority", e)}
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-indigo-500/80 hover:w-1.5 transition-all select-none z-10"
                    style={{ borderRight: "2px solid #cbd5e1" }}
                  />
                </th>
                <th className="py-3 px-4 text-right relative group">
                  <span className="truncate block">Team assignment</span>
                  <div 
                    onMouseDown={(e) => startResize("teamAssignment", e)}
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-indigo-500/80 hover:w-1.5 transition-all select-none z-10"
                    style={{ borderRight: "2px solid #cbd5e1" }}
                  />
                </th>
                <th className="py-3 px-4 text-right relative">
                  <span className="truncate block">Trial status</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {filteredRepository.map((s) => {
                // Determine matches semantic explanation if active
                const semanticExplain = semanticActive
                  ? semanticMatches.find((m) => String(m.id) === String(s.id))?.explanation
                  : null;

                const scoreVal = s.priority_score || 50;

                return (
                  <tr
                    key={s.id}
                    onClick={() => onSelectStartup(s)}
                    className="hover:bg-slate-50/50 cursor-pointer transition-all"
                  >
                    <td className="py-4 px-4 space-y-1 text-left overflow-hidden">
                      <div className="flex items-center gap-1 truncate">
                        <span className="font-extrabold text-slate-900 hover:text-blue-600 truncate">{s.startup_name}</span>
                        {s.website && (
                          <a
                            href={s.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-slate-400 hover:text-blue-500 inline-block pl-1 flex-shrink-0"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <ExternalLink size={12} />
                          </a>
                        )}
                      </div>
                      <p className="text-slate-500 text-[11px] line-clamp-2 leading-relaxed whitespace-normal">
                        {s.description}
                      </p>
                      {semanticExplain && (
                        <div className="bg-amber-50 border border-amber-200 text-amber-900 p-2 rounded text-[10.5px] mt-1.5 flex items-start gap-1 whitespace-normal">
                          <Sparkles size={11} className="text-amber-500 flex-shrink-0 mt-0.5" />
                          <span>{semanticExplain}</span>
                        </div>
                      )}
                    </td>

                    <td className="py-4 px-4 space-y-1 text-left overflow-hidden">
                      {s.industry && (
                        <span className="inline-block bg-indigo-50 text-indigo-700 font-bold px-1.5 py-0.5 rounded text-[9.5px] border border-indigo-100 uppercase tracking-wider truncate max-w-full">
                          {s.industry}
                        </span>
                      )}
                      <div className="flex flex-wrap items-center gap-1.5 mt-0.5 max-w-full">
                        <span className="inline-block bg-slate-100 text-slate-700 font-bold px-1.5 py-0.5 rounded text-[10px] truncate max-w-[120px]">
                          {s.sector}
                        </span>
                        <span className="text-[10px] text-slate-400 font-medium truncate max-w-[100px]">
                          {s.subsector || s.subSector || "Innovation"}
                        </span>
                      </div>
                    </td>

                    <td className="py-3 px-4 space-y-1 whitespace-nowrap text-left overflow-hidden">
                      <p className="font-bold text-slate-800 truncate">{s.funding_amount || "$1.5M"}</p>
                      <p className="text-[10px] text-slate-400 truncate">{s.funding_stage}</p>
                    </td>

                    <td className="py-3 px-4 text-left space-y-1 overflow-hidden">
                      {s.business_models && s.business_models.length > 0 ? (
                        <div className="flex flex-wrap gap-1 max-w-full">
                          {s.business_models.map((bm) => (
                            <span key={bm} className="text-[9.5px] bg-emerald-50 text-emerald-700 font-semibold px-1.5 py-0.5 rounded border border-emerald-100 truncate">
                              {bm}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-[10px] text-slate-400 italic">No business model</span>
                      )}
                      {s.tags && s.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1 max-w-full">
                          {s.tags.slice(0, 4).map((tag) => (
                            <span key={tag} className="text-[9px] bg-slate-100 text-slate-600 px-1 py-0.5 rounded font-mono truncate">
                              #{tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>

                    <td className="py-3 px-4 text-left overflow-hidden">
                      <p className="text-slate-600 line-clamp-2 max-w-[280px] whitespace-normal">
                        {s.entity_relevance}
                      </p>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {s.relevance_mapping && Object.keys(s.relevance_mapping).map((ent) => (
                          <span key={ent} className="text-[9px] bg-blue-50 text-blue-700 px-1 py-0.5 rounded truncate">
                            {ent}
                          </span>
                        ))}
                      </div>
                    </td>

                    <td className="py-3 px-4 text-center overflow-hidden">
                      <span
                        className={`inline-block font-mono font-bold text-xs px-2 py-0.5 rounded-full ${
                          scoreVal >= 90
                            ? "bg-red-100 text-red-700"
                            : scoreVal >= 80
                            ? "bg-amber-100 text-amber-700"
                            : "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {scoreVal}
                      </span>
                    </td>

                    <td className="py-3 px-4 text-right font-semibold text-slate-700 overflow-hidden truncate">
                      {s.assigned_team}
                    </td>

                    <td className="py-3 px-4 text-right overflow-hidden">
                      <span
                        className={`inline-block text-[10.5px] font-bold px-2.5 py-1 rounded truncate ${
                          s.status === "Partnership"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-250"
                            : s.status === "Proof of Concept"
                            ? "bg-blue-50 text-blue-700 border border-blue-200"
                            : s.status === "Evaluation"
                            ? "bg-amber-50 text-amber-700 border border-amber-200"
                            : "bg-slate-50 text-slate-600 border border-slate-200"
                        }`}
                      >
                        {s.status || "Screening"}
                      </span>
                    </td>
                  </tr>
                );
              })}
              {filteredRepository.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400 font-medium">
                    No startups matched filter criteria inside our database. Try expanding standard parameters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* MODAL 1: ADD STARTUP MANUAL */}
      {showAddModal && (
        <div className="fixed inset-0 bg-slate-900/60 flex items-center justify-center p-4 z-50 animate-fade-in" id="add-startup-modal">
          <div className="bg-white w-full max-w-lg rounded-xl shadow-2xl overflow-hidden border border-slate-150 text-left">
            <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-900 text-white">
              <h4 className="font-bold text-sm">Add New FinTech Venture to Registry</h4>
              <button onClick={() => setShowAddModal(false)} className="text-white hover:text-slate-300 cursor-pointer border-0 bg-transparent">
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateStartup} className="p-5 space-y-4">
              {formError && (
                <div className="p-3 bg-red-100 border border-red-300 rounded-lg text-xs font-semibold text-red-700">
                  {formError}
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10.5px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                    Startup Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={newStartup.name}
                    onChange={(e) => setNewStartup({ ...newStartup, name: e.target.value })}
                    placeholder="e.g. Perfios"
                    className="w-full bg-slate-50 border border-slate-200 text-slate-805 text-slate-800 text-xs rounded-lg p-2 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[10.5px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                    Website Address
                  </label>
                  <input
                    type="text"
                    value={newStartup.website}
                    onChange={(e) => setNewStartup({ ...newStartup, website: e.target.value })}
                    placeholder="e.g. https://perfios.com"
                    className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-2 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10.5px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                  Innovational Description *
                  </label>
                <textarea
                  required
                  rows={3}
                  value={newStartup.description}
                  onChange={(e) => setNewStartup({ ...newStartup, description: e.target.value })}
                  placeholder="Detail the core technology solution, usecases, and business propositions clearly so our AI models can accurately index use cases."
                  className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-2 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[10.5px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                    Target Sector
                  </label>
                  <select
                    value={newStartup.sector}
                    onChange={(e) => setNewStartup({ ...newStartup, sector: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-2"
                  >
                    <option value="InsurTech">InsurTech</option>
                    <option value="WealthTech">WealthTech</option>
                    <option value="LendingTech">LendingTech</option>
                    <option value="AI Ops">AI Ops</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10.5px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                    Funding Stage
                  </label>
                  <input
                    type="text"
                    value={newStartup.funding_stage}
                    onChange={(e) => setNewStartup({ ...newStartup, funding_stage: e.target.value })}
                    placeholder="Series A"
                    className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-2 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[10.5px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                    Valuation / Raised
                  </label>
                  <input
                    type="text"
                    value={newStartup.funding_amount}
                    onChange={(e) => setNewStartup({ ...newStartup, funding_amount: e.target.value })}
                    placeholder="e.g. $14M"
                    className="w-full bg-slate-50 border border-slate-200 text-slate-805 text-slate-800 text-xs rounded-lg p-2 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-[11px] text-slate-500 flex items-start gap-2">
                <Sparkles size={14} className="text-amber-500 mt-0.5 flex-shrink-0" />
                <p>
                  <strong>AI Enrichment active:</strong> Submitting this form triggers a database entry. You can run immediate Mistral evaluations to score corporate readiness and co-creation fits in the detail drawer!
                </p>
              </div>

              <div className="flex gap-2 justify-end pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="bg-slate-105 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs px-4 py-2 rounded-lg font-semibold transition-all cursor-pointer border-0"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-5 py-2 rounded-lg font-semibold shadow-sm transition-all flex items-center gap-1 cursor-pointer border-0"
                >
                  {formLoading ? "Saving..." : "Register Venture"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: BATCH CSV FILE UPLOAD */}
      {showCSVModal && (
        <div className="fixed inset-0 bg-slate-900/60 flex items-center justify-center p-4 z-50 animate-fade-in" id="csv-upload-modal">
          <div className="bg-white w-full max-w-2xl rounded-xl shadow-2xl overflow-hidden border border-slate-150 text-left">
            <div className="p-5 border-b border-indigo-605 border-indigo-600 bg-slate-900 text-white flex justify-between items-center">
              <div className="flex items-center gap-2">
                <Upload size={18} className="text-indigo-400" />
                <h4 className="font-bold text-sm">Automated CSV Data Importer Desk</h4>
              </div>
              <button onClick={() => setShowCSVModal(false)} className="text-white hover:text-slate-350 cursor-pointer border-0 bg-transparent">
                <X size={18} />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="text-xs text-slate-600 leading-relaxed">
                Import large databases of global FinTech records easily. Copy-paste standard tabular content or comma separated sequences matching the formatting columns template below.
              </div>

              {/* Template Block */}
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    CSV Columns Layout Template Required
                  </span>
                  <button
                    onClick={() => setCsvText(sampleCSVTemplate)}
                    className="text-[10px] text-blue-650 hover:underline font-bold flex items-center gap-1 bg-transparent border-0 cursor-pointer"
                  >
                    <PlusCircle size={10} /> Load Sample Template
                  </button>
                </div>
                <pre className="text-[10.5px] font-mono text-indigo-800 leading-relaxed bg-white/70 p-2 rounded max-h-24 overflow-y-auto border border-slate-100">
                  {sampleCSVTemplate}
                </pre>
              </div>

              {/* Text Input area */}
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block">
                  Paste Raw CSV Dataset content
                </label>
                <textarea
                  rows={6}
                  value={csvText}
                  onChange={(e) => setCsvText(e.target.value)}
                  placeholder="Paste Name, Description, Website, Funding Stage, Funding Amount..."
                  className="w-full bg-slate-55 bg-slate-50 border border-slate-200 text-slate-805 text-[11px] font-mono rounded-lg p-2.5 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              {/* Status and duplicate reporting log */}
              {csvStatus && (
                <div className="p-2.5 bg-blue-50 border border-blue-200 text-blue-800 text-xs rounded-lg font-semibold flex items-center justify-between">
                  <span>{csvStatus}</span>
                </div>
              )}

              {csvDuplicates.length > 0 && (
                <div className="p-2.5 bg-amber-50 border border-amber-205 text-amber-900 rounded-lg text-[11px] space-y-1">
                  <strong>Skipped existing duplicates:</strong>
                  <p className="font-mono text-slate-500">{csvDuplicates.join(", ")}</p>
                </div>
              )}

              <div className="bg-slate-50 p-3 rounded-lg text-slate-500 text-[10.5px]">
                <strong className="text-slate-705">Sandbox Rule check:</strong> Pre-existing/duplicate startup records are omitted to prevent redundancy errors. Newly imported files undergo automated category-team mapping.
              </div>

              <div className="flex gap-2 justify-end pt-3 border-t border-slate-100">
                <button
                  onClick={() => setShowCSVModal(false)}
                  className="bg-slate-105 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs px-4 py-2 rounded-lg font-semibold border-0 cursor-pointer"
                >
                  Close Desk
                </button>
                <button
                  onClick={handleCSVSubmit}
                  disabled={csvLoading}
                  className="bg-indigo-650 hover:bg-indigo-700 text-white text-xs px-5 py-2 rounded-lg font-semibold shadow-sm transition-all border-0 cursor-pointer"
                >
                  {csvLoading ? "Processing lines..." : "Begin Batch Import"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
