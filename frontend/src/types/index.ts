export type FundingStage =
  | "Pre-Seed"
  | "Seed"
  | "Series A"
  | "Series B"
  | "Series C"
  | "Series D+"
  | "Growth";

export type StartupStatus = "New" | "In Review" | "Engaged" | "Pipeline" | "Passed";

export interface Startup {
  id: string;
  name: string;
  sector: string;
  subsector: string;
  city: string;
  country: string;
  fundingStage: FundingStage;
  bfsiScore: number; // 0-100
  priorityScore: number; // 0-100
  assignedTeam: string;
  source: string;
  lastUpdated: string; // ISO
  status: StartupStatus;
  description: string;
  website: string;
  founded: number;
  employees: number;
  totalFundingUSD: number;
  founders: string[];
  tags: string[];
  saved?: boolean;
}

export interface AIInsight {
  id: string;
  startupId: string;
  startupName: string;
  type: "Opportunity" | "Risk" | "Trend" | "Match";
  title: string;
  summary: string;
  confidence: number;
  createdAt: string;
}

export interface Assignment {
  id: string;
  startupId: string;
  startupName: string;
  assignee: string;
  team: string;
  dueDate: string;
  priority: "Low" | "Medium" | "High" | "Critical";
  status: "Open" | "In Progress" | "Blocked" | "Done";
  createdAt: string;
}

export interface WorkflowRun {
  id: string;
  name: string;
  type: "Ingestion" | "Scoring" | "Enrichment" | "Export";
  status: "Running" | "Success" | "Failed" | "Queued";
  startedAt: string;
  durationMs: number;
  recordsProcessed: number;
}

export interface SourceFeed {
  id: string;
  name: string;
  type: "API" | "Scraper" | "Manual" | "Partner";
  status: "Healthy" | "Degraded" | "Down";
  lastSync: string;
  recordsToday: number;
  uptime: number;
}

export interface ActivityEvent {
  id: string;
  startupId: string;
  type: "note" | "status" | "score" | "assignment" | "tag";
  actor: string;
  message: string;
  at: string;
}
