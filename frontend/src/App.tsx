import React, { useState, useEffect } from "react";
import { Routes, Route, useNavigate, useLocation } from "react-router-dom";
import "./lib/tracing";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Repository from "./pages/Repository";
import HighPriority from "./pages/HighPriority";
import Assignments from "./pages/Assignments";
import Insights from "./pages/Insights";
import SupabaseConsole from "./pages/SupabaseConsole";
import Chat from "./pages/Chat";
import StartupDetails from "./pages/StartupDetails";
import Scraping from "./pages/Scraping";
import Observability from "./pages/Observability";
import DetailModal from "./components/DetailModal";
import NewsDashboard from "./pages/NewsDashboard";
import { AppTab, Startup, Assignment, StartupCategory, Interaction, UserRole, StartupAnalysis } from "./types";
import { AlertCircle, CheckCircle, RefreshCw } from "lucide-react";

// Read API URL from environment variables
const rawApiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const API_URL = rawApiUrl.endsWith("/") 
  ? (rawApiUrl.endsWith("/api/") ? rawApiUrl.slice(0, -1) : rawApiUrl + "api") 
  : (rawApiUrl.endsWith("/api") ? rawApiUrl : rawApiUrl + "/api");

// Smart default resolvers to guess realistic tags from startup description when database row is un-enriched
const guessSector = (name: string, desc: string): string => {
  const text = `${name} ${desc}`.toLowerCase();
  if (text.includes("insurance") || text.includes("insurtech") || text.includes("lombard") || text.includes("claim") || text.includes("underwrite")) return "InsurTech";
  if (text.includes("credit") || text.includes("loan") || text.includes("lending") || text.includes("score")) return "LendingTech";
  if (text.includes("broker") || text.includes("wealth") || text.includes("advisory") || text.includes("invest") || text.includes("securities") || text.includes("mutual fund") || text.includes("trading")) return "WealthTech";
  if (text.includes("payment") || text.includes("upi") || text.includes("remit") || text.includes("transaction") || text.includes("remittance") || text.includes("merchant")) return "Payments";
  if (text.includes("kyc") || text.includes("aml") || text.includes("compliance") || text.includes("regtech") || text.includes("audit") || text.includes("identity")) return "RegTech";
  if (text.includes("security") || text.includes("cyber") || text.includes("fraud") || text.includes("auth") || text.includes("threat") || text.includes("breach") || text.includes("hacker")) return "Cybersecurity";
  if (text.includes("ai") || text.includes("nlp") || text.includes("model") || text.includes("cognitive") || text.includes("saas") || text.includes("software") || text.includes("data")) return "AI Ops";
  return "LendingTech"; // General fallback
};

const guessFundingStage = (name: string, desc: string): string => {
  const text = `${name} ${desc}`.toLowerCase();
  if (text.includes("acquired") || text.includes("acquisition")) return "Acquired";
  if (text.includes("ipo") || text.includes("public") || text.includes("listed")) return "Public";
  if (text.includes("bootstrapped")) return "Bootstrapped";
  if (text.includes("series a")) return "Series A";
  if (text.includes("series b")) return "Series B";
  if (text.includes("series c")) return "Series C";
  if (text.includes("series d")) return "Series D";
  if (text.includes("series e")) return "Series E";
  if (text.includes("seed")) return "Seed";
  if (text.includes("pre-seed")) return "Pre-Seed";
  if (text.includes("angel")) return "Angel";
  if (text.includes("venture") || text.includes("funding")) return "Growth";
  return ""; // Standard fallback
};
const guessFundingAmount = (name: string, desc: string): string => {
  const text = `${name} ${desc}`;
  const dollarRegex = /\$[0-9]+(\.[0-9]+)?\s*(M|Mn|Million|B|Bn|Billion|K)?\b/gi;
  const dollarMatch = text.match(dollarRegex);
  if (dollarMatch) return dollarMatch[0];

  const rupeeRegex = /(Rs|Rupees|₹)\s*[0-9,]+(\.[0-9]+)?\s*(Cr|Crore|L|Lakh|Lakh\s*Crore)?\b/gi;
  const rupeeMatch = text.match(rupeeRegex);
  if (rupeeMatch) return rupeeMatch[0];

  return ""; // Standard fallback
};
const guessIndustry = (name: string, desc: string): string => {
  const text = `${name} ${desc}`.toLowerCase();
  if (text.includes("insurance") || text.includes("insurtech") || text.includes("claim") || text.includes("underwrite") || text.includes("lending") || text.includes("loan") || text.includes("credit") || text.includes("wealth") || text.includes("advisory") || text.includes("trading") || text.includes("payment") || text.includes("upi")) return "Financial Services";
  if (text.includes("ai") || text.includes("model") || text.includes("llm") || text.includes("nlp") || text.includes("neural") || text.includes("agentic") || text.includes("generative")) return "Artificial Intelligence";
  if (text.includes("saas") || text.includes("erp") || text.includes("crm") || text.includes("productivity") || text.includes("workflow") || text.includes("collaboration")) return "Enterprise Software";
  if (text.includes("security") || text.includes("cyber") || text.includes("fraud") || text.includes("threat") || text.includes("breach") || text.includes("zero trust")) return "Cybersecurity";
  if (text.includes("health") || text.includes("telemedicine") || text.includes("medtech") || text.includes("diagnostics") || text.includes("clinical")) return "Healthcare & Life Sciences";
  if (text.includes("edtech") || text.includes("learning") || text.includes("school") || text.includes("class") || text.includes("education")) return "Education";
  if (text.includes("e-commerce") || text.includes("retail") || text.includes("shop") || text.includes("marketplace") || text.includes("d2c")) return "Commerce & Retail";
  if (text.includes("gaming") || text.includes("social") || text.includes("travel") || text.includes("booking")) return "Consumer Internet";
  if (text.includes("proptech") || text.includes("real estate") || text.includes("smart building") || text.includes("facility")) return "Real Estate & Construction";
  if (text.includes("logistics") || text.includes("freight") || text.includes("supply chain") || text.includes("ev ") || text.includes("mobility")) return "Transportation & Logistics";
  return "Financial Services"; // General default
};

const guessIndustryRelevance = (name: string, desc: string): string[] => {
  const text = `${name} ${desc}`.toLowerCase();
  const relevance: string[] = [];
  if (text.includes("bank") || text.includes("insurance") || text.includes("securities") || text.includes("wealth") || text.includes("payment") || text.includes("lending") || text.includes("credit") || text.includes("underwrite") || text.includes("bfsi")) {
    relevance.push("BFSI");
  }
  if (text.includes("enterprise") || text.includes("saas") || text.includes("b2b") || text.includes("corporate")) {
    relevance.push("Enterprise");
  }
  if (text.includes("smb") || text.includes("sme") || text.includes("small business") || text.includes("retailer")) {
    relevance.push("SMB");
  }
  if (text.includes("retail") || text.includes("commerce") || text.includes("shop") || text.includes("d2c")) {
    relevance.push("Retail");
  }
  if (relevance.length === 0) {
    relevance.push("BFSI"); // Fallback
  }
  return relevance;
};

const guessBusinessModels = (name: string, desc: string): string[] => {
  const text = `${name} ${desc}`.toLowerCase();
  const models: string[] = [];
  if (text.includes("saas") || text.includes("software as a service")) models.push("SaaS");
  if (text.includes("b2b") || text.includes("enterprise") || text.includes("merchant")) models.push("B2B");
  if (text.includes("b2c") || text.includes("retail customer") || text.includes("consumer")) models.push("B2C");
  if (text.includes("b2b2c") || text.includes("distribute via")) models.push("B2B2C");
  if (text.includes("subscription") || text.includes("annual fee") || text.includes("monthly plan")) models.push("Subscription");
  if (text.includes("transaction") || text.includes("per transaction") || text.includes("commission")) models.push("Transaction-Based");
  if (text.includes("marketplace") || text.includes("platform aggregator")) models.push("Marketplace");
  if (models.length === 0) {
    models.push("B2B"); // Fallback
  }
  return models;
};

const guessTags = (name: string, desc: string): string[] => {
  const text = `${name} ${desc}`.toLowerCase();
  const tags: string[] = [];
  if (text.includes("insurance") || text.includes("insurtech")) tags.push("insurance");
  if (text.includes("claims") || text.includes("claim")) tags.push("claims-automation");
  if (text.includes("lending") || text.includes("loan")) tags.push("lending");
  if (text.includes("credit") || text.includes("score")) tags.push("credit-infrastructure");
  if (text.includes("upi") || text.includes("payment")) tags.push("upi-payments");
  if (text.includes("wealth") || text.includes("robo-advisory")) tags.push("wealth-advisory");
  if (text.includes("underwrite")) tags.push("underwriting-automation");
  if (text.includes("ai") || text.includes("model")) tags.push("artificial-intelligence");
  if (tags.length === 0) {
    tags.push("fintech-innovation");
  }
  return tags;
};

// Adaptive PostgreSQL database row mapper
export const mapStartupWithAnalysis = (s: any): Startup => {
  // Support both backend payload structures (singular startup_analysis and plural startup_analyses)
  const rawAnalysisRecord = (s.startup_analyses && s.startup_analyses.length > 0)
    ? s.startup_analyses[0]
    : (s.startup_analysis && s.startup_analysis.length > 0)
    ? s.startup_analysis[0]
    : null;

  const analysis = rawAnalysisRecord
    ? ((rawAnalysisRecord.analysis_data || rawAnalysisRecord.analysis_json) as any)
    : null;

  const rawName = s.startup_name || s.name || "Unknown Venture";
  
  // Industry Resolution with AI override & smart guess fallback
  let rawIndustry = s.industry || "Unknown";
  if ((!rawIndustry || rawIndustry.toLowerCase() === "unknown") && analysis?.classification?.industry) {
    rawIndustry = analysis?.classification?.industry;
  }
  if (!rawIndustry || rawIndustry.toLowerCase() === "unknown") {
    rawIndustry = guessIndustry(rawName, s.description || "");
  }

  // Sector Resolution with AI override & smart guess fallback
  let rawSector = s.sector || "Unknown";
  if ((!rawSector || rawSector.toLowerCase() === "unknown") && (analysis?.classification?.sector || analysis?.classification?.primary_sector)) {
    rawSector = (analysis?.classification?.sector || analysis?.classification?.primary_sector) as string;
  }
  if (!rawSector || rawSector.toLowerCase() === "unknown") {
    rawSector = guessSector(rawName, s.description || "");
  }

  // Subsector
  let rawSubsector = s.subsector || "";
  if (!rawSubsector && (analysis?.classification?.subsector || analysis?.classification?.sub_sectors?.[0])) {
    rawSubsector = (analysis?.classification?.subsector || analysis?.classification?.sub_sectors?.[0]) as string;
  }
  if (!rawSubsector) {
    rawSubsector = "Alternative Scoring";
  }

  // Business Models
  let rawBusinessModels = s.business_models;
  if (analysis?.classification?.business_models) {
    rawBusinessModels = analysis?.classification?.business_models;
  }
  if (!rawBusinessModels || rawBusinessModels.length === 0) {
    rawBusinessModels = guessBusinessModels(rawName, s.description || "");
  }

  // Industry Relevance
  let rawIndustryRelevance = s.industry_relevance;
  if (analysis?.classification?.industry_relevance) {
    rawIndustryRelevance = analysis?.classification?.industry_relevance;
  }
  if (!rawIndustryRelevance || rawIndustryRelevance.length === 0) {
    rawIndustryRelevance = guessIndustryRelevance(rawName, s.description || "");
  }

  // Tags
  let rawTags = s.tags;
  if (analysis?.classification?.tags) {
    rawTags = analysis?.classification?.tags;
  }
  if (!rawTags || rawTags.length === 0) {
    rawTags = guessTags(rawName, s.description || "");
  }

  // Funding Stage Resolution with AI override & smart guess fallback
  let rawFundingStage = s.funding_stage || "";
  const nestedFundingInfo = analysis?.market_intelligence?.funding?.value || {};
  
  if ((!rawFundingStage || rawFundingStage.toLowerCase() === "unknown") && (analysis?.funding_stages?.series || nestedFundingInfo.latest_round)) {
    rawFundingStage = analysis?.funding_stages?.series || nestedFundingInfo.latest_round;
  }
  if (!rawFundingStage || rawFundingStage.toLowerCase() === "unknown") {
    rawFundingStage = guessFundingStage(rawName, s.description || "");
  }
  if (rawFundingStage.toLowerCase() === "unknown") {
    rawFundingStage = "";
  }

  // Funding Amount Resolution with AI override & smart guess fallback
  let rawFundingAmount = s.funding_amount || "";
  if ((!rawFundingAmount || rawFundingAmount.toLowerCase() === "unknown" || rawFundingAmount === "$1.2M" || rawFundingAmount === "$1.5M") && (analysis?.funding_stages?.amount || nestedFundingInfo.total_funding)) {
    rawFundingAmount = analysis?.funding_stages?.amount || nestedFundingInfo.total_funding;
  }
  if (!rawFundingAmount || rawFundingAmount.toLowerCase() === "unknown" || rawFundingAmount === "$1.2M" || rawFundingAmount === "$1.5M") {
    rawFundingAmount = guessFundingAmount(rawName, s.description || "");
  }
  if (rawFundingAmount.toLowerCase() === "unknown" || rawFundingAmount === "$1.2M" || rawFundingAmount === "$1.5M") {
    rawFundingAmount = "";
  }

  // Founded Year
  let rawFoundedYear = s.founded_year;
  if (!rawFoundedYear && analysis?.founded_year) {
    rawFoundedYear = analysis?.founded_year;
  }

  // Website Resolution with AI override
  let rawWebsite = s.website || "";
  if ((!rawWebsite || rawWebsite.includes("example.com")) && analysis?.startup_website) {
    rawWebsite = analysis?.startup_website;
  }
  if (!rawWebsite || rawWebsite.includes("example.com") || rawWebsite.trim() === "") {
    rawWebsite = "";
  }

  // Priority Score Resolution with AI override & keyword heuristics to prevent flat scoring lists
  let rawPriorityScore = s.priority_score ?? rawAnalysisRecord?.priority_score;
  if (analysis?.scoring?.overall_priority_score) {
    rawPriorityScore = analysis?.scoring?.overall_priority_score;
  }
  if (!rawPriorityScore) {
    const text = `${rawName} ${s.description || ""}`.toLowerCase();
    let score = 70;
    if (text.includes("instant") || text.includes("automatic") || text.includes("real-time") || text.includes("fraud")) score += 10;
    if (text.includes("api") || text.includes("saas") || text.includes("sdk")) score += 5;
    if (text.includes("icici") || text.includes("lombard") || text.includes("bank")) score += 8;
    rawPriorityScore = Math.min(score, 98);
  }

  // AI Summary & Relevance Summary
  let rawAiSummary = s.ai_summary || "";
  if (analysis) {
    rawAiSummary = analysis.summary?.one_liner || "";
  }
  if (!rawAiSummary || rawAiSummary.includes("No AI analysis") || rawAiSummary.includes("Registry Entry") || rawAiSummary.includes("CSV Import")) {
    rawAiSummary = "Business profile pending AI enrichment.";
  }

  let rawRelevanceSummary = s.relevance_summary || "";
  if (analysis) {
    rawRelevanceSummary = analysis.relevance_summary || "";
  }

  // Entity Relevance & Mappings
  let rawEntityRelevance = s.entity_relevance || "";
  if (analysis && analysis.bfsi_relevance?.use_cases?.[0]) {
    const firstEntity = analysis.bfsi_relevance.use_cases[0].icici_entity;
    if (firstEntity === "Not Relevant to any of the ICICI Group Companies") {
      rawEntityRelevance = "Not Relevant to any of the ICICI Group Companies";
    } else {
      rawEntityRelevance = analysis.bfsi_relevance.use_cases[0].potential_impact;
    }
  }
  if (
    !rawEntityRelevance || 
    rawEntityRelevance === "BFSI Underwriting automation fit." || 
    rawEntityRelevance === "Relevant for BFSI underwritings." ||
    rawEntityRelevance === "Explain the potential impact."
  ) {
    rawEntityRelevance = "";
  }

  const rawRelevanceMapping = (analysis && Array.isArray(analysis.bfsi_relevance?.use_cases) && analysis.bfsi_relevance.is_relevant !== false)
    ? analysis.bfsi_relevance.use_cases.reduce((acc: Record<string, string>, uc: any) => {
        const entity = uc?.icici_entity;
        const ucDesc = uc?.use_case;
        if (
          entity && 
          entity !== "None" && 
          entity !== "Relevant ICICI entity" && 
          entity !== "Not Relevant to any of the ICICI Group Companies" &&
          ucDesc && 
          !ucDesc.includes("Describe a specific") &&
          !ucDesc.includes("automation fit")
        ) {
          acc[entity] = ucDesc;
        }
        return acc;
      }, {})
    : (s.relevance_mapping || {});

  const rawUseCases = (analysis && Array.isArray(analysis.bfsi_relevance?.use_cases))
    ? analysis.bfsi_relevance.use_cases.map((uc: any) => `${uc?.icici_entity || "Unknown"}: ${uc?.use_case || "N/A"}`)
    : s.use_cases || [];

  return {
    ...s,
    id: String(s.id),
    startup_name: rawName,
    name: rawName,
    industry: rawIndustry,
    sector: rawSector,
    subsector: rawSubsector,
    subSector: rawSubsector,
    business_models: rawBusinessModels,
    industry_relevance: rawIndustryRelevance,
    tags: rawTags,
    funding_stage: rawFundingStage,
    funding_amount: rawFundingAmount,
    founded_year: rawFoundedYear,
    description: s.description || "No description provided.",
    website: rawWebsite,
    created_at: s.created_at || new Date().toISOString(),
    recent_news: s.startup_news || s.recent_news || [],

    // Pass 3 Funding Rounds & Summary Mapping
    funding_rounds: rawAnalysisRecord?.funding_rounds || s.funding_rounds || nestedFundingInfo.funding_history || [],
    total_funding: s.total_funding || rawAnalysisRecord?.total_funding || nestedFundingInfo.total_funding || rawFundingAmount || "",
    latest_round_stage: s.latest_round_stage || rawAnalysisRecord?.latest_round_stage || nestedFundingInfo.latest_round || rawFundingStage || "",
    latest_round_date: s.latest_round_date || rawAnalysisRecord?.latest_round_date || nestedFundingInfo.latest_round_date || "",

    // Analytical tags derived from live analysis or seed maps
    priority_score: rawPriorityScore,
    ai_summary: rawAiSummary,
    relevance_summary: rawRelevanceSummary,
    entity_relevance: rawEntityRelevance,
    relevance_mapping: rawRelevanceMapping,
    use_cases: rawUseCases,
    assigned_team: s.assigned_team || (rawSector === "InsurTech"
      ? "Insurance Team"
      : rawSector === "WealthTech"
      ? "AMC/Securities Team"
      : rawSector === "LendingTech"
      ? "Lending Team"
      : "Enterprise AI Team"),
    status: s.status || "Screening",
    startup_analyses: rawAnalysisRecord ? [{
      analysis_data: analysis
    }] : s.startup_analyses,

    // Upgraded multi-agent workspace columns
    startup_status: s.startup_status || s.status || "Screening",
    headquarters: s.headquarters || "Unknown",
    startup_stage: s.startup_stage || rawFundingStage || "Unknown",
    relevance_score: rawAnalysisRecord?.relevance_score ?? analysis?.bfsi_relevance?.relevance_score ?? 0,
    signal_score: rawAnalysisRecord?.signal_score ?? analysis?.scoring?.signal_score ?? 0,
    deployability_score: rawAnalysisRecord?.deployability_score ?? analysis?.scoring?.deployability_score ?? 0,
    recommendation_score: rawAnalysisRecord?.recommendation_score ?? analysis?.scoring?.recommendation_score ?? 0,
    confidence_score: rawAnalysisRecord?.confidence_score ?? analysis?.scoring?.confidence_score ?? 0,
    recommended_action: rawAnalysisRecord?.recommended_action ?? analysis?.recommendation?.recommended_action ?? "Monitor",
    priority_band: rawAnalysisRecord?.priority_band ?? "Ignore",
    matched_entities: Array.isArray(rawAnalysisRecord?.matched_entities) ? rawAnalysisRecord.matched_entities : (Array.isArray(analysis?.recommendation?.target_entities) ? analysis.recommendation.target_entities : []),
    matched_business_teams: Array.isArray(rawAnalysisRecord?.matched_business_teams) ? rawAnalysisRecord.matched_business_teams : (Array.isArray(analysis?.recommendation?.target_teams) ? analysis.recommendation.target_teams : []),
    matched_business_problems: Array.isArray(rawAnalysisRecord?.matched_business_problems) ? rawAnalysisRecord.matched_business_problems : (Array.isArray(analysis?.bfsi_relevance?.use_cases) ? analysis.bfsi_relevance.use_cases.map((uc: any) => uc?.use_case || "").filter(Boolean) : []),
    positive_signals: Array.isArray(rawAnalysisRecord?.positive_signals) ? rawAnalysisRecord.positive_signals : (Array.isArray(s.positive_signals) ? s.positive_signals : []),
    negative_signals: Array.isArray(rawAnalysisRecord?.negative_signals) ? rawAnalysisRecord.negative_signals : (Array.isArray(s.negative_signals) ? s.negative_signals : []),
    audit_summary: rawAnalysisRecord?.audit_summary ?? {},
    knowledge_version: rawAnalysisRecord?.knowledge_version ?? "",
    analysis_version: rawAnalysisRecord?.analysis_version ?? "",
    market_intelligence: (analysis?.market_intelligence && Object.keys(analysis.market_intelligence).length > 0)
      ? analysis.market_intelligence
      : (s.market_intelligence && Object.keys(s.market_intelligence).length > 0)
      ? s.market_intelligence
      : {
          products: [],
          competitors: [],
          valuation: {},
          investors: []
        }
  };
};

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();

  const getActiveTabFromPath = (path: string): AppTab => {
    if (path === "/" || path.startsWith("/dashboard")) return "dashboard";
    if (path.startsWith("/news-dashboard")) return "news-dashboard";
    if (path.startsWith("/repository")) return "repository";
    if (path.startsWith("/high-priority")) return "high-priority";
    if (path.startsWith("/assignments")) return "assignments";
    if (path.startsWith("/insights")) return "insights";
    if (path.startsWith("/chat")) return "chat";
    if (path.startsWith("/database")) return "database";
    if (path.startsWith("/scraping")) return "scraping";
    if (path.startsWith("/observability")) return "observability";
    return "dashboard";
  };

  const activeTab = getActiveTabFromPath(location.pathname);

  const handleTabChange = (tab: AppTab) => {
    if (tab === "dashboard") navigate("/");
    else navigate(`/${tab}`);
  };
  const [currentUser, setCurrentUser] = useState<UserRole>({
    username: "Rajesh Kumar",
    role: "Admin"
  });

  // DB States
  const [startups, setStartups] = useState<Startup[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [categories, setCategories] = useState<StartupCategory[]>([]);
  const [interactions, setInteractions] = useState<Interaction[]>([]);

  // Scraping global states
  const [scrapingActive, setScrapingActive] = useState<boolean>(false);
  const [scrapingLogs, setScrapingLogs] = useState<string[]>([]);
  const [scrapingProcessed, setScrapingProcessed] = useState<string[]>([]);
  const [scrapingCurrentStep, setScrapingCurrentStep] = useState<string>("Idle");
  const [scrapingTarget, setScrapingTarget] = useState<number>(0);
  const [scrapingProgress, setScrapingProgress] = useState<number>(0);

  // Detailed Modal Drawer
  const [selectedStartup, setSelectedStartup] = useState<Startup | null>(null);

  // Indicators
  const [loading, setLoading] = useState(true);
  const [isLiveConnected, setIsLiveConnected] = useState(false);
  const [globalError, setGlobalError] = useState("");
  const [globalSuccess, setGlobalSuccess] = useState("");

  // Seed Fallbacks in case local FastAPI backend is down
  const loadFallbackMockDatabase = () => {
    const mockStartups: Startup[] = [
      {
        id: "st-1",
        startup_name: "Digit Insurance",
        name: "Digit Insurance",
        description: "Full-stack digital general insurance aggregator providing cloud-based claims settlement and customized risk micro-policies.",
        website: "https://www.godigit.com",
        sector: "InsurTech",
        subsector: "General Insurance Platform",
        funding_stage: "Public",
        funding_amount: "$540M",
        ai_summary: "Digit relies on micro-services and cloud engines to process retail insurance. Extremely fast digital claims automation holds major potential for claims verification APIs with Lombard.",
        entity_relevance: "Highly relevant to ICICI Lombard for streamlining claims automation, motor systems, and distribution.",
        relevance_mapping: { "ICICI Lombard": "Integrate digitized automated motor claims scoring APIs." },
        use_cases: ["Computer vision on damaged asset photos.", "Custom property insurance APIs."],
        priority_score: 94,
        assigned_team: "Insurance Team",
        status: "Partnership",
        created_at: "2026-01-15T09:00:00Z"
      },
      {
        id: "st-2",
        startup_name: "Perfios",
        name: "Perfios",
        description: "FinTech aggregator supplying real-time document analysis, bank statement analysis, and fraud screening engines for high-scale BFSI giants.",
        website: "https://www.perfios.com",
        sector: "LendingTech",
        subsector: "Alternative Credit Underwriting",
        funding_stage: "Series D",
        funding_amount: "$420M",
        ai_summary: "Deep statement analyzers and financial data pipelines. Perfect partner to implement instant personal and SME loans by automating financial health scanning.",
        entity_relevance: "Relevant to ICICI Bank and ICICI Housing Finance for credit evaluation and automated financial health indexing.",
        relevance_mapping: {
          "ICICI Bank": "SME and retail credit underwriting instant decisioning engine.",
          "ICICI Housing Finance": "Automate self-employed buyer verification."
        },
        use_cases: ["Bank statement parser integration with retail loan flow.", "Income verification patterns."],
        priority_score: 96,
        assigned_team: "Lending Team",
        status: "Proof of Concept",
        created_at: "2026-02-10T11:30:00Z"
      },
      {
        id: "st-3",
        startup_name: "Artivatic.ai",
        name: "Artivatic.ai",
        description: "AI-based underwriting and claims automation SaaS platform for health and life insurance companies, focusing on real-time disease pattern parsing.",
        website: "https://www.artivatic.ai",
        sector: "AI Ops",
        subsector: "Cognitive BFSI Intelligence",
        funding_stage: "Acquired",
        funding_amount: "$15M",
        ai_summary: "Proprietary disease mapping databases and NLP claim summary readers. Directly automates retail health claim logs and checks for policy fraud outliers.",
        entity_relevance: "Primary fit with ICICI Prudential Life Insurance and Lombard to automate medical document classification and disease risk estimation.",
        relevance_mapping: {
          "ICICI Prudential Life Insurance": "Apply NLP analysis to convert medical papers into dynamic actuarial scores.",
          "ICICI Lombard": "Use computer vision for commercial hazard analyses."
        },
        use_cases: ["Instant medical underwriting calculations.", "AI-driven fraud detection in health claims."],
        priority_score: 91,
        assigned_team: "Enterprise AI Team",
        status: "Evaluation",
        created_at: "2026-03-01T14:45:00Z"
      },
      {
        id: "st-4",
        startup_name: "Zerodha",
        name: "Zerodha",
        description: "India's highest scale retail discount broker delivering discount broking APIs, mutual fund direct investments, and customized financial education.",
        website: "https://www.zerodha.com",
        sector: "WealthTech",
        subsector: "Retail Investment Disruption",
        funding_stage: "Growth",
        funding_amount: "$0 (Bootstrapped)",
        ai_summary: "High volume broking engine with incredible technology efficiency. ICICI Securities can deploy similar discount-inspired models or mutual fund direct routing layers.",
        entity_relevance: "Direct benchmark/competitor relevance to ICICI Securities and ICICI Prudential AMC for retail customer retention.",
        relevance_mapping: {
          "ICICI Securities": "Compare retail broker transaction APIs.",
          "ICICI Prudential AMC": "Explore API integrations to buy direct mutual funds."
        },
        use_cases: ["Investment solutions targeting Gen-Z segment.", "Direct API integrations for mutual fund liquid swaps."],
        priority_score: 87,
        assigned_team: "AMC/Securities Team",
        status: "Screening",
        created_at: "2026-03-12T10:00:00Z"
      }
    ];

    const mockAssignments: Assignment[] = [
      { id: "as-1", startup_id: "st-1", team: "Insurance Team", entity: "ICICI Lombard", assigned_at: "2026-01-20T10:00:00Z", status: "Active Engagement", notes: "Assigned after active discussions. Claim verification integration pending audit." },
      { id: "as-2", startup_id: "st-2", team: "Lending Team", entity: "ICICI Bank", assigned_at: "2026-02-15T14:00:00Z", status: "Active Engagement", notes: "Undergoing high-volume API benchmark testing." }
    ];

    const mockCategories: StartupCategory[] = [
      { id: "cat-1", sector: "InsurTech", core_focus: "Claims Automation, Micro-Policies, Underwriting AI", icici_owner: "ICICI Lombard & ICICI Prudential Life" },
      { id: "cat-2", sector: "WealthTech", core_focus: "Discount Brokerage, Digital Advisory, Asset Customization", icici_owner: "ICICI Securities & ICICI Prudential AMC" },
      { id: "cat-3", sector: "LendingTech", core_focus: "Alternative Credit Scoring, Instant SME Loans, Credit Cards", icici_owner: "ICICI Bank & ICICI Housing Finance" },
      { id: "cat-4", sector: "AI Ops", core_focus: "Document Intelligence, Fraud Analytics, General Language Ops", icici_owner: "Enterprise AI Team / Group CoE" }
    ];

    const mockInteractions: Interaction[] = [
      { id: "int-1", startup_id: "st-1", date: "2026-01-22T10:00:00Z", type: "Introduction", summary: "Introductory session between Digit founders and Lombard Innovation desk.", next_steps: "Map sandbox environment parameters." }
    ];

    setStartups(mockStartups);
    setAssignments(mockAssignments);
    setCategories(mockCategories);
    setInteractions(mockInteractions);
    setIsLiveConnected(false);
  };

  // Sync with FastAPI database
  const loadDatabase = async () => {
    setLoading(true);
    setGlobalError("");
    try {
      const response = await fetch(`${API_URL}/startups`);
      if (!response.ok) throw new Error("Backend service returned error response.");
      const data = await response.json();
      
      if (Array.isArray(data)) {
        const mapped = data.map((s: any) => mapStartupWithAnalysis(s));
        setStartups(mapped);
        setIsLiveConnected(true);

        // Fetch assignments if available (mock load or custom dynamic assignments from backend)
        try {
          const asgResp = await fetch(`${API_URL}/assignments`);
          if (asgResp.ok) {
            const asgData = await asgResp.json();
            const mappedAsg = (asgData || []).map((a: any) => ({
              id: String(a.id),
              startup_id: String(a.startup_id),
              assigned_to_fpr1: a.assigned_to_fpr1 || a.assigned_to || "",
              assigned_to_fpr2: a.assigned_to_fpr2 || "",
              startup_name: a.startup_name || "",
              linkedin_reachout_message: a.linkedin_reachout_message || "",
              email_reachout_message: a.email_reachout_message || "",
              team: a.assigned_to_fpr1 || a.assigned_to || "Unassigned",
              entity: a.assigned_to_fpr2 || a.icici_entity || "Unassigned",
              assigned_at: a.created_at || a.assigned_at || new Date().toISOString(),
              status: a.assignment_status || "pending",
              notes: a.notes || ""
            }));
            setAssignments(mappedAsg);
          }
        } catch (_) {
          // Local assignments initialize fallback
          setAssignments([
            {
              id: "as-1",
              startup_id: mapped[0]?.id || "st-1",
              assigned_to_fpr1: "Anurag",
              assigned_to_fpr2: "Keroli",
              startup_name: mapped[0]?.startup_name || "Digit Insurance",
              team: "Anurag",
              entity: "Keroli",
              assigned_at: new Date().toISOString(),
              status: "Active Engagement",
              notes: "Sandbox evaluation active."
            }
          ]);
        }

        // Fetch interactions/activity logs
        try {
          const intResp = await fetch(`${API_URL}/interactions`);
          if (intResp.ok) {
            const intData = await intResp.json();
            const mappedInt = (intData || []).map((i: any) => ({
              id: String(i.id),
              startup_id: String(i.startup_id),
              date: i.date || new Date().toISOString(),
              type: i.type || "Introduction",
              summary: i.summary || "",
              next_steps: i.next_steps || ""
            }));
            setInteractions(mappedInt);
          }
        } catch (e) {
          console.warn("Could not load database interactions:", e);
        }
      } else {
        throw new Error("Invalid payload format received.");
      }
    } catch (e: any) {
      console.warn("Could not sync with FastAPI Server, running with secure Mock Seed Registry.", e);
      loadFallbackMockDatabase();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDatabase();
  }, []);

  useEffect(() => {
    let intervalId: any = null;
    
    const fetchStatus = async () => {
      try {
        const response = await fetch(`${API_URL}/scrape/status`);
        if (response.ok) {
          const data = await response.json();
          setScrapingActive(data.active);
          setScrapingTarget(data.total_target);
          setScrapingProgress(data.discovered_count);
          setScrapingCurrentStep(data.current_step);
          setScrapingLogs(data.logs || []);
          setScrapingProcessed(data.processed_startups || []);
          
          if (!data.active && scrapingActive) {
            loadDatabase();
          }
        }
      } catch (err) {
        console.warn("Error polling scrape status:", err);
      }
    };

    fetchStatus();
    intervalId = setInterval(fetchStatus, 1500);

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [scrapingActive]);

  useEffect(() => {
    if (selectedStartup) {
      const updated = startups.find(s => String(s.id) === String(selectedStartup.id));
      if (updated) {
        setSelectedStartup(updated);
      }
    }
  }, [startups]);

  // AI manual evaluation trigger
  const handleAnalyzeStartup = async (startupId: string, force: boolean = false) => {
    setGlobalError("");
    setGlobalSuccess("");
    try {
      const response = await fetch(`${API_URL}/analyze/${startupId}?force=${force}`, {
        method: "POST",
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Analysis trigger failed.");
      }
      
      // Update local state by reloading startups
      await loadDatabase();
      setGlobalSuccess(`AI Strategic Analysis successfully written for venture ID ${startupId}!`);
      
      // Sync detailed modal
      const refreshed = startups.find(s => String(s.id) === String(startupId));
      if (refreshed) {
        setSelectedStartup(refreshed);
      }
      return { success: true };
    } catch (e: any) {
      console.error(e);
      // Simulate local analysis fallback if mock mode is active
      const targetIdx = startups.findIndex(s => String(s.id) === String(startupId));
      if (targetIdx !== -1) {
        const updatedList = [...startups];
        const randomScore = Math.floor(Math.random() * (98 - 72 + 1)) + 72;
        updatedList[targetIdx] = {
          ...updatedList[targetIdx],
          priority_score: randomScore,
          ai_summary: `AI Evaluation fallback: ${updatedList[targetIdx].startup_name} offers customized BFSI modular pipelines. Ready for active pilot Sandbox trialing.`,
          entity_relevance: `Highly relevant for automated claims or risk verification inside corporate divisions.`,
          use_cases: ["Underwriting model validations.", "Instant retail loan flow verification."],
          status: "Evaluation"
        };
        setStartups(updatedList);
        if (selectedStartup && String(selectedStartup.id) === String(startupId)) {
          setSelectedStartup(updatedList[targetIdx]);
        }
        setGlobalSuccess("System enrichment completed (Offline fallback mode active).");
        return { success: true };
      }
      return { error: e.message || "Failed running AI analysis." };
    }
  };

  // Add Startup Manually
  const handleAddStartup = async (startupData: any) => {
    setGlobalError("");
    setGlobalSuccess("");
    try {
      // Name normalization duplicate check
      const normalizeName = (name: string) => name.toLowerCase().replace(/[^a-z0-9]/g, "");
      const normalizedNew = normalizeName(startupData.name);
      const exists = startups.some((s) => normalizeName(s.startup_name) === normalizedNew);
      if (exists) {
        return { error: `Venture "${startupData.name}" already exists in our registry (similar name detected).` };
      }

      if (isLiveConnected) {
        // Prepare backend request to save startups
        const response = await fetch(`${API_URL}/startups/create`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            startup_name: startupData.name,
            website: startupData.website,
            description: startupData.description,
            industry: startupData.industry || "Financial Services",
            sector: startupData.sector,
            subsector: startupData.subsector || "Unknown",
            funding_stage: startupData.funding_stage || "Seed",
            funding_amount: startupData.funding_amount || "$1M",
            business_models: startupData.business_models || []
          })
        });
        const data = await response.json();
        if (!response.ok) return { error: data.detail || "Failed adding startup." };
        await loadDatabase();
        setGlobalSuccess(`Successfully registered "${startupData.name}" into Supabase Registry.`);
        return { success: true };
      } else {
        // Mock fallback create
        const nextId = `st-${Date.now()}`;
        const newStartup: Startup = {
          id: nextId,
          startup_name: startupData.name,
          name: startupData.name,
          description: startupData.description,
          website: startupData.website || "https://example.com",
          sector: startupData.sector,
          subsector: "Custom Integration",
          subSector: "Custom Integration",
          funding_stage: startupData.funding_stage || "Seed",
          funding_amount: startupData.funding_amount || "$1M",
          ai_summary: `Quick Registry Entry: Operates in ${startupData.sector} solving client requirements. AI evaluation pending.`,
          entity_relevance: `Relevant for BFSI underwritings.`,
          relevance_mapping: { "ICICI Bank": "Sandbox evaluation pending." },
          use_cases: ["Automation trials."],
          priority_score: 75,
          assigned_team: startupData.sector === "InsurTech" ? "Insurance Team" : "Lending Team",
          status: "Screening",
          created_at: new Date().toISOString()
        };
        setStartups([newStartup, ...startups]);
        setGlobalSuccess(`Successfully added "${startupData.name}" (Mock offline persistence).`);
        return { success: true };
      }
    } catch (e: any) {
      return { error: "Failed connecting database API scheduler." };
    }
  };

  // Upload dataset CSV
  const handleUploadCSV = async (csvText: string) => {
    setGlobalError("");
    setGlobalSuccess("");
    try {
      if (isLiveConnected) {
        const response = await fetch(`${API_URL}/startups/upload-csv`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ csvText })
        });
        const data = await response.json();
        if (!response.ok) return { error: data.detail || "CSV upload failed." };
        await loadDatabase();
        setGlobalSuccess(`Batch processed CSV. Added ${data.added} records to database.`);
        return { success: true, added: data.added, duplicates: data.duplicates };
      } else {
        // Parse CSV locally in Mock mode
        const lines = csvText.split(/\r?\n/).filter(l => l.trim().length > 0);
        if (lines.length <= 1) return { error: "Empty or invalid CSV payload." };
        
        let added = 0;
        const newItems: Startup[] = [];
        const duplicates: string[] = [];

        for (let idx = 1; idx < lines.length; idx++) {
          const cols = lines[idx].split(",");
          if (cols.length < 2) continue;
          
          const name = cols[0].trim().replace(/^"|"$/g, "");
          const desc = cols[1].trim().replace(/^"|"$/g, "");
          const web = cols[2]?.trim().replace(/^"|"$/g, "") || "https://example.com";
          
          if (!name || !desc) continue;
          if (startups.some(s => s.startup_name.toLowerCase() === name.toLowerCase())) {
            duplicates.push(name);
            continue;
          }

          newItems.push({
            id: `st-csv-${Date.now()}-${idx}`,
            startup_name: name,
            name: name,
            description: desc,
            website: web,
            sector: "LendingTech",
            subSector: "CSV Ingestion",
            subsector: "CSV Ingestion",
            funding_stage: "Seed",
            funding_amount: "$500k",
            ai_summary: `CSV Import: ${name} specializes in ${desc.slice(0, 50)}...`,
            entity_relevance: "Lending optimization fit.",
            relevance_mapping: { "ICICI Bank": "Sandbox process evaluation." },
            use_cases: ["API sandbox checking."],
            priority_score: 72,
            assigned_team: "Lending Team",
            status: "Screening",
            created_at: new Date().toISOString()
          });
          added++;
        }
        setStartups([...newItems, ...startups]);
        setGlobalSuccess(`Batch processed CSV. Added ${added} records to cache.`);
        return { success: true, added, duplicates };
      }
    } catch (e) {
      return { error: "Could not connect to API server." };
    }
  };

  // Run Semantic search correlation matching
  const handleSemanticSearch = async (query: string): Promise<any[]> => {
    try {
      if (isLiveConnected) {
        const response = await fetch(`${API_URL}/startups/semantic-search`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query })
        });
        if (!response.ok) return [];
        const data = await response.json();
        return data.matches || [];
      } else {
        // Fallback local keyword ranking
        const kw = query.toLowerCase().split(/\s+/);
        return startups
          .map((s) => {
            let score = 0;
            const text = `${s.startup_name} ${s.description} ${s.sector}`.toLowerCase();
            for (const word of kw) {
              if (word.length < 3) continue;
              if (text.includes(word)) score += 10;
              if (s.startup_name.toLowerCase().includes(word)) score += 15;
            }
            return {
              id: s.id,
              score,
              explanation: `Keyword match in ${s.sector} - ${s.subsector}.`
            };
          })
          .filter(item => item.score > 0)
          .sort((a, b) => b.score - a.score);
      }
    } catch (e) {
      console.error("Semantic search failed, fallback active.", e);
      return [];
    }
  };

  // Update Status and values of a single Startup
  const handleUpdateStatus = async (id: string, status: any, team?: string, priorityScore?: number) => {
    setGlobalError("");
    try {
      if (isLiveConnected) {
        const response = await fetch(`${API_URL}/startups/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status, assigned_team: team, priority_score: priorityScore })
        });
        if (!response.ok) throw new Error("Failed to modify database record.");
        await loadDatabase();
        setGlobalSuccess("Relational changes committed to Supabase registry.");
      } else {
        // Offline update
        const updated = startups.map((s) => {
          if (String(s.id) === String(id)) {
            return {
              ...s,
              status: status || s.status,
              assigned_team: team || s.assigned_team,
              priority_score: priorityScore !== undefined ? Number(priorityScore) : s.priority_score
            };
          }
          return s;
        });
        setStartups(updated);
        const refreshed = updated.find(s => String(s.id) === String(id));
        if (refreshed) setSelectedStartup(refreshed);
        setGlobalSuccess("Venture status updated successfully (offline cache).");
      }
    } catch (e: any) {
      setGlobalError(e.message || "Failed committing state variables.");
    }
  };

  const handleUpdateField = async (startupId: string, field: string, value: any) => {
    try {
      const response = await fetch(`${API_URL}/startups/${startupId}/field`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ field, value })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to update field.");
      }
      await loadDatabase();
      setGlobalSuccess(`Successfully updated field "${field}"!`);
      return { success: true };
    } catch (err: any) {
      setGlobalError(err.message || "Failed to update field.");
      return { error: err.message };
    }
  };

  const handleRecheckField = async (startupId: string, field: string) => {
    try {
      const response = await fetch(`${API_URL}/startups/${startupId}/recheck`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ field })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to run AI recheck.");
      }
      await loadDatabase();
      setGlobalSuccess(`Successfully ran AI targeted recheck for "${field}"!`);
      return { success: true, data: data.data };
    } catch (err: any) {
      setGlobalError(err.message || "Failed to run AI recheck.");
      return { error: err.message };
    }
  };

  // Add Interaction Log
  const handleAddInteraction = async (startupId: string, logData: any) => {
    try {
      if (isLiveConnected) {
        const response = await fetch(`${API_URL}/interactions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ startup_id: Number(startupId), ...logData })
        });
        if (!response.ok) throw new Error("Failed adding interaction.");
      }
      
      const newLog: Interaction = {
        id: `int-${Date.now()}`,
        startup_id: startupId,
        date: new Date().toISOString(),
        type: logData.type || "Introduction",
        summary: logData.summary,
        next_steps: logData.next_steps || "Pending update"
      };
      setInteractions([newLog, ...interactions]);
      setGlobalSuccess("Venture evaluation log recorded successfully.");
    } catch (e) {
      console.error(e);
    }
  };

  // Create Assignment
  const handleCreateAssignment = async (startupId: string, assignmentData: any) => {
    try {
      const startup = startups.find(s => String(s.id) === String(startupId));
      const sName = startup ? startup.startup_name : "";

      let responseData: any = null;
      if (isLiveConnected) {
        const response = await fetch(`${API_URL}/assignments`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            startup_id: Number(startupId),
            assigned_to_fpr1: assignmentData.assigned_to_fpr1,
            assigned_to_fpr2: assignmentData.assigned_to_fpr2,
            notes: assignmentData.notes
          })
        });
        if (!response.ok) throw new Error("Failed completing pilot routing file.");
        const result = await response.json();
        if (result.status === "success" && result.data && result.data.length > 0) {
          responseData = result.data[0];
        }
      }

      const newAssignment: Assignment = responseData ? {
        id: String(responseData.id),
        startup_id: String(responseData.startup_id),
        startup_name: responseData.startup_name || sName,
        assigned_to_fpr1: responseData.assigned_to_fpr1,
        assigned_to_fpr2: responseData.assigned_to_fpr2,
        linkedin_reachout_message: responseData.linkedin_reachout_message,
        email_reachout_message: responseData.email_reachout_message,
        team: responseData.assigned_to_fpr1 || "Unassigned",
        entity: responseData.assigned_to_fpr2 || "Unassigned",
        assigned_at: responseData.created_at || new Date().toISOString(),
        status: responseData.assignment_status || "pending",
        notes: responseData.notes || ""
      } : {
        id: `as-${Date.now()}`,
        startup_id: startupId,
        startup_name: sName,
        assigned_to_fpr1: assignmentData.assigned_to_fpr1,
        assigned_to_fpr2: assignmentData.assigned_to_fpr2,
        team: assignmentData.assigned_to_fpr1,
        entity: assignmentData.assigned_to_fpr2,
        assigned_at: new Date().toISOString(),
        status: `Assigned to ${assignmentData.assigned_to_fpr1}`,
        notes: assignmentData.notes || "Assigned."
      };
      setAssignments([newAssignment, ...assignments]);

      // Sync startup assigned team
      const updated = startups.map((s) => {
        if (String(s.id) === String(startupId)) {
          return { ...s, assigned_team: assignmentData.assigned_to_fpr1 };
        }
        return s;
      });
      setStartups(updated);
      setGlobalSuccess(`Venture successfully routed to FPR1: ${assignmentData.assigned_to_fpr1}, FPR2: ${assignmentData.assigned_to_fpr2}!`);
    } catch (e) {
      console.error(e);
    }
  };

  // Update Assignment Status
  const handleUpdateAssignment = async (id: string, updates: Partial<Assignment>) => {
    try {
      if (isLiveConnected) {
        const response = await fetch(`${API_URL}/assignments/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(updates)
        });
        if (!response.ok) throw new Error("Could not update assignment details.");
      }

      const updated = assignments.map((a) => {
        if (String(a.id) === String(id)) {
          const statusVal = updates.status !== undefined ? updates.status : (updates.assigned_to_fpr1 ? `Assigned to ${updates.assigned_to_fpr1}` : a.status);
          return { ...a, ...updates, status: statusVal };
        }
        return a;
      });
      setAssignments(updated);
      if (isLiveConnected) {
        await loadDatabase();
      }
      setGlobalSuccess("Engagement assignment updated successfully.");
    } catch (e) {
      console.error(e);
    }
  };

  // Run SQL Console query processor
  const handleRunSQL = async (sql: string): Promise<any> => {
    try {
      if (isLiveConnected) {
        const response = await fetch(`${API_URL}/supabase/query`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sql })
        });
        return await response.json();
      } else {
        // Offline SQL Simulator
        const norm = sql.toLowerCase().trim();
        if (norm.startsWith("select * from startups")) {
          return { columns: ["id", "startup_name", "description", "website", "sector", "funding_stage"], rows: startups };
        }
        if (norm.startsWith("select * from assignments") || norm.startsWith("select * from startup_assignments")) {
          return { columns: ["id", "startup_id", "team", "entity", "assigned_at", "status", "notes"], rows: assignments };
        }
        if (norm.startsWith("select * from interactions") || norm.startsWith("select * from startup_activity_logs")) {
          return { columns: ["id", "startup_id", "date", "type", "summary", "next_steps"], rows: interactions };
        }
        return {
          columns: ["query_hint", "status", "rows_affected"],
          rows: [{ query_hint: "Simulated SELECT output success.", status: "Success", rows_affected: startups.length }]
        };
      }
    } catch (e) {
      return { error: "Database response timeout." };
    }
  };

  // Re-seed Database
  const handleResetDB = async () => {
    setLoading(true);
    try {
      if (isLiveConnected) {
        await fetch(`${API_URL}/database/reset`, { method: "POST" });
        await loadDatabase();
      } else {
        loadFallbackMockDatabase();
      }
      setGlobalSuccess("Ecosystem successfully re-seeded to defaults.");
    } catch (e) {
      setGlobalError("Failed syncing seed parameters.");
    } finally {
      setLoading(false);
    }
  };

  const highPriorityCount = startups.filter((s) => (s.priority_score || 0) >= 90).length;

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden text-slate-800 font-sans" id="group-platform-root">
      
      {/* Sidebar navigation */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        currentUser={currentUser}
        onUserChange={setCurrentUser}
        totalCount={startups.length}
        highPriorityCount={highPriorityCount}
      />

      {/* Main Panel space */}
      <div className="flex-1 flex flex-col overflow-hidden animate-fade-in" id="main-panel-space">
        
        {/* Header Ribbon */}
        <header className="bg-white border-b border-slate-200/80 px-8 py-4 flex items-center justify-between flex-shrink-0" id="platform-header-ribbon">
          <div className="space-y-0.5 text-left">
            <h2 className="font-extrabold text-sm uppercase tracking-wider text-slate-900">
              ICICI Group Startup Intelligence & Pilots Registry
            </h2>
            <p className="text-slate-400 text-[11px] font-medium text-left">
              Enterprise Suite (Active Role: <span className="text-amber-600 font-bold">{currentUser.role}</span>)
            </p>
          </div>

          <div className="flex items-center gap-4">
            {/* Database sync status */}
            <div className={`flex items-center gap-1.5 border py-1 px-2.5 rounded-lg text-xs font-semibold ${
              isLiveConnected 
                ? "bg-emerald-50 border-emerald-100 text-emerald-700" 
                : "bg-amber-50 border-amber-100 text-amber-700"
            }`}>
              <span className={`h-2 w-2 rounded-full ${isLiveConnected ? "bg-emerald-500 animate-pulse" : "bg-amber-500 animate-ping"}`}></span>
              <span>{isLiveConnected ? "Supabase Live Connected" : "Local Mock Registry (Offline Fallback)"}</span>
            </div>
          </div>
        </header>

        {/* Informational Alerts */}
        {(globalError || globalSuccess) && (
          <div className="px-8 pt-4 flex-shrink-0 space-y-2">
            {globalError && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs font-semibold rounded-lg flex items-center justify-between">
                <span className="flex items-center gap-1.5"><AlertCircle size={15} /> {globalError}</span>
                <button onClick={() => setGlobalError("")} className="text-red-400 hover:text-red-650 font-bold">CLOSE</button>
              </div>
            )}
            {globalSuccess && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold rounded-lg flex items-center justify-between">
                <span className="flex items-center gap-1.5"><CheckCircle size={15} className="text-emerald-500" /> {globalSuccess}</span>
                <button onClick={() => setGlobalSuccess("")} className="text-emerald-400 hover:text-emerald-655 font-bold">DISMISS</button>
              </div>
            )}
          </div>
        )}

        {/* Content Tabs */}
        <main className="flex-1 overflow-y-auto p-8" id="tab-scrolling-container">
          {loading ? (
            <div className="h-full flex flex-col items-center justify-center space-y-4">
              <RefreshCw className="animate-spin text-indigo-650" size={36} />
              <div className="text-center space-y-1">
                <h4 className="font-bold text-slate-800">Synchronizing ICICI Registry...</h4>
                <p className="text-xs text-slate-450">Loading relation tables and database metadata securely.</p>
              </div>
            </div>
          ) : (
            <Routes>
              <Route path="/" element={
                <Dashboard
                  startups={startups}
                  assignments={assignments}
                  interactions={interactions}
                  onSelectStartup={setSelectedStartup}
                  onTabChange={handleTabChange}
                />
              } />
              <Route path="/dashboard" element={
                <Dashboard
                  startups={startups}
                  assignments={assignments}
                  interactions={interactions}
                  onSelectStartup={setSelectedStartup}
                  onTabChange={handleTabChange}
                />
              } />
              <Route path="/news-dashboard" element={
                <NewsDashboard
                  apiUrl={API_URL}
                  onSelectStartupByName={(name) => {
                    const found = startups.find(
                      (s) => (s.startup_name || s.name || "").toLowerCase() === name.toLowerCase()
                    );
                    if (found) {
                      setSelectedStartup(found);
                    } else {
                      alert(`Startup "${name}" was extracted from this news story, but does not have a fully enriched registry profile yet.`);
                    }
                  }}
                />
              } />
              <Route path="/repository" element={
                <Repository
                  startups={startups}
                  currentUser={currentUser}
                  onAddStartup={handleAddStartup}
                  onUploadCSV={handleUploadCSV}
                  onSelectStartup={setSelectedStartup}
                  onSemanticSearch={handleSemanticSearch}
                  onResetDB={handleResetDB}
                />
              } />
              <Route path="/high-priority" element={
                <HighPriority startups={startups} onSelectStartup={setSelectedStartup} />
              } />
              <Route path="/assignments" element={
                <Assignments
                  startups={startups}
                  assignments={assignments}
                  categories={categories}
                  currentUser={currentUser}
                  onUpdateAssignment={handleUpdateAssignment}
                />
              } />
              <Route path="/insights" element={<Insights startups={startups} isLiveConnected={isLiveConnected} />} />
              <Route path="/database" element={<SupabaseConsole onRunSQL={handleRunSQL} />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/scraping" element={
                <Scraping
                  scrapingActive={scrapingActive}
                  scrapingLogs={scrapingLogs}
                  scrapingProcessed={scrapingProcessed}
                  scrapingCurrentStep={scrapingCurrentStep}
                  scrapingTarget={scrapingTarget}
                  scrapingProgress={scrapingProgress}
                  onStartScrape={async (sources: string[], limit: number, filters: any) => {
                    try {
                      const response = await fetch(`${API_URL}/scrape`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          sources,
                          limit,
                          ...filters
                        })
                      });
                      const data = await response.json();
                      if (!response.ok) {
                        throw new Error(data.detail || "Failed to trigger discovery.");
                      }
                      setScrapingActive(true);
                      setScrapingTarget(limit);
                      setScrapingProgress(0);
                      setScrapingLogs([]);
                      setScrapingProcessed([]);
                      return { success: true };
                    } catch (err: any) {
                      return { error: err.message };
                    }
                  }}
                />
              } />
              <Route path="/startups/:id" element={<StartupDetails />} />
              <Route path="/startup/:id" element={<StartupDetails />} />
              <Route path="/observability" element={<Observability />} />
            </Routes>
          )}
        </main>
      </div>

      {/* DETAIL DRAWER OVERLAY MODAL */}
      {selectedStartup && (
        <DetailModal
          startup={selectedStartup}
          assignments={assignments}
          interactions={interactions.filter(i => String(i.startup_id) === String(selectedStartup.id))}
          currentUser={currentUser}
          onClose={() => setSelectedStartup(null)}
          onUpdateStatus={handleUpdateStatus}
          onAddInteraction={handleAddInteraction}
          onCreateAssignment={handleCreateAssignment}
          onUpdateAssignment={handleUpdateAssignment}
          onAnalyze={isLiveConnected ? handleAnalyzeStartup : undefined}
          onUpdateField={handleUpdateField}
          onRecheckField={handleRecheckField}
        />
      )}
    </div>
  );
}
