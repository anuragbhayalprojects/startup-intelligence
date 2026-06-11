// frontend/src/types.ts

export type AppTab =
  | "dashboard"
  | "repository"
  | "high-priority"
  | "assignments"
  | "insights"
  | "database"
  | "chat"
  | "scraping"
  | "observability";

export interface Startup {
  id: string;
  startup_name: string; // Live PostgreSQL column
  name?: string;         // Mock fallback / alias
  logo?: string;         // Mock logo attribute
  description: string;
  website: string;
  sector: string;
  subsector?: string;    // Live database column
  subSector?: string;    // Mock fallback
  funding_stage: string;
  funding_amount?: string;
  founded_year?: number;
  city?: string;
  state?: string;
  country?: string;
  source?: string;
  source_url?: string;
  created_at: string;
  updated_at?: string;

  ai_summary?: string;
  relevance_summary?: string;
  entity_relevance?: string;
  relevance_mapping?: Record<string, string>;
  use_cases?: string[]; // fallback string list or mapped live use cases
  priority_score?: number;
  assigned_team?: string;
  status?: "Screening" | "Evaluation" | "Proof of Concept" | "Partnership" | "Rejected" | string;

  // Live database PostgreSQL relational joins
  startup_analyses?: { id?: number; analysis_data: StartupAnalysis }[];
  startup_analysis?: { analysis_json?: StartupAnalysis; analysis_data?: StartupAnalysis }[];

  // News history feed — populated from startup_news table
  recent_news?: {
    id: number;
    headline: string;
    summary?: string;
    source?: string;
    source_url?: string;
    published_at?: string;
  }[];

  // Funding rounds — populated from startup_analysis Pass 3 enrichment
  funding_rounds?: {
    stage: string;
    amount: string;
    date: string;
    lead_investor: string;
    co_investors: string[];
  }[];
  total_funding?: string;
  latest_round_stage?: string;
  latest_round_date?: string;

  // Master Taxonomy attributes
  industry?: string;
  business_models?: string[];
  industry_relevance?: string[];
  tags?: string[];

  // Founder info (synced from analysis)
  founder_name?: string;
  founder_linkedin_url?: string;

  // Upgraded multi-agent workspace columns
  startup_status?: string;
  headquarters?: string;
  startup_stage?: string;
  relevance_score?: number;
  signal_score?: number;
  deployability_score?: number;
  recommendation_score?: number;
  confidence_score?: number;
  recommended_action?: string;
  priority_band?: string;
  matched_entities?: string[];
  matched_business_teams?: string[];
  matched_business_problems?: string[];
  positive_signals?: string[];
  negative_signals?: string[];
  audit_summary?: any;
  knowledge_version?: string;
  analysis_version?: string;
  market_intelligence?: {
    products?: {
      product_name: string;
      category: string;
      description: string;
      target_customer: string;
      deployment_model: string;
    }[];
    competitors?: {
      company_name: string;
      category: string;
      positioning: string;
    }[];
    valuation?: {
      estimated_valuation?: string;
      valuation_methodology?: string;
      revenue_multiple?: string;
      comparable_companies?: string[];
    };
    investors?: {
      investor_name: string;
      round: string;
      date: string;
    }[];
    strategic_positioning?: string;
  };
}

export interface StartupAnalysis {
  extracted_startup_name?: string;
  startup_website?: string;
  founded_year?: number;
  summary: {
    one_liner: string;
    business_model: string;
    target_audience: string;
  };
  founders?: {
    name: string;
    role: string;
    brief_details: string;
  }[];
  funding_stages?: {
    series: string;
    amount: string;
    investors: string[];
  };
  valuation_metrics?: {
    revenue: string;
    ebitda_multiple: string;
    other_metrics: string;
  };
  bfsi_relevance: {
    is_relevant: boolean;
    relevance_score: number;
    use_cases: {
      icici_entity: string;
      use_case: string;
      potential_impact: string;
    }[];
  };
  strategic_fit: {
    enterprise_readiness: number;
    partnership_opportunity: string;
    integration_feasibility: string;
  };
  scoring: {
    overall_priority_score: number;
    risk_assessment: string | string[];
  };
  classification: {
    industry?: string;
    sector?: string;
    subsector?: string;
    business_models?: string[];
    industry_relevance?: string[];
    primary_sector?: string;
    sub_sectors?: string[];
    tags: string[];
  };
}

export interface StartupScore {
  startup_id: string;
  market_size: number;
  team_strength: number;
  product_fit: number;
  compliance_risk: number;
  overall_score: number;
}

export interface Assignment {
  id: string;
  startup_id?: string;  // support live DB
  startupId?: string;    // support mock data
  startupName?: string;  // support mock data
  owner?: string;        // support mock data
  priority?: string;     // support mock data
  updatedAt?: string;    // support mock data
  assigned_to_fpr1?: string; // support live DB renamed columns
  assigned_to_fpr2?: string; // support live DB new columns
  startup_name?: string;     // support live DB new columns
  linkedin_reachout_message?: string;
  email_reachout_message?: string;
  team: string;          // support mock data / fallback mapped team (FPR1)
  entity?: string;       // support mock data / fallback mapped entity (FPR2)
  assigned_at?: string;  // support live DB
  status: "Pending Review" | "Active Engagement" | "On Hold" | "Completed" | string;
  notes?: string;        // support live DB
  icici_entity?: string; // support live DB entity routing
  
  // Upgraded routing fields
  business_team?: string;
  engagement_stage?: string;
  assignment_score?: number;
  assignment_band?: string;
  assignment_score_manual_override?: number;
  assignment_score_override_reason?: string;
  last_followup_date?: string;
}

export interface StartupCategory {
  id: string;
  sector: string;
  core_focus: string;
  icici_owner: string;
}

export interface Interaction {
  id: string;
  startup_id: string;
  date: string;
  type: "Introduction" | "Technical Review" | "POC Execution" | "MOU Signed" | "Stakeholder Pitch" | string;
  summary: string;
  next_steps: string;
}

export interface DBConsoleState {
  activeTable: "startups" | "startup_scores" | "assignments" | "startup_categories" | "interactions";
  customSQL: string;
  queryResult: any[] | null;
  queryError: string | null;
}

export interface UserRole {
  username: string;
  role: "Admin" | "Investment Officer" | "ICICI Entity Stakeholder";
  entity?: string; // Optional target ICICI entity
}

// Pre-existing Workspace Mocks
export interface Source {
  id: string;
  name: string;
  type: "News" | "Database" | "Crunchbase" | "RSS" | "Social" | string;
  status: "Active" | "Paused" | "Error" | string;
  lastScrape: string;
  startupCount: number;
  successRate: number;
}

export interface WorkflowJob {
  id: string;
  name: string;
  stage: "Ingest" | "Enrich" | "Score" | "Notify" | string;
  status: "Running" | "Queued" | "Completed" | "Failed" | string;
  progress: number;
  startedAt: string;
}
