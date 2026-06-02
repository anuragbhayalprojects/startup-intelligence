import React from "react";
import {
  TrendingUp,
  Layers,
  Sparkles,
  Award,
  Zap,
  PieChart,
  Shield,
  Activity,
  Clock,
  ArrowUpRight
} from "lucide-react";
import { Startup, Assignment, Interaction } from "../types";

interface DashboardProps {
  startups: Startup[];
  assignments: Assignment[];
  interactions: Interaction[];
  onSelectStartup: (startup: Startup) => void;
  onTabChange: (tab: any) => void;
}

export default function Dashboard({
  startups,
  assignments,
  interactions,
  onSelectStartup,
  onTabChange
}: DashboardProps) {
  // Metric Calculations
  const totalCount = startups.length;
  const highPriorityCount = startups.filter((s) => (s.priority_score || 0) >= 90).length;

  // Breakdown by Sector
  const sectorCounts = startups.reduce((acc, s) => {
    acc[s.sector] = (acc[s.sector] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Breakdown by Funding Stage
  const stageCounts = startups.reduce((acc, s) => {
    acc[s.funding_stage] = (acc[s.funding_stage] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Average Priority Score
  const averagePriority = totalCount
    ? Math.round(startups.reduce((acc, s) => acc + (s.priority_score || 0), 0) / totalCount)
    : 0;

  // Active Proof of Concepts / pilots
  const activePocCount = startups.filter(
    (s) => s.status === "Proof of Concept" || s.status === "Partnership" || s.status === "piloting" || s.status === "completed"
  ).length;

  return (
    <div className="space-y-6" id="dashboard-tab-view">
      {/* Dynamic Greeting */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white p-6 rounded-xl border border-slate-200/80 shadow-sm text-left" id="dashboard-hero">
        <div>
          <span className="bg-amber-100 text-amber-800 text-[10px] font-bold px-2 py-1 rounded-full uppercase tracking-wider">
            ICICI Group Corporate Registry
          </span>
          <h2 className="text-2xl font-bold text-slate-905 text-slate-900 tracking-tight mt-2 flex items-center gap-2">
            Executive Hub <TrendingUp className="text-amber-505 text-amber-500" size={22} />
          </h2>
          <p className="text-slate-500 text-sm mt-1">
            Real-time screening, AI assessments, and strategic team routing of global fintech ecosystems.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => onTabChange("repository")}
            className="bg-slate-900 text-white hover:bg-slate-800 text-xs px-4 py-2 rounded-lg font-medium shadow-sm transition-all flex items-center gap-1.5 border-0 cursor-pointer"
          >
            Launch Search Desk <ArrowUpRight size={14} />
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" id="kpi-cards-grid">
        {/* KPI 1 */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm flex items-start justify-between hover:border-slate-350 transition-all text-left">
          <div className="space-y-2">
            <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">Total Scanned</p>
            <h3 className="text-3xl font-extrabold text-slate-900 tracking-tight">{totalCount}</h3>
            <p className="text-[11px] text-slate-400">Unique FinTech entities stored</p>
          </div>
          <div className="p-2.5 bg-blue-50 text-blue-600 rounded-lg">
            <Layers size={20} />
          </div>
        </div>

        {/* KPI 2 */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm flex items-start justify-between hover:border-slate-350 transition-all text-left">
          <div className="space-y-2">
            <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">High Priority</p>
            <h3 className="text-3xl font-extrabold text-amber-600 tracking-tight">{highPriorityCount}</h3>
            <p className="text-[11px] text-amber-600/80 font-medium">Score ≥ 90 (Requires Action)</p>
          </div>
          <div className="p-2.5 bg-amber-50 text-amber-600 rounded-lg">
            <Sparkles size={20} />
          </div>
        </div>

        {/* KPI 3 */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm flex items-start justify-between hover:border-slate-350 transition-all text-left">
          <div className="space-y-2">
            <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">Average Score</p>
            <h3 className="text-3xl font-extrabold text-slate-900 tracking-tight">{averagePriority}/100</h3>
            <p className="text-[11px] text-slate-400">Weighted AI evaluation index</p>
          </div>
          <div className="p-2.5 bg-purple-50 text-purple-600 rounded-lg">
            <Award size={20} />
          </div>
        </div>

        {/* KPI 4 */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm flex items-start justify-between hover:border-slate-350 transition-all text-left">
          <div className="space-y-2">
            <p className="text-xs text-slate-405 text-slate-400 font-bold uppercase tracking-wider">Active Trials / POCs</p>
            <h3 className="text-3xl font-extrabold text-emerald-600 tracking-tight">{activePocCount}</h3>
            <p className="text-[11px] text-emerald-650 text-emerald-600/80 font-medium">Engaged inside active sandbox</p>
          </div>
          <div className="p-2.5 bg-emerald-50 text-emerald-600 rounded-lg">
            <Zap size={20} />
          </div>
        </div>
      </div>

      {/* Charts & Breakdown Rows */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in" id="dashboard-charts-row">
        {/* Sector Distribution */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4 col-span-1 text-left">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
            <h4 className="font-bold text-slate-900 text-sm flex items-center gap-2">
              <PieChart size={16} className="text-blue-500" /> Startups by Sector
            </h4>
            <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
              Market Depth
            </span>
          </div>

          <div className="space-y-3.5">
            {Object.entries(sectorCounts).map(([sector, count]) => {
              const pct = totalCount ? Math.round((count / totalCount) * 100) : 0;
              const sectorColor =
                sector === "InsurTech"
                  ? "bg-blue-500"
                  : sector === "WealthTech"
                  ? "bg-amber-500"
                  : sector === "LendingTech"
                  ? "bg-purple-500"
                  : "bg-teal-500";

              return (
                <div key={sector} className="space-y-1">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-slate-700">{sector}</span>
                    <span className="text-slate-500 font-medium font-mono">
                      {count} ({pct}%)
                    </span>
                  </div>
                  <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div className={`h-full ${sectorColor}`} style={{ width: `${pct}%` }}></div>
                  </div>
                </div>
              );
            })}
            {Object.keys(sectorCounts).length === 0 && (
              <p className="text-xs text-slate-400 py-6 text-center">No sector indicators recorded yet.</p>
            )}
          </div>
        </div>

        {/* Funding Stage distribution */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4 col-span-1 text-left">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
            <h4 className="font-bold text-slate-900 text-sm flex items-center gap-2">
              <TrendingUp size={16} className="text-emerald-500" /> Funding Stages Breakdown
            </h4>
            <span className="text-[10px] bg-slate-100 text-slate-655 text-slate-600 px-2 py-0.5 rounded font-mono">
              Cap Tables
            </span>
          </div>

          <div className="space-y-3">
            {Object.entries(stageCounts).map(([stage, count]) => {
              return (
                <div key={stage} className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-50 border border-slate-100 transition-all">
                  <div className="flex items-center gap-2.5">
                    <div className="h-2 w-2 rounded-full bg-emerald-500"></div>
                    <span className="text-xs font-semibold text-slate-700">{stage}</span>
                  </div>
                  <span className="text-xs text-slate-550 text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded font-mono font-bold">
                    {count}
                  </span>
                </div>
              );
            })}
            {Object.keys(stageCounts).length === 0 && (
              <p className="text-xs text-slate-400 py-6 text-center">No stage data available yet.</p>
            )}
          </div>
        </div>

        {/* Actionable Strategy summary */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4 col-span-1 text-left">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
            <h4 className="font-bold text-slate-900 text-sm flex items-center gap-2">
              <Shield size={16} className="text-orange-500" /> Routing Strategy
            </h4>
            <span className="text-[10px] bg-orange-100 text-orange-850 px-2 py-0.5 rounded font-mono">
              BFSI Teams
            </span>
          </div>

          <div className="text-xs text-slate-600 leading-relaxed space-y-2">
            <p>
              Auto-routing aligns inbound startup submissions securely based on defined sector capabilities:
            </p>
            <div className="grid grid-cols-2 gap-2 pt-1 font-mono text-left">
              <div className="p-2 bg-blue-50 border border-blue-100/50 rounded text-[10px]">
                <strong className="text-blue-700">Insurance Team</strong>
                <p className="text-slate-500">InsurTech files</p>
              </div>
              <div className="p-2 bg-amber-50 border border-amber-100/50 rounded text-[10px]">
                <strong className="text-amber-700 font-semibold">AMC/Securities</strong>
                <p className="text-slate-500">WealthTech files</p>
              </div>
              <div className="p-2 bg-purple-50 border border-purple-100/50 rounded text-[10px]">
                <strong className="text-purple-700">Lending Team</strong>
                <p className="text-slate-500">LendingTech files</p>
              </div>
              <div className="p-2 bg-teal-50 border border-teal-100/50 rounded text-[10px]">
                <strong className="text-teal-700">Enterprise AI</strong>
                <p className="text-slate-500">AI Ops files</p>
              </div>
            </div>
            <p className="text-[10.5px] italic text-slate-400 pt-2 border-t border-slate-100 block">
              Routing tags are continuously synchronized in Supabase tables.
            </p>
          </div>
        </div>
      </div>

      {/* Recent Sandbox Engagements & Active Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6" id="dashboard-bottom-row">
        {/* Startup Activity Feed */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4 text-left">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
            <h4 className="font-bold text-slate-900 text-sm flex items-center gap-2">
              <Activity size={16} className="text-blue-600" /> Recent Startup Registry
            </h4>
            <button onClick={() => onTabChange("repository")} className="text-xs text-blue-605 text-blue-600 font-bold hover:underline bg-transparent border-0 cursor-pointer">
              View All
            </button>
          </div>

          <div className="divide-y divide-slate-100 max-h-[310px] overflow-y-auto pr-1">
            {startups.slice(0, 4).map((s) => (
              <div
                key={s.id}
                onClick={() => onSelectStartup(s)}
                className="py-3 flex items-start justify-between gap-4 cursor-pointer hover:bg-slate-50/50 px-2 rounded-lg transition-all"
              >
                <div>
                  <h5 className="font-bold text-xs text-slate-900 hover:text-blue-600">{s.startup_name}</h5>
                  <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">{s.description}</p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-[9px] bg-slate-100 text-slate-600 font-bold px-1.5 py-0.5 rounded">
                      {s.sector}
                    </span>
                    <span className="text-[9px] font-mono text-slate-400">
                      Score: {s.priority_score}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-blue-605 text-blue-650 bg-blue-50/80 font-semibold px-2 py-0.5 rounded uppercase">
                    {s.status || "Screening"}
                  </span>
                </div>
              </div>
            ))}
            {startups.length === 0 && (
              <p className="text-xs text-slate-400 py-8 text-center">No startups stored inside registry.</p>
            )}
          </div>
        </div>

        {/* Interactions Feed */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4 text-left">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
            <h4 className="font-bold text-slate-900 text-sm flex items-center gap-2">
              <Clock size={16} className="text-amber-500" /> Evaluation logs
            </h4>
            <button onClick={() => onTabChange("assignments")} className="text-xs text-amber-600 font-bold hover:underline bg-transparent border-0 cursor-pointer">
              View Milestones
            </button>
          </div>

          <div className="space-y-4 max-h-[315px] overflow-y-auto pr-1">
            {interactions.slice(0, 3).map((log) => {
              const linked = startups.find((s) => String(s.id) === String(log.startup_id));
              return (
                <div key={log.id} className="relative pl-5 border-l border-slate-200 group pb-1">
                  <div className="absolute -left-[5px] top-1 h-2.5 w-2.5 rounded-full bg-slate-400 group-hover:bg-amber-500 transition-all"></div>
                  <div className="text-[10.5px] text-slate-400 font-mono">
                    {new Date(log.date).toLocaleDateString()} • {log.type}
                  </div>
                  <h5 className="font-bold text-xs text-slate-800 mt-0.5">
                    {linked ? linked.startup_name : "Unregistered"} Engagement log
                  </h5>
                  <p className="text-xs text-slate-600 mt-1 line-clamp-2">{log.summary}</p>
                  <p className="text-[10px] text-amber-700 mt-1 font-mono">
                    Next status: {log.next_steps}
                  </p>
                </div>
              );
            })}
            {interactions.length === 0 && (
              <p className="text-xs text-slate-400 py-8 text-center">No interactive evaluation logs recorded.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
