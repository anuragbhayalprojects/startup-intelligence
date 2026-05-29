export type Startup = {
  id: string;
  name: string;
  logo: string;
  sector: string;
  subSector: string;
  stage: "Seed" | "Series A" | "Series B" | "Series C" | "Series D+" | "Pre-Seed";
  hq: string;
  country: string;
  founded: number;
  employees: number;
  website: string;
  description: string;
  totalFunding: number; // USD
  lastRound: { type: string; amount: number; date: string; leadInvestor: string };
  investors: string[];
  founders: { name: string; role: string; linkedin: string }[];
  bfsiRelevance: number; // 0-100
  iciciFitScore: number; // 0-100
  useCases: string[];
  aiInsight: string;
  tags: string[];
};

export type Assignment = {
  id: string;
  startupId: string;
  startupName: string;
  owner: string;
  team: "M&A" | "Partnerships" | "Innovation" | "Risk" | "Tech";
  status: "New" | "In Review" | "Engaged" | "Piloting" | "Closed";
  priority: "Low" | "Medium" | "High" | "Critical";
  updatedAt: string;
};

export type Source = {
  id: string;
  name: string;
  type: "News" | "Database" | "Crunchbase" | "RSS" | "Social";
  status: "Active" | "Paused" | "Error";
  lastScrape: string;
  startupCount: number;
  successRate: number;
};

export type WorkflowJob = {
  id: string;
  name: string;
  stage: "Ingest" | "Enrich" | "Score" | "Notify";
  status: "Running" | "Queued" | "Completed" | "Failed";
  progress: number;
  startedAt: string;
};
