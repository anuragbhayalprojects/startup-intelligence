import React, { useState } from "react";
import {
  ClipboardList,
  ChevronRight,
  BookOpen,
  RefreshCcw
} from "lucide-react";
import { Startup, Assignment, StartupCategory, UserRole } from "../types";

interface AssignmentsProps {
  startups: Startup[];
  assignments: Assignment[];
  categories: StartupCategory[];
  currentUser: UserRole;
  onUpdateAssignment: (id: string, status: any, notes: string) => Promise<void>;
}

export default function Assignments({
  startups,
  assignments,
  categories,
  currentUser,
  onUpdateAssignment
}: AssignmentsProps) {
  // Editing state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editStatus, setEditStatus] = useState<string>("");
  const [editNotes, setEditNotes] = useState("");
  const [loading, setLoading] = useState(false);

  const startEdit = (as: Assignment) => {
    setEditingId(as.id);
    setEditStatus(as.status);
    setEditNotes(as.notes);
  };

  const saveEdit = async (id: string) => {
    setLoading(true);
    try {
      await onUpdateAssignment(id, editStatus, editNotes);
      setEditingId(null);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // Provide categories seeded list if empty
  const defaultCategories: StartupCategory[] = categories.length > 0 ? categories : [
    { id: "cat-1", sector: "InsurTech", core_focus: "Claims Automation, Micro-Policies, Underwriting AI", icici_owner: "ICICI Lombard & ICICI Prudential Life" },
    { id: "cat-2", sector: "WealthTech", core_focus: "Discount Brokerage, Digital Advisory, Asset Customization", icici_owner: "ICICI Securities & ICICI Prudential AMC" },
    { id: "cat-3", sector: "LendingTech", core_focus: "Alternative Credit Scoring, Instant SME Loans, Credit Cards", icici_owner: "ICICI Bank & ICICI Housing Finance" },
    { id: "cat-4", sector: "AI Ops", core_focus: "Document Intelligence, Fraud Analytics, General Language Ops", icici_owner: "Enterprise AI Team / Group CoE" }
  ];

  return (
    <div className="space-y-6" id="assignment-tracker-panel">
      {/* Top Banner */}
      <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4 text-left">
        <div>
          <span className="bg-blue-105 bg-blue-100 text-blue-800 text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider">
            Operational Routing Console
          </span>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight mt-2 flex items-center gap-2">
            Inter-Department Assignment Tracker
          </h2>
          <p className="text-slate-500 text-xs mt-1">
            Supervise pilots, active engagements, and regulatory clearance status of routed tech partnerships.
          </p>
        </div>
      </div>

      {/* Grid of Tables: left: assignments tracker list, right: categories map info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* ASSIGNMENTS TABLE */}
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden col-span-2">
          <div className="p-4 bg-slate-900 border-b border-indigo-650 border-indigo-600 flex justify-between items-center text-white">
            <h3 className="font-bold text-xs uppercase tracking-wider flex items-center gap-2">
              <ClipboardList size={16} className="text-indigo-400" /> Relational Table: startup_assignments
            </h3>
            <span className="text-[10px] bg-indigo-500/20 text-indigo-300 font-mono py-0.5 px-2 rounded-full border border-indigo-500/30">
              Active pilot files
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-500 text-[10.5px] uppercase font-bold border-b border-slate-100">
                  <th className="py-3 px-4">Partnership / Venture</th>
                  <th className="py-3 px-4">Assigned Unit</th>
                  <th className="py-3 px-4">Sandbox Roadmap</th>
                  <th className="py-3 px-4 text-center">Engagement State</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {assignments.map((as) => {
                  const linked = startups.find((s) => String(s.id) === String(as.startup_id));
                  const isEditing = editingId === as.id;

                  return (
                    <tr key={as.id} className="hover:bg-slate-50/40">
                      <td className="py-4 px-4 space-y-1 text-left">
                        <span className="font-bold text-slate-905 text-slate-900 text-xs">
                          {linked ? linked.startup_name : "Unknown Venture"}
                        </span>
                        <div className="text-[10px] text-slate-400 font-mono">
                          ID: {as.id} • Assigned: {new Date(as.assigned_at).toLocaleDateString()}
                        </div>
                      </td>

                      <td className="py-4 px-4 space-y-1 text-left">
                        <p className="font-bold text-slate-800 text-xs">{as.entity}</p>
                        <p className="text-[10px] text-indigo-650 text-indigo-650 font-mono">{as.team}</p>
                      </td>

                      <td className="py-4 px-4 text-left">
                        {isEditing ? (
                          <textarea
                            value={editNotes}
                            onChange={(e) => setEditNotes(e.target.value)}
                            className="w-full bg-slate-50 border border-slate-200 rounded text-xs p-1.5 focus:outline-none"
                            rows={2}
                          />
                        ) : (
                          <p className="text-slate-655 text-slate-600 text-xs leading-relaxed max-w-[240px] italic">
                            "{as.notes || "No additional directives."}"
                          </p>
                        )}
                      </td>

                      <td className="py-4 px-4 text-center">
                        {isEditing ? (
                          <select
                            value={editStatus}
                            onChange={(e) => setEditStatus(e.target.value)}
                            className="bg-white border border-slate-200 rounded text-xs p-1 focus:outline-none"
                          >
                            <option value="pending">pending</option>
                            <option value="piloting">piloting</option>
                            <option value="onhold">onhold</option>
                            <option value="completed">completed</option>
                          </select>
                        ) : (
                          <span
                            className={`inline-block py-0.5 px-2.5 rounded text-[10.5px] font-mono font-bold uppercase ${
                              as.status === "completed" || as.status === "Completed"
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : as.status === "piloting" || as.status === "Active Engagement"
                                ? "bg-blue-50 text-blue-700 border border-blue-200"
                                : as.status === "onhold" || as.status === "On Hold"
                                ? "bg-amber-50 text-amber-700 border border-amber-200"
                                : "bg-slate-50 text-slate-600 border border-slate-200"
                            }`}
                          >
                            {as.status}
                          </span>
                        )}
                      </td>

                      <td className="py-4 px-4 text-right">
                        {isEditing ? (
                          <div className="flex justify-end gap-1.5">
                            <button
                              onClick={() => setEditingId(null)}
                              className="text-slate-400 hover:text-slate-600 font-extrabold text-[11px] bg-transparent border-0 cursor-pointer"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => saveEdit(as.id)}
                              disabled={loading}
                              className="text-blue-600 font-bold hover:underline text-[11px] bg-transparent border-0 cursor-pointer"
                            >
                              Save
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => startEdit(as)}
                            disabled={currentUser.role === "ICICI Entity Stakeholder"}
                            className="text-blue-650 hover:text-blue-700 font-bold hover:underline text-xs disabled:opacity-30 flex items-center gap-1 ml-auto bg-transparent border-0 cursor-pointer"
                          >
                            Modify
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {assignments.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-400">
                      No matching task assignments recorded in table. Add records through a startup detail.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* STARTUP CATEGORIES */}
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden flex flex-col text-left">
          <div className="p-4 bg-slate-900 border-b border-orange-500 text-white flex justify-between items-center">
            <h3 className="font-bold text-xs uppercase tracking-wider flex items-center gap-2">
              <BookOpen size={16} className="text-orange-400" /> Relational Table: categories
            </h3>
          </div>

          <div className="p-4 space-y-4 flex-1 overflow-y-auto">
            {defaultCategories.map((cat) => (
              <div key={cat.id} className="p-4 bg-slate-50 rounded-xl border border-slate-150 space-y-2 hover:border-slate-300 transition-all">
                <div className="flex justify-between items-center border-b border-slate-100 pb-1.5">
                  <span className="font-extrabold text-xs text-indigo-950 uppercase tracking-wider">{cat.sector}</span>
                  <span className="text-[10px] font-mono text-slate-400">ID: {cat.id}</span>
                </div>
                <div className="space-y-1">
                  <p className="text-[10px] uppercase font-bold text-slate-400">Core Focus Topics:</p>
                  <p className="text-slate-750 text-xs leading-relaxed">{cat.core_focus}</p>
                </div>
                <div className="space-y-1 pt-2 border-t border-slate-100/60">
                  <p className="text-[10px] uppercase font-bold text-slate-405 text-slate-400">ICICI Internal Sponsors:</p>
                  <p className="text-indigo-650 text-xs font-bold leading-relaxed">{cat.icici_owner}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
