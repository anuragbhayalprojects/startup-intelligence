import React from "react";
import {
  TrendingUp,
  Database,
  Briefcase,
  Layers,
  Sparkles,
  ArrowRightLeft,
  ChevronRight,
  ShieldCheck,
  User,
  Zap,
  MessageSquare
} from "lucide-react";
import { AppTab, UserRole } from "../types";

interface SidebarProps {
  activeTab: AppTab;
  onTabChange: (tab: AppTab) => void;
  currentUser: UserRole;
  onUserChange: (user: UserRole) => void;
  totalCount: number;
  highPriorityCount: number;
}

const ROLES: UserRole[] = [
  { username: "Rajesh Kumar", role: "Admin" },
  { username: "Pooja Mehta", role: "Investment Officer" },
  { username: "Sandeep Bakhshi", role: "ICICI Entity Stakeholder", entity: "ICICI Lombard" },
  { username: "Ananya Sen", role: "ICICI Entity Stakeholder", entity: "ICICI Securities" }
];

export default function Sidebar({
  activeTab,
  onTabChange,
  currentUser,
  onUserChange,
  totalCount,
  highPriorityCount
}: SidebarProps) {
  return (
    <aside className="w-72 bg-slate-900 text-slate-100 flex flex-col border-r border-slate-800" id="platform-sidebar">
      {/* Brand Header */}
      <div className="p-6 border-b border-slate-800 flex items-center justify-between" id="brand-header">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-orange-500 rounded-lg text-slate-900 font-bold flex items-center justify-center shadow-lg shadow-orange-500/10">
            <TrendingUp size={20} />
          </div>
          <div>
            <h1 className="font-bold text-md tracking-tight bg-gradient-to-r from-white to-amber-400 bg-clip-text text-transparent">
              ICICI Group
            </h1>
            <p className="text-xs text-slate-400 font-medium">Startup Intelligence</p>
          </div>
        </div>
      </div>

      {/* Nav Actions */}
      <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto" id="sidebar-navigation">
        <p className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
          Intelligence Desk
        </p>

        <button
          id="nav-dashboard"
          onClick={() => onTabChange("dashboard")}
          className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
            activeTab === "dashboard"
              ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500 font-semibold"
              : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
          }`}
        >
          <div className="flex items-center gap-2.5">
            <Zap size={18} />
            <span>Dashboard Overview</span>
          </div>
          <ChevronRight size={14} className="opacity-40" />
        </button>

        <button
          id="nav-repository"
          onClick={() => onTabChange("repository")}
          className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
            activeTab === "repository"
              ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500 font-semibold"
              : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
          }`}
        >
          <div className="flex items-center gap-2.5">
            <Layers size={18} />
            <span>Startup Repository</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-400 font-mono font-bold">
              {totalCount}
            </span>
            <ChevronRight size={14} className="opacity-40" />
          </div>
        </button>

        <button
          id="nav-high-priority"
          onClick={() => onTabChange("high-priority")}
          className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
            activeTab === "high-priority"
              ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500 font-semibold"
              : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
          }`}
        >
          <div className="flex items-center gap-2.5">
            <Sparkles size={18} className="text-amber-400" />
            <span>High Priority Startups</span>
          </div>
          <div className="flex items-center gap-1">
            {highPriorityCount > 0 && (
              <span className="text-[10px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded font-bold font-mono">
                {highPriorityCount}
              </span>
            )}
            <ChevronRight size={14} className="opacity-40" />
          </div>
        </button>

        <button
          id="nav-assignments"
          onClick={() => onTabChange("assignments")}
          className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
            activeTab === "assignments"
              ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500 font-semibold"
              : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
          }`}
        >
          <div className="flex items-center gap-2.5">
            <ArrowRightLeft size={18} />
            <span>Assignment Tracker</span>
          </div>
          <ChevronRight size={14} className="opacity-40" />
        </button>

        <button
          id="nav-insights"
          onClick={() => onTabChange("insights")}
          className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
            activeTab === "insights"
              ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500 font-semibold"
              : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
          }`}
        >
          <div className="flex items-center gap-2.5">
            <Briefcase size={18} />
            <span>AI Strategic Desk</span>
          </div>
          <ChevronRight size={14} className="opacity-40" />
        </button>

        <button
          id="nav-chat"
          onClick={() => onTabChange("chat")}
          className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
            activeTab === "chat"
              ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500 font-semibold"
              : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
          }`}
        >
          <div className="flex items-center gap-2.5">
            <MessageSquare size={18} />
            <span>Assistant Chat</span>
          </div>
          <ChevronRight size={14} className="opacity-40" />
        </button>

        <div className="pt-6">
          <p className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
            Backing Systems
          </p>
          <button
            id="nav-scraping"
            onClick={() => onTabChange("scraping")}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all mb-1 ${
              activeTab === "scraping"
                ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500 font-semibold"
                : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
            }`}
          >
            <div className="flex items-center gap-2.5">
              <Zap size={18} className="text-amber-500" />
              <span>Scraping Console</span>
            </div>
            <ChevronRight size={14} className="opacity-40" />
          </button>

          <button
            id="nav-database"
            onClick={() => onTabChange("database")}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "database"
                ? "bg-cyan-500/10 text-cyan-400 border-l-2 border-cyan-500 font-semibold"
                : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
            }`}
          >
            <div className="flex items-center gap-2.5">
              <Database size={18} />
              <span>Supabase Console</span>
            </div>
            <ChevronRight size={14} className="opacity-40" />
          </button>
        </div>
      </nav>

      {/* Role Manager */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/70" id="role-manager">
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-semibold uppercase tracking-widest">
            <ShieldCheck size={12} className="text-amber-500" />
            <span>Session Identity</span>
          </div>
          <span className="text-[9px] bg-slate-800 text-slate-300 font-mono py-0.5 px-1.5 rounded">
            Role Auth
          </span>
        </div>

        <select
          id="identity-selector"
          value={currentUser.username}
          onChange={(e) => {
            const found = ROLES.find((r) => r.username === e.target.value);
            if (found) onUserChange(found);
          }}
          className="w-full bg-slate-900 border border-slate-800 text-slate-200 text-xs rounded-lg py-1.5 px-2.5 focus:ring-1 focus:ring-orange-500 focus:outline-none mb-3"
        >
          {ROLES.map((r) => (
            <option key={r.username} value={r.username}>
              {r.username} ({r.role})
            </option>
          ))}
        </select>

        <div className="flex items-center gap-2 bg-slate-900 p-2 rounded-lg border border-slate-800">
          <div className="h-8 w-8 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-500 flex items-center justify-center text-xs font-bold">
            <User size={14} />
          </div>
          <div className="overflow-hidden">
            <p className="text-xs font-medium text-slate-200 truncate">{currentUser.username}</p>
            <p className="text-[10px] text-slate-500 truncate text-left">
              {currentUser.role} {currentUser.entity ? `• ${currentUser.entity}` : ""}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
