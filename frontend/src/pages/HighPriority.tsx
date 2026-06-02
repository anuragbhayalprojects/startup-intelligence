import React from "react";
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
  Milestone
} from "lucide-react";
import { Startup } from "../types";

interface HighPriorityProps {
  startups: Startup[];
  onSelectStartup: (startup: Startup) => void;
}

export default function HighPriority({ startups, onSelectStartup }: HighPriorityProps) {
  const highPriorityList = startups.filter((s) => (s.priority_score || 0) >= 90);

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
