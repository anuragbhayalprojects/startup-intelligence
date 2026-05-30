
// frontend/src/types.ts

export interface Startup {
  id: string;
  created_at: string;
  startup_name: string;
  description: string;
  source: string;
  source_url: string;
  startup_analyses: { analysis_data: StartupAnalysis }[];
}

export interface StartupAnalysis {
  summary: {
    one_liner: string;
    business_model: string;
    target_audience: string;
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
    risk_assessment: string;
  };
  classification: {
    primary_sector: string;
    sub_sectors: string[];
    tags: string[];
  };
}
