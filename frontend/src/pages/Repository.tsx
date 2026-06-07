import React, { useState, useMemo, useEffect } from "react";
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
  CheckCircle2,
  TrendingUp,
  AlertTriangle,
  Award,
  Shield,
  Zap,
  Percent
} from "lucide-react";
import { Startup, UserRole } from "../types";
import { TAXONOMY } from "../lib/taxonomy";

interface RepositoryProps {
  startups: Startup[];
  currentUser: UserRole;
  onAddStartup: (startupData: any) => Promise<any>;
  onUploadCSV: (csvText: string) => Promise<any>;
  onSelectStartup: (startup: Startup) => void;
  onSemanticSearch: (query: string) => Promise<any[]>;
  onResetDB: () => Promise<void>;
}

const ENTITIES = [
  "All Entities",
  "ICICI Bank",
  "ICICI Lombard",
  "ICICI Prudential Life",
  "ICICI Prudential AMC",
  "ICICI Securities",
  "ICICI HFC"
];

const BANDS = [
  "All Bands",
  "Critical",
  "High",
  "Medium",
  "Low",
  "Ignore"
];

const ACTIONS = [
  "All Actions",
  "Founder Meeting",
  "Business Introduction",
  "POC",
  "Strategic Investment Review",
  "Monitor"
];

const TEAMS = [
  "All Teams",
  "Lending Team",
  "Insurance Team",
  "AMC/Securities Team",
  "Enterprise AI Team"
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
  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [semanticActive, setSemanticActive] = useState(false);
  const [semanticQuery, setSemanticQuery] = useState("");
  const [semanticMatches, setSemanticMatches] = useState<any[]>([]); // Array of { id, explanation }
  const [searchLoading, setSearchLoading] = useState(false);

  // New Filters State
  const [selectedIndustry, setSelectedIndustry] = useState("All Industries");
  const [selectedSector, setSelectedSector] = useState("All Sectors");
  const [selectedSubsector, setSelectedSubsector] = useState("All Subsectors");
  const [selectedStage, setSelectedStage] = useState("All Stages");
  const [selectedBusinessModel, setSelectedBusinessModel] = useState("All Models");
  
  // Upgraded Filters
  const [selectedEntity, setSelectedEntity] = useState("All Entities");
  const [selectedPriorityBand, setSelectedPriorityBand] = useState("All Bands");
  const [selectedRecAction, setSelectedRecAction] = useState("All Actions");
  const [selectedBusinessTeam, setSelectedBusinessTeam] = useState("All Teams");
  
  // Sliders
  const [minRelevanceScore, setMinRelevanceScore] = useState(0);
  const [minStrategicFitScore, setMinStrategicFitScore] = useState(0);
  const [minPriorityScore, setMinPriorityScore] = useState(0);

  // Dynamic dropdown calculations
  const sectorOptions = useMemo(() => {
    if (selectedIndustry === "All Industries") {
      const allSectors = TAXONOMY.industries.reduce((acc, ind) => {
        return [...acc, ...Object.keys(ind.sectors)];
      }, [] as string[]);
      return ["All Sectors", ...Array.from(new Set(allSectors))];
    } else {
      const ind = TAXONOMY.industries.find((i) => i.name === selectedIndustry);
      return ["All Sectors", ...(ind ? Object.keys(ind.sectors) : [])];
    }
  }, [selectedIndustry]);

  const subsectorOptions = useMemo(() => {
    if (selectedSector === "All Sectors") {
      if (selectedIndustry === "All Industries") {
        const allSubs = TAXONOMY.industries.reduce((acc, ind) => {
          const indSubs = Object.values(ind.sectors).reduce((acc2, subs) => [...acc2, ...subs], [] as string[]);
          return [...acc, ...indSubs];
        }, [] as string[]);
        return ["All Subsectors", ...Array.from(new Set(allSubs))];
      } else {
        const ind = TAXONOMY.industries.find((i) => i.name === selectedIndustry);
        if (!ind) return ["All Subsectors"];
        const indSubs = Object.values(ind.sectors).reduce((acc, subs) => [...acc, ...subs], [] as string[]);
        return ["All Subsectors", ...Array.from(new Set(indSubs))];
      }
    } else {
      let targetSectorSubs: string[] = [];
      for (const ind of TAXONOMY.industries) {
        if (ind.sectors[selectedSector]) {
          targetSectorSubs = ind.sectors[selectedSector];
          break;
        }
      }
      return ["All Subsectors", ...targetSectorSubs];
    }
  }, [selectedIndustry, selectedSector]);

  useEffect(() => {
    setSelectedSector("All Sectors");
    setSelectedSubsector("All Subsectors");
  }, [selectedIndustry]);

  useEffect(() => {
    setSelectedSubsector("All Subsectors");
  }, [selectedSector]);

  // Modal Toggles
  const [showAddModal, setShowAddModal] = useState(false);
  const [showCSVModal, setShowCSVModal] = useState(false);

  // Resizable columns widths mapping
  const [colWidths, setColWidths] = useState<Record<string, number>>({
    startup: 230,
    priorityBand: 110,
    recommendedAction: 150,
    primaryEntity: 140,
    businessTeam: 140,
    confidenceScore: 90,
    priority: 80,
    trialStatus: 110
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

  useEffect(() => {
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

  // Manual Creation Form State
  const [newStartup, setNewStartup] = useState({
    name: "",
    website: "",
    description: "",
    industry: "Financial Services",
    sector: "FinTech",
    subsector: "Digital Banking",
    funding_stage: "Seed",
    funding_amount: "",
    business_models: [] as string[]
  });
  const [formError, setFormError] = useState("");
  const [formLoading, setFormLoading] = useState(false);

  // Cascade fields
  useEffect(() => {
    const ind = TAXONOMY.industries.find((i) => i.name === newStartup.industry);
    const sectors = ind ? Object.keys(ind.sectors) : [];
    const defaultSector = sectors[0] || "";
    const defaultSubs = defaultSector && ind ? ind.sectors[defaultSector] : [];
    const defaultSub = defaultSubs[0] || "Unknown";
    setNewStartup((prev) => ({
      ...prev,
      sector: defaultSector,
      subsector: defaultSub
    }));
  }, [newStartup.industry]);

  useEffect(() => {
    const ind = TAXONOMY.industries.find((i) => i.name === newStartup.industry);
    if (!ind) return;
    const subs = ind.sectors[newStartup.sector] || [];
    setNewStartup((prev) => ({
      ...prev,
      subsector: subs[0] || "Unknown"
    }));
  }, [newStartup.sector]);

  // CSV Import State
  const [csvText, setCsvText] = useState("");
  const [csvStatus, setCsvStatus] = useState("");
  const [csvDuplicates, setCsvDuplicates] = useState<string[]>([]);
  const [csvLoading, setCsvLoading] = useState(false);

  const sampleCSVTemplate = `Name,Description,Website,Funding Stage,Funding Amount
FinMinds,Algorithmic tax harvest and personal tax assistant for Securities investors.,https://finminds.io,Series A,$3.2M
ClaimSentry,Automated mobile photo analysis checks for instant car crash estimates.,https://claimsentry.com,Seed,$1.5M
HansaCredit,Prepaid payroll card issuance layer for building SME credit buffers.,https://hansacredit.in,Series B,$8M`;

  // Dynamic Filtering Logic
  const filteredRepository = useMemo(() => {
    let list = startups;

    // Apply Semantic Search query matching if active
    if (semanticActive && semanticMatches.length > 0) {
      const matchIds = semanticMatches.map((m) => String(m.id));
      list = list.filter((s) => matchIds.includes(String(s.id)));
    } else {
      // General search query matching
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

    // Taxonomy Filters
    if (selectedIndustry !== "All Industries") {
      list = list.filter((s) => s.industry === selectedIndustry);
    }
    if (selectedSector !== "All Sectors") {
      list = list.filter((s) => s.sector === selectedSector);
    }
    if (selectedSubsector !== "All Subsectors") {
      list = list.filter((s) => s.subsector === selectedSubsector || s.subSector === selectedSubsector);
    }
    if (selectedStage !== "All Stages") {
      list = list.filter((s) => s.funding_stage === selectedStage || s.startup_stage === selectedStage);
    }
    if (selectedBusinessModel !== "All Models") {
      list = list.filter((s) => s.business_models && s.business_models.some((bm) => bm.toLowerCase() === selectedBusinessModel.toLowerCase()));
    }

    // Upgraded Filters
    if (selectedEntity !== "All Entities") {
      list = list.filter(
        (s) =>
          s.matched_entities?.includes(selectedEntity) ||
          s.entity_relevance?.toLowerCase().includes(selectedEntity.toLowerCase()) ||
          (s.relevance_mapping && typeof s.relevance_mapping === "object" && !Array.isArray(s.relevance_mapping) && s.relevance_mapping[selectedEntity] !== undefined)
      );
    }
    if (selectedPriorityBand !== "All Bands") {
      list = list.filter((s) => s.priority_band === selectedPriorityBand);
    }
    if (selectedRecAction !== "All Actions") {
      list = list.filter((s) => s.recommended_action === selectedRecAction);
    }
    if (selectedBusinessTeam !== "All Teams") {
      list = list.filter(
        (s) =>
          s.matched_business_teams?.includes(selectedBusinessTeam) ||
          s.assigned_team === selectedBusinessTeam
      );
    }

    // Slider Limits
    if (minRelevanceScore > 0) {
      list = list.filter((s) => (s.relevance_score || 0) >= minRelevanceScore);
    }
    if (minStrategicFitScore > 0) {
      list = list.filter((s) => (s.deployability_score || 0) >= minStrategicFitScore);
    }
    if (minPriorityScore > 0) {
      list = list.filter((s) => (s.priority_score || 0) >= minPriorityScore);
    }

    return list;
  }, [
    startups,
    searchQuery,
    selectedIndustry,
    selectedSector,
    selectedSubsector,
    selectedStage,
    selectedBusinessModel,
    selectedEntity,
    selectedPriorityBand,
    selectedRecAction,
    selectedBusinessTeam,
    minRelevanceScore,
    minStrategicFitScore,
    minPriorityScore,
    semanticActive,
    semanticMatches
  ]);

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
          industry: "Financial Services",
          sector: "FinTech",
          subsector: "Digital Banking",
          funding_stage: "Seed",
          funding_amount: "",
          business_models: []
        });
      }
    } catch (err: any) {
      setFormError("Platform error. Please check backend connection.");
    } finally {
      setFormLoading(false);
    }
  };

  // Handle CSV Dataset upload
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

  // Run Semantic search
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

  const clearSearch = () => {
    setSearchQuery("");
    setSemanticQuery("");
    setSemanticActive(false);
    setSemanticMatches([]);
    setSelectedIndustry("All Industries");
    setSelectedSector("All Sectors");
    setSelectedSubsector("All Subsectors");
    setSelectedStage("All Stages");
    setSelectedBusinessModel("All Models");
    setSelectedEntity("All Entities");
    setSelectedPriorityBand("All Bands");
    setSelectedRecAction("All Actions");
    setSelectedBusinessTeam("All Teams");
    setMinRelevanceScore(0);
    setMinStrategicFitScore(0);
    setMinPriorityScore(0);
  };

  return (
    <div className="space-y-6" id="startup-repository-panel">
      
      {/* Search Bar Block */}
      <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4 text-left">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h3 className="font-black text-slate-900 text-base">Startup Registry Search Desk</h3>
            <p className="text-slate-500 text-xs mt-1">
              Search by simple keyword or toggle semantic neural search to correlate claims, AI underwriting, or robo-advisory context.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 w-full md:w-auto select-none">
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 shadow-sm transition-all text-center flex-1 md:flex-none justify-center border-0 cursor-pointer animate-pulse-subtle"
            >
              <Plus size={15} /> Add Startup
            </button>
            <button
              onClick={() => setShowCSVModal(true)}
              className="bg-slate-100 border border-slate-200 text-slate-700 hover:bg-slate-200 text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 transition-all text-center flex-1 md:flex-none justify-center cursor-pointer"
            >
              <Upload size={15} /> CSV Import
            </button>
            <button
              onClick={onResetDB}
              className="border border-red-200 text-red-600 bg-red-50/20 hover:bg-red-50 text-xs font-semibold px-3 py-2 rounded-lg flex items-center gap-1 transition-all cursor-pointer"
              title="Reset Database"
            >
              <RefreshCcw size={14} /> Reset Seed
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="relative">
            <Search className="absolute left-3.5 top-3.5 text-slate-400" size={16} />
            <input
              type="text"
              placeholder="Search by name, tags, description..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                if (semanticActive) setSemanticActive(false);
              }}
              className="w-full bg-slate-50 text-slate-800 border border-slate-200 rounded-lg py-2.5 pl-10 pr-4 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <div className="flex gap-2">
            <div className="relative flex-1">
              <Sparkles className="absolute left-3.5 top-3.5 text-amber-500" size={16} />
              <input
                type="text"
                placeholder="Semantic query e.g. 'Show insurance claims auto estimation'..."
                value={semanticQuery}
                onChange={(e) => setSemanticQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && triggerSemanticSearch()}
                className="w-full bg-amber-500/5 text-slate-800 border-2 border-amber-500/20 rounded-lg py-2 pl-10 pr-4 text-xs focus:ring-2 focus:ring-amber-500/50 focus:outline-none"
              />
            </div>
            <button
              onClick={triggerSemanticSearch}
              disabled={searchLoading}
              className="bg-amber-505 bg-amber-500 text-slate-950 border-0 hover:bg-amber-600 text-xs font-bold px-4 py-2.5 rounded-lg shadow-md transition-all flex items-center gap-1.5 cursor-pointer"
            >
              {searchLoading ? <RefreshCcw className="animate-spin" size={14} /> : <Sparkles size={14} />}
              Match
            </button>
          </div>
        </div>

        {(semanticActive || searchQuery.trim().length > 0) && (
          <div className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-xs text-slate-600 select-none">
            <div className="flex items-center gap-2">
              <span className={`h-2.5 w-2.5 rounded-full ${semanticActive ? "bg-amber-500 animate-pulse" : "bg-blue-500"}`}></span>
              <span>
                {semanticActive
                  ? `Gemini Vector Search Active matching "${semanticQuery}" (${filteredRepository.length} results grouped)`
                  : `Structured Keyword filter applied (${filteredRepository.length} results)`}
              </span>
            </div>
            <button onClick={clearSearch} className="text-xs text-blue-600 hover:underline font-bold bg-transparent border-0 cursor-pointer">
              Clear filters
            </button>
          </div>
        )}
      </div>

      {/* Advanced Filters Panel */}
      <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4 text-left select-none">
        <h4 className="text-xs font-black text-slate-900 uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-100 pb-2">
          <Filter size={14} className="text-slate-450" /> Filter Workspaces
        </h4>
        
        {/* Dropdown Filters Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="text-[9px] font-black text-slate-400 uppercase block mb-1">Target Entity</label>
            <select
              value={selectedEntity}
              onChange={(e) => setSelectedEntity(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-lg p-2 focus:outline-none"
            >
              <option value="All Entities">All Entities</option>
              {ENTITIES.slice(1).map((e) => (
                <option key={e} value={e}>{e}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-[9px] font-black text-slate-400 uppercase block mb-1">Priority Band</label>
            <select
              value={selectedPriorityBand}
              onChange={(e) => setSelectedPriorityBand(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-lg p-2 focus:outline-none"
            >
              {BANDS.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-[9px] font-black text-slate-400 uppercase block mb-1">Recommended Action</label>
            <select
              value={selectedRecAction}
              onChange={(e) => setSelectedRecAction(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-lg p-2 focus:outline-none"
            >
              {ACTIONS.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-[9px] font-black text-slate-400 uppercase block mb-1">Business Team</label>
            <select
              value={selectedBusinessTeam}
              onChange={(e) => setSelectedBusinessTeam(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-lg p-2 focus:outline-none"
            >
              {TEAMS.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Sliders Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-3 border-t border-slate-100">
          <div className="flex items-center justify-between gap-3">
            <span className="text-[10px] font-black text-slate-450 uppercase whitespace-nowrap">Min Relevance:</span>
            <div className="flex items-center gap-2 flex-1 justify-end">
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={minRelevanceScore}
                onChange={(e) => setMinRelevanceScore(Number(e.target.value))}
                className="w-full accent-blue-600 cursor-pointer"
              />
              <span className="text-xs bg-slate-100 font-mono text-slate-700 px-2 py-0.5 rounded font-bold">{minRelevanceScore}</span>
            </div>
          </div>

          <div className="flex items-center justify-between gap-3">
            <span className="text-[10px] font-black text-slate-450 uppercase whitespace-nowrap">Min Strategic Fit:</span>
            <div className="flex items-center gap-2 flex-1 justify-end">
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={minStrategicFitScore}
                onChange={(e) => setMinStrategicFitScore(Number(e.target.value))}
                className="w-full accent-indigo-600 cursor-pointer"
              />
              <span className="text-xs bg-slate-100 font-mono text-slate-700 px-2 py-0.5 rounded font-bold">{minStrategicFitScore}</span>
            </div>
          </div>

          <div className="flex items-center justify-between gap-3">
            <span className="text-[10px] font-black text-slate-450 uppercase whitespace-nowrap">Min Priority:</span>
            <div className="flex items-center gap-2 flex-1 justify-end">
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={minPriorityScore}
                onChange={(e) => setMinPriorityScore(Number(e.target.value))}
                className="w-full accent-orange-550 accent-orange-500 cursor-pointer"
              />
              <span className="text-xs bg-slate-100 font-mono text-slate-700 px-2 py-0.5 rounded font-bold">{minPriorityScore}</span>
            </div>
          </div>
        </div>

        {/* Standard Taxonomy Filters Row */}
        <div className="flex flex-wrap gap-2.5 pt-3 border-t border-slate-100">
          <select
            value={selectedIndustry}
            onChange={(e) => setSelectedIndustry(e.target.value)}
            className="bg-slate-50 border border-slate-200 text-slate-700 text-[11px] rounded-lg p-1.5"
          >
            <option value="All Industries">All Industries</option>
            {TAXONOMY.industries.map((ind) => (
              <option key={ind.name} value={ind.name}>{ind.name}</option>
            ))}
          </select>

          <select
            value={selectedSector}
            onChange={(e) => setSelectedSector(e.target.value)}
            className="bg-slate-50 border border-slate-200 text-slate-700 text-[11px] rounded-lg p-1.5"
          >
            {sectorOptions.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          <select
            value={selectedSubsector}
            onChange={(e) => setSelectedSubsector(e.target.value)}
            className="bg-slate-50 border border-slate-200 text-slate-700 text-[11px] rounded-lg p-1.5"
          >
            {subsectorOptions.map((sub) => (
              <option key={sub} value={sub}>{sub}</option>
            ))}
          </select>

          <select
            value={selectedStage}
            onChange={(e) => setSelectedStage(e.target.value)}
            className="bg-slate-50 border border-slate-200 text-slate-700 text-[11px] rounded-lg p-1.5"
          >
            <option value="All Stages">All Stages</option>
            {TAXONOMY.stages.map((stg) => (
              <option key={stg} value={stg}>{stg}</option>
            ))}
          </select>

          {(selectedIndustry !== "All Industries" || selectedSector !== "All Sectors" || selectedEntity !== "All Entities" || selectedPriorityBand !== "All Bands" || minPriorityScore > 0) && (
            <button
              onClick={clearSearch}
              className="text-xs text-rose-600 hover:text-rose-800 font-bold bg-transparent border-0 cursor-pointer ml-auto"
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Upgraded Table List */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden" id="repository-grid-section">
        <div className="p-4 border-b border-indigo-650 bg-slate-900 flex justify-between items-center text-white select-none">
          <h4 className="font-black text-xs uppercase tracking-wider">
            Supabase Corporate Registry ({filteredRepository.length} Startups)
          </h4>
          <span className="text-[10px] bg-indigo-500/20 text-indigo-300 font-mono py-0.5 px-2 rounded-full border border-indigo-500/30">
            Real-time Table
          </span>
        </div>

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
              <col style={{ width: `${colWidths.priorityBand}px` }} />
              <col style={{ width: `${colWidths.recommendedAction}px` }} />
              <col style={{ width: `${colWidths.primaryEntity}px` }} />
              <col style={{ width: `${colWidths.businessTeam}px` }} />
              <col style={{ width: `${colWidths.confidenceScore}px` }} />
              <col style={{ width: `${colWidths.priority}px` }} />
              <col style={{ width: `${colWidths.trialStatus}px` }} />
            </colgroup>
            <thead>
              <tr className="bg-slate-50 text-slate-500 text-[10px] uppercase font-bold border-b border-slate-100 select-none">
                <th className="py-3 px-4 relative group">
                  <span className="truncate block">Startup</span>
                  <div
                    onMouseDown={(e) => startResize("startup", e)}
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-indigo-500/80 hover:w-1.5 transition-all select-none z-10"
                    style={{ borderRight: "2px solid #cbd5e1" }}
                  />
                </th>
                <th className="py-3 px-4 relative group">
                  <span className="truncate block">Priority Band</span>
                  <div
                    onMouseDown={(e) => startResize("priorityBand", e)}
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-indigo-500/80 hover:w-1.5 transition-all select-none z-10"
                    style={{ borderRight: "2px solid #cbd5e1" }}
                  />
                </th>
                <th className="py-3 px-4 relative group">
                  <span className="truncate block">Action</span>
                  <div
                    onMouseDown={(e) => startResize("recommendedAction", e)}
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-indigo-500/80 hover:w-1.5 transition-all select-none z-10"
                    style={{ borderRight: "2px solid #cbd5e1" }}
                  />
                </th>
                <th className="py-3 px-4 relative group">
                  <span className="truncate block">Primary Entity</span>
                  <div
                    onMouseDown={(e) => startResize("primaryEntity", e)}
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-indigo-500/80 hover:w-1.5 transition-all select-none z-10"
                    style={{ borderRight: "2px solid #cbd5e1" }}
                  />
                </th>
                <th className="py-3 px-4 relative group">
                  <span className="truncate block">Business Team</span>
                  <div
                    onMouseDown={(e) => startResize("businessTeam", e)}
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-indigo-500/80 hover:w-1.5 transition-all select-none z-10"
                    style={{ borderRight: "2px solid #cbd5e1" }}
                  />
                </th>
                <th className="py-3 px-4 text-center relative group">
                  <span className="truncate block">Confidence</span>
                  <div
                    onMouseDown={(e) => startResize("confidenceScore", e)}
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
                <th className="py-3 px-4 text-right relative">
                  <span className="truncate block">Trial Status</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {filteredRepository.map((s) => {
                const semanticExplain = semanticActive
                  ? semanticMatches.find((m) => String(m.id) === String(s.id))?.explanation
                  : null;

                const primaryEntity = s.matched_entities?.[0] || Object.keys(s.relevance_mapping || {})?.[0] || "ICICI Bank";
                const businessTeam = s.matched_business_teams?.[0] || s.assigned_team || "Lending Team";
                const confidence = s.confidence_score || 0;

                return (
                  <tr
                    key={s.id}
                    onClick={() => onSelectStartup(s)}
                    className="hover:bg-slate-50/50 cursor-pointer transition-all"
                  >
                    {/* Startup Details */}
                    <td className="py-4 px-4 space-y-1 text-left overflow-hidden">
                      <div className="flex items-center gap-1 truncate">
                        <span className="font-extrabold text-slate-900 hover:text-blue-600 truncate">{s.startup_name}</span>
                      </div>
                      <p className="text-slate-500 text-[11px] line-clamp-2 leading-relaxed mt-1 whitespace-normal">
                        {s.ai_summary}
                      </p>
                      <div className="flex flex-wrap items-center gap-3 mt-1.5 text-[10px] text-slate-400 select-none">
                        {s.website && s.website.trim() !== "" && (
                          <a
                            href={s.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 hover:text-blue-650 transition-colors"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <Globe size={11} className="text-slate-450" />
                            <span className="underline">Website</span>
                          </a>
                        )}
                        {s.source_url && (
                          <a
                            href={s.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 hover:text-blue-650 transition-colors"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <ExternalLink size={11} className="text-slate-450" />
                            <span className="underline">{s.source || "Article"}</span>
                          </a>
                        )}
                      </div>
                      {semanticExplain && (
                        <div className="bg-amber-50 border border-amber-200 text-amber-900 p-2 rounded text-[10px] mt-2 flex items-start gap-1 whitespace-normal">
                          <Sparkles size={11} className="text-amber-505 text-amber-500 flex-shrink-0 mt-0.5" />
                          <span>{semanticExplain}</span>
                        </div>
                      )}
                    </td>

                    {/* Priority Band */}
                    <td className="py-3 px-4 text-left overflow-hidden">
                      <span className={`inline-block text-[10px] font-black px-2 py-0.5 rounded uppercase ${
                        s.priority_band === "Critical" ? "bg-rose-100 text-rose-800 border border-rose-250" :
                        s.priority_band === "High" ? "bg-orange-100 text-orange-800 border border-orange-250" :
                        s.priority_band === "Medium" ? "bg-amber-105 bg-amber-100 text-amber-800 border border-amber-250" :
                        s.priority_band === "Low" ? "bg-blue-100 text-blue-800 border border-blue-200" :
                        "bg-slate-100 text-slate-600 border border-slate-200"
                      }`}>
                        {s.priority_band || "Ignore"}
                      </span>
                    </td>

                    {/* Action */}
                    <td className="py-3 px-4 text-left overflow-hidden">
                      <span className="inline-block bg-slate-100 border border-slate-200 text-slate-700 font-bold px-2 py-0.5 rounded text-[10px] uppercase truncate max-w-full">
                        {s.recommended_action || "Monitor"}
                      </span>
                    </td>

                    {/* Sponsoring Entity */}
                    <td className="py-3 px-4 font-bold text-slate-700 overflow-hidden truncate">
                      {primaryEntity}
                    </td>

                    {/* Sponsoring Team */}
                    <td className="py-3 px-4 font-semibold text-slate-600 overflow-hidden truncate">
                      {businessTeam}
                    </td>

                    {/* Confidence Score */}
                    <td className="py-3 px-4 text-center overflow-hidden font-mono font-black text-emerald-600 text-xs">
                      {confidence}%
                    </td>

                    {/* Priority Score */}
                    <td className="py-3 px-4 text-center overflow-hidden">
                      <span className={`inline-block font-mono font-bold text-xs px-2 py-0.5 rounded-full ${
                        (s.priority_score || 0) >= 90
                          ? "bg-red-100 text-red-700"
                          : (s.priority_score || 0) >= 80
                          ? "bg-amber-105 bg-amber-100 text-amber-700"
                          : "bg-slate-100 text-slate-700"
                      }`}>
                        {s.priority_score || 0}
                      </span>
                    </td>

                    {/* Trial Status */}
                    <td className="py-3 px-4 text-right overflow-hidden select-none">
                      <span className={`inline-block text-[10px] font-black px-2.5 py-1 rounded truncate ${
                        s.status === "Partnership"
                          ? "bg-emerald-100 text-emerald-800 border border-emerald-250"
                          : s.status === "Proof of Concept"
                          ? "bg-blue-100 text-blue-800 border border-blue-250"
                          : s.status === "Evaluation"
                          ? "bg-amber-100 text-amber-800 border border-amber-250"
                          : "bg-slate-100 text-slate-655 text-slate-600 border border-slate-205"
                      }`}>
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
                    className="w-full bg-slate-55 bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-2 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
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

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10.5px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                    Industry
                  </label>
                  <select
                    value={newStartup.industry}
                    onChange={(e) => setNewStartup({ ...newStartup, industry: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-2 focus:ring-1 focus:ring-indigo-500"
                  >
                    {TAXONOMY.industries.map((ind) => (
                      <option key={ind.name} value={ind.name}>
                        {ind.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-[10.5px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                    Sector
                  </label>
                  <select
                    value={newStartup.sector}
                    onChange={(e) => setNewStartup({ ...newStartup, sector: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-2 focus:ring-1 focus:ring-indigo-500"
                  >
                    {(TAXONOMY.industries.find((i) => i.name === newStartup.industry)?.sectors ? Object.keys(TAXONOMY.industries.find((i) => i.name === newStartup.industry)!.sectors) : []).map((sec) => (
                      <option key={sec} value={sec}>
                        {sec}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[10.5px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                    Sub Sector
                  </label>
                  <select
                    value={newStartup.subsector}
                    onChange={(e) => setNewStartup({ ...newStartup, subsector: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-2 focus:ring-1 focus:ring-indigo-500"
                  >
                    {(TAXONOMY.industries.find((i) => i.name === newStartup.industry)?.sectors[newStartup.sector] || []).map((sub) => (
                      <option key={sub} value={sub}>
                        {sub}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-[10.5px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                    Funding Stage
                  </label>
                  <select
                    value={newStartup.funding_stage}
                    onChange={(e) => setNewStartup({ ...newStartup, funding_stage: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-2 focus:ring-1 focus:ring-indigo-500"
                  >
                    {TAXONOMY.stages.map((stg) => (
                      <option key={stg} value={stg}>
                        {stg}
                      </option>
                    ))}
                  </select>
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
                    className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-2 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10.5px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">
                  Business Models
                </label>
                <div className="grid grid-cols-3 gap-2 bg-slate-50 p-2.5 rounded-lg border border-slate-200 max-h-28 overflow-y-auto">
                  {TAXONOMY.business_models.map((bm) => (
                    <label key={bm} className="flex items-center gap-1.5 text-xs text-slate-700 font-semibold cursor-pointer">
                      <input
                        type="checkbox"
                        checked={newStartup.business_models.includes(bm)}
                        onChange={(e) => {
                          const updated = e.target.checked
                            ? [...newStartup.business_models, bm]
                            : newStartup.business_models.filter((x) => x !== bm);
                          setNewStartup({ ...newStartup, business_models: updated });
                        }}
                        className="accent-blue-600 rounded"
                      />
                      <span>{bm}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-[11px] text-slate-500 flex items-start gap-2">
                <Sparkles size={14} className="text-amber-500 mt-0.5 flex-shrink-0" />
                <p>
                  <strong>AI Enrichment active:</strong> Submitting this form triggers a database entry. You can run immediate evaluations to score corporate readiness and co-creation fits in the detail drawer!
                </p>
              </div>

              <div className="flex gap-2 justify-end pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs px-4 py-2 rounded-lg font-semibold transition-all cursor-pointer border-0"
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
            <div className="p-5 border-b border-indigo-600 bg-slate-900 text-white flex justify-between items-center">
              <div className="flex items-center gap-2">
                <Upload size={18} className="text-indigo-400" />
                <h4 className="font-bold text-sm">Automated CSV Data Importer Desk</h4>
              </div>
              <button onClick={() => setShowCSVModal(false)} className="text-white hover:text-slate-350 cursor-pointer border-0 bg-transparent">
                <X size={18} />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="text-xs text-slate-655 text-slate-600 leading-relaxed">
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
                    className="text-[10px] text-blue-650 hover:underline font-bold flex items-center gap-1 bg-transparent border-0 cursor-pointer animate-pulse-subtle"
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
                  className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-[11px] font-mono rounded-lg p-2.5 focus:ring-1 focus:ring-blue-500 focus:outline-none"
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
                <strong className="text-slate-700">Sandbox Rule check:</strong> Pre-existing/duplicate startup records are omitted to prevent redundancy errors. Newly imported files undergo automated category-team mapping.
              </div>

              <div className="flex gap-2 justify-end pt-3 border-t border-slate-100">
                <button
                  onClick={() => setShowCSVModal(false)}
                  className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs px-4 py-2 rounded-lg font-semibold border-0 cursor-pointer"
                >
                  Close Desk
                </button>
                <button
                  onClick={handleCSVSubmit}
                  disabled={csvLoading}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs px-5 py-2 rounded-lg font-semibold shadow-sm transition-all border-0 cursor-pointer"
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
