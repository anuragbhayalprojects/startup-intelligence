import React from 'react';
import {
  LayoutDashboard,
  MessageSquare
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  return (
    <aside className="w-72 bg-slate-900 text-slate-100 flex flex-col border-r border-slate-800" id="platform-sidebar">
      {/* Brand Header */}
      <div className="p-6 border-b border-slate-800 flex items-center justify-between" id="brand-header">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-orange-500 rounded-lg text-slate-900 font-bold flex items-center justify-center shadow-lg shadow-orange-500/10">
            <LayoutDashboard size={20} />
          </div>
          <div>
            <h1 className="font-bold text-md tracking-tight bg-gradient-to-r from-white to-amber-400 bg-clip-text text-transparent">
              Startup OS
            </h1>
            <p className="text-xs text-slate-400 font-medium">Intelligence Platform</p>
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
          onClick={() => setActiveTab("dashboard")}
          className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
            activeTab === "dashboard"
              ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500 font-semibold"
              : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
          }`}
        >
          <div className="flex items-center gap-2.5">
            <LayoutDashboard size={18} />
            <span>Dashboard</span>
          </div>
        </button>

        <button
          id="nav-chat"
          onClick={() => setActiveTab("chat")}
          className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
            activeTab === "chat"
              ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500 font-semibold"
              : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
          }`}
        >
          <div className="flex items-center gap-2.5">
            <MessageSquare size={18} />
            <span>Chat</span>
          </div>
        </button>
      </nav>
    </aside>
  );
};

export default Sidebar;
