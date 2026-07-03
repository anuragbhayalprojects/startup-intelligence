import React, { useState, useEffect } from "react";
import { 
  Activity, 
  Terminal, 
  Database, 
  Cpu, 
  Share2, 
  RefreshCw, 
  Download, 
  Copy, 
  ArrowRight, 
  Search, 
  AlertCircle,
  Eye,
  CheckCircle,
  Clock
} from "lucide-react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from "recharts";
import { getActiveTraceId, rotateTraceId, logFrontendEvent } from "../lib/tracing";

// Read API URL from environment variables
const rawApiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const API_URL = rawApiUrl.endsWith("/") 
  ? (rawApiUrl.endsWith("/api/") ? rawApiUrl.slice(0, -1) : rawApiUrl + "api") 
  : (rawApiUrl.endsWith("/api") ? rawApiUrl : rawApiUrl + "/api");

interface TraceInfo {
  trace_id: string;
  startup_name?: string;
  article_url?: string;
  created_at: string;
}

interface APICall {
  id: number;
  route: string;
  method: string;
  payload: any;
  response: any;
  status_code: number;
  duration_ms: number;
  created_at: string;
}

interface AgentExecution {
  id: number;
  exec_id: string;
  agent_name: string;
  input_payload: any;
  output_payload: any;
  duration_ms: number;
  created_at: string;
}

interface PromptRecord {
  id: number;
  prompt_id: string;
  agent_name: string;
  prompt_template: string;
  injected_context: string;
  raw_response: string;
  parsed_response: any;
  duration_ms: number;
  created_at: string;
}

interface DBMutation {
  id: number;
  txn_id: string;
  table_name: string;
  operation: string;
  rows_affected: number;
  duration_ms: number;
  created_at: string;
}

interface GraphMutation {
  id: number;
  mutation_id: string;
  operation: string;
  details: any;
  created_at: string;
}

interface FrontendEvent {
  id: number;
  page: string;
  component: string;
  action: string;
  payload: any;
  created_at: string;
}

interface TraceDetail {
  trace: TraceInfo;
  api_calls: APICall[];
  agent_executions: AgentExecution[];
  prompts: PromptRecord[];
  db_mutations: DBMutation[];
  graph_mutations: GraphMutation[];
  frontend_events: FrontendEvent[];
}

export default function Observability() {
  const [activeTraceId, setActiveTraceId] = useState<string>(getActiveTraceId());
  const [traces, setTraces] = useState<TraceInfo[]>([]);
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [traceDetail, setTraceDetail] = useState<TraceDetail | null>(null);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [activeTab, setActiveTab] = useState<"flow" | "mermaid" | "prompts" | "db" | "raw">("flow");
  const [searchQuery, setSearchQuery] = useState("");
  const [copied, setCopied] = useState(false);
  const [copiedPromptId, setCopiedPromptId] = useState<number | null>(null);

  useEffect(() => {
    fetchTraces();
    // Log initial dashboard visit
    logFrontendEvent("observability", "ObservabilityDashboard", "view_dashboard", { currentTraceId: activeTraceId });
  }, []);

  useEffect(() => {
    if (selectedTraceId) {
      fetchTraceDetail(selectedTraceId);
    }
  }, [selectedTraceId]);

  const fetchTraces = async () => {
    setLoadingList(true);
    try {
      const response = await fetch(`${API_URL}/observability/traces`);
      if (response.ok) {
        const data = await response.json();
        setTraces(data);
        if (data.length > 0 && !selectedTraceId) {
          setSelectedTraceId(data[0].trace_id);
        }
      }
    } catch (e) {
      console.error("Failed to load trace list:", e);
    } finally {
      setLoadingList(false);
    }
  };

  const fetchTraceDetail = async (traceId: string) => {
    setLoadingDetail(true);
    try {
      const response = await fetch(`${API_URL}/observability/traces/${traceId}`);
      if (response.ok) {
        const data = await response.json();
        setTraceDetail(data);
      }
    } catch (e) {
      console.error("Failed to load trace details:", e);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleRotateTrace = () => {
    const newId = rotateTraceId();
    setActiveTraceId(newId);
    logFrontendEvent("observability", "TraceControls", "rotate_trace_id", { newTraceId: newId });
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const copyPromptToClipboard = (text: string, id: number) => {
    navigator.clipboard.writeText(text);
    setCopiedPromptId(id);
    setTimeout(() => setCopiedPromptId(null), 2000);
  };

  // Generate dynamic Mermaid code from the trace details
  const generateMermaidCode = (): string => {
    if (!traceDetail) return "graph TD\n  Start[No Trace Loaded]";

    const { trace, api_calls, agent_executions, prompts, db_mutations } = traceDetail;
    let code = "sequenceDiagram\n  autonumber\n";
    code += "  actor User as Browser/User\n";
    code += "  participant FE as React Frontend\n";
    code += "  participant BE as FastAPI API\n";
    
    // Track participants dynamically
    const agents = new Set<string>();
    agent_executions.forEach(a => agents.add(a.agent_name));
    
    agents.forEach(a => {
      code += `  participant ${a} as ${a}\n`;
    });
    
    code += "  participant LLM as Ollama (qwen2.5)\n";
    code += "  participant DB as Supabase DB\n";

    // Trace sequence flows
    api_calls.forEach(api => {
      code += `  User->>FE: Trigger UI Action\n`;
      code += `  FE->>BE: ${api.method} ${api.route}\n`;
    });

    agent_executions.forEach(agent => {
      code += `  BE->>${agent.agent_name}: run(state)\n`;
      
      // Find LLM prompts run inside this agent
      const agentPrompts = prompts.filter(p => p.agent_name === agent.agent_name);
      agentPrompts.forEach(p => {
        code += `  ${agent.agent_name}->>LLM: call_ollama(prompt)\n`;
        code += `  LLM-->>${agent.agent_name}: response (${Math.round(p.duration_ms)}ms)\n`;
      });

      // Find DB mutations inside this agent (approximate timestamp overlap)
      const agentMutations = db_mutations.filter(db => 
        new Date(db.created_at).getTime() >= new Date(agent.created_at).getTime() &&
        new Date(db.created_at).getTime() <= new Date(agent.created_at).getTime() + agent.duration_ms
      );
      agentMutations.forEach(db => {
        code += `  ${agent.agent_name}->>DB: ${db.operation} ${db.table_name}\n`;
        code += `  DB-->>${agent.agent_name}: ${db.rows_affected} row(s) affected\n`;
      });

      code += `  ${agent.agent_name}-->>BE: return result (${Math.round(agent.duration_ms)}ms)\n`;
    });

    api_calls.forEach(api => {
      code += `  BE-->>FE: Response (${api.status_code})\n`;
      code += `  FE-->>User: Refresh View\n`;
    });

    return code;
  };

  const handleExportJSON = () => {
    if (!traceDetail) return;
    const blob = new Blob([JSON.stringify(traceDetail, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `trace_${traceDetail.trace.trace_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportMarkdown = () => {
    if (!traceDetail) return;
    const { trace, api_calls, agent_executions, prompts, db_mutations } = traceDetail;
    
    let md = `# Startup Intelligence OS - Trace Report\n\n`;
    md += `**Trace ID:** \`${trace.trace_id}\`\n`;
    md += `**Target Startup:** ${trace.startup_name || "N/A"}\n`;
    md += `**Created At:** ${new Date(trace.created_at).toLocaleString()}\n\n`;
    
    md += `## 1. API Endpoint Calls\n\n`;
    api_calls.forEach(api => {
      md += `* **Route:** \`${api.method} ${api.route}\`\n`;
      md += `  * **Status Code:** ${api.status_code}\n`;
      md += `  * **Latency:** ${api.duration_ms.toFixed(2)} ms\n\n`;
    });

    md += `## 2. Multi-Agent Executions\n\n`;
    agent_executions.forEach(agent => {
      md += `### ${agent.agent_name}\n`;
      md += `* **Latency:** ${agent.duration_ms.toFixed(2)} ms\n`;
      md += `* **Input Payload:**\n\`\`\`json\n${JSON.stringify(agent.input_payload, null, 2)}\n\`\`\`\n`;
      md += `* **Output Payload:**\n\`\`\`json\n${JSON.stringify(agent.output_payload, null, 2)}\n\`\`\`\n\n`;
    });

    md += `## 3. LLM Prompt Ledger\n\n`;
    prompts.forEach(p => {
      md += `### Prompt (${p.agent_name})\n`;
      md += `* **Duration:** ${p.duration_ms.toFixed(2)} ms\n`;
      md += `* **Prompt:**\n\`\`\`\n${p.prompt_template}\n\`\`\`\n`;
      md += `* **Response:**\n\`\`\`json\n${JSON.stringify(p.parsed_response, null, 2)}\n\`\`\`\n\n`;
    });

    md += `## 4. Database Mutations\n\n`;
    md += `| Table | Operation | Rows Affected | Duration (ms) |\n`;
    md += `| :--- | :--- | :--- | :--- |\n`;
    db_mutations.forEach(db => {
      md += `| ${db.table_name} | ${db.operation} | ${db.rows_affected} | ${db.duration_ms.toFixed(2)} |\n`;
    });

    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `trace_${trace.trace_id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getLatencyChartData = () => {
    if (!traceDetail) return [];
    
    const apiDuration = traceDetail.api_calls.reduce((sum, a) => sum + a.duration_ms, 0);
    const agentDuration = traceDetail.agent_executions.reduce((sum, a) => sum + a.duration_ms, 0);
    const llmDuration = traceDetail.prompts.reduce((sum, a) => sum + a.duration_ms, 0);
    const dbDuration = traceDetail.db_mutations.reduce((sum, a) => sum + a.duration_ms, 0);
    
    return [
      { name: "Total API", ms: apiDuration, color: "#6366f1" },
      { name: "Agents Run", ms: agentDuration, color: "#10b981" },
      { name: "Ollama (LLM)", ms: llmDuration, color: "#ec4899" },
      { name: "Supabase DB", ms: dbDuration, color: "#f59e0b" }
    ];
  };

  const filteredTraces = traces.filter(t => 
    t.trace_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (t.startup_name && t.startup_name.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-4 md:p-6 text-slate-800">
      {/* HEADER CONTROLS */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-100 shadow-sm">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold flex items-center gap-2 bg-gradient-to-r from-slate-900 to-indigo-850 bg-clip-text text-transparent">
            <Activity className="text-indigo-600 animate-pulse" size={28} />
            Live Trace & Observability Audit
          </h1>
          <p className="text-xs text-slate-450">
            Real-time forensic execution tracing across Frontend events, Backend REST routes, Agent pipelines, LLM prompt ledgers, and database mutations.
          </p>
        </div>
        <div className="flex items-center gap-2 self-start md:self-center">
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Active Workspace Trace ID</span>
            <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 px-3 py-1.5 rounded-lg">
              <span className="font-mono text-xs font-bold text-indigo-650">{activeTraceId}</span>
              <button 
                onClick={handleRotateTrace} 
                className="text-slate-400 hover:text-indigo-600 p-0.5 rounded hover:bg-slate-100 transition"
                title="Generate New Trace ID"
              >
                <RefreshCw size={14} />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT PANEL: TRACE LIST */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden flex flex-col h-[750px]">
          <div className="p-4 border-b border-slate-100 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-700 flex items-center gap-2">
                <Terminal size={18} className="text-slate-500" />
                Trace History
              </h3>
              <button 
                onClick={fetchTraces} 
                className="text-slate-400 hover:text-indigo-600 p-1 hover:bg-slate-50 rounded transition"
                disabled={loadingList}
              >
                <RefreshCw size={16} className={loadingList ? "animate-spin" : ""} />
              </button>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-2.5 text-slate-400" size={16} />
              <input
                type="text"
                placeholder="Search trace or startup..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-50 border border-slate-100 rounded-lg pl-9 pr-4 py-2 text-xs focus:outline-none focus:border-indigo-500 transition font-medium"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-slate-50">
            {loadingList ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                <RefreshCw size={24} className="animate-spin mx-auto mb-2 text-indigo-600" />
                Fetching active traces...
              </div>
            ) : filteredTraces.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                No traces found matching search criteria.
              </div>
            ) : (
              filteredTraces.map((t) => (
                <div 
                  key={t.trace_id}
                  onClick={() => setSelectedTraceId(t.trace_id)}
                  className={`p-4 cursor-pointer transition flex flex-col gap-2 ${selectedTraceId === t.trace_id ? "bg-indigo-50/40 border-l-4 border-indigo-600" : "hover:bg-slate-50"}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-indigo-600">{t.trace_id}</span>
                    <span className="text-[10px] text-slate-400 font-bold">
                      {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>
                  {t.startup_name && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] bg-slate-100 text-slate-650 px-2 py-0.5 rounded font-bold">{t.startup_name}</span>
                    </div>
                  )}
                  {t.article_url && (
                    <span className="text-[10px] text-slate-400 truncate block">{t.article_url}</span>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* RIGHT PANEL: TRACE DETAILS */}
        <div className="lg:col-span-8 space-y-6">
          {loadingDetail ? (
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-24 text-center text-slate-400 text-sm">
              <RefreshCw size={36} className="animate-spin mx-auto mb-3 text-indigo-600" />
              Compiling forensic trace execution path...
            </div>
          ) : !traceDetail ? (
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-24 text-center text-slate-400 text-sm">
              <AlertCircle size={40} className="mx-auto mb-3 text-slate-300" />
              Select a trace from the panel to view its runtime logs and latency breakdown.
            </div>
          ) : (
            <>
              {/* DETAILS METRICS CARD PANEL */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm flex flex-col justify-between">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="text-[10px] font-bold uppercase tracking-wider">Trace Duration</span>
                    <Clock size={16} />
                  </div>
                  <span className="text-xl font-extrabold text-indigo-650 mt-2">
                    {Math.round(traceDetail.api_calls.reduce((sum, a) => sum + a.duration_ms, 0) || 0)}ms
                  </span>
                </div>
                <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm flex flex-col justify-between">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="text-[10px] font-bold uppercase tracking-wider">API Requests</span>
                    <Terminal size={16} />
                  </div>
                  <span className="text-xl font-extrabold text-indigo-650 mt-2">{traceDetail.api_calls.length}</span>
                </div>
                <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm flex flex-col justify-between">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="text-[10px] font-bold uppercase tracking-wider">Agents Executed</span>
                    <Cpu size={16} />
                  </div>
                  <span className="text-xl font-extrabold text-indigo-650 mt-2">{traceDetail.agent_executions.length}</span>
                </div>
                <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm flex flex-col justify-between">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="text-[10px] font-bold uppercase tracking-wider">LLM Prompts</span>
                    <Activity size={16} />
                  </div>
                  <span className="text-xl font-extrabold text-indigo-650 mt-2">{traceDetail.prompts.length}</span>
                </div>
                <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm flex flex-col justify-between col-span-2 md:col-span-1">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="text-[10px] font-bold uppercase tracking-wider">DB Mutations</span>
                    <Database size={16} />
                  </div>
                  <span className="text-xl font-extrabold text-indigo-650 mt-2">{traceDetail.db_mutations.length}</span>
                </div>
              </div>

              {/* ACTION EXPORTERS & TABS */}
              <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
                <div className="p-4 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  {/* Tabs */}
                  <div className="flex items-center gap-1.5 bg-slate-50 p-1 rounded-lg border border-slate-100 self-start">
                    <button
                      onClick={() => setActiveTab("flow")}
                      className={`px-3 py-1.5 rounded-md text-xs font-bold transition ${activeTab === "flow" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
                    >
                      Execution Flow
                    </button>
                    <button
                      onClick={() => setActiveTab("mermaid")}
                      className={`px-3 py-1.5 rounded-md text-xs font-bold transition ${activeTab === "mermaid" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
                    >
                      Mermaid Diagram
                    </button>
                    <button
                      onClick={() => setActiveTab("prompts")}
                      className={`px-3 py-1.5 rounded-md text-xs font-bold transition ${activeTab === "prompts" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
                    >
                      Prompt Ledger ({traceDetail.prompts.length})
                    </button>
                    <button
                      onClick={() => setActiveTab("db")}
                      className={`px-3 py-1.5 rounded-md text-xs font-bold transition ${activeTab === "db" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
                    >
                      DB Transactions ({traceDetail.db_mutations.length})
                    </button>
                    <button
                      onClick={() => setActiveTab("raw")}
                      className={`px-3 py-1.5 rounded-md text-xs font-bold transition ${activeTab === "raw" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
                    >
                      Raw Logs
                    </button>
                  </div>
                  {/* Export Buttons */}
                  <div className="flex items-center gap-2">
                    <button 
                      onClick={handleExportJSON}
                      className="flex items-center gap-1 px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-[10px] font-bold rounded-lg transition"
                    >
                      <Download size={12} /> JSON
                    </button>
                    <button 
                      onClick={handleExportMarkdown}
                      className="flex items-center gap-1 px-3 py-1.5 bg-slate-900 hover:bg-black text-white text-[10px] font-bold rounded-lg transition shadow-sm"
                    >
                      <Share2 size={12} /> Export Report (MD)
                    </button>
                  </div>
                </div>

                {/* TAB WINDOW CONTENT */}
                <div className="p-6">
                  {/* FLOW TAB */}
                  {activeTab === "flow" && (
                    <div className="space-y-8">
                      {/* Latency breakdown chart */}
                      <div className="bg-slate-50/50 p-4 rounded-xl border border-slate-100">
                        <h4 className="text-xs font-bold text-slate-500 mb-4 uppercase tracking-wider">Trace Latency Breakdown (ms)</h4>
                        <div className="h-44 w-full">
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={getLatencyChartData()} layout="vertical">
                              <XAxis type="number" hide />
                              <YAxis dataKey="name" type="category" width={100} axisLine={false} tickLine={false} tick={{ fontSize: 10, fontWeight: "bold", fill: "#64748b" }} />
                              <Tooltip cursor={{ fill: "transparent" }} formatter={(value: any) => [`${Math.round(value)} ms`, "Latency"]} />
                              <Bar dataKey="ms" radius={6} barSize={20}>
                                {getLatencyChartData().map((entry, index) => (
                                  <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                              </Bar>
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      </div>

                      {/* Step by step timeline */}
                      <div className="relative border-l border-slate-200 pl-6 space-y-6">
                        {/* API Call root event */}
                        {traceDetail.api_calls.map((api, index) => (
                          <div key={api.id} className="relative">
                            <span className="absolute -left-[31px] top-1 flex h-4 w-4 items-center justify-center rounded-full bg-indigo-600 ring-4 ring-white">
                              <Terminal size={10} className="text-white" />
                            </span>
                            <div className="bg-white p-4 rounded-xl border border-indigo-100 shadow-sm space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-slate-800 text-xs flex items-center gap-2">
                                  <span className="bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded text-[10px] font-bold">{api.method}</span>
                                  {api.route}
                                </span>
                                <span className="text-[10px] font-mono font-bold text-slate-450">{api.duration_ms.toFixed(1)} ms</span>
                              </div>
                              {api.payload && Object.keys(api.payload).length > 0 && (
                                <pre className="text-[10px] bg-slate-50 p-2.5 rounded border border-slate-100 text-slate-650 overflow-x-auto max-h-24">
                                  {JSON.stringify(api.payload, null, 2)}
                                </pre>
                              )}
                            </div>
                          </div>
                        ))}

                        {/* Agent run executions */}
                        {traceDetail.agent_executions.map((agent) => (
                          <div key={agent.id} className="relative">
                            <span className="absolute -left-[31px] top-1 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 ring-4 ring-white">
                              <Cpu size={10} className="text-white" />
                            </span>
                            <div className="bg-white p-4 rounded-xl border border-emerald-100 shadow-sm space-y-3">
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-slate-800 text-xs flex items-center gap-2">
                                  <span className="bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded text-[10px] font-bold">AGENT</span>
                                  {agent.agent_name}
                                </span>
                                <span className="text-[10px] font-mono font-bold text-slate-450">{agent.duration_ms.toFixed(1)} ms</span>
                              </div>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <div>
                                  <span className="text-[9px] font-bold uppercase tracking-wider text-slate-400 block mb-1">Inputs</span>
                                  <pre className="text-[9px] bg-slate-50 p-2 rounded border border-slate-100 text-slate-600 max-h-36 overflow-y-auto">
                                    {JSON.stringify(agent.input_payload, null, 2)}
                                  </pre>
                                </div>
                                <div>
                                  <span className="text-[9px] font-bold uppercase tracking-wider text-slate-400 block mb-1">Outputs</span>
                                  <pre className="text-[9px] bg-slate-50 p-2 rounded border border-slate-100 text-slate-600 max-h-36 overflow-y-auto">
                                    {JSON.stringify(agent.output_payload, null, 2)}
                                  </pre>
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}

                        {/* UI Event final rendering if exists */}
                        {traceDetail.frontend_events.map((fe) => (
                          <div key={fe.id} className="relative">
                            <span className="absolute -left-[31px] top-1 flex h-4 w-4 items-center justify-center rounded-full bg-pink-500 ring-4 ring-white">
                              <Eye size={10} className="text-white" />
                            </span>
                            <div className="bg-white p-4 rounded-xl border border-pink-100 shadow-sm space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-slate-800 text-xs flex items-center gap-2">
                                  <span className="bg-pink-50 text-pink-700 px-2 py-0.5 rounded text-[10px] font-bold">UI EVENT</span>
                                  {fe.page} / {fe.component}
                                </span>
                                <span className="text-[10px] font-mono font-bold text-pink-600">{fe.action}</span>
                              </div>
                              {fe.payload && Object.keys(fe.payload).length > 0 && (
                                <pre className="text-[10px] bg-slate-50 p-2.5 rounded border border-slate-100 text-slate-650 overflow-x-auto">
                                  {JSON.stringify(fe.payload, null, 2)}
                                </pre>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* MERMAID DIAGRAM TAB */}
                  {activeTab === "mermaid" && (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Dynamic Sequence Diagram (Mermaid)</span>
                        <button
                          onClick={() => copyToClipboard(generateMermaidCode())}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-lg transition"
                        >
                          {copied ? <CheckCircle size={14} className="text-emerald-600" /> : <Copy size={14} />}
                          {copied ? "Copied!" : "Copy Code"}
                        </button>
                      </div>
                      <div className="bg-slate-50 p-4 rounded-xl border border-slate-150 overflow-x-auto">
                        <pre className="font-mono text-xs text-slate-700 text-left whitespace-pre select-all">
                          {generateMermaidCode()}
                        </pre>
                      </div>
                      <p className="text-[10px] text-slate-400">
                        Paste this code block directly into any Mermaid-compatible editor (like Github, Notion, or Mermaid Live Editor) to visualize the forensic sequence flow.
                      </p>
                    </div>
                  )}

                  {/* PROMPT LEDGER TAB */}
                  {activeTab === "prompts" && (
                    <div className="space-y-6">
                      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Exact Ollama Prompts & Injected Context</h4>
                      {traceDetail.prompts.length === 0 ? (
                        <div className="text-center py-12 text-slate-400 text-xs border border-dashed border-slate-200 rounded-xl">
                          No Ollama calls were made during this execution pass.
                        </div>
                      ) : (
                        traceDetail.prompts.map((p) => (
                          <div key={p.id} className="bg-white rounded-xl border border-slate-150 overflow-hidden shadow-sm">
                            <div className="bg-slate-50 px-4 py-3 border-b border-slate-150 flex items-center justify-between">
                              <span className="font-bold text-xs text-slate-700 flex items-center gap-2">
                                <span className="bg-pink-100 text-pink-700 px-2 py-0.5 rounded text-[9px] font-bold">OLLAMA</span>
                                {p.agent_name}
                              </span>
                              <span className="text-[10px] font-mono font-bold text-slate-450">{p.duration_ms.toFixed(1)} ms</span>
                            </div>
                            <div className="p-4 space-y-4">
                              <div className="grid grid-cols-1 gap-4">
                                <div className="space-y-1">
                                  <div className="flex items-center justify-between">
                                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                                      Full Rendered Prompt Passed to AI ({p.prompt_template ? p.prompt_template.length : 0} characters)
                                    </span>
                                    <button
                                      onClick={() => copyPromptToClipboard(p.prompt_template || "", p.id)}
                                      className="flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-850 font-bold px-2 py-1 hover:bg-indigo-50 rounded transition"
                                    >
                                      {copiedPromptId === p.id ? (
                                        <>
                                          <CheckCircle size={12} className="text-emerald-600" /> Copied!
                                        </>
                                      ) : (
                                        <>
                                          <Copy size={12} /> Copy Prompt
                                        </>
                                      )}
                                    </button>
                                  </div>
                                  <div className="bg-slate-900 text-slate-100 p-3 rounded-lg text-xs font-mono max-h-[600px] overflow-y-auto whitespace-pre-wrap">
                                    {p.prompt_template}
                                  </div>
                                </div>
                                <div className="space-y-1">
                                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Parsed AI JSON Output</span>
                                  <pre className="bg-indigo-50/50 text-slate-750 p-3 rounded-lg text-xs font-mono max-h-[600px] overflow-y-auto whitespace-pre-wrap border border-indigo-100/50">
                                    {JSON.stringify(p.parsed_response, null, 2)}
                                  </pre>
                                </div>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  {/* DATABASE TRANSACTIONS TAB */}
                  {activeTab === "db" && (
                    <div className="space-y-4">
                      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Supabase Query Mutator Audit Log</h4>
                      {traceDetail.db_mutations.length === 0 ? (
                        <div className="text-center py-12 text-slate-400 text-xs border border-dashed border-slate-200 rounded-xl">
                          No database transactions occurred during this trace path.
                        </div>
                      ) : (
                        <div className="bg-white rounded-xl border border-slate-150 overflow-hidden shadow-sm overflow-x-auto">
                          <table className="w-full text-left border-collapse">
                            <thead>
                              <tr className="bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-450 border-b border-slate-150">
                                <th className="px-4 py-3">Operation</th>
                                <th className="px-4 py-3">Target Table</th>
                                <th className="px-4 py-3">Rows Affected</th>
                                <th className="px-4 py-3">Duration (ms)</th>
                                <th className="px-4 py-3">Transaction ID</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 text-xs">
                              {traceDetail.db_mutations.map((db) => (
                                <tr key={db.id} className="hover:bg-slate-50 transition">
                                  <td className="px-4 py-3 font-bold">
                                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                      db.operation === "INSERT" ? "bg-emerald-55 text-emerald-700" :
                                      db.operation === "UPDATE" ? "bg-amber-55 text-amber-700" :
                                      db.operation === "DELETE" ? "bg-rose-55 text-rose-700" :
                                      "bg-blue-55 text-blue-700"
                                    }`}>
                                      {db.operation}
                                    </span>
                                  </td>
                                  <td className="px-4 py-3 font-mono font-medium text-slate-650">{db.table_name}</td>
                                  <td className="px-4 py-3 font-bold text-slate-700">{db.rows_affected}</td>
                                  <td className="px-4 py-3 font-mono text-slate-450">{db.duration_ms.toFixed(1)} ms</td>
                                  <td className="px-4 py-3 font-mono text-slate-400 text-[10px]">{db.txn_id}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}

                  {/* RAW LOGS TAB */}
                  {activeTab === "raw" && (
                    <div className="space-y-4">
                      <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Full Raw Trace Package (JSON)</span>
                      <pre className="bg-slate-900 text-slate-100 p-4 rounded-xl border border-slate-950 text-xs font-mono overflow-y-auto max-h-[500px]">
                        {JSON.stringify(traceDetail, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
