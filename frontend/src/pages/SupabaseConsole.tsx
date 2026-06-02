import React, { useState } from "react";
import {
  Database,
  Play,
  RefreshCw,
  Terminal,
  Table,
  Info,
  ShieldCheck
} from "lucide-react";
import { DBConsoleState } from "../types";

interface SupabaseConsoleProps {
  onRunSQL: (query: string) => Promise<any>;
}

const SCHEMAS = [
  {
    name: "startups",
    comment: "Core registry of screened startups, sectors, and prioritized pilot scores.",
    columns: [
      { name: "id", type: "text (PK)", comment: "Unique startup primary key" },
      { name: "startup_name", type: "text", comment: "Venture business name" },
      { name: "description", type: "text", comment: "Core innovation summary" },
      { name: "website", type: "text", comment: "Venture URL" },
      { name: "sector", type: "text", comment: "Mapped ecosystem hub" },
      { name: "funding_stage", type: "text", comment: "Stage category" },
      { name: "priority_score", type: "integer", comment: "Suitability alignment rating (0-100)" }
    ]
  },
  {
    name: "startup_analysis",
    comment: "Detailed AI evaluations covering strategic fit, enterprise readiness, and target usecases.",
    columns: [
      { name: "id", type: "text (PK)", comment: "Analysis record primary key" },
      { name: "startup_id", type: "text (FK)", comment: "References startups.id" },
      { name: "bfsi_relevance_score", type: "integer", comment: "Relevance score to BFSI" },
      { name: "enterprise_readiness_score", type: "integer", comment: "Readiness score" },
      { name: "icici_primary_entity", type: "text", comment: "Primary target ICICI vertical" },
      { name: "use_cases", type: "jsonb", comment: "Practical integration scopes list" }
    ]
  },
  {
    name: "startup_assignments",
    comment: "Task mappings of pilots routed to specific ICICI business entities.",
    columns: [
      { name: "id", type: "text (PK)", comment: "Assignment primary key" },
      { name: "startup_id", type: "text (FK)", comment: "References startups.id" },
      { name: "assigned_to", type: "text", comment: "Team owner" },
      { name: "icici_entity", type: "text", comment: "Target ICICI Group business vertical" },
      { name: "assignment_status", type: "text", comment: "Current deployment task status" }
    ]
  },
  {
    name: "startup_activity_logs",
    comment: "Timeline history of sandbox meetings, reviews, and evaluation logs.",
    columns: [
      { name: "id", type: "text (PK)", comment: "Activity log primary key" },
      { name: "startup_id", type: "text (FK)", comment: "References startups.id" },
      { name: "activity_type", type: "text", comment: "Type (Introduction, Tech Review)" },
      { name: "activity_notes", type: "text", comment: "Detailed review comments" }
    ]
  }
];

const PRESETS = [
  "SELECT * FROM startups LIMIT 10;",
  "SELECT * FROM startup_analysis WHERE priority_score >= 90 LIMIT 5;",
  "SELECT * FROM startup_assignments WHERE assignment_status = 'piloting';",
  "SELECT * FROM startup_activity_logs LIMIT 10;"
];

export default function SupabaseConsole({ onRunSQL }: SupabaseConsoleProps) {
  const [consoleState, setConsoleState] = useState<DBConsoleState>({
    activeTable: "startups",
    customSQL: "SELECT * FROM startups LIMIT 10;",
    queryResult: null,
    queryError: null
  });
  const [loading, setLoading] = useState(false);

  // Run SQL Action
  const triggerQuery = async (queryToRun: string) => {
    setLoading(true);
    setConsoleState((prev) => ({ ...prev, queryResult: null, queryError: null }));
    try {
      const data = await onRunSQL(queryToRun);
      if (data && data.error) {
        setConsoleState((prev) => ({ ...prev, queryError: data.error, queryResult: null }));
      } else if (data && data.rows) {
        setConsoleState((prev) => ({ ...prev, queryResult: data.rows, queryError: null }));
      } else {
        setConsoleState((prev) => ({ ...prev, queryError: "Empty response from SQL Compiler Engine." }));
      }
    } catch (e) {
      setConsoleState((prev) => ({ ...prev, queryError: "SQL Connection Timeout or parser syntax issues." }));
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSchema = (tableName: any) => {
    setConsoleState((prev) => ({
      ...prev,
      activeTable: tableName,
      customSQL: `SELECT * FROM ${tableName} LIMIT 10;`,
      queryResult: null,
      queryError: null
    }));
  };

  const currentSchema = SCHEMAS.find((s) => s.name === consoleState.activeTable) || SCHEMAS[0];

  return (
    <div className="space-y-6" id="supabase-console-playground">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 text-slate-100 p-6 rounded-xl shadow-md flex justify-between items-center flex-wrap gap-4 text-left">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-cyan-950 text-cyan-400 rounded-xl border border-cyan-800/40 shadow-md">
            <Database size={24} />
          </div>
          <div>
            <h2 className="text-lg font-bold tracking-tight bg-gradient-to-r from-cyan-400 to-indigo-300 bg-clip-text text-transparent">
              ICICI Supabase Relational Console
            </h2>
            <p className="text-slate-400 text-xs">
              Direct simulated access to the startups schemas, scores, categories, assignments, and interactions relational models in PostgreSQL.
            </p>
          </div>
        </div>
        <span className="text-[10px] font-mono bg-cyan-950 text-cyan-400 px-2 py-1 rounded-full border border-cyan-800/30">
          PG_STAT_ACTIVITY_ACTIVE
        </span>
      </div>

      {/* Main Console Split Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT PANEL: SCHEMAS & PRESETS VIEW */}
        <div className="space-y-6 lg:col-span-1 text-left">
          {/* Table list */}
          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm space-y-3">
            <h4 className="font-bold text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2">
              PostgreSQL Tables
            </h4>
            <div className="space-y-1.5">
              {SCHEMAS.map((sch) => (
                <button
                  key={sch.name}
                  onClick={() => handleSelectSchema(sch.name as any)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold select-none transition-all border-0 cursor-pointer ${
                    consoleState.activeTable === sch.name
                      ? "bg-cyan-50 text-cyan-700 border-l-2 border-cyan-600 font-bold"
                      : "text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Table size={14} className="text-slate-450 text-slate-400" />
                    <span>{sch.name}</span>
                  </div>
                  <span className="text-[9px] bg-slate-100 text-slate-400 py-0.5 px-1 rounded uppercase font-mono">
                    Table DB
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Quick Preset Queries */}
          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm space-y-3">
            <h4 className="font-bold text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2">
              Template preset SQLs
            </h4>
            <div className="space-y-2">
              {PRESETS.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setConsoleState((prev) => ({ ...prev, customSQL: q }));
                    triggerQuery(q);
                  }}
                  className="w-full text-left p-2 bg-slate-50 rounded-lg hover:bg-slate-100 border border-slate-200 transition-all font-mono text-[10px] text-slate-700 block select-none leading-relaxed cursor-pointer"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT PANEL: INTERACTIVE TERMINAL & RESULTS */}
        <div className="lg:col-span-2 space-y-6 text-left">
          {/* Terminal Editor */}
          <div className="bg-slate-950 rounded-xl border border-slate-800 shadow-lg overflow-hidden flex flex-col">
            <div className="p-3 bg-slate-900 flex justify-between items-center text-slate-300 border-b border-slate-800">
              <div className="flex items-center gap-1.5 text-xs font-mono text-slate-405 text-slate-400">
                <Terminal size={14} className="text-cyan-400 animate-pulse" />
                <span>SQL Compiler Editor (Read-Only Parser simulator)</span>
              </div>
              <button
                onClick={() => triggerQuery(consoleState.customSQL)}
                disabled={loading}
                className="bg-cyan-500 hover:bg-cyan-600 border-0 text-slate-950 font-bold text-xs py-1 px-4 rounded flex items-center gap-1 transition-all cursor-pointer"
              >
                {loading ? <RefreshCw className="animate-spin" size={13} /> : <Play size={13} />}
                Run Query
              </button>
            </div>

            {/* Editable Field */}
            <div className="p-4 bg-slate-950/80 font-mono text-xs w-full">
              <textarea
                value={consoleState.customSQL}
                onChange={(e) => setConsoleState((prev) => ({ ...prev, customSQL: e.target.value }))}
                className="w-full bg-transparent text-cyan-300 border-0 resize-none font-mono focus:outline-none min-h-[75px] leading-relaxed"
                rows={3}
              />
            </div>
          </div>

          {/* Table Schema metadata */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-2.5">
            <h5 className="font-extrabold text-[11px] text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Info size={14} className="text-sky-500" /> Schema details: {currentSchema.name}
            </h5>
            <p className="text-xs text-slate-500 italic pr-3">"{currentSchema.comment}"</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-1">
              {currentSchema.columns.map((col) => (
                <div key={col.name} className="p-2 bg-slate-50 border border-slate-100 rounded text-[10.5px]">
                  <strong className="text-slate-805 text-slate-800 block">{col.name}</strong>
                  <span className="text-cyan-705 text-cyan-700 italic font-mono text-[9.5px] block">{col.type}</span>
                  <span className="text-[10px] text-slate-400 leading-tight block truncate mt-1">{col.comment}</span>
                </div>
              ))}
            </div>
          </div>

          {/* QUERY RESULTS CARD */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden min-h-[160px] flex flex-col justify-between">
            <div className="p-3 bg-slate-50 border-b border-slate-100 flex justify-between items-center">
              <span className="text-xs font-bold text-slate-505 text-slate-500 uppercase tracking-widest">Compiler output</span>
              <span className="text-[10px] bg-slate-200 text-slate-600 px-2 py-0.5 rounded font-mono font-bold">
                Output console
              </span>
            </div>

            {/* Loading / Error / Success Output area */}
            <div className="p-4 flex-1 overflow-x-auto">
              {loading && (
                <div className="flex flex-col items-center justify-center py-6 gap-2">
                  <RefreshCw className="animate-spin text-cyan-600" size={24} />
                  <p className="text-xs text-slate-400 font-mono">Running query plan in Supabase VM...</p>
                </div>
              )}

              {consoleState.queryError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs font-mono text-red-700 leading-relaxed">
                  <strong>PostgreSQL Error:</strong> {consoleState.queryError}
                </div>
              )}

              {!loading && !consoleState.queryError && consoleState.queryResult && (
                <div className="overflow-x-auto max-h-72">
                  <table className="w-full text-left border-collapse text-[10.5px]">
                    <thead>
                      <tr className="bg-slate-100 text-slate-655 text-slate-600 uppercase font-mono font-bold border-b border-slate-200">
                        {Object.keys(consoleState.queryResult[0] || {}).map((col) => (
                          <th key={col} className="p-2 py-1.5 md:p-2.5">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono text-slate-700">
                      {consoleState.queryResult.map((row, idx) => (
                        <tr key={idx} className="hover:bg-slate-50">
                          {Object.values(row).map((val: any, sIdx) => {
                            const stringVal = typeof val === "object" ? JSON.stringify(val) : String(val);
                            return (
                              <td key={sIdx} className="p-2 max-w-[200px] truncate leading-normal">
                                {stringVal}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {!loading && !consoleState.queryError && !consoleState.queryResult && (
                <div className="text-slate-400 text-xs py-8 text-center italic">
                  Run standard SELECT query or use presets to fetch live logs securely.
                </div>
              )}
            </div>

            <div className="p-3 bg-slate-50 border-t border-slate-100 text-[10px] text-slate-400 font-medium flex items-center justify-between">
              <span className="flex items-center gap-1 font-mono">
                <ShieldCheck size={12} className="text-emerald-500 animate-pulse animate-pulse" /> Read-only Postgres transaction active
              </span>
              <span>ID: {Date.now()}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
