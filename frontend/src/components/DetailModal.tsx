import React, { useState, useEffect } from "react";
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
  Copy,
  Check,
  Building,
  AlertTriangle,
  Award,
  Users,
  Eye,
  Info,
  ArrowRight,
  ShieldAlert,
  ThumbsUp,
  ThumbsDown,
  Percent
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

const STAGE_LIST = [
  "New", "Under Review", "Business Team Intro", "Meeting Scheduled",
  "POC Evaluation", "Pilot", "Commercial Discussion", "Closed Won", "Closed Lost", "Monitor"
];

const ENTITIES_LIST = [
  "ICICI Bank", "ICICI Lombard", "ICICI Prudential Life",
  "ICICI Prudential AMC", "ICICI Securities", "ICICI HFC"
];

const TEAMS_LIST = [
  "Lending Team", "Insurance Team", "AMC/Securities Team", "Enterprise AI Team"
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
  onUpdateAssignment?: (id: string, updates: Partial<Assignment>) => Promise<void>;
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
  onUpdateAssignment,
  onAnalyze,
  onUpdateField,
  onRecheckField
}: DetailModalProps) {
  // Exactly 3 tabs: company, icici, workspace
  const [activeTab, setActiveTab] = useState<"company" | "icici" | "workspace">("company");

  // Drawer resize logic
  const [drawerWidth, setDrawerWidth] = useState<number>(() => {
    const saved = localStorage.getItem("detail_drawer_width");
    if (saved) {
      const parsed = parseInt(saved, 10);
      if (!isNaN(parsed)) return parsed;
    }
    return Math.floor(window.innerWidth * 0.6);
  });

  useEffect(() => {
    localStorage.setItem("detail_drawer_width", String(drawerWidth));
  }, [drawerWidth]);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = drawerWidth;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = moveEvent.clientX - startX;
      const newWidth = startWidth - deltaX;

      const minW = Math.floor(window.innerWidth * 0.5);
      const maxW = Math.floor(window.innerWidth * 0.95);

      setDrawerWidth(Math.max(minW, Math.min(maxW, newWidth)));
    };

    const handleMouseUp = () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  // Form State
  const [newInteraction, setNewInteraction] = useState({
    type: "Introduction",
    summary: "",
    next_steps: ""
  });
  const [logLoading, setLogLoading] = useState(false);

  // New assignment Form
  const [newAssignment, setNewAssignment] = useState({
    assigned_to_fpr1: "Anurag",
    assigned_to_fpr2: "Keroli",
    notes: "",
    icici_entity: "ICICI Bank",
    business_team: "Lending Team"
  });
  const [assignLoading, setAssignLoading] = useState(false);

  // Status updating state
  const [localStatus, setLocalStatus] = useState(startup.status || "Screening");
  const [localTeam, setLocalTeam] = useState(startup.assigned_team || "Lending Team");
  const [localPriority, setLocalPriority] = useState(startup.priority_score || 70);
  const [statusLoading, setStatusLoading] = useState(false);

  // AI analysis loader
  const [analyzing, setAnalyzing] = useState(false);

  // Recent news history state
  const [recentNews, setRecentNews] = useState<any[]>([]);
  const [newsLoading, setNewsLoading] = useState(false);

  // Copy Feedback States
  const [copiedLinkedIn, setCopiedLinkedIn] = useState(false);
  const [copiedEmail, setCopiedEmail] = useState(false);

  const rawApiUrl = (import.meta as any).env?.VITE_API_URL || "http://localhost:8000/api";
  const API_URL = rawApiUrl.endsWith("/")
    ? (rawApiUrl.endsWith("/api/") ? rawApiUrl.slice(0, -1) : rawApiUrl + "api")
    : (rawApiUrl.endsWith("/api") ? rawApiUrl : rawApiUrl + "/api");

  // Fetch recent news when drawer opens
  useEffect(() => {
    if (startup.recent_news && Array.isArray(startup.recent_news) && startup.recent_news.length > 0) {
      setRecentNews(startup.recent_news);
      return;
    }
    if (!startup.id) return;
    setNewsLoading(true);
    fetch(`${API_URL}/startup/${startup.id}/news`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data && Array.isArray(data.news)) {
          setRecentNews(data.news);
        }
      })
      .catch(() => { })
      .finally(() => setNewsLoading(false));
  }, [startup.id]);

  const rawAnalysisRecord = (startup.startup_analyses && startup.startup_analyses.length > 0)
    ? startup.startup_analyses[0]
    : (startup.startup_analysis && startup.startup_analysis.length > 0)
      ? startup.startup_analysis[0]
      : null;

  const analysis = rawAnalysisRecord
    ? (((rawAnalysisRecord as any).analysis_data || (rawAnalysisRecord as any).analysis_json) as any)
    : null;

  // Inline edit fields form states
  const [editingField, setEditingField] = useState<"startup_name" | "website" | "linkedin" | "founders" | "description" | "products" | "funding" | null>(null);
  const [nameInput, setNameInput] = useState(startup.startup_name || "");
  const [websiteInput, setWebsiteInput] = useState(startup.website || "");
  const [linkedinInput, setLinkedinInput] = useState(startup.linkedin_url || "");
  const [foundersInput, setFoundersInput] = useState("");
  const [descriptionInput, setDescriptionInput] = useState("");
  const [productsInput, setProductsInput] = useState("");
  const [fundingSeriesInput, setFundingSeriesInput] = useState("");
  const [fundingAmountInput, setFundingAmountInput] = useState("");
  const [fundingInvestorsInput, setFundingInvestorsInput] = useState("");
  const [savingField, setSavingField] = useState(false);
  const [recheckingField, setRecheckingField] = useState<any>(false);
  const isFieldSpinning = (field: string) => {
    return recheckingField === "all" || recheckingField === field || recheckingField === true;
  };
  const [editError, setEditError] = useState<string | null>(null);

  // Resizable products table states
  const [colWidths, setColWidths] = useState<number[]>([150, 150, 300, 150, 150]);
  const [rowHeights, setRowHeights] = useState<Record<number, number>>({});

  const startResizeCol = (index: number, e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = colWidths[index];
    
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const delta = moveEvent.clientX - startX;
      setColWidths(prev => {
        const next = [...prev];
        next[index] = Math.max(80, startWidth + delta);
        return next;
      });
    };

    const handleMouseUp = () => {
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  const startResizeRow = (index: number, e: React.MouseEvent) => {
    e.preventDefault();
    const startY = e.clientY;
    const startHeight = rowHeights[index] || 45; // default row height
    
    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const delta = moveEvent.clientY - startY;
      setRowHeights(prev => ({
        ...prev,
        [index]: Math.max(30, startHeight + delta)
      }));
    };

    const handleMouseUp = () => {
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };


  // Sync inputs on startup update
  useEffect(() => {
    setNameInput(startup.startup_name || "");
    setWebsiteInput(startup.website || "");
    setLinkedinInput(startup.linkedin_url || "");
    setDescriptionInput(startup.ai_summary || startup.description || "");

    const mIntel = startup.market_intelligence || analysis?.market_intelligence || {};
    
    // Unpack products for edit input text area
    const rawProducts = mIntel.products;
    const unpackedProducts = Array.isArray(rawProducts)
      ? rawProducts
      : (rawProducts && typeof rawProducts === "object" && Array.isArray((rawProducts as any).value))
        ? (rawProducts as any).value
        : [];
    const localProducts = unpackedProducts.map((prod: any) => ({
      product_name: prod.product_name || prod.name || "",
      category: prod.category || prod.type || "",
      description: prod.description || "",
      target: prod.target || prod.target_audience || "",
      deployment: prod.deployment || prod.evidence_url || ""
    }));
    setProductsInput(JSON.stringify(localProducts, null, 2));

    const initialFounders = analysis?.founders || (startup.founder_name ? [{ name: startup.founder_name, role: "Founder", brief_details: "", linkedin_url: startup.founder_linkedin_url }] : []);
    setFoundersInput(JSON.stringify(initialFounders, null, 2));

    // Unpack funding for edit inputs
    const fundingInfo = mIntel.funding && typeof mIntel.funding === "object" && "value" in mIntel.funding
      ? (mIntel.funding as any).value
      : mIntel.funding || {};
    
    const fundingSeries = startup.latest_round_stage || fundingInfo.latest_round || analysis?.funding_stages?.series || startup.funding_stage || "";
    const fundingAmount = startup.total_funding || fundingInfo.total_funding || analysis?.funding_stages?.amount || startup.funding_amount || "";
    
    const rawInvestorsList = fundingInfo.investors || analysis?.funding_stages?.investors || [];
    const fundingInvestors = Array.isArray(rawInvestorsList)
      ? rawInvestorsList.join(", ")
      : typeof rawInvestorsList === "string"
        ? rawInvestorsList
        : "";

    setFundingSeriesInput(fundingSeries);
    setFundingAmountInput(fundingAmount);
    setFundingInvestorsInput(fundingInvestors);
    setEditError(null);
    setEditingField(null);
  }, [startup, analysis]);

  const handleSaveField = async (field: "startup_name" | "website" | "linkedin" | "founders" | "description" | "products" | "funding") => {
    if (!onUpdateField) return;
    setSavingField(true);
    setEditError(null);
    try {
      let value: any;
      if (field === "startup_name") {
        value = nameInput.trim();
      } else if (field === "website") {
        value = websiteInput.trim();
      } else if (field === "linkedin") {
        value = linkedinInput.trim();
      } else if (field === "description") {
        value = descriptionInput.trim();
      } else if (field === "products") {
        try {
          value = JSON.parse(productsInput);
          if (!Array.isArray(value)) {
            throw new Error("Products list must be a JSON array.");
          }
        } catch (je: any) {
          setEditError(`Invalid JSON format: ${je.message}`);
          setSavingField(false);
          return;
        }
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

  const handleRecheckFieldClick = async (field: string) => {
    if (!onRecheckField) return;
    setRecheckingField(field);
    setEditError(null);
    try {
      const res = await onRecheckField(startup.id, field);
      if (res.error) {
        throw new Error(res.error);
      }
      if (field === "startup_name") {
        setNameInput(res.data?.brand_name || "");
      } else if (field === "website") {
        setWebsiteInput(res.data?.startup_website || "");
      } else if (field === "linkedin") {
        setLinkedinInput(res.data?.linkedin_company_url || "");
      } else if (field === "description") {
        setDescriptionInput(res.data?.company_profile || "");
      } else if (field === "products") {
        setProductsInput(JSON.stringify(res.data?.products || [], null, 2));
      } else if (field === "founders") {
        setFoundersInput(JSON.stringify(res.data?.founders || [], null, 2));
      } else if (field === "funding") {
        const stages = res.data?.funding_stages || {};
        setFundingSeriesInput(stages.series || "");
        setFundingAmountInput(stages.amount || "");
        setFundingInvestorsInput((stages.investors || []).join(", "));
      }
      setEditingField(null);
    } catch (err: any) {
      setEditError(err.message || "AI targeted recheck failed.");
    } finally {
      setRecheckingField(false);
    }
  };

  // Submit Status updates
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

  // Submit Assignment creation
  const handleCreateAssignment = async (e: React.FormEvent) => {
    e.preventDefault();
    setAssignLoading(true);
    try {
      await onCreateAssignment(startup.id, newAssignment);
      setNewAssignment({
        assigned_to_fpr1: "Anurag",
        assigned_to_fpr2: "Keroli",
        notes: "",
        icici_entity: "ICICI Bank",
        business_team: "Lending Team"
      });
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

  // Copy helper
  const copyText = (text: string, type: "linkedin" | "email") => {
    navigator.clipboard.writeText(text);
    if (type === "linkedin") {
      setCopiedLinkedIn(true);
      setTimeout(() => setCopiedLinkedIn(false), 2000);
    } else {
      setCopiedEmail(true);
      setTimeout(() => setCopiedEmail(false), 2000);
    }
  };

  // Find assignment record if exists
  const assignment = assignments.find(a => String(a.startup_id) === String(startup.id));

  // Extract products, competitors, valuation, investors from nested market intelligence structure
  const mIntel = startup.market_intelligence || analysis?.market_intelligence || {};
  
  // Unpack products and support both agent schema (name, type) and legacy/UI schema (product_name, category)
  const rawProducts = mIntel.products;
  const productsList = Array.isArray(rawProducts) 
    ? rawProducts 
    : (rawProducts && typeof rawProducts === "object" && Array.isArray((rawProducts as any).value))
      ? (rawProducts as any).value
      : [];
  const products = productsList.map((prod: any) => ({
    product_name: prod.product_name || prod.name || "",
    category: prod.category || prod.type || "",
    description: prod.description || "",
    target: prod.target || prod.target_audience || "",
    deployment: prod.deployment || prod.evidence_url || ""
  }));

  // Unpack competitors and support both agent schema (name, reason) and legacy/UI schema (company_name, positioning)
  const rawCompetitors = mIntel.competitors;
  const competitorsList = Array.isArray(rawCompetitors)
    ? rawCompetitors
    : (rawCompetitors && typeof rawCompetitors === "object" && Array.isArray((rawCompetitors as any).value))
      ? (rawCompetitors as any).value
      : [];
  const competitors = competitorsList.map((comp: any) => ({
    company_name: comp.company_name || comp.name || "",
    category: comp.category || (comp.website ? comp.website.replace("https://", "").replace("http://", "").replace("www.", "") : "Competitor"),
    positioning: comp.positioning || comp.reason || ""
  }));

  // Valuation
  const rawValuation = mIntel.valuation;
  const valuation = (rawValuation && typeof rawValuation === "object" && !("value" in rawValuation))
    ? rawValuation
    : (rawValuation && typeof rawValuation === "object" && "value" in rawValuation)
      ? (rawValuation as any).value
      : {};

  // Funding
  const fundingInfo = mIntel.funding && typeof mIntel.funding === "object" && "value" in mIntel.funding
    ? (mIntel.funding as any).value
    : mIntel.funding || {};

  // Build structured investors list from funding_history or flat investors list
  let investors: any[] = [];
  if (Array.isArray(mIntel.investors) && mIntel.investors.length > 0) {
    investors = mIntel.investors;
  } else if (Array.isArray(fundingInfo.funding_history)) {
    const list: any[] = [];
    fundingInfo.funding_history.forEach((roundInfo: any) => {
      const round = roundInfo.round || "Funding Round";
      const date = roundInfo.date || "Date Unspecified";
      const roundInvestors = roundInfo.investors || [];
      if (Array.isArray(roundInvestors)) {
        roundInvestors.forEach((invName: any) => {
          list.push({
            round,
            investor_name: typeof invName === "string" ? invName : (invName.name || "Unknown"),
            date
          });
        });
      } else if (typeof roundInvestors === "string") {
        list.push({
          round,
          investor_name: roundInvestors,
          date
        });
      }
    });
    investors = list;
  } else if (Array.isArray(fundingInfo.investors)) {
    investors = fundingInfo.investors.map((name: any) => ({
      round: "Investor",
      investor_name: String(name),
      date: ""
    }));
  }

  const strategicPositioning = mIntel.strategic_positioning || "";

  // Dynamic status color helper
  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "Partnership":
      case "Closed Won":
        return "bg-emerald-100 text-emerald-800 border-emerald-250";
      case "Proof of Concept":
      case "Pilot":
        return "bg-blue-100 text-blue-800 border-blue-250";
      case "Evaluation":
      case "Under Review":
        return "bg-amber-100 text-amber-800 border-amber-250";
      case "Rejected":
      case "Closed Lost":
        return "bg-rose-100 text-rose-800 border-rose-250";
      default:
        return "bg-slate-100 text-slate-800 border-slate-205";
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-end z-50 animate-fade-in" id="startup-detail-drawer">
      <div
        className="bg-slate-50 h-full flex flex-col shadow-2xl relative border-l border-slate-200 w-full md:w-auto"
        style={{
          width: window.innerWidth >= 768 ? `${drawerWidth}px` : "100vw"
        }}
      >
        {/* Resize Handler Bar */}
        <div
          className="hidden md:block absolute top-0 left-0 bottom-0 w-1.5 cursor-ew-resize hover:bg-amber-500/50 active:bg-amber-500 transition-colors z-50"
          onMouseDown={handleMouseDown}
          title="Drag to resize side panel"
        />

        {/* Drawer Header Block */}
        <div className="p-6 bg-slate-900 text-white flex justify-between items-start border-b border-orange-500 select-none">
          <div className="space-y-2 text-left">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="bg-orange-500 text-slate-950 font-black px-2.5 py-0.5 rounded text-[10px] tracking-wider uppercase">
                {startup.sector}
              </span>
              {startup.priority_band && (
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${startup.priority_band === "Critical" ? "bg-rose-600 text-white" :
                    startup.priority_band === "High" ? "bg-orange-600 text-white" :
                      startup.priority_band === "Medium" ? "bg-amber-500 text-slate-950" :
                        "bg-slate-700 text-slate-300"
                  }`}>
                  {startup.priority_band} Priority
                </span>
              )}
              <span className="text-[11px] text-slate-400 font-mono">ID: {startup.id}</span>
            </div>

            {editingField === "startup_name" ? (
              <div className="flex items-center gap-2 mt-1">
                <input
                  type="text"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  className="bg-slate-800 border border-slate-700 text-white text-sm rounded px-2 py-1 focus:outline-none focus:border-orange-500 font-bold"
                  placeholder="Startup Name"
                />
                <button
                  onClick={() => handleSaveField("startup_name")}
                  className="bg-orange-500 hover:bg-orange-600 text-slate-950 text-[10px] font-bold px-2 py-1 rounded"
                >
                  Save
                </button>
                <button
                  onClick={() => setEditingField(null)}
                  className="bg-slate-700 hover:bg-slate-650 text-white text-[10px] font-bold px-2 py-1 rounded"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <h3 className="text-2xl font-black text-white flex items-center gap-2.5">
                {startup.startup_name}
                {startup.website && startup.website.trim() !== "" && (
                  <a
                    href={startup.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-slate-400 hover:text-orange-400 transition-colors"
                  >
                    <Globe size={18} />
                  </a>
                )}
                {onUpdateField && (
                  <button
                    onClick={() => {
                      setNameInput(startup.startup_name || "");
                      setEditingField("startup_name");
                    }}
                    className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition-colors border-0 bg-transparent cursor-pointer"
                    title="Edit Name"
                  >
                    <Pencil size={14} />
                  </button>
                )}
                {onRecheckField && (
                  <button
                    onClick={() => handleRecheckFieldClick("startup_name")}
                    className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition-colors border-0 bg-transparent cursor-pointer"
                    title="AI Recheck Name"
                    disabled={recheckingField}
                  >
                    <RefreshCw size={14} className={isFieldSpinning("startup_name") ? "animate-spin" : ""} />
                  </button>
                )}
              </h3>
            )}
            <p className="text-slate-400 text-xs font-semibold">{startup.subsector}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-full text-slate-450 hover:bg-slate-800 hover:text-white transition-all cursor-pointer">
            <X size={20} />
          </button>
        </div>

        {/* Dynamic Tab Navigation (Exactly 3 tabs) */}
        <div className="bg-slate-100 border-b border-slate-200 px-6 py-2.5 flex gap-2">
          <button
            onClick={() => setActiveTab("company")}
            className={`px-4 py-2 text-xs font-black uppercase tracking-wider rounded-lg transition-all flex items-center gap-2 ${activeTab === "company"
                ? "bg-slate-900 text-white shadow-sm"
                : "text-slate-650 hover:bg-slate-200 hover:text-slate-900"
              }`}
          >
            <Building size={14} />
            Company Intelligence
          </button>
          <button
            onClick={() => setActiveTab("icici")}
            className={`px-4 py-2 text-xs font-black uppercase tracking-wider rounded-lg transition-all flex items-center gap-2 ${activeTab === "icici"
                ? "bg-slate-900 text-white shadow-sm"
                : "text-slate-650 hover:bg-slate-200 hover:text-slate-900"
              }`}
          >
            <Award size={14} />
            ICICI Relevance
          </button>
          <button
            onClick={() => setActiveTab("workspace")}
            className={`px-4 py-2 text-xs font-black uppercase tracking-wider rounded-lg transition-all flex items-center gap-2 ${activeTab === "workspace"
                ? "bg-slate-900 text-white shadow-sm"
                : "text-slate-650 hover:bg-slate-200 hover:text-slate-900"
              }`}
          >
            <ClipboardList size={14} />
            Engagement Workspace
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6" id="detail-scroller">

          {/* AI enrichment banner if pending */}
          {(!startup.recommendation_score || startup.recommendation_score === 0) && onAnalyze && (
            <div className="bg-orange-50 border border-orange-200 p-4 rounded-xl flex items-center justify-between gap-4">
              <div className="space-y-1 text-left">
                <h5 className="text-xs font-black text-orange-850 flex items-center gap-1.5">
                  <Sparkles size={14} className="text-orange-500" /> Multi-Agent Intelligence Available
                </h5>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Trigger multi-agent pipeline to extract market insights, match business problems and perform scoring metrics.
                </p>
              </div>
              <button
                onClick={handleRunAIAnalysis}
                disabled={analyzing}
                className="bg-orange-500 hover:bg-orange-600 text-slate-950 text-xs font-black px-3.5 py-2 rounded-lg shadow-sm transition-all whitespace-nowrap flex items-center gap-1.5 cursor-pointer border-0"
              >
                {analyzing ? <RefreshCw className="animate-spin" size={13} /> : <Sparkles size={13} />}
                {analyzing ? "Enriching..." : "Enrich Workspace"}
              </button>
            </div>
          )}

          {/* TAB 1: COMPANY INTELLIGENCE */}
          {activeTab === "company" && (
            <div className="space-y-6 animate-fade-in text-left">

              {/* Overview Section */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2">
                  Company Overview
                </h4>
                <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
                  <div>
                    <p className="text-[10px] uppercase font-bold text-slate-400 flex items-center justify-between">
                      <span>Website</span>
                      <span className="flex gap-1">
                        {onUpdateField && (
                          <button
                            onClick={() => {
                              setWebsiteInput(startup.website || "");
                              setEditingField("website");
                            }}
                            className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0"
                            title="Edit Website"
                          >
                            <Pencil size={10} />
                          </button>
                        )}
                        {onRecheckField && (
                          <button
                            onClick={() => handleRecheckFieldClick("website")}
                            className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0"
                            title="AI Recheck Website"
                            disabled={recheckingField}
                          >
                            <RefreshCw size={10} className={isFieldSpinning("website") ? "animate-spin" : ""} />
                          </button>
                        )}
                      </span>
                    </p>
                    {editingField === "website" ? (
                      <div className="flex flex-col gap-1 mt-1">
                        <input
                          type="text"
                          value={websiteInput}
                          onChange={(e) => setWebsiteInput(e.target.value)}
                          className="w-full bg-slate-50 border border-slate-200 text-xs rounded p-1"
                        />
                        <div className="flex gap-1">
                          <button
                            onClick={() => handleSaveField("website")}
                            className="bg-indigo-600 hover:bg-indigo-705 text-white text-[9px] font-bold px-1.5 py-0.5 rounded cursor-pointer border-0"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => setEditingField(null)}
                            className="bg-slate-300 hover:bg-slate-400 text-slate-700 text-[9px] font-bold px-1.5 py-0.5 rounded cursor-pointer border-0"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : startup.website ? (
                      <a href={startup.website} target="_blank" rel="noopener noreferrer" className="text-xs font-bold text-blue-600 hover:underline flex items-center gap-1 mt-1 truncate">
                        Visit <ExternalLink size={10} />
                      </a>
                    ) : (
                      <p className="text-xs font-semibold text-slate-400 mt-1">N/A</p>
                    )}
                  </div>
                  <div>
                    <p className="text-[10px] uppercase font-bold text-slate-400 flex items-center justify-between">
                      <span>LinkedIn</span>
                      <span className="flex gap-1">
                        {onUpdateField && (
                          <button
                            onClick={() => {
                              setLinkedinInput(startup.linkedin_url || "");
                              setEditingField("linkedin");
                            }}
                            className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0"
                            title="Edit LinkedIn"
                          >
                            <Pencil size={10} />
                          </button>
                        )}
                        {onRecheckField && (
                          <button
                            onClick={() => handleRecheckFieldClick("linkedin")}
                            className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0"
                            title="AI Recheck LinkedIn"
                            disabled={recheckingField}
                          >
                            <RefreshCw size={10} className={isFieldSpinning("linkedin") ? "animate-spin" : ""} />
                          </button>
                        )}
                      </span>
                    </p>
                    {editingField === "linkedin" ? (
                      <div className="flex flex-col gap-1 mt-1">
                        <input
                          type="text"
                          value={linkedinInput}
                          onChange={(e) => setLinkedinInput(e.target.value)}
                          className="w-full bg-slate-50 border border-slate-200 text-xs rounded p-1"
                        />
                        <div className="flex gap-1">
                          <button
                            onClick={() => handleSaveField("linkedin")}
                            className="bg-indigo-600 hover:bg-indigo-705 text-white text-[9px] font-bold px-1.5 py-0.5 rounded cursor-pointer border-0"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => setEditingField(null)}
                            className="bg-slate-300 hover:bg-slate-400 text-slate-700 text-[9px] font-bold px-1.5 py-0.5 rounded cursor-pointer border-0"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : startup.linkedin_url ? (
                      <a href={startup.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-xs font-bold text-blue-600 hover:underline flex items-center gap-1 mt-1 truncate">
                        LinkedIn <ExternalLink size={10} />
                      </a>
                    ) : (
                      <p className="text-xs font-semibold text-slate-400 mt-1">N/A</p>
                    )}
                  </div>
                  <div>
                    <p className="text-[10px] uppercase font-bold text-slate-400 flex items-center justify-between">
                      <span>Headquarters</span>
                      {onRecheckField && (
                        <button
                          onClick={() => handleRecheckFieldClick("headquarters")}
                          className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0 ml-1"
                          title="AI Recheck Headquarters"
                          disabled={recheckingField}
                        >
                          <RefreshCw size={8} className={isFieldSpinning("headquarters") ? "animate-spin" : ""} />
                        </button>
                      )}
                    </p>
                    <p className="text-xs font-bold text-slate-800 mt-1">{startup.headquarters || "India"}</p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase font-bold text-slate-400 flex items-center justify-between">
                      <span>Founded</span>
                      {onRecheckField && (
                        <button
                          onClick={() => handleRecheckFieldClick("founded")}
                          className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0 ml-1"
                          title="AI Recheck Founded Year"
                          disabled={recheckingField}
                        >
                          <RefreshCw size={8} className={isFieldSpinning("founded") ? "animate-spin" : ""} />
                        </button>
                      )}
                    </p>
                    <p className="text-xs font-bold text-slate-800 mt-1">{startup.founded_year || "Unknown"}</p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase font-bold text-slate-400 flex items-center justify-between">
                      <span>Stage</span>
                      {onRecheckField && (
                        <button
                          onClick={() => handleRecheckFieldClick("stage")}
                          className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0 ml-1"
                          title="AI Recheck Stage"
                          disabled={recheckingField}
                        >
                          <RefreshCw size={8} className={isFieldSpinning("stage") ? "animate-spin" : ""} />
                        </button>
                      )}
                    </p>
                    <p className="text-xs font-bold text-slate-800 mt-1">{startup.startup_stage || startup.funding_stage || "Early Stage"}</p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase font-bold text-slate-400 flex items-center justify-between">
                      <span>Status</span>
                      {onRecheckField && (
                        <button
                          onClick={() => handleRecheckFieldClick("status")}
                          className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0 ml-1"
                          title="AI Recheck Status"
                          disabled={recheckingField}
                        >
                          <RefreshCw size={8} className={isFieldSpinning("status") ? "animate-spin" : ""} />
                        </button>
                      )}
                    </p>
                    <p className="text-xs font-bold text-slate-800 mt-1">{startup.startup_status || startup.status || "Screening"}</p>
                  </div>
                </div>
              </div>

              {/* Founders & Leadership */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2 flex items-center justify-between">
                  <span>Founders &amp; Leadership</span>
                  <div className="flex gap-2">
                    {onUpdateField && (
                      <button
                        onClick={() => {
                          const initialFounders = analysis?.founders || (startup.founder_name ? [{ name: startup.founder_name, role: "Founder", brief_details: "", linkedin_url: startup.founder_linkedin_url }] : []);
                          setFoundersInput(JSON.stringify(initialFounders, null, 2));
                          setEditingField(editingField === "founders" ? null : "founders");
                        }}
                        className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0"
                        title="Edit Founders"
                      >
                        <Pencil size={12} />
                      </button>
                    )}
                    {onRecheckField && (
                      <button
                        onClick={() => handleRecheckFieldClick("founders")}
                        className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0"
                        title="AI Recheck Founders"
                        disabled={recheckingField}
                      >
                        <RefreshCw size={12} className={isFieldSpinning("founders") ? "animate-spin" : ""} />
                      </button>
                    )}
                  </div>
                </h4>
                {editingField === "founders" ? (
                  <div className="space-y-2">
                    <textarea
                      rows={6}
                      value={foundersInput}
                      onChange={(e) => setFoundersInput(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 text-xs rounded p-2 font-mono"
                      placeholder="JSON Array of founders..."
                    />
                    {editError && <p className="text-red-500 text-[10px]">{editError}</p>}
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => handleSaveField("founders")}
                        className="bg-indigo-600 hover:bg-indigo-705 text-white text-[11px] font-bold px-3 py-1 rounded cursor-pointer border-0"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => setEditingField(null)}
                        className="bg-slate-300 hover:bg-slate-400 text-slate-700 text-[11px] font-bold px-3 py-1 rounded cursor-pointer border-0"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : Array.isArray(analysis?.founders) && analysis.founders.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {analysis.founders.map((founder: any, idx: number) => (
                      <div key={idx} className="p-3 bg-slate-50 border border-slate-200/60 rounded-xl flex items-start gap-3 hover:bg-slate-100/60 transition-colors">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-slate-700 to-slate-900 text-white flex items-center justify-center font-bold text-xs uppercase flex-shrink-0">
                          {founder.name ? founder.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2) : "FD"}
                        </div>
                        <div className="space-y-1 text-left min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs font-bold text-slate-855 truncate">{founder.name}</span>
                            {founder.linkedin_url && (
                              <a href={founder.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-700">
                                <Linkedin size={11} />
                              </a>
                            )}
                          </div>
                          <p className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">{founder.role || "Co-Founder"}</p>
                          {founder.brief_details && <p className="text-[11px] text-slate-655 leading-normal">{founder.brief_details}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : startup.founder_name ? (
                  <div className="p-3 bg-slate-50 border border-slate-200/60 rounded-xl flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-slate-700 text-white flex items-center justify-center font-bold text-xs uppercase">
                        {startup.founder_name.split(" ").map((w: string) => w[0]).join("").slice(0, 2)}
                      </div>
                      <div className="text-left">
                        <p className="text-xs font-bold text-slate-800">{startup.founder_name}</p>
                        <p className="text-[10px] text-slate-400">Founder</p>
                      </div>
                    </div>
                    {startup.founder_linkedin_url && (
                      <a href={startup.founder_linkedin_url} target="_blank" rel="noopener noreferrer" className="bg-slate-200 p-1.5 rounded-lg text-blue-650 hover:bg-blue-100 hover:text-blue-800 transition-colors">
                        <Linkedin size={14} />
                      </a>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-slate-450 italic">No founder profiles recorded. Enrich this startup to parse founder details.</p>
                )}
              </div>

              {/* Taxonomy Chips */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2 flex items-center justify-between">
                  <span>Industry Taxonomy Mapping</span>
                  {onRecheckField && (
                    <button
                      onClick={() => handleRecheckFieldClick("industry")}
                      className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0"
                      title="AI Recheck Taxonomy Mapping"
                      disabled={recheckingField}
                    >
                      <RefreshCw size={10} className={isFieldSpinning("industry") ? "animate-spin" : ""} />
                    </button>
                  )}
                </h4>
                <div className="space-y-3">
                  <div className="flex flex-wrap gap-2 items-center">
                    <span className="text-[10px] uppercase font-bold text-slate-400 w-24">Path:</span>
                    <div className="flex items-center gap-1.5 text-xs font-black text-slate-700 font-mono bg-slate-100 px-3 py-1 rounded-lg">
                      <span className="text-indigo-600">{startup.industry || "Financial Services"}</span>
                      <ChevronRight size={12} className="text-slate-400" />
                      <span className="text-blue-600">{startup.sector || "FinTech"}</span>
                      <ChevronRight size={12} className="text-slate-400" />
                      <span className="text-emerald-600">{startup.subsector || "Unknown"}</span>
                    </div>
                  </div>

                  {Array.isArray(startup.business_models) && startup.business_models.length > 0 && (
                    <div className="flex flex-wrap gap-2 items-center">
                      <span className="text-[10px] uppercase font-bold text-slate-400 w-24">Business Models:</span>
                      <div className="flex flex-wrap gap-1">
                        {startup.business_models.map((bm, i) => (
                          <span key={i} className="bg-slate-100 text-slate-700 border border-slate-200 text-[10px] font-black px-2 py-0.5 rounded uppercase">
                            {bm}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {Array.isArray(startup.tags) && startup.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 items-start">
                      <span className="text-[10px] uppercase font-bold text-slate-400 w-24 mt-1">Focus Tags:</span>
                      <div className="flex flex-wrap gap-1 flex-1">
                        {startup.tags.map((tag, i) => (
                          <span key={i} className="bg-indigo-50/50 text-indigo-700 border border-indigo-100/50 text-[10px] font-medium px-2 py-0.5 rounded">
                            #{tag.toLowerCase().replace(/\s+/g, "-")}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {Array.isArray(analysis?.classification?.tags) && analysis.classification.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 items-start pt-2 border-t border-slate-50">
                      <span className="text-[10px] uppercase font-bold text-slate-400 w-24 mt-1">Tech Stack:</span>
                      <div className="flex flex-wrap gap-1 flex-1">
                        {analysis.classification.tags.map((tech: string, i: number) => (
                          <span key={i} className="bg-emerald-50 text-emerald-700 border border-emerald-100/50 text-[10px] font-medium px-2 py-0.5 rounded">
                            {tech}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Profile Summary */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-3">
                <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2 flex items-center justify-between">
                  <span>Business Profile</span>
                  <div className="flex gap-2">
                    {onUpdateField && (
                      <button
                        onClick={() => {
                          setDescriptionInput(startup.ai_summary || startup.description || "");
                          setEditingField(editingField === "description" ? null : "description");
                        }}
                        className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0"
                        title="Edit Profile"
                      >
                        <Pencil size={12} />
                      </button>
                    )}
                    {onRecheckField && (
                      <button
                        onClick={() => handleRecheckFieldClick("description")}
                        className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0"
                        title="AI Recheck Profile"
                        disabled={recheckingField}
                      >
                        <RefreshCw size={12} className={isFieldSpinning("description") ? "animate-spin" : ""} />
                      </button>
                    )}
                  </div>
                </h4>
                {editingField === "description" ? (
                  <div className="space-y-2">
                    <textarea
                      rows={4}
                      value={descriptionInput}
                      onChange={(e) => setDescriptionInput(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 text-xs rounded p-2"
                      placeholder="Company description..."
                    />
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => handleSaveField("description")}
                        className="bg-indigo-650 hover:bg-indigo-750 text-white text-[11px] font-bold px-3 py-1 rounded cursor-pointer border-0"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => setEditingField(null)}
                        className="bg-slate-300 hover:bg-slate-400 text-slate-700 text-[11px] font-bold px-3 py-1 rounded cursor-pointer border-0"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <p className="text-slate-650 text-xs leading-relaxed">
                    {startup.ai_summary || startup.description || "No company description parsed yet."}
                  </p>
                )}
              </div>

              {/* Products & Solutions */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2 flex items-center justify-between">
                  <span>Products &amp; Solutions</span>
                  <div className="flex gap-2">
                    {onUpdateField && (
                      <button
                        onClick={() => {
                          setProductsInput(JSON.stringify(products, null, 2));
                          setEditingField(editingField === "products" ? null : "products");
                        }}
                        className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0"
                        title="Edit Products"
                      >
                        <Pencil size={12} />
                      </button>
                    )}
                    {onRecheckField && (
                      <button
                        onClick={() => handleRecheckFieldClick("products")}
                        className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0"
                        title="AI Recheck Products"
                        disabled={recheckingField}
                      >
                        <RefreshCw size={12} className={isFieldSpinning("products") ? "animate-spin" : ""} />
                      </button>
                    )}
                  </div>
                </h4>
                {editingField === "products" ? (
                  <div className="space-y-2">
                    <textarea
                      rows={6}
                      value={productsInput}
                      onChange={(e) => setProductsInput(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 text-xs rounded p-2 font-mono"
                      placeholder="JSON Array of products..."
                    />
                    {editError && <p className="text-red-500 text-[10px]">{editError}</p>}
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => handleSaveField("products")}
                        className="bg-indigo-650 hover:bg-indigo-750 text-white text-[11px] font-bold px-3 py-1 rounded cursor-pointer border-0"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => setEditingField(null)}
                        className="bg-slate-300 hover:bg-slate-400 text-slate-700 text-[11px] font-bold px-3 py-1 rounded cursor-pointer border-0"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : products.length > 0 ? (
                  <div className="overflow-x-auto rounded-xl border border-slate-200">
                    <table className="w-full text-left text-xs border-collapse" style={{ tableLayout: "fixed" }}>
                      <thead>
                        <tr className="bg-slate-50 border-b border-slate-200">
                          <th className="px-4 py-2.5 font-bold text-slate-500 uppercase text-[9px] tracking-wider relative group/col" style={{ width: colWidths[0] }}>
                            <span>Product</span>
                            <div 
                              onMouseDown={(e) => startResizeCol(0, e)}
                              className="absolute right-0 top-0 bottom-0 w-1.5 cursor-col-resize bg-transparent group-hover/col:bg-slate-300 hover:!bg-indigo-500 transition-colors z-20"
                            />
                          </th>
                          <th className="px-4 py-2.5 font-bold text-slate-500 uppercase text-[9px] tracking-wider relative group/col" style={{ width: colWidths[1] }}>
                            <span>Category</span>
                            <div 
                              onMouseDown={(e) => startResizeCol(1, e)}
                              className="absolute right-0 top-0 bottom-0 w-1.5 cursor-col-resize bg-transparent group-hover/col:bg-slate-300 hover:!bg-indigo-500 transition-colors z-20"
                            />
                          </th>
                          <th className="px-4 py-2.5 font-bold text-slate-500 uppercase text-[9px] tracking-wider relative group/col" style={{ width: colWidths[2] }}>
                            <span>Description</span>
                            <div 
                              onMouseDown={(e) => startResizeCol(2, e)}
                              className="absolute right-0 top-0 bottom-0 w-1.5 cursor-col-resize bg-transparent group-hover/col:bg-slate-300 hover:!bg-indigo-500 transition-colors z-20"
                            />
                          </th>
                          <th className="px-4 py-2.5 font-bold text-slate-500 uppercase text-[9px] tracking-wider relative group/col" style={{ width: colWidths[3] }}>
                            <span>Target</span>
                            <div 
                              onMouseDown={(e) => startResizeCol(3, e)}
                              className="absolute right-0 top-0 bottom-0 w-1.5 cursor-col-resize bg-transparent group-hover/col:bg-slate-300 hover:!bg-indigo-500 transition-colors z-20"
                            />
                          </th>
                          <th className="px-4 py-2.5 font-bold text-slate-500 uppercase text-[9px] tracking-wider relative group/col" style={{ width: colWidths[4] }}>
                            <span>Deployment</span>
                            <div 
                              onMouseDown={(e) => startResizeCol(4, e)}
                              className="absolute right-0 top-0 bottom-0 w-1.5 cursor-col-resize bg-transparent group-hover/col:bg-slate-300 hover:!bg-indigo-500 transition-colors z-20"
                            />
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-150">
                        {Array.isArray(products) && products.map((prod: any, i: number) => (
                          <tr key={i} className="hover:bg-slate-50/50 group/row" style={{ height: rowHeights[i] ? `${rowHeights[i]}px` : undefined }}>
                            <td className="px-4 py-2.5 font-bold text-slate-800 relative select-none truncate" title={prod.product_name}>
                              {prod.product_name}
                              <div 
                                onMouseDown={(e) => startResizeRow(i, e)}
                                className="absolute bottom-0 left-0 right-0 h-1.5 cursor-row-resize bg-transparent group-hover/row:bg-slate-200 hover:!bg-indigo-500 transition-colors z-10"
                              />
                            </td>
                            <td className="px-4 py-2.5 text-slate-660 font-medium relative select-none truncate" title={prod.category}>
                              {prod.category}
                              <div 
                                onMouseDown={(e) => startResizeRow(i, e)}
                                className="absolute bottom-0 left-0 right-0 h-1.5 cursor-row-resize bg-transparent group-hover/row:bg-slate-200 hover:!bg-indigo-500 transition-colors z-10"
                              />
                            </td>
                            <td className="px-4 py-2.5 text-slate-500 relative select-none truncate" title={prod.description}>
                              {prod.description}
                              <div 
                                onMouseDown={(e) => startResizeRow(i, e)}
                                className="absolute bottom-0 left-0 right-0 h-1.5 cursor-row-resize bg-transparent group-hover/row:bg-slate-200 hover:!bg-indigo-500 transition-colors z-10"
                              />
                            </td>
                            <td className="px-4 py-2.5 text-slate-650 relative select-none truncate" title={prod.target_customer}>
                              {prod.target_customer}
                              <div 
                                onMouseDown={(e) => startResizeRow(i, e)}
                                className="absolute bottom-0 left-0 right-0 h-1.5 cursor-row-resize bg-transparent group-hover/row:bg-slate-200 hover:!bg-indigo-500 transition-colors z-10"
                              />
                            </td>
                            <td className="px-4 py-2.5 text-slate-500 relative select-none truncate" title={prod.deployment_model}>
                              {prod.deployment_model}
                              <div 
                                onMouseDown={(e) => startResizeRow(i, e)}
                                className="absolute bottom-0 left-0 right-0 h-1.5 cursor-row-resize bg-transparent group-hover/row:bg-slate-200 hover:!bg-indigo-500 transition-colors z-10"
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-xs text-slate-450 italic py-2">No product list compiled. Trigger Enrichment to crawl solutions.</p>
                )}
              </div>

              {/* Competitive Benchmarking */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2 flex items-center justify-between">
                  <span>Competitive Benchmarking</span>
                  {onRecheckField && (
                    <button
                      onClick={() => handleRecheckFieldClick("competitors")}
                      className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0"
                      title="AI Recheck Competitors"
                      disabled={recheckingField}
                    >
                      <RefreshCw size={10} className={isFieldSpinning("competitors") ? "animate-spin" : ""} />
                    </button>
                  )}
                </h4>
                <div className="overflow-x-auto rounded-xl border border-slate-200">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200">
                        <th className="px-4 py-2.5 font-bold text-slate-500 uppercase text-[9px] tracking-wider">Company</th>
                        <th className="px-4 py-2.5 font-bold text-slate-500 uppercase text-[9px] tracking-wider">Category</th>
                        <th className="px-4 py-2.5 font-bold text-slate-500 uppercase text-[9px] tracking-wider">Positioning / Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-150">
                      {/* Subject Company First */}
                      <tr className="bg-blue-50/40">
                        <td className="px-4 py-3 font-black text-blue-900 flex items-center gap-1.5">
                          {startup.startup_name} <span className="bg-blue-200 text-blue-800 text-[9px] font-bold px-1.5 py-0.2 rounded uppercase">Target</span>
                        </td>
                        <td className="px-4 py-3 font-semibold text-blue-800">{startup.subsector || "FinTech"}</td>
                        <td className="px-4 py-3 text-slate-700 italic font-medium">Subject Company / Integration Focus</td>
                      </tr>
                      {/* Competitors below */}
                      {Array.isArray(competitors) && competitors.map((comp: any, i: number) => (
                        <tr key={i} className="hover:bg-slate-50/50">
                          <td className="px-4 py-2.5 font-bold text-slate-800">{comp.company_name}</td>
                          <td className="px-4 py-2.5 text-slate-600">{comp.category}</td>
                          <td className="px-4 py-2.5 text-slate-500">{comp.positioning}</td>
                        </tr>
                      ))}
                      {competitors.length === 0 && (
                        <tr>
                          <td colSpan={3} className="px-4 py-3 text-slate-400 italic text-center">No comparable competitors recorded.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Funding & Investors */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2 flex items-center justify-between">
                  <span>Funding &amp; Capitalization</span>
                  <div className="flex gap-2">
                    {onUpdateField && (
                      <button
                        onClick={() => {
                          const mIntel = startup.market_intelligence || analysis?.market_intelligence || {};
                          const fundingInfo = mIntel.funding && typeof mIntel.funding === "object" && "value" in mIntel.funding
                            ? (mIntel.funding as any).value
                            : mIntel.funding || {};
                          const rawInvestorsList = fundingInfo.investors || analysis?.funding_stages?.investors || [];
                          const fundingInvestors = Array.isArray(rawInvestorsList)
                            ? rawInvestorsList.join(", ")
                            : typeof rawInvestorsList === "string"
                              ? rawInvestorsList
                              : "";
                          setFundingSeriesInput(startup.latest_round_stage || fundingInfo.latest_round || analysis?.funding_stages?.series || startup.funding_stage || "");
                          setFundingAmountInput(startup.total_funding || fundingInfo.total_funding || analysis?.funding_stages?.amount || startup.funding_amount || "");
                          setFundingInvestorsInput(fundingInvestors);
                          setEditingField(editingField === "funding" ? null : "funding");
                        }}

                        className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0"
                        title="Edit Funding"
                      >
                        <Pencil size={12} />
                      </button>
                    )}
                    {onRecheckField && (
                      <button
                        onClick={() => handleRecheckFieldClick("funding")}
                        className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0"
                        title="AI Recheck Funding"
                        disabled={recheckingField}
                      >
                        <RefreshCw size={12} className={isFieldSpinning("funding") ? "animate-spin" : ""} />
                      </button>
                    )}
                  </div>
                </h4>
                {editingField === "funding" ? (
                  <div className="space-y-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div>
                        <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">Stage / Series</label>
                        <input
                          type="text"
                          value={fundingSeriesInput}
                          onChange={(e) => setFundingSeriesInput(e.target.value)}
                          className="w-full bg-white border border-slate-200 text-xs rounded p-1.5"
                          placeholder="e.g. Series A, Seed"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">Amount Raised</label>
                        <input
                          type="text"
                          value={fundingAmountInput}
                          onChange={(e) => setFundingAmountInput(e.target.value)}
                          className="w-full bg-white border border-slate-200 text-xs rounded p-1.5"
                          placeholder="e.g. $10M, Bootstrapped"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">Investors (comma separated)</label>
                      <input
                        type="text"
                        value={fundingInvestorsInput}
                        onChange={(e) => setFundingInvestorsInput(e.target.value)}
                        className="w-full bg-white border border-slate-200 text-xs rounded p-1.5"
                        placeholder="Investor 1, Investor 2"
                      />
                    </div>
                    <div className="flex gap-2 justify-end pt-1">
                      <button
                        onClick={() => handleSaveField("funding")}
                        className="bg-indigo-650 hover:bg-indigo-705 text-white text-[11px] font-bold px-3 py-1 rounded cursor-pointer border-0"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => setEditingField(null)}
                        className="bg-slate-300 hover:bg-slate-400 text-slate-700 text-[11px] font-bold px-3 py-1 rounded cursor-pointer border-0"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
                      <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                        <p className="text-[9px] uppercase font-bold text-slate-400">Latest Funding Stage</p>
                        <p className="text-sm font-black text-slate-800 mt-1 font-mono">{startup.latest_round_stage || startup.funding_stage || "Unknown"}</p>
                      </div>
                      <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                        <p className="text-[9px] uppercase font-bold text-slate-400">Total Funding Raised</p>
                        <p className="text-sm font-black text-slate-800 mt-1 font-mono">{startup.total_funding || startup.funding_amount || "N/A"}</p>
                      </div>
                      <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                        <p className="text-[9px] uppercase font-bold text-slate-400">Latest Round Date</p>
                        <p className="text-sm font-black text-slate-800 mt-1 font-mono">{startup.latest_round_date || "N/A"}</p>
                      </div>
                    </div>
                    {Array.isArray(investors) && investors.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {investors.map((inv: any, i: number) => (
                          <div key={i} className="p-3 bg-slate-50 border border-slate-150 rounded-xl space-y-1 hover:border-emerald-250 transition-colors text-left">
                            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">{inv.round || "Investment Round"}</p>
                            <p className="text-xs font-black text-slate-800 leading-snug">{inv.investor_name}</p>
                            <p className="text-[10px] text-slate-500 font-mono">{inv.date || "Date Unspecified"}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-450 italic">No detailed investors list verified. Check fields above or trigger targeted enrichment.</p>
                    )}
                  </>
                )}
              </div>

              {/* Valuation & Multiples */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2 flex items-center gap-1.5">
                  Valuation &amp; Comparable Multiples
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-left">
                    <p className="text-[9px] uppercase font-bold text-slate-400">Estimated Valuation</p>
                    <p className="text-lg font-black text-slate-800 mt-1 font-mono">{valuation.estimated_valuation || "Not Publicly Disclosed"}</p>
                  </div>
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-left">
                    <p className="text-[9px] uppercase font-bold text-slate-400">Valuation Methodology</p>
                    <p className="text-xs font-bold text-slate-700 mt-1.5">{valuation.valuation_methodology || "Insufficient Public Filings"}</p>
                  </div>
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-left">
                    <p className="text-[9px] uppercase font-bold text-slate-400">ARR / Revenue Multiple</p>
                    <p className="text-lg font-black text-slate-850 mt-1 font-mono">{valuation.revenue_multiple || "N/A"}</p>
                  </div>
                </div>
                {Array.isArray(valuation?.comparable_companies) && valuation.comparable_companies.length > 0 && (
                  <div className="p-3 bg-indigo-50/30 border border-indigo-100/50 rounded-xl flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] text-indigo-750 font-bold uppercase">Comps:</span>
                    {valuation.comparable_companies.map((comp: string, i: number) => (
                      <span key={i} className="bg-white text-slate-700 border border-slate-200 rounded px-2 py-0.5 text-[10px] font-semibold">
                        {comp}
                      </span>
                    ))}
                  </div>
                )}
                {strategicPositioning && (
                  <div className="p-3 bg-amber-50/50 border border-amber-100/60 text-slate-800 text-[11px] leading-relaxed rounded-xl text-left">
                    <strong>Positioning Strategy:</strong> {strategicPositioning}
                  </div>
                )}
              </div>

              {/* News History Feed */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2">
                  Recent News Timeline
                </h4>
                {newsLoading ? (
                  <p className="text-slate-400 text-xs italic py-2">Loading timeline...</p>
                ) : recentNews.length > 0 ? (
                  <div className="relative border-l border-slate-200 pl-4 ml-2 space-y-5 text-left">
                    {recentNews.map((newsItem: any, idx: number) => {
                      const dateText = newsItem.published_at
                        ? new Date(newsItem.published_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
                        : "";
                      return (
                        <div key={newsItem.id || idx} className="relative">
                          <span className="absolute -left-[21px] top-1.5 w-2 h-2 rounded-full bg-orange-500" />
                          <div className="p-3 bg-slate-50 border border-slate-150 rounded-xl space-y-1 hover:border-amber-250 transition-colors">
                            <div className="flex justify-between items-start gap-3">
                              <h5 className="text-[11.5px] font-black text-slate-800 leading-snug">{newsItem.headline}</h5>
                              <span className="text-[9.5px] text-slate-400 font-mono whitespace-nowrap">{dateText}</span>
                            </div>
                            {newsItem.summary && <p className="text-xs text-slate-550 leading-relaxed pt-0.5">{newsItem.summary}</p>}
                            {newsItem.source_url && (
                              <a href={newsItem.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 text-[10px] text-blue-600 hover:text-blue-800 font-bold pt-1.5">
                                {newsItem.source || "View details"} <ExternalLink size={8} />
                              </a>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 italic">No updates in history.</p>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: ICICI INTELLIGENCE */}
          {activeTab === "icici" && (
            <div className="space-y-6 animate-fade-in text-left">

              {/* Executive Recommendation Hero Block */}
              <div className="bg-slate-900 text-white p-5 rounded-2xl border-l-8 border-orange-500 shadow-md space-y-4">
                <div className="flex items-center justify-between flex-wrap gap-2 border-b border-slate-800 pb-3">
                  <h5 className="text-xs font-black text-orange-400 uppercase tracking-widest flex items-center gap-1.5">
                    <Sparkles size={14} className="text-orange-400" />
                    Executive Recommendation
                  </h5>
                  <span className="text-[10px] bg-slate-850 text-slate-300 font-bold px-2 py-0.5 rounded font-mono">
                    Audit: v{startup.analysis_version || "1.0"}
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
                  <div className="space-y-1">
                    <p className="text-[10px] uppercase font-bold text-slate-450 tracking-wider">Recommended Action</p>
                    <span className="inline-block bg-orange-500/15 text-orange-400 border border-orange-500/30 text-xs font-black px-3 py-1 rounded-lg uppercase mt-1">
                      {startup.recommended_action || "Monitor"}
                    </span>
                  </div>
                  <div className="space-y-1">
                    <p className="text-[10px] uppercase font-bold text-slate-450 tracking-wider">Engagement Value</p>
                    <p className="text-2xl font-black text-white mt-1 font-mono">{startup.recommendation_score || 0}<span className="text-slate-500 text-sm font-normal">/100</span></p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-[10px] uppercase font-bold text-slate-450 tracking-wider">Confidence Level</p>
                    <p className="text-2xl font-black text-white mt-1 font-mono">{startup.confidence_score || 0}<span className="text-slate-500 text-sm font-normal">/100</span></p>
                  </div>
                </div>
              </div>

              {/* Multi-Agent Scorecard */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2">
                  Deterministic Scorecard
                </h4>
                <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-center">
                    <p className="text-[9px] uppercase font-bold text-slate-400">Relevance</p>
                    <p className="text-lg font-black text-slate-800 mt-1 font-mono">{startup.relevance_score || 0}</p>
                  </div>
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-center">
                    <p className="text-[9px] uppercase font-bold text-slate-400">Strategic Fit</p>
                    <p className="text-lg font-black text-slate-800 mt-1 font-mono">{startup.deployability_score || 0}</p>
                  </div>
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-center">
                    <p className="text-[9px] uppercase font-bold text-slate-400">Deployability</p>
                    <p className="text-lg font-black text-slate-800 mt-1 font-mono">{startup.deployability_score || 0}</p>
                  </div>
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-center">
                    <p className="text-[9px] uppercase font-bold text-slate-400">Signals</p>
                    <p className="text-lg font-black text-slate-800 mt-1 font-mono">{startup.signal_score || 0}</p>
                  </div>
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-center">
                    <p className="text-[9px] uppercase font-bold text-slate-400">Priority</p>
                    <p className="text-lg font-black text-orange-600 mt-1 font-mono">{startup.priority_score || 0}</p>
                  </div>
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-center">
                    <p className="text-[9px] uppercase font-bold text-slate-400">Confidence</p>
                    <p className="text-lg font-black text-emerald-600 mt-1 font-mono">{startup.confidence_score || 0}</p>
                  </div>
                </div>
              </div>

              {/* Entity Relevance Matrix */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-3">
                <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2">
                  Entity Relevance Matrix
                </h4>
                <div className="space-y-2.5">
                  {startup.relevance_mapping && typeof startup.relevance_mapping === "object" && !Array.isArray(startup.relevance_mapping) && Object.keys(startup.relevance_mapping).length > 0 ? (
                    Object.entries(startup.relevance_mapping || {}).map(([ent, description]) => (
                      <div key={ent} className="p-3 bg-blue-50/40 border border-blue-100/60 rounded-xl flex flex-col md:flex-row md:items-start justify-between gap-3 text-left">
                        <strong className="text-xs text-blue-900 font-bold whitespace-nowrap min-w-[150px]">{ent}</strong>
                        <span className="text-xs text-slate-650 leading-relaxed font-medium">{description}</span>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-slate-400 italic py-2 text-center">No active entity relevance matrices mapped.</p>
                  )}
                </div>
              </div>

              {/* Business Problems & Teams Mapped */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2 flex items-center justify-between">
                  <span>Business Problems Mapped</span>
                  {onRecheckField && (
                    <button
                      onClick={() => handleRecheckFieldClick("opportunity_mapping")}
                      className="text-slate-400 hover:text-slate-600 border-0 bg-transparent cursor-pointer p-0"
                      title="AI Recheck Business Opportunities"
                      disabled={recheckingField}
                    >
                      <RefreshCw size={10} className={isFieldSpinning("opportunity_mapping") ? "animate-spin" : ""} />
                    </button>
                  )}
                </h4>
                {Array.isArray(analysis?.bfsi_relevance?.use_cases) && analysis.bfsi_relevance.use_cases.length > 0 ? (
                  <div className="space-y-3">
                    {analysis.bfsi_relevance.use_cases.map((uc: any, i: number) => (
                      <div key={i} className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-left space-y-1.5 hover:border-slate-300 transition-colors">
                        <div className="flex items-center justify-between gap-2 border-b border-slate-150 pb-1">
                          <span className="text-xs font-black text-slate-800">{uc.icici_entity}</span>
                          <span className="text-[10px] bg-slate-200 text-slate-650 px-2 py-0.5 rounded font-semibold font-mono">Mapped Owner</span>
                        </div>
                        <p className="text-xs font-bold text-slate-700">Problem / Scenario: {uc.use_case}</p>
                        {uc.potential_impact && <p className="text-[11px] text-slate-500 leading-normal">Operational Relevance: {uc.potential_impact}</p>}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-450 italic py-2">No direct business problem associations generated yet.</p>
                )}
              </div>

              {/* Mapped Business Teams */}
              {Array.isArray(startup.matched_business_teams) && startup.matched_business_teams.length > 0 && (
                <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-3">
                  <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2">
                    Mapped Business Teams
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {startup.matched_business_teams.map((team: string, i: number) => (
                      <span key={i} className="bg-orange-50 text-orange-700 border border-orange-100 text-xs font-bold px-3 py-1 rounded-lg uppercase tracking-wide">
                        {team}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Co-Creation Opportunities */}
              {analysis?.strategic_fit?.partnership_opportunity && (
                <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-3">
                  <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2">
                    Co-Creation Opportunities
                  </h4>
                  <p className="text-xs text-slate-700 leading-relaxed font-medium">
                    {analysis.strategic_fit.partnership_opportunity}
                  </p>
                </div>
              )}

              {/* Momentum Signals */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2">
                  Momentum Signals (Signal Score: {startup.signal_score || 0})
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Positive Signals */}
                  <div className="space-y-2.5">
                    <h5 className="text-[10px] font-black text-emerald-700 uppercase tracking-wider flex items-center gap-1">
                      <ThumbsUp size={11} /> Positive Signals
                    </h5>
                    {Array.isArray(startup.positive_signals) && startup.positive_signals.length > 0 ? (
                      <ul className="space-y-2">
                        {startup.positive_signals.map((sig, i) => (
                          <li key={i} className="flex gap-2 items-start p-2 bg-emerald-50/50 border border-emerald-100/50 rounded-lg text-xs text-slate-700 leading-normal text-left">
                            <CheckCircle2 size={13} className="text-emerald-500 flex-shrink-0 mt-0.5" />
                            <span>{sig}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-400 italic">No positive momentum indicators logged.</p>
                    )}
                  </div>

                  {/* Negative Signals */}
                  <div className="space-y-2.5">
                    <h5 className="text-[10px] font-black text-rose-700 uppercase tracking-wider flex items-center gap-1">
                      <ThumbsDown size={11} /> Negative Signals / Risks
                    </h5>
                    {Array.isArray(startup.negative_signals) && startup.negative_signals.length > 0 ? (
                      <ul className="space-y-2">
                        {startup.negative_signals.map((sig, i) => (
                          <li key={i} className="flex gap-2 items-start p-2 bg-rose-50/50 border border-rose-100/50 rounded-lg text-xs text-slate-700 leading-normal text-left">
                            <ShieldAlert size={13} className="text-rose-500 flex-shrink-0 mt-0.5" />
                            <span>{sig}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-400 italic font-medium">No alerts detected in news timeline.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: ENGAGEMENT WORKSPACE */}
          {activeTab === "workspace" && (
            <div className="space-y-6 animate-fade-in text-left">

              {/* Assignment Controls */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2">
                  Owner Assignment &amp; Routing
                </h4>

                {assignment ? (
                  <div className="space-y-4 text-left">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <div>
                        <label className="text-[9px] font-black text-slate-400 uppercase block mb-1">Primary Owner (FPR1)</label>
                        <select
                          value={assignment.assigned_to_fpr1 || ""}
                          onChange={(e) => onUpdateAssignment?.(assignment.id, { assigned_to_fpr1: e.target.value })}
                          className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-1.5 font-semibold"
                        >
                          <option value="">Unassigned</option>
                          {FPR1_LIST.map((fpr) => (
                            <option key={fpr} value={fpr}>{fpr}</option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="text-[9px] font-black text-slate-400 uppercase block mb-1">Secondary Owner (FPR2)</label>
                        <select
                          value={assignment.assigned_to_fpr2 || ""}
                          onChange={(e) => onUpdateAssignment?.(assignment.id, { assigned_to_fpr2: e.target.value })}
                          className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-1.5 font-semibold"
                        >
                          <option value="">Unassigned</option>
                          {FPR2_LIST.map((fpr) => (
                            <option key={fpr} value={fpr}>{fpr}</option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="text-[9px] font-black text-slate-400 uppercase block mb-1">Internal Business Team</label>
                        <select
                          value={assignment.business_team || ""}
                          onChange={(e) => onUpdateAssignment?.(assignment.id, { business_team: e.target.value })}
                          className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-1.5 font-semibold"
                        >
                          {TEAMS_LIST.map((team) => (
                            <option key={team} value={team}>{team}</option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="text-[9px] font-black text-slate-400 uppercase block mb-1">Sponsoring Entity</label>
                        <select
                          value={assignment.icici_entity || "ICICI Bank"}
                          onChange={(e) => onUpdateAssignment?.(assignment.id, { icici_entity: e.target.value })}
                          className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-1.5 font-semibold"
                        >
                          {ENTITIES_LIST.map((ent) => (
                            <option key={ent} value={ent}>{ent}</option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {/* Engagement Stage */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="text-[9px] font-black text-slate-400 uppercase block mb-1">Engagement Stage</label>
                        <select
                          value={assignment.engagement_stage || "New"}
                          onChange={(e) => onUpdateAssignment?.(assignment.id, { engagement_stage: e.target.value })}
                          className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-1.5 font-bold"
                        >
                          {STAGE_LIST.map((stg) => (
                            <option key={stg} value={stg}>{stg}</option>
                          ))}
                        </select>
                      </div>

                      <div className="flex gap-2 items-center justify-between p-2.5 bg-slate-100 rounded-lg border border-slate-200 mt-5">
                        <div className="text-left">
                          <p className="text-[8.5px] uppercase font-bold text-slate-400 leading-tight">Assignment Score / Band</p>
                          <p className="text-xs font-black text-slate-700 font-mono mt-0.5">
                            {assignment.assignment_score || 0}/100 • <span className="text-indigo-650 font-bold uppercase">{assignment.assignment_band || "Ignore"}</span>
                          </p>
                        </div>
                        {assignment.assignment_score_manual_override ? (
                          <span className="bg-amber-100 text-amber-700 text-[8.5px] font-black uppercase px-2 py-0.5 rounded border border-amber-250">Override Active</span>
                        ) : (
                          <span className="bg-slate-200 text-slate-500 text-[8.5px] font-black uppercase px-2 py-0.5 rounded">Standard Score</span>
                        )}
                      </div>
                    </div>

                    {/* Notes Textarea */}
                    <div>
                      <label className="text-[9px] font-black text-slate-400 uppercase block mb-1">FPR Collaboration Notes</label>
                      <textarea
                        rows={3}
                        defaultValue={assignment.notes || ""}
                        onBlur={(e) => onUpdateAssignment?.(assignment.id, { notes: e.target.value })}
                        placeholder="Add special instructions, meeting feedback, details of pilot roadmaps..."
                        className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-2 focus:outline-none"
                      />
                      <span className="text-[9px] text-slate-400 italic block mt-0.5">Changes saved automatically on click away/blur.</span>
                    </div>

                    {/* Manual Score Overrides */}
                    <div className="p-4 bg-amber-50/30 border border-amber-100/60 rounded-xl space-y-3">
                      <h5 className="text-[10px] font-black text-amber-800 uppercase tracking-wider flex items-center gap-1">
                        <Pencil size={11} /> Score Overrides &amp; Justifications
                      </h5>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div>
                          <label className="text-[9px] font-black text-slate-400 uppercase block mb-1">Manual Assignment Score Override</label>
                          <input
                            type="number"
                            min="0"
                            max="100"
                            placeholder="Score (0-100)"
                            defaultValue={assignment.assignment_score_manual_override || ""}
                            onBlur={(e) => {
                              const val = e.target.value === "" ? null : Number(e.target.value);
                              onUpdateAssignment?.(assignment.id, { assignment_score_manual_override: val as any });
                            }}
                            className="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg p-1.5 font-mono"
                          />
                        </div>
                        <div>
                          <label className="text-[9px] font-black text-slate-400 uppercase block mb-1">Override Reason</label>
                          <input
                            type="text"
                            placeholder="Explain the override context..."
                            defaultValue={assignment.assignment_score_override_reason || ""}
                            onBlur={(e) => onUpdateAssignment?.(assignment.id, { assignment_score_override_reason: e.target.value })}
                            className="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg p-1.5"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Follow-up Tracker */}
                    <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-100">
                      <div>
                        <p className="text-[9px] uppercase font-bold text-slate-450 tracking-wider">Last Follow-Up Date</p>
                        <p className="text-xs font-black text-slate-850 mt-1 font-mono">
                          {assignment.last_followup_date ? new Date(assignment.last_followup_date).toLocaleDateString("en-IN", { hour: "2-digit", minute: "2-digit" }) : "Never"}
                        </p>
                      </div>
                      <div>
                        <p className="text-[9px] uppercase font-bold text-slate-450 tracking-wider">Follow-Up Action Trigger</p>
                        <span className="text-xs font-bold text-slate-650 mt-1 block">Log meeting or edit notes to reset last follow-up check.</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <form onSubmit={handleCreateAssignment} className="space-y-3 text-left">
                    <p className="text-xs text-slate-450 italic">No assignment record currently active for this startup. File one below to initialize ownership routing.</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-[9.5px] font-bold text-slate-400 block mb-1">FPR1</label>
                        <select
                          value={newAssignment.assigned_to_fpr1}
                          onChange={(e) => setNewAssignment({ ...newAssignment, assigned_to_fpr1: e.target.value })}
                          className="w-full bg-slate-50 border border-slate-200 text-xs p-1.5 rounded-lg"
                        >
                          {FPR1_LIST.map((fpr) => (
                            <option key={fpr} value={fpr}>{fpr}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="text-[9.5px] font-bold text-slate-400 block mb-1">FPR2</label>
                        <select
                          value={newAssignment.assigned_to_fpr2}
                          onChange={(e) => setNewAssignment({ ...newAssignment, assigned_to_fpr2: e.target.value })}
                          className="w-full bg-slate-50 border border-slate-200 text-xs p-1.5 rounded-lg"
                        >
                          {FPR2_LIST.map((fpr) => (
                            <option key={fpr} value={fpr}>{fpr}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div>
                      <label className="text-[9.5px] font-bold text-slate-400 block mb-1">Sponsoring Entity</label>
                      <select
                        value={newAssignment.icici_entity}
                        onChange={(e) => setNewAssignment({ ...newAssignment, icici_entity: e.target.value })}
                        className="w-full bg-slate-50 border border-slate-200 text-xs p-1.5 rounded-lg"
                      >
                        {ENTITIES_LIST.map((ent) => (
                          <option key={ent} value={ent}>{ent}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-[9.5px] font-bold text-slate-400 block mb-1">Business Team</label>
                      <select
                        value={newAssignment.business_team}
                        onChange={(e) => setNewAssignment({ ...newAssignment, business_team: e.target.value })}
                        className="w-full bg-slate-50 border border-slate-200 text-xs p-1.5 rounded-lg"
                      >
                        {TEAMS_LIST.map((team) => (
                          <option key={team} value={team}>{team}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-[9.5px] font-bold text-slate-400 block mb-1">Sponsorship Directives Notes</label>
                      <textarea
                        required
                        rows={2}
                        value={newAssignment.notes}
                        onChange={(e) => setNewAssignment({ ...newAssignment, notes: e.target.value })}
                        placeholder="Add special instructions, pilot roadmap targets..."
                        className="w-full bg-slate-50 border border-slate-200 text-xs p-1.5 rounded-lg focus:outline-none"
                      />
                    </div>
                    <div className="text-right">
                      <button
                        type="submit"
                        disabled={assignLoading}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-4 py-2 rounded-lg"
                      >
                        {assignLoading ? "Filing..." : "Initialize Assignment"}
                      </button>
                    </div>
                  </form>
                )}
              </div>

              {/* Outreach Messages */}
              {assignment && (assignment.linkedin_reachout_message || assignment.email_reachout_message) && (
                <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                  <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2">
                    Agent Outreach Pitch Tools
                  </h4>
                  <div className="space-y-4">
                    {assignment.linkedin_reachout_message && (
                      <div className="p-3.5 bg-blue-50/50 border border-blue-100/60 rounded-xl space-y-2 relative">
                        <div className="flex justify-between items-center">
                          <span className="text-[9.5px] font-black text-blue-800 uppercase tracking-wide">LinkedIn Pitch Message</span>
                          <button
                            onClick={() => copyText(assignment.linkedin_reachout_message || "", "linkedin")}
                            className="bg-white hover:bg-blue-100 text-blue-600 border border-blue-200 text-[10px] font-bold px-2.5 py-1 rounded flex items-center gap-1 cursor-pointer transition-colors"
                          >
                            {copiedLinkedIn ? <Check size={11} /> : <Copy size={11} />}
                            {copiedLinkedIn ? "Copied!" : "Copy Pitch"}
                          </button>
                        </div>
                        <p className="text-xs text-slate-700 leading-relaxed italic pr-10">"{assignment.linkedin_reachout_message}"</p>
                      </div>
                    )}

                    {assignment.email_reachout_message && (
                      <div className="p-3.5 bg-indigo-50/40 border border-indigo-100/60 rounded-xl space-y-2 relative">
                        <div className="flex justify-between items-center">
                          <span className="text-[9.5px] font-black text-indigo-850 uppercase tracking-wide">Email Pitch Message</span>
                          <button
                            onClick={() => copyText(assignment.email_reachout_message || "", "email")}
                            className="bg-white hover:bg-indigo-100 text-indigo-700 border border-indigo-200 text-[10px] font-bold px-2.5 py-1 rounded flex items-center gap-1 cursor-pointer transition-colors"
                          >
                            {copiedEmail ? <Check size={11} /> : <Copy size={11} />}
                            {copiedEmail ? "Copied!" : "Copy Pitch"}
                          </button>
                        </div>
                        <p className="text-xs text-slate-700 leading-relaxed italic whitespace-pre-wrap">"{assignment.email_reachout_message}"</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Record Evaluation Milestone */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2">
                  Record Evaluation Milestone
                </h4>
                <form onSubmit={handleAddLog} className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[9.5px] font-bold text-slate-400 block mb-1">Activity Type</label>
                      <select
                        value={newInteraction.type}
                        onChange={(e) => setNewInteraction({ ...newInteraction, type: e.target.value })}
                        className="w-full bg-slate-50 border border-slate-200 text-xs p-1.5 rounded-lg focus:outline-none"
                      >
                        <option value="Introduction">Introduction</option>
                        <option value="Technical Review">Technical Review</option>
                        <option value="POC Execution">POC Execution</option>
                        <option value="MOU Signed">MOU Signed</option>
                        <option value="Stakeholder Pitch">Stakeholder Pitch</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-[9.5px] font-bold text-slate-400 block mb-1">Milestone Outcome</label>
                      <input
                        type="text"
                        placeholder="In progress / Approved"
                        value={newInteraction.next_steps}
                        onChange={(e) => setNewInteraction({ ...newInteraction, next_steps: e.target.value })}
                        className="w-full bg-slate-50 border border-slate-200 text-xs p-1.5 rounded-lg focus:outline-none"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-[9.5px] font-bold text-slate-400 block mb-1">Milestone Summary</label>
                    <textarea
                      required
                      rows={2}
                      value={newInteraction.summary}
                      onChange={(e) => setNewInteraction({ ...newInteraction, summary: e.target.value })}
                      placeholder="Details of the discussion, integration roadblocks, feedback..."
                      className="w-full bg-slate-50 border border-slate-200 text-xs p-1.5 rounded-lg focus:outline-none"
                    />
                  </div>
                  <div className="text-right">
                    <button
                      type="submit"
                      disabled={logLoading}
                      className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold px-4 py-1.5 rounded-lg flex items-center gap-1 ml-auto cursor-pointer border-0"
                    >
                      <Plus size={14} /> {logLoading ? "Commiting..." : "Commit Log"}
                    </button>
                  </div>
                </form>
              </div>

              {/* Activity Timeline */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
                <h4 className="font-black text-slate-900 text-xs uppercase tracking-widest border-b border-slate-100 pb-2">
                  Evaluation Activity Timeline
                </h4>
                <div className="relative border-l border-slate-200 pl-4 ml-2 space-y-4 text-left">
                  {/* Milestones log */}
                  {interactions.map((log) => (
                    <div key={log.id} className="relative">
                      <span className="absolute -left-[21px] top-1.5 w-2.5 h-2.5 rounded-full bg-indigo-500 border-2 border-white" />
                      <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1 hover:border-slate-350 transition-colors">
                        <div className="flex justify-between items-center flex-wrap gap-2">
                          <span className="text-[10px] font-black text-indigo-750 uppercase bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">
                            {log.type}
                          </span>
                          <span className="text-[9.5px] text-slate-400 font-mono">
                            {new Date(log.date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
                          </span>
                        </div>
                        <p className="text-xs text-slate-700 leading-normal font-medium pt-1">{log.summary}</p>
                        {log.next_steps && (
                          <div className="text-[10px] text-slate-500 font-semibold pt-1">
                            Outcome: <span className="text-indigo-650 font-bold">{log.next_steps}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {/* Fallback to audittrail details if no milestone logs yet */}
                  {interactions.length === 0 && startup.audit_summary && (
                    <div className="text-xs text-slate-450 italic py-2">
                      No milestones filed yet. Ingested via Multi-Agent pipeline.
                    </div>
                  )}

                  {interactions.length === 0 && !startup.audit_summary && (
                    <p className="text-xs text-slate-400 italic py-3 text-center">No timeline records registered.</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Global Action Panel Footer (trial status, team, priority) */}
        <div className="bg-white p-5 border-t border-slate-200 select-none">
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="grid grid-cols-3 gap-2 flex-1 w-full text-left">
              <div>
                <label className="text-[9px] font-bold text-slate-400 uppercase mb-1 block">Global Stage</label>
                <select
                  value={localStatus}
                  onChange={(e) => setLocalStatus(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-1.5 focus:outline-none font-semibold"
                >
                  <option value="Screening">Screening</option>
                  <option value="Evaluation">Evaluation</option>
                  <option value="Proof of Concept">Proof of Concept</option>
                  <option value="Partnership">Partnership</option>
                  <option value="Rejected">Rejected</option>
                </select>
              </div>

              <div>
                <label className="text-[9px] font-bold text-slate-400 uppercase mb-1 block">Advisor Group</label>
                <select
                  value={localTeam}
                  onChange={(e) => setLocalTeam(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-1.5 focus:outline-none font-semibold"
                >
                  <option value="Lending Team">Lending Team</option>
                  <option value="Insurance Team">Insurance Team</option>
                  <option value="AMC/Securities Team">AMC/Securities Team</option>
                  <option value="Enterprise AI Team">Enterprise AI Team</option>
                </select>
              </div>

              <div>
                <label className="text-[9px] font-bold text-slate-400 uppercase mb-1 block">Priority Score</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={localPriority}
                  onChange={(e) => setLocalPriority(Number(e.target.value))}
                  className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-1.5 focus:outline-none font-mono font-bold"
                />
              </div>
            </div>

            <div className="w-full sm:w-auto text-right flex gap-2 flex-shrink-0">
              {onAnalyze && (
                <button
                  type="button"
                  onClick={() => {
                    setAnalyzing(true);
                    setRecheckingField("all");
                    onAnalyze(startup.id, true).finally(() => {
                      setAnalyzing(false);
                      setRecheckingField(null);
                    });
                  }}
                  disabled={analyzing || statusLoading}
                  className="w-full sm:w-auto bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 hover:border-slate-400 text-xs font-bold px-3 py-2 rounded-lg flex items-center justify-center gap-1.5 transition-all cursor-pointer"
                >
                  {analyzing ? <RefreshCw className="animate-spin" size={13} /> : <Sparkles size={13} />}
                  <span>{analyzing ? "Enriching..." : "Re-Enrich AI"}</span>
                </button>
              )}
              <button
                type="button"
                onClick={handleUpdateDetails}
                disabled={statusLoading || analyzing}
                className="w-full sm:w-auto bg-slate-900 hover:bg-slate-800 text-white border-0 hover:text-orange-400 text-xs font-black px-4 py-2 rounded-lg shadow-sm transition-all cursor-pointer"
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
