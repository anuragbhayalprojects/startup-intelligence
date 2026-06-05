import React, { useState } from "react";
import {
  X,
  Globe,
  DollarSign,
  Briefcase,
  Layers,
  Sparkles,
  ClipboardList,
  MessageSquare,
  Activity,
  Plus,
  Compass,
  FileText,
  User,
  ShieldCheck,
  CheckCircle2,
  Calendar,
  RefreshCw,
  ChevronRight,
  ExternalLink,
  Linkedin,
  Pencil,
  Edit
} from "lucide-react";
import { Startup, StartupScore, Assignment, Interaction, UserRole } from "../types";

const FPR1_LIST = [
  "Anurag", "Simran", "Rameez", "Shubham", "Dhanush", 
  "Rahul", "Jayvi", "Ishan", "Utkarsh", "Shivani", 
  "Divya", "Nikhil", "Akash", "Mohit"
];

const FPR2_LIST = [
  "Keroli", "Shakti", "Vishesh", "Kushal"
];

interface DetailModalProps {
  startup: Startup;
  score?: StartupScore;
  assignments: Assignment[];
  interactions: Interaction[];
  currentUser: UserRole;
  onClose: () => void;
  onUpdateStatus: (id: string, status: any, team?: string, priorityScore?: number) => Promise<void>;
  onAddInteraction: (startupId: string, logData: any) => Promise<void>;
  onCreateAssignment: (startupId: string, assignmentData: any) => Promise<void>;
  onAnalyze?: (startupId: string, force?: boolean) => Promise<any>;
  onUpdateField?: (startupId: string, field: string, value: any) => Promise<any>;
  onRecheckField?: (startupId: string, field: string) => Promise<any>;
}

export default function DetailModal({
  startup,
  score,
  assignments,
  interactions,
  currentUser,
  onClose,
  onUpdateStatus,
  onAddInteraction,
  onCreateAssignment,
  onAnalyze,
  onUpdateField,
  onRecheckField
}: DetailModalProps) {
  // Local state
  const [activeTab, setActiveTab] = useState<"insights" | "interactions" | "assignment">("insights");

  // Interaction Form
  const [newInteraction, setNewInteraction] = useState({
    type: "Introduction",
    summary: "",
    next_steps: ""
  });
  const [logLoading, setLogLoading] = useState(false);

  // Assignment Form
  const [newAssignment, setNewAssignment] = useState({
    assigned_to_fpr1: "Anurag",
    assigned_to_fpr2: "Keroli",
    notes: ""
  });
  const [assignLoading, setAssignLoading] = useState(false);

  // Status updating state
  const [localStatus, setLocalStatus] = useState(startup.status || "Screening");
  const [localTeam, setLocalTeam] = useState(startup.assigned_team || "Lending Team");
  const [localPriority, setLocalPriority] = useState(startup.priority_score || 70);
  const [statusLoading, setStatusLoading] = useState(false);

  // AI analysis loader
  const [analyzing, setAnalyzing] = useState(false);

  const rawAnalysisRecord = (startup.startup_analyses && startup.startup_analyses.length > 0)
    ? startup.startup_analyses[0]
    : (startup.startup_analysis && startup.startup_analysis.length > 0)
    ? startup.startup_analysis[0]
    : null;

  const analysis = rawAnalysisRecord
    ? ((rawAnalysisRecord.analysis_data || rawAnalysisRecord.analysis_json) as any)
    : null;

  // Rich details resolver with fallback for preloaded mock data
  const getRichDetails = () => {
    // If analysis contains the live enrichment data, return it
    if (analysis && (analysis.founders || analysis.funding_stages || analysis.valuation_metrics)) {
      return {
        founded_year: analysis.founded_year || startup.founded_year || 2018,
        founders: (analysis.founders && analysis.founders.length > 0)
          ? analysis.founders
          : (startup.founder_name
            ? [{ name: startup.founder_name, role: "Founder", brief_details: "", linkedin_url: startup.founder_linkedin_url }]
            : []),
        funding_stages: analysis.funding_stages || { 
          series: startup.funding_stage, 
          amount: startup.funding_amount || "Unknown", 
          investors: [] 
        },
        valuation_metrics: analysis.valuation_metrics || { 
          revenue: "Unknown", 
          ebitda_multiple: "N/A", 
          other_metrics: "" 
        }
      };
    }

    // Default premium mocks for standard pre-loaded fintech entities
    const nameLower = startup.startup_name.toLowerCase();
    if (nameLower.includes("digit")) {
      return {
        founded_year: 2016,
        founders: [
          { name: "Kamesh Goyal", role: "Founder & Chairman", brief_details: "Former CEO of Allianz Insurance India with 30+ years in insurance operations." },
          { name: "Jasleen Kohli", role: "Managing Director & CEO", brief_details: "Ex-Director of Allianz with extensive experience in scaling digital distribution." }
        ],
        funding_stages: {
          series: "Series H / IPO",
          amount: "$540M",
          investors: ["Fairfax Financial Holdings", "Sequoia Capital India", "A91 Partners", "IIFL Asset Management"]
        },
        valuation_metrics: {
          revenue: "$950M (Rs 7,900 Cr)",
          ebitda_multiple: "18.5x EV/Revenue",
          other_metrics: "Claims settlement ratio of 98.9%, leading digital general insurer in India."
        }
      };
    } else if (nameLower.includes("perfios")) {
      return {
        founded_year: 2008,
        founders: [
          { name: "VR Govindarajan", role: "Co-Founder & Chairman", brief_details: "Ex-Product head at Aztecsoft with 35+ years in database systems and B2B SaaS." },
          { name: "Debashish Chakraborty", role: "Co-Founder & CTO", brief_details: "Software pioneer with deep expertise in cognitive statement parsers and document AI." }
        ],
        funding_stages: {
          series: "Series D (Unicorn)",
          amount: "$420M",
          investors: ["Kedaara Capital", "Bessemer Venture Partners", "Warburg Pincus", "Ontario Teachers' Pension Plan"]
        },
        valuation_metrics: {
          revenue: "$74M (Rs 615 Cr)",
          ebitda_multiple: "14.2x EV/EBITDA",
          other_metrics: "Profitable SaaS. Powers 90% of statement analysis for Indian retail lending banks."
        }
      };
    } else if (nameLower.includes("artivatic")) {
      return {
        founded_year: 2017,
        founders: [
          { name: "Layak Singh", role: "Founder & CEO", brief_details: "IIT Kharagpur alum, Forbes 30 Under 30, serial tech product innovator." },
          { name: "Puneet Tandon", role: "Co-Founder & Chief Architect", brief_details: "Deep learning specialist, designed real-time medical document scanners." }
        ],
        funding_stages: {
          series: "Acquired",
          amount: "$15M",
          investors: ["DMI Finance", "DMI Sparkle Fund", "Indian Angel Network", "Scale Ventures"]
        },
        valuation_metrics: {
          revenue: "$4.5M (Rs 37 Cr)",
          ebitda_multiple: "8.5x Revenue Multiple",
          other_metrics: "Acquired by DMI Finance to power in-house digital insurance and lending underwriting."
        }
      };
    } else if (nameLower.includes("zerodha")) {
      return {
        founded_year: 2010,
        founders: [
          { name: "Nithin Kamath", role: "Founder & CEO", brief_details: "Pioneered discount broking model in India, avid promoter of financial literacy." },
          { name: "Nikhil Kamath", role: "Co-Founder & CIO", brief_details: "Sovereign fund manager, runs True Beacon asset manager and investments desk." }
        ],
        funding_stages: {
          series: "Bootstrapped",
          amount: "$0 (Fully Self-funded)",
          investors: ["None (100% Promoter Owned)"]
        },
        valuation_metrics: {
          revenue: "$1.05B (Rs 8,300 Cr)",
          ebitda_multiple: "12.0x EBITDA Multiple",
          other_metrics: "Highly profitable. Operates India's largest retail trading platform with 12M+ users."
        }
      };
    }

    // Default generic fallback
    return {
      founded_year: startup.founded_year || undefined,
      founders: startup.founder_name
        ? [{ name: startup.founder_name, role: "Founder", brief_details: "", linkedin_url: startup.founder_linkedin_url }]
        : [],
      funding_stages: {
        series: startup.funding_stage || "",
        amount: startup.funding_amount || "",
        investors: []
      },
      valuation_metrics: {
        revenue: "",
        ebitda_multiple: "",
        other_metrics: ""
      }
    };
  };

  const details = getRichDetails();

  // Edit forms states
  const [editingField, setEditingField] = useState<"website" | "founders" | "funding" | null>(null);

  // Field values
  const [websiteInput, setWebsiteInput] = useState(startup.website || "");
  const [foundersInput, setFoundersInput] = useState("");
  
  // Funding stage & amount
  const [fundingSeriesInput, setFundingSeriesInput] = useState("");
  const [fundingAmountInput, setFundingAmountInput] = useState("");
  const [fundingInvestorsInput, setFundingInvestorsInput] = useState("");

  const [savingField, setSavingField] = useState(false);
  const [recheckingField, setRecheckingField] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Sync inputs on startup change or details resolution
  React.useEffect(() => {
    setWebsiteInput(startup.website || "");
    setFoundersInput(JSON.stringify(details?.founders || [], null, 2));
    setFundingSeriesInput(details?.funding_stages?.series || "");
    setFundingAmountInput(details?.funding_stages?.amount || "");
    setFundingInvestorsInput((details?.funding_stages?.investors || []).join(", "));
    setEditError(null);
    setEditingField(null);
  }, [startup, details?.founded_year, details?.funding_stages?.series]);

  const handleSaveField = async (field: "website" | "founders" | "funding") => {
    if (!onUpdateField) return;
    setSavingField(true);
    setEditError(null);
    try {
      let value: any;
      if (field === "website") {
        value = websiteInput.trim();
      } else if (field === "founders") {
        try {
          value = JSON.parse(foundersInput);
          if (!Array.isArray(value)) {
            throw new Error("Founders list must be a JSON array.");
          }
        } catch (je: any) {
          setEditError(`Invalid JSON format: ${je.message}`);
          setSavingField(false);
          return;
        }
      } else {
        const investorsList = fundingInvestorsInput
          .split(",")
          .map(i => i.trim())
          .filter(i => i.length > 0);
        value = {
          series: fundingSeriesInput.trim(),
          amount: fundingAmountInput.trim(),
          investors: investorsList
        };
      }

      await onUpdateField(startup.id, field, value);
      setEditingField(null);
    } catch (err: any) {
      setEditError(err.message || "Failed to update field.");
    } finally {
      setSavingField(false);
    }
  };

  const handleRecheckFieldClick = async (field: "website" | "founders" | "funding") => {
    if (!onRecheckField) return;
    setRecheckingField(true);
    setEditError(null);
    try {
      const res = await onRecheckField(startup.id, field);
      if (res.error) {
        throw new Error(res.error);
      }
      
      if (field === "website") {
        const url = res.data?.startup_website || "";
        setWebsiteInput(url);
      } else if (field === "founders") {
        const list = res.data?.founders || [];
        setFoundersInput(JSON.stringify(list, null, 2));
      } else if (field === "funding") {
        const stages = res.data?.funding_stages || {};
        setFundingSeriesInput(stages.series || "");
        setFundingAmountInput(stages.amount || "");
        setFundingInvestorsInput((stages.investors || []).join(", "));
      }
      setEditingField(null);
    } catch (err: any) {
      setEditError(err.message || "AI Targeted Recheck failed.");
    } finally {
      setRecheckingField(false);
    }
  };

  // Submit Status Change
  const handleUpdateDetails = async () => {
    setStatusLoading(true);
    try {
      await onUpdateStatus(startup.id, localStatus, localTeam, localPriority);
    } catch (e) {
      console.error(e);
    } finally {
      setStatusLoading(false);
    }
  };

  // Submit Interaction Log
  const handleAddLog = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newInteraction.summary) return;
    setLogLoading(true);
    try {
      await onAddInteraction(startup.id, newInteraction);
      setNewInteraction({ type: "Introduction", summary: "", next_steps: "" });
    } catch (e) {
      console.error(e);
    } finally {
      setLogLoading(false);
    }
  };

  // Submit Assignment Create
  const handleCreateAssignment = async (e: React.FormEvent) => {
    e.preventDefault();
    setAssignLoading(true);
    try {
      await onCreateAssignment(startup.id, newAssignment);
      setNewAssignment({ assigned_to_fpr1: "Anurag", assigned_to_fpr2: "Keroli", notes: "" });
    } catch (e) {
      console.error(e);
    } finally {
      setAssignLoading(false);
    }
  };

  // Trigger LLM enrich pipeline
  const handleRunAIAnalysis = async () => {
    if (!onAnalyze) return;
    setAnalyzing(true);
    try {
      await onAnalyze(startup.id);
    } catch (e) {
      console.error(e);
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 flex items-center justify-end z-50 animate-fade-in" id="startup-detail-modal">
      <div className="bg-slate-50 w-full max-w-2xl h-full flex flex-col shadow-2xl overflow-hidden border-l border-slate-200">
        
        {/* Header Block */}
        <div className="p-6 bg-slate-900 text-white flex justify-between items-start border-b border-orange-500" id="detail-header">
          <div className="space-y-1.5 text-left">
            <div className="flex items-center gap-2">
              <span className="bg-amber-500 text-slate-950 font-bold px-2 py-0.5 rounded text-[10px] tracking-wide uppercase">
                {startup.sector}
              </span>
              <span className="text-[11px] text-slate-400 font-mono">ID: {startup.id}</span>
            </div>
            <h3 className="text-xl font-extrabold text-white flex items-center gap-2">
              {startup.startup_name}
              {startup.website && startup.website.trim() !== "" && startup.website !== "https://example.com" && (
                <a
                  href={startup.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-slate-400 hover:text-amber-400 transition-colors"
                >
                  <Globe size={16} />
                </a>
              )}
            </h3>
            <p className="text-slate-450 text-xs font-semibold">{startup.subsector}</p>
          </div>
          <button onClick={onClose} className="p-1 rounded-full text-slate-400 hover:bg-slate-800 hover:text-white transition-all cursor-pointer">
            <X size={20} />
          </button>
        </div>

        {/* Content Body - Scaled with scroll grids */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6" id="detail-scroller">
          
          {/* AI enrichment banner if pending */}
          {startup.priority_score <= 50 && onAnalyze && (
            <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl flex items-center justify-between gap-4">
              <div className="space-y-0.5 text-left">
                <h5 className="text-xs font-bold text-amber-800 flex items-center gap-1">
                  <Sparkles size={14} className="text-amber-500" /> AI Evaluation Pending
                </h5>
                <p className="text-[11px] text-slate-500">Run local LLM analysis to score integration fit, construct co-creation use-cases, and identify group owners.</p>
              </div>
              <button
                onClick={handleRunAIAnalysis}
                disabled={analyzing}
                className="bg-amber-500 hover:bg-amber-600 text-slate-900 border-0 text-xs font-bold px-3 py-2 rounded-lg shadow-sm transition-all whitespace-nowrap flex items-center gap-1 cursor-pointer"
              >
                {analyzing ? <RefreshCw className="animate-spin" size={13} /> : <Sparkles size={13} />}
                Enrich AI
              </button>
            </div>
          )}

          {/* Metadata Block */}
          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm grid grid-cols-2 lg:grid-cols-4 gap-4 text-left">
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Funding Stage</p>
              <p className="text-sm font-bold text-slate-800 mt-1">{startup.funding_stage}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Total Raised</p>
              <p className="text-sm font-bold text-slate-800 mt-1 flex items-center gap-0.5">
                <DollarSign size={13} className="text-slate-500" />
                {startup.funding_amount}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Advisor Team</p>
              <p className="text-sm font-bold text-blue-650 mt-1 truncate">{startup.assigned_team}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Priority Index</p>
              <p className="text-sm font-bold text-amber-600 mt-1 font-mono">{startup.priority_score || 0}/100</p>
            </div>
          </div>

          {/* Description Block */}
          <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-3 text-left">
            <h4 className="font-extrabold text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2">
              Brief Business Profile
            </h4>
            <p className="text-slate-655 text-xs leading-relaxed">
              {analysis?.summary?.business_model || 
               (startup.ai_summary && !startup.ai_summary.includes("No AI analysis") && !startup.ai_summary.includes("Registry Entry") && !startup.ai_summary.includes("CSV Import") ? startup.ai_summary : "") || 
               "Business profile pending AI evaluation. Please trigger 'Enrich AI' above to construct the business model and value propositions."}
            </p>
          </div>

          {/* News Article Summary Block */}
          {startup.description && startup.description.trim() !== "" && (
            <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-3 text-left animate-fade-in">
              <h4 className="font-extrabold text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2 flex items-center justify-between">
                <span>Recent News & Updates</span>
                {startup.source_url && (
                  <a
                    href={startup.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-slate-400 hover:text-blue-600 text-[10px] font-bold tracking-normal normal-case flex items-center gap-1 cursor-pointer"
                    onClick={(e) => e.stopPropagation()}
                  >
                    Source: {startup.source || "News Link"} <ExternalLink size={10} />
                  </a>
                )}
              </h4>
              <p className="text-slate-650 text-xs leading-relaxed">{startup.description}</p>
            </div>
          )}

          {/* Taxonomy & Classification Mapping */}
          <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4 text-left">
            <h4 className="font-extrabold text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2 flex items-center gap-1.5">
              <Compass size={14} className="text-indigo-500" />
              Taxonomy & Strategic Mapping
            </h4>

            {/* Industry, Sector, Subsector Path */}
            <div className="p-3 bg-slate-50 border border-slate-150 rounded-lg space-y-1.5">
              <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Classification Path</p>
              <div className="flex flex-wrap items-center gap-1 text-[11px] font-semibold text-slate-600 font-mono">
                <span className="text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded">{startup.industry || "Financial Services"}</span>
                <ChevronRight size={12} className="text-slate-400" />
                <span className="text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded">{startup.sector || "FinTech"}</span>
                <ChevronRight size={12} className="text-slate-400" />
                <span className="text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">{startup.subsector || "Lending"}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Business Models */}
              <div className="space-y-1.5">
                <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1">
                  <Briefcase size={11} className="text-slate-450" />
                  Business Model
                </p>
                <div className="flex flex-wrap gap-1">
                  {startup.business_models && startup.business_models.map((bm, idx) => (
                    <span key={idx} className="bg-slate-105 bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-[10px] font-bold border border-slate-200/40 uppercase">
                      {bm}
                    </span>
                  ))}
                  {(!startup.business_models || startup.business_models.length === 0) && (
                    <span className="text-slate-400 text-xs italic">B2B SaaS</span>
                  )}
                </div>
              </div>

              {/* Industry Relevance */}
              <div className="space-y-1.5">
                <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1">
                  <Layers size={11} className="text-slate-450" />
                  Target Focus Verticals
                </p>
                <div className="flex flex-wrap gap-1">
                  {startup.industry_relevance && startup.industry_relevance.map((rel, idx) => (
                    <span key={idx} className="bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded text-[10px] font-bold border border-indigo-100/50 uppercase">
                      {rel}
                    </span>
                  ))}
                  {(!startup.industry_relevance || startup.industry_relevance.length === 0) && (
                    <span className="text-slate-400 text-xs italic">BFSI</span>
                  )}
                </div>
              </div>
            </div>

            {/* Focus Keywords / Tags */}
            {startup.tags && startup.tags.length > 0 && (
              <div className="space-y-1.5 pt-2 border-t border-slate-50">
                <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Classification Tags / Keywords</p>
                <div className="flex flex-wrap gap-1">
                  {startup.tags.map((tag, idx) => (
                    <span key={idx} className="bg-slate-50 hover:bg-slate-100/80 text-slate-650 px-2 py-0.5 rounded text-[10px] font-medium border border-slate-200/50 transition-colors">
                      #{tag.toLowerCase().replace(/\s+/g, "-")}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Collaborative Tab Navigation */}
          <div className="border-b border-slate-200 flex gap-4">
            <button
              onClick={() => setActiveTab("insights")}
              className={`pb-2.5 text-xs font-bold uppercase tracking-wider relative ${
                activeTab === "insights"
                  ? "text-blue-600 border-b-2 border-blue-600"
                  : "text-slate-400 hover:text-slate-600"
              }`}
            >
              <span className="flex items-center gap-1.5">
                <Sparkles size={14} /> AI Strategic Fit
              </span>
            </button>
            <button
              onClick={() => setActiveTab("interactions")}
              className={`pb-2.5 text-xs font-bold uppercase tracking-wider relative ${
                activeTab === "interactions"
                  ? "text-blue-600 border-b-2 border-blue-600"
                  : "text-slate-400 hover:text-slate-600"
              }`}
            >
              <span className="flex items-center gap-1.5">
                <MessageSquare size={14} /> Engagements ({interactions.length})
              </span>
            </button>
            <button
              onClick={() => setActiveTab("assignment")}
              className={`pb-2.5 text-xs font-bold uppercase tracking-wider relative ${
                activeTab === "assignment"
                  ? "text-blue-600 border-b-2 border-blue-600"
                  : "text-slate-400 hover:text-slate-600"
              }`}
            >
              <span className="flex items-center gap-1.5">
                <ClipboardList size={14} /> Team Assign log
              </span>
            </button>
          </div>

          {/* Tab Content Panels */}
          {activeTab === "insights" && (
            <div className="space-y-5 animate-fade-in text-left" id="detail-tab-insights">
              {/* Summary and Gaps */}
              <div className="bg-slate-900 text-slate-100 p-5 rounded-xl space-y-3.5 border-l-4 border-amber-500 shadow-md">
                <div className="flex items-center justify-between">
                  <h5 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1">
                    <Sparkles size={13} className="text-amber-400" />
                    AI Intelligence Evaluation
                  </h5>
                  <span className="text-[10px] bg-amber-500/15 text-amber-400 uppercase font-bold py-0.5 px-2 rounded">
                    CoE verified
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed italic">
                  "{startup.ai_summary}"
                </p>
              </div>

              {/* Founding & Capital Structure Card */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <div className="flex justify-between items-center border-b border-slate-100 pb-2.5">
                  <h5 className="font-bold text-slate-900 text-xs uppercase tracking-wide flex items-center gap-1.5">
                    <Calendar size={14} className="text-blue-500" />
                    Founding & Capital Structure
                  </h5>
                  <span className="text-[10px] bg-blue-50 text-blue-700 px-2 py-0.5 rounded font-mono font-bold">
                    Est. {details?.founded_year || "Unknown"}
                  </span>
                </div>

                {/* Website row */}
                <div className="space-y-1 pb-3 border-b border-slate-100/60">
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] uppercase font-bold text-slate-450 tracking-wider">
                      Corporate Website
                    </span>
                    <button 
                      onClick={() => setEditingField(editingField === "website" ? null : "website")}
                      className="text-slate-450 hover:text-blue-600 transition-colors p-1"
                      title="Edit website"
                    >
                      <Pencil size={11} />
                    </button>
                  </div>
                  {editingField === "website" ? (
                    <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2.5 mt-1 animate-fade-in">
                      <input
                        type="url"
                        value={websiteInput}
                        onChange={(e) => setWebsiteInput(e.target.value)}
                        placeholder="https://example.com"
                        className="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg p-2 outline-none focus:ring-1 focus:ring-blue-500 transition-all font-mono"
                      />
                      {editError && <p className="text-[10px] font-semibold text-red-650">{editError}</p>}
                      <div className="flex justify-end gap-2 text-xs">
                        <button
                          type="button"
                          onClick={() => setEditingField(null)}
                          className="px-2.5 py-1 bg-slate-200 text-slate-700 font-bold rounded-md"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRecheckFieldClick("website")}
                          disabled={recheckingField || savingField}
                          className="px-2.5 py-1 bg-amber-500 text-slate-950 font-bold rounded-md flex items-center gap-1"
                        >
                          {recheckingField ? <RefreshCw size={10} className="animate-spin" /> : <Sparkles size={10} />}
                          AI Re-check
                        </button>
                        <button
                          type="button"
                          onClick={() => handleSaveField("website")}
                          disabled={recheckingField || savingField}
                          className="px-2.5 py-1 bg-blue-600 text-white font-bold rounded-md"
                        >
                          {savingField ? "Saving..." : "Save"}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs font-semibold text-slate-800 flex items-center gap-1">
                      {startup.website ? (
                        <a href={startup.website} target="_blank" rel="noopener noreferrer" className="text-blue-650 hover:underline flex items-center gap-1">
                          {startup.website} <ExternalLink size={11} />
                        </a>
                      ) : (
                        <span className="text-slate-400 italic font-medium">Not configured</span>
                      )}
                    </p>
                  )}
                </div>
                
                {/* Founders Row */}
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Founding Leadership</p>
                    <button 
                      onClick={() => setEditingField(editingField === "founders" ? null : "founders")}
                      className="text-slate-450 hover:text-blue-600 transition-colors p-1"
                      title="Edit founders"
                    >
                      <Pencil size={11} />
                    </button>
                  </div>
                  {editingField === "founders" ? (
                    <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2.5 mt-1 animate-fade-in">
                      <label className="block text-[10px] font-bold text-slate-450 uppercase mb-1">
                        Founders List (JSON Array)
                      </label>
                      <textarea
                        rows={6}
                        value={foundersInput}
                        onChange={(e) => setFoundersInput(e.target.value)}
                        placeholder='[ { "name": "Name", "role": "CEO", "brief_details": "Bio", "linkedin_url": "" } ]'
                        className="w-full bg-white border border-slate-200 text-slate-800 text-[10.5px] font-mono rounded-lg p-2 outline-none focus:ring-1 focus:ring-blue-500 transition-all leading-normal"
                      />
                      <span className="text-[9px] text-slate-450 font-semibold leading-tight block">
                        Must be a valid JSON array of objects with keys: name, role, brief_details, linkedin_url.
                      </span>
                      {editError && <p className="text-[10px] font-semibold text-red-650">{editError}</p>}
                      <div className="flex justify-end gap-2 text-xs">
                        <button
                          type="button"
                          onClick={() => setEditingField(null)}
                          className="px-2.5 py-1 bg-slate-200 text-slate-700 font-bold rounded-md"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRecheckFieldClick("founders")}
                          disabled={recheckingField || savingField}
                          className="px-2.5 py-1 bg-amber-500 text-slate-950 font-bold rounded-md flex items-center gap-1"
                        >
                          {recheckingField ? <RefreshCw size={10} className="animate-spin" /> : <Sparkles size={10} />}
                          AI Re-check
                        </button>
                        <button
                          type="button"
                          onClick={() => handleSaveField("founders")}
                          disabled={recheckingField || savingField}
                          className="px-2.5 py-1 bg-blue-600 text-white font-bold rounded-md"
                        >
                          {savingField ? "Saving..." : "Save"}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 gap-2.5">
                      {(details?.founders || []).map((founder: any, idx: number) => (
                        <div key={idx} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg border border-slate-100 hover:bg-slate-100/50 transition-colors">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-650 text-white flex items-center justify-center font-bold text-xs uppercase shadow-sm flex-shrink-0">
                            {founder?.name ? founder.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2) : "FD"}
                          </div>
                          <div className="space-y-0.5 text-left">
                            <div className="flex flex-wrap items-center gap-1.5">
                              <span className="text-xs font-bold text-slate-800">{founder?.name || "Founder"}</span>
                              {founder?.linkedin_url && (
                                <a
                                  href={founder.linkedin_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-500 hover:text-blue-700 inline-flex items-center"
                                  title="LinkedIn Profile"
                                >
                                  <Linkedin size={11} />
                                </a>
                              )}
                              <span className="text-[9px] bg-indigo-50 text-indigo-700 px-1.5 py-0.2 rounded font-bold uppercase tracking-wide">{founder?.role || "Founder"}</span>
                            </div>
                            <p className="text-[11px] text-slate-500 leading-normal">{founder?.brief_details || ""}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Funding Stage & Capital Raised Card */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <div className="flex justify-between items-center border-b border-slate-100 pb-2.5">
                  <h5 className="font-bold text-slate-900 text-xs uppercase tracking-wide flex items-center gap-1.5">
                    <DollarSign size={14} className="text-emerald-500" />
                    Funding Rounds & Investors
                  </h5>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded font-bold uppercase tracking-wide">
                      {details?.funding_stages?.series || "Unknown"}
                    </span>
                    <button 
                      onClick={() => setEditingField(editingField === "funding" ? null : "funding")}
                      className="text-slate-450 hover:text-blue-600 transition-colors p-1"
                      title="Edit funding details"
                    >
                      <Pencil size={11} />
                    </button>
                  </div>
                </div>

                {editingField === "funding" ? (
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-3 mt-1 animate-fade-in text-left">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="text-[10px] font-bold text-slate-450 uppercase mb-1 block">Series / Stage</label>
                        <input
                          type="text"
                          value={fundingSeriesInput}
                          onChange={(e) => setFundingSeriesInput(e.target.value)}
                          placeholder="e.g. Series A"
                          className="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg p-2 outline-none focus:ring-1 focus:ring-blue-500 transition-all"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-slate-450 uppercase mb-1 block">Capital Raised Amount</label>
                        <input
                          type="text"
                          value={fundingAmountInput}
                          onChange={(e) => setFundingAmountInput(e.target.value)}
                          placeholder="e.g. $10M"
                          className="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg p-2 outline-none focus:ring-1 focus:ring-blue-500 transition-all font-mono"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-450 uppercase mb-1 block">Investors (comma separated)</label>
                      <input
                        type="text"
                        value={fundingInvestorsInput}
                        onChange={(e) => setFundingInvestorsInput(e.target.value)}
                        placeholder="Investor 1, Investor 2"
                        className="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg p-2 outline-none focus:ring-1 focus:ring-blue-500 transition-all"
                      />
                    </div>
                    {editError && <p className="text-[10px] font-semibold text-red-650">{editError}</p>}
                    <div className="flex justify-end gap-2 text-xs pt-1">
                      <button
                        type="button"
                        onClick={() => setEditingField(null)}
                        className="px-2.5 py-1 bg-slate-200 text-slate-700 font-bold rounded-md"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRecheckFieldClick("funding")}
                        disabled={recheckingField || savingField}
                        className="px-2.5 py-1 bg-amber-500 text-slate-950 font-bold rounded-md flex items-center gap-1"
                      >
                        {recheckingField ? <RefreshCw size={10} className="animate-spin" /> : <Sparkles size={10} />}
                        AI Re-check
                      </button>
                      <button
                        type="button"
                        onClick={() => handleSaveField("funding")}
                        disabled={recheckingField || savingField}
                        className="px-2.5 py-1 bg-blue-600 text-white font-bold rounded-md"
                      >
                        {savingField ? "Saving..." : "Save"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 bg-emerald-50/40 rounded-lg border border-emerald-100/50 text-left">
                        <p className="text-[9px] uppercase font-bold text-slate-400 tracking-wider">Total Capital Raised</p>
                        <p className="text-base font-black text-emerald-650 mt-1 flex items-baseline gap-0.5">
                          <span className="text-xs font-bold">$</span>
                          {details?.funding_stages?.amount ? String(details.funding_stages.amount).replace("$", "") : "Unknown"}
                        </p>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 text-left">
                        <p className="text-[9px] uppercase font-bold text-slate-400 tracking-wider">Investment Status</p>
                        <p className="text-xs font-bold text-slate-700 mt-1.5 truncate">
                          {details?.funding_stages?.series?.includes("Bootstrapped") ? "Organic Operations" : "Strategic Fit Validated"}
                        </p>
                      </div>
                    </div>

                    {/* Key Investors */}
                    <div className="space-y-2 text-left">
                      <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Key Capital Supporters</p>
                      <div className="flex flex-wrap gap-1.5">
                        {(details?.funding_stages?.investors || []).length > 0 ? (
                          (details?.funding_stages?.investors || []).map((inv: string, idx: number) => (
                            <span key={idx} className="bg-slate-50 hover:bg-slate-100 text-slate-700 px-2 py-1 rounded text-[10.5px] font-medium border border-slate-200/50 transition-colors">
                              {inv}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-400 text-xs italic font-medium">No cap table investors reported (Bootstrapped or Self-Funded).</span>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>

              {/* Financials & Valuation Multiples Card */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <div className="flex justify-between items-center border-b border-slate-100 pb-2.5">
                  <h5 className="font-bold text-slate-900 text-xs uppercase tracking-wide flex items-center gap-1.5">
                    <Activity size={14} className="text-amber-500" />
                    Financial Valuations & Multiples
                  </h5>
                  <span className="text-[10px] bg-amber-50 text-amber-700 px-2 py-0.5 rounded font-bold uppercase tracking-wider">
                    ARR Metrics
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-amber-50/30 rounded-lg border border-amber-100/50">
                    <p className="text-[9px] uppercase font-bold text-slate-400 tracking-wider">Reported Annual Revenue</p>
                    <p className="text-xs font-black text-slate-800 mt-1.5 truncate">
                      {details?.valuation_metrics?.revenue || "Unknown"}
                    </p>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                    <p className="text-[9px] uppercase font-bold text-slate-400 tracking-wider">EBITDA / Valuation Multiple</p>
                    <p className="text-xs font-black text-slate-800 mt-1.5 truncate">
                      {details?.valuation_metrics?.ebitda_multiple || "N/A"}
                    </p>
                  </div>
                </div>

                {details?.valuation_metrics?.other_metrics && (
                  <div className="p-2.5 bg-blue-50/50 rounded-lg border border-blue-100/50 text-[10.5px] leading-relaxed text-blue-900 flex items-start gap-2 shadow-xs">
                    <Sparkles size={12} className="text-blue-500 mt-0.5 flex-shrink-0" />
                    <span><strong>Key Performance Metric:</strong> {details.valuation_metrics.other_metrics}</span>
                  </div>
                )}
              </div>

              {/* Entity Relevance Matrix Table */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-3">
                <h5 className="font-bold text-slate-900 text-xs uppercase tracking-wide border-b border-slate-100 pb-2">
                  Tailored Group Relevance
                </h5>
                <p className="text-xs text-slate-500 mb-2">{startup.entity_relevance}</p>
                <div className="space-y-3">
                  {startup.relevance_mapping && typeof startup.relevance_mapping === "object" && !Array.isArray(startup.relevance_mapping) && Object.entries(startup.relevance_mapping).map(([ent, desc]) => (
                    <div key={ent} className="p-3 bg-blue-50/50 rounded-lg border border-blue-100/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                      <strong className="text-xs text-blue-800 font-bold whitespace-nowrap">{ent}</strong>
                      <span className="text-[11px] text-slate-655 leading-relaxed text-left sm:text-right">
                        {desc}
                      </span>
                    </div>
                  ))}
                  {(!startup.relevance_mapping || typeof startup.relevance_mapping !== "object" || Array.isArray(startup.relevance_mapping) || Object.keys(startup.relevance_mapping).length === 0) && (
                    <p className="text-xs text-slate-400 text-center py-4">
                      No standalone target relevance records.
                    </p>
                  )}
                </div>
              </div>

              {/* Integration Use Cases */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-3">
                <h5 className="font-bold text-slate-900 text-xs uppercase tracking-wide border-b border-slate-100 pb-2">
                  Target Sandbox Use Cases
                </h5>
                <ul className="space-y-2 text-xs">
                  {startup.use_cases && startup.use_cases.map((uc, index) => (
                    <li key={index} className="flex gap-2.5 items-start p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                      <CheckCircle2 size={15} className="text-emerald-500 flex-shrink-0 mt-0.5" />
                      <span className="text-slate-650 leading-relaxed">{uc}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {activeTab === "interactions" && (
            <div className="space-y-6 animate-fade-in text-left" id="detail-tab-interactions">
              {/* Interaction Form for Admin / investment team ONLY */}
              {(currentUser.role === "Admin" || currentUser.role === "Investment Officer") && (
                <form onSubmit={handleAddLog} className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm space-y-3">
                  <h5 className="text-xs font-bold text-slate-900 uppercase tracking-wider border-b border-slate-100 pb-1.5">
                    Record Evaluation Milestone
                  </h5>

                  <div className="grid grid-cols-2 gap-3 ">
                    <div>
                      <label className="text-[10px] font-bold text-slate-450 uppercase mb-1 block">Activity Type</label>
                      <select
                        value={newInteraction.type}
                        onChange={(e) => setNewInteraction({ ...newInteraction, type: e.target.value })}
                        className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-1.5"
                      >
                        <option value="Introduction">Introduction</option>
                        <option value="Technical Review">Technical Review</option>
                        <option value="POC Execution">POC Execution</option>
                        <option value="MOU Signed">MOU Signed</option>
                        <option value="Stakeholder Pitch">Stakeholder Pitch</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-450 uppercase mb-1 block">Timeline target</label>
                      <input
                        type="text"
                        placeholder="In progress / Complete"
                        value={newInteraction.next_steps}
                        onChange={(e) => setNewInteraction({ ...newInteraction, next_steps: e.target.value })}
                        className="w-full bg-slate-50 border border-slate-200 text-slate-850 text-xs rounded-lg p-1.5 focus:outline-none"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-[10px] font-bold text-slate-450 uppercase mb-1 block">Detailed Meeting notes</label>
                    <textarea
                      required
                      rows={2}
                      value={newInteraction.summary}
                      onChange={(e) => setNewInteraction({ ...newInteraction, summary: e.target.value })}
                      placeholder="Discussed integration requirements, compliance restrictions, and secure API testing secure parameters..."
                      className="w-full bg-slate-50 border border-slate-200 text-slate-805 text-slate-800 text-xs rounded-lg p-1.5 focus:outline-none"
                    />
                  </div>

                  <div className="text-right">
                    <button
                      type="submit"
                      disabled={logLoading}
                      className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-4 py-1.5 rounded-lg font-bold transition-all inline-flex items-center gap-1 cursor-pointer border-0"
                    >
                      <Plus size={14} /> {logLoading ? "Recording log..." : "Commit Log"}
                    </button>
                  </div>
                </form>
              )}

              {/* History list */}
              <div className="space-y-3">
                <h5 className="font-bold text-slate-900 text-xs uppercase tracking-wide">
                  History log thread ({interactions.length})
                </h5>
                <div className="space-y-3">
                  {interactions.map((log) => (
                    <div key={log.id} className="p-4 bg-white rounded-xl border border-slate-200/80 shadow-xs space-y-1">
                      <div className="flex justify-between items-center bg-slate-50/50 p-1 rounded">
                        <span className="text-[10px] font-mono text-slate-400">
                          {new Date(log.date).toLocaleDateString()}
                        </span>
                        <span className="text-[10.5px] font-bold text-amber-700 uppercase bg-amber-50 px-1.5 rounded">
                          {log.type}
                        </span>
                      </div>
                      <p className="text-xs text-slate-700 leading-relaxed pt-1">{log.summary}</p>
                      <div className="pt-1.5 border-t border-slate-50 text-[10.5px] italic text-slate-500">
                        <strong>Target next status:</strong> {log.next_steps}
                      </div>
                    </div>
                  ))}
                  {interactions.length === 0 && (
                    <p className="text-xs text-slate-400 text-center py-6 bg-slate-50 border border-slate-100 rounded-lg">
                      No evaluation milestones logged for this startup file yet.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === "assignment" && (
            <div className="space-y-6 animate-fade-in text-left" id="detail-tab-assignments">
              {/* Creator Form for privileged roles */}
              {(currentUser.role === "Admin" || currentUser.role === "Investment Officer") && (
                <form onSubmit={handleCreateAssignment} className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm space-y-3">
                  <h5 className="text-xs font-bold text-slate-900 uppercase tracking-wider border-b border-slate-100 pb-1.5">
                    Launch New Department Task Assignment
                  </h5>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[10px] font-bold text-slate-450 uppercase mb-1 block">Assigned FPR1</label>
                      <select
                        value={newAssignment.assigned_to_fpr1}
                        onChange={(e) => setNewAssignment({ ...newAssignment, assigned_to_fpr1: e.target.value })}
                        className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-1.5 focus:outline-none"
                      >
                        {FPR1_LIST.map((fpr) => (
                          <option key={fpr} value={fpr}>
                            {fpr}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="text-[10px] font-bold text-slate-450 uppercase mb-1 block">Assigned FPR2</label>
                      <select
                        value={newAssignment.assigned_to_fpr2}
                        onChange={(e) => setNewAssignment({ ...newAssignment, assigned_to_fpr2: e.target.value })}
                        className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-1.5 focus:outline-none"
                      >
                        {FPR2_LIST.map((fpr) => (
                          <option key={fpr} value={fpr}>
                            {fpr}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="text-[10px] font-bold text-slate-450 uppercase mb-1 block">Sponsorship Notes</label>
                    <textarea
                      required
                      rows={2}
                      value={newAssignment.notes}
                      onChange={(e) => setNewAssignment({ ...newAssignment, notes: e.target.value })}
                      placeholder="Special directives, pilot roadmap, compliance checks sponsors directives..."
                      className="w-full bg-slate-50 border border-slate-200 text-slate-850 text-xs rounded-lg p-1.5 focus:outline-none"
                    />
                  </div>

                  <div className="text-right">
                    <button
                      type="submit"
                      disabled={assignLoading}
                      className="bg-indigo-600 hover:bg-indigo-700 text-indigo-700 border border-indigo-200 bg-indigo-50 text-xs px-4 py-1.5 rounded-lg font-bold transition-all cursor-pointer"
                    >
                      {assignLoading ? "Filing..." : "File Deployment Task"}
                    </button>
                  </div>
                </form>
              )}

              {/* Active record list */}
              <div className="space-y-3">
                <h5 className="font-bold text-slate-900 text-xs uppercase tracking-wide">
                  Active Department Assignments ({assignments.filter(a => String(a.startup_id) === String(startup.id)).length})
                </h5>
                <div className="space-y-3">
                  {assignments.filter(a => String(a.startup_id) === String(startup.id)).map((as) => (
                    <div key={as.id} className="p-4 bg-white rounded-xl border border-slate-200/80 shadow-xs space-y-3">
                      <div className="flex justify-between items-center border-b border-slate-100 pb-1">
                        <span className="font-extrabold text-xs text-indigo-900">ICICI Bank</span>
                        <span className="text-[9.5px] bg-indigo-50 text-indigo-750 px-1.5 py-0.5 rounded font-bold font-mono">
                          {as.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-655 text-slate-600 font-medium leading-relaxed italic">
                        "{as.notes}"
                      </p>

                      {/* Outreach Pitch Templates inside Assignment */}
                      {as.linkedin_reachout_message && (
                        <div className="p-2.5 bg-blue-50/50 rounded-lg border border-blue-100 text-[10.5px] leading-relaxed text-blue-900 shadow-xs">
                          <span className="font-extrabold text-blue-800 block mb-0.5">LinkedIn Outreach Pitch:</span>
                          <p className="italic">"{as.linkedin_reachout_message}"</p>
                        </div>
                      )}

                      {as.email_reachout_message && (
                        <div className="p-2.5 bg-indigo-50/50 rounded-lg border border-indigo-100 text-[10.5px] leading-relaxed text-indigo-950 shadow-xs">
                          <span className="font-extrabold text-indigo-850 block mb-0.5">Email Outreach Proposal:</span>
                          <p className="whitespace-pre-wrap font-sans italic">"{as.email_reachout_message}"</p>
                        </div>
                      )}

                      <div className="flex justify-between items-center text-[10px] text-slate-400 pt-1 border-t border-slate-100/40">
                        <span>FPR1: {as.assigned_to_fpr1 || as.team} • FPR2: {as.assigned_to_fpr2 || as.entity}</span>
                        <span>Filed: {as.assigned_at ? new Date(as.assigned_at).toLocaleDateString() : ""}</span>
                      </div>
                    </div>
                  ))}
                  {assignments.filter(a => String(a.startup_id) === String(startup.id)).length === 0 && (
                    <p className="text-xs text-slate-400 text-center py-6 bg-slate-50 border border-slate-100 rounded-lg">
                      No standalone team routing assignment tasks generated for this venture yet.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Action Panel Footer: modify status & priority */}
        <div className="bg-white p-5 border-t border-slate-200" id="detail-actions-footer">
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            {/* Status Dropdowns */}
            <div className="grid grid-cols-3 gap-2 flex-1 w-full text-left">
              <div>
                <label className="text-[9px] font-bold text-slate-450 uppercase mb-1 block">Sandbox Trial Status</label>
                <select
                  value={localStatus}
                  onChange={(e) => setLocalStatus(e.target.value as any)}
                  className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-1.5 focus:outline-none"
                >
                  <option value="Screening">Screening</option>
                  <option value="Evaluation">Evaluation</option>
                  <option value="Proof of Concept">Proof of Concept</option>
                  <option value="Partnership">Partnership</option>
                  <option value="Rejected">Rejected</option>
                </select>
              </div>

              <div>
                <label className="text-[9px] font-bold text-slate-450 uppercase mb-1 block">Assigned Advisor Core</label>
                <select
                  value={localTeam}
                  onChange={(e) => setLocalTeam(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-1.5 focus:outline-none"
                >
                  <option value="Lending Team">Lending Team</option>
                  <option value="Insurance Team">Insurance Team</option>
                  <option value="AMC/Securities Team">AMC/Securities Team</option>
                  <option value="Enterprise AI Team">Enterprise AI Team</option>
                </select>
              </div>

              <div>
                <label className="text-[9px] font-bold text-slate-450 uppercase mb-1 block">Priority Score</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={localPriority}
                  onChange={(e) => setLocalPriority(Number(e.target.value))}
                  className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-1.5 focus:outline-none font-mono"
                />
              </div>
            </div>

            {/* Commit update button */}
            <div className="w-full sm:w-auto text-right flex gap-2 flex-shrink-0">
              {onAnalyze && (
                <button
                  type="button"
                  onClick={() => {
                    setAnalyzing(true);
                    onAnalyze(startup.id, true).finally(() => setAnalyzing(false));
                  }}
                  disabled={analyzing || statusLoading}
                  className="w-full sm:w-auto bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 hover:border-slate-400 text-xs font-bold px-3 py-2 rounded-lg flex items-center justify-center gap-1 transition-all cursor-pointer"
                >
                  {analyzing ? <RefreshCw className="animate-spin" size={13} /> : <Sparkles size={13} />}
                  <span>Re-Enrich Profile</span>
                </button>
              )}
              <button
                type="button"
                onClick={handleUpdateDetails}
                disabled={statusLoading || analyzing}
                className="w-full sm:w-auto bg-slate-900 hover:bg-slate-800 text-white border-0 hover:text-amber-400 text-xs font-bold px-4 py-2 rounded-lg shadow-sm transition-all cursor-pointer"
              >
                {statusLoading ? "Updating..." : "Commit Update"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
