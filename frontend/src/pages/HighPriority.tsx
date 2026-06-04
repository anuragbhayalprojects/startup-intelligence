import React, { useState, useMemo } from "react";
import {
  Flame,
  Award,
  ArrowUpRight,
  ShieldAlert,
  Search,
  ExternalLink,
  ChevronRight,
  Sparkles,
  Layers,
  Activity,
  Milestone,
  Filter
} from "lucide-react";
import { Startup } from "../types";
import { TAXONOMY } from "../lib/taxonomy";

interface HighPriorityProps {
  startups: Startup[];
  onSelectStartup: (startup: Startup) => void;
}

export default function HighPriority({ startups, onSelectStartup }: HighPriorityProps) {
  // Filters State
  const [selectedIndustry, setSelectedIndustry] = useState("All Industries");
  const [selectedSector, setSelectedSector] = useState("All Sectors");
  const [selectedSubsector, setSelectedSubsector] = useState("All Subsectors");
  const [selectedStage, setSelectedStage] = useState("All Stages");
  const [selectedBusinessModel, setSelectedBusinessModel] = useState("All Models");

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

  React.useEffect(() => {
    setSelectedSector("All Sectors");
    setSelectedSubsector("All Subsectors");
  }, [selectedIndustry]);

  React.useEffect(() => {
    setSelectedSubsector("All Subsectors");
  }, [selectedSector]);

  // Filtered List
  const highPriorityList = useMemo(() => {
    let list = startups.filter((s) => (s.priority_score || 0) >= 90);

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
      list = list.filter((s) => s.funding_stage === selectedStage);
    }
    if (selectedBusinessModel !== "All Models") {
      list = list.filter((s) => s.business_models && s.business_models.some((bm) => bm.toLowerCase() === selectedBusinessModel.toLowerCase()));
    }
    return list;
  }, [startups, selectedIndustry, selectedSector, selectedSubsector, selectedStage, selectedBusinessModel]);

  return (
    <div className="space-y-6" id="high-priority-startups-panel">
      {/* Banner */}
      <div className="bg-slate-900 text-slate-100 p-6 rounded-xl border-l-4 border-amber-500 shadow-lg flex flex-col md:flex-row justify-between items-start md:items-center gap-4 text-left">
        <div>
          <span className="bg-amber-500/10 text-amber-400 text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider">
            Critical Action Targets
          </span>
          <h2 className="text-xl font-bold text-white tracking-tight mt-2 flex items-center gap-2">
            Priority-1 Strategic Portfolios <Flame className="text-amber-500" size={20} />
          </h2>
          <p className="text-slate-400 text-xs mt-1">
            Fintechs scoring ≥ 90 represent maximum readiness and value for immediate ICICI Bank / Lombard / AMC sandbox piloting.
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-xs bg-slate-800 p-2 rounded-lg border border-slate-700 font-mono text-slate-300">
          <ShieldAlert size={14} className="text-amber-500 animate-pulse" />
          <span>Active files: {highPriorityList.length}</span>
        </div>
      </div>

      {/* Dynamic Filters */}
      <div className="bg-slate-50 border border-slate-200/80 p-4 rounded-xl flex flex-wrap gap-4 items-center" id="high-priority-filters">
        <div className="flex items-center gap-2 text-xs text-slate-550 font-bold">
          <Filter size={14} />
          <span>Filters:</span>
        </div>

        {/* Industry */}
        <div className="space-y-1">
          <select
            value={selectedIndustry}
            onChange={(e) => setSelectedIndustry(e.target.value)}
            className="bg-white border border-slate-200 text-slate-700 text-xs rounded-lg p-1.5 focus:outline-none"
          >
            <option value="All Industries">All Industries</option>
            {TAXONOMY.industries.map((ind) => (
              <option key={ind.name} value={ind.name}>
                {ind.name}
              </option>
            ))}
          </select>
        </div>

        {/* Sector */}
        <div className="space-y-1">
          <select
            value={selectedSector}
            onChange={(e) => setSelectedSector(e.target.value)}
            className="bg-white border border-slate-200 text-slate-700 text-xs rounded-lg p-1.5 focus:outline-none"
          >
            {sectorOptions.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {/* Sub Sector */}
        <div className="space-y-1">
          <select
            value={selectedSubsector}
            onChange={(e) => setSelectedSubsector(e.target.value)}
            className="bg-white border border-slate-200 text-slate-700 text-xs rounded-lg p-1.5 focus:outline-none"
          >
            {subsectorOptions.map((sub) => (
              <option key={sub} value={sub}>
                {sub}
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
            <option value="All Stages">All Stages</option>
            {TAXONOMY.stages.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {/* Business Model */}
        <div className="space-y-1">
          <select
            value={selectedBusinessModel}
            onChange={(e) => setSelectedBusinessModel(e.target.value)}
            className="bg-white border border-slate-200 text-slate-700 text-xs rounded-lg p-1.5 focus:outline-none"
          >
            <option value="All Models">All Models</option>
            {TAXONOMY.business_models.map((bm) => (
              <option key={bm} value={bm}>
                {bm}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Grid of high priority targets */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-left" id="high-priority-grid">
        {highPriorityList.map((s) => (
          <div
            key={s.id}
            onClick={() => onSelectStartup(s)}
            className="bg-white rounded-xl border border-slate-200/85 hover:border-slate-350 shadow-sm overflow-hidden flex flex-col justify-between hover:shadow-md transition-all cursor-pointer group"
          >
            {/* Target Header */}
            <div className="p-5 border-b border-slate-100 bg-slate-50/50 flex justify-between items-start">
              <div className="space-y-1">
                <span className="bg-orange-100 text-orange-850 text-[10px] font-bold px-2 py-0.5 rounded uppercase">
                  {s.sector}
                </span>
                <h4 className="font-extrabold text-slate-900 text-base group-hover:text-blue-600 transition-colors mt-1.5 leading-snug">
                  {s.startup_name}
                </h4>
                <p className="text-xs text-slate-400 font-mono">{s.subsector || s.subSector || "Innovation"}</p>
              </div>

              <div className="text-center">
                <span className="text-xs font-bold text-red-650 bg-red-50 py-1 px-2.5 rounded-full border border-red-200 font-mono">
                  {s.priority_score} Score
                </span>
              </div>
            </div>

            {/* Assessment and Relevance summary */}
            <div className="p-5 flex-1 space-y-4">
              <div className="space-y-1">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 flex items-center gap-1">
                  <Sparkles size={11} className="text-indigo-500 animate-pulse" /> Gemini Pilot Evaluation
                </p>
                <p className="text-slate-600 text-xs leading-relaxed italic pr-2">
                  "{s.ai_summary}"
                </p>
              </div>

              <div className="grid grid-cols-1 gap-2 pt-2 border-t border-slate-100">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Target Integration Scope</p>
                <div className="space-y-1">
                  {s.use_cases && s.use_cases.map((uc, idx) => (
                    <div key={idx} className="flex gap-2 items-start py-1 text-xs text-slate-600">
                      <div className="h-1.5 w-1.5 rounded-full bg-indigo-500 flex-shrink-0 mt-1.5"></div>
                      <span className="leading-tight">{uc}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Target Footer Action */}
            <div className="p-4 bg-slate-50 border-t border-slate-100 flex justify-between items-center text-xs">
              <p className="text-slate-400 font-medium">Auto assigned to: <strong className="text-slate-700">{s.assigned_team}</strong></p>
              <span className="text-blue-650 hover:text-blue-700 font-bold group-hover:translate-x-1 transition-all flex items-center gap-0.5 cursor-pointer">
                Expose Sandbox Trial <ChevronRight size={14} />
              </span>
            </div>
          </div>
        ))}

        {highPriorityList.length === 0 && (
          <div className="bg-white col-span-2 p-12 text-center rounded-xl border border-slate-200 text-slate-400 font-medium">
            Currently no targets matching priority scores ≥ 90 in registry. Start adding or custom uploading high-relevance ventures!
          </div>
        )}
      </div>
    </div>
  );
}
