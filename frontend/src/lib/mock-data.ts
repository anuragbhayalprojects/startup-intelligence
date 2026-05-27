import type {
  Startup,
  AIInsight,
  Assignment,
  WorkflowRun,
  SourceFeed,
  ActivityEvent,
} from "@/types";

const SECTORS = [
  { s: "Fintech", sub: ["Payments", "Lending", "WealthTech", "InsurTech", "RegTech", "Neobanking"] },
  { s: "SaaS", sub: ["HR Tech", "DevOps", "Productivity", "Analytics"] },
  { s: "AI/ML", sub: ["LLM Infra", "Computer Vision", "NLP", "MLOps"] },
  { s: "HealthTech", sub: ["Diagnostics", "Telemedicine", "Pharma"] },
  { s: "Logistics", sub: ["B2B Logistics", "Last Mile", "Freight"] },
  { s: "ConsumerTech", sub: ["D2C", "Social", "Gaming"] },
  { s: "ClimateTech", sub: ["EV", "Renewables", "Carbon"] },
];

const CITIES = ["Bengaluru", "Mumbai", "Delhi NCR", "Hyderabad", "Pune", "Chennai", "Singapore", "London", "New York", "Dubai"];
const STAGES = ["Pre-Seed", "Seed", "Series A", "Series B", "Series C", "Series D+", "Growth"] as const;
const TEAMS = ["Ventures Team", "Innovation Lab", "Corporate Strategy", "Digital Banking", "Risk & Compliance", "Wealth Group"];
const SOURCES = ["Crunchbase", "Tracxn", "LinkedIn", "Partner Network", "News API", "Manual Entry", "YourStory"];
const STATUSES = ["New", "In Review", "Engaged", "Pipeline", "Passed"] as const;

const NAME_PREFIXES = ["Neo", "Fin", "Apex", "Zenith", "Orbit", "Nimbus", "Quant", "Vector", "Hexa", "Lumen", "Stride", "Pulse", "Atlas", "Nova", "Kite", "Helix", "Verve", "Spark", "Echo", "Forge"];
const NAME_SUFFIXES = ["Pay", "Lend", "Bank", "AI", "Labs", "Cloud", "Works", "Sense", "Stack", "Flow", "Loop", "Hub", "X", "Tech", "Stream"];

const FOUNDER_FIRST = ["Arjun", "Priya", "Rohan", "Sneha", "Vikram", "Aditi", "Karan", "Meera", "Nikhil", "Ananya", "Rahul", "Divya", "Sameer", "Ishita"];
const FOUNDER_LAST = ["Sharma", "Mehta", "Iyer", "Kapoor", "Reddy", "Khan", "Singh", "Verma", "Bose", "Nair"];

function seededRand(seed: number) {
  let s = seed;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
}

function pick<T>(arr: readonly T[], r: () => number) {
  return arr[Math.floor(r() * arr.length)];
}

function generateStartups(count = 120): Startup[] {
  const r = seededRand(42);
  const list: Startup[] = [];
  for (let i = 0; i < count; i++) {
    const sect = pick(SECTORS, r);
    const subsector = pick(sect.sub, r);
    const name = `${pick(NAME_PREFIXES, r)}${pick(NAME_SUFFIXES, r)}${r() > 0.7 ? Math.floor(r() * 99) : ""}`;
    const bfsi = sect.s === "Fintech" ? 65 + Math.floor(r() * 35) : 20 + Math.floor(r() * 60);
    const priority = Math.floor((bfsi * 0.6 + r() * 40));
    const founders = Array.from({ length: 1 + Math.floor(r() * 2) }, () =>
      `${pick(FOUNDER_FIRST, r)} ${pick(FOUNDER_LAST, r)}`
    );
    const stage = pick(STAGES, r);
    const stageIdx = STAGES.indexOf(stage);
    const funding = Math.floor((stageIdx + 1) * (0.5 + r() * 4) * 1_000_000);
    const daysAgo = Math.floor(r() * 60);
    list.push({
      id: `stp_${i.toString().padStart(4, "0")}`,
      name,
      sector: sect.s,
      subsector,
      city: pick(CITIES, r),
      country: "India",
      fundingStage: stage,
      bfsiScore: bfsi,
      priorityScore: Math.min(100, priority),
      assignedTeam: pick(TEAMS, r),
      source: pick(SOURCES, r),
      lastUpdated: new Date(Date.now() - daysAgo * 86400000).toISOString(),
      status: pick(STATUSES, r),
      description: `${name} is building next-generation ${subsector.toLowerCase()} infrastructure for emerging markets, focused on scale, compliance and embedded financial workflows.`,
      website: `https://${name.toLowerCase()}.io`,
      founded: 2015 + Math.floor(r() * 9),
      employees: 5 + Math.floor(r() * 500),
      totalFundingUSD: funding,
      founders,
      tags: [sect.s, subsector, stage, r() > 0.5 ? "BFSI" : "Growth"],
      saved: r() > 0.78,
    });
  }
  return list;
}

export const STARTUPS = generateStartups();

export function getStartupById(id: string) {
  return STARTUPS.find((s) => s.id === id);
}

const INSIGHT_TITLES = [
  "Strong alignment with digital lending mandate",
  "Emerging traction in cross-border payments",
  "Regulatory exposure flagged in latest filing",
  "Potential partnership fit with Wealth Group",
  "Rapid hiring detected — scale phase",
  "Competitor raised Series B at 4x multiple",
];

export const INSIGHTS: AIInsight[] = STARTUPS.slice(0, 24).map((s, i) => ({
  id: `ins_${i}`,
  startupId: s.id,
  startupName: s.name,
  type: (["Opportunity", "Risk", "Trend", "Match"] as const)[i % 4],
  title: INSIGHT_TITLES[i % INSIGHT_TITLES.length],
  summary: `Our intelligence engine detected meaningful signals around ${s.name} in the ${s.subsector} category. Estimated relevance to ICICI Group portfolio strategy is high, with multiple converging indicators across hiring, funding and product velocity.`,
  confidence: 60 + Math.floor(Math.random() * 38),
  createdAt: new Date(Date.now() - i * 3_600_000).toISOString(),
}));

export const ASSIGNMENTS: Assignment[] = STARTUPS.slice(0, 28).map((s, i) => ({
  id: `asn_${i}`,
  startupId: s.id,
  startupName: s.name,
  assignee: ["Aarav Mehta", "Priya Nair", "Rohit Sen", "Kavya Iyer", "Manish Kapoor"][i % 5],
  team: s.assignedTeam,
  dueDate: new Date(Date.now() + (i - 10) * 86400000).toISOString(),
  priority: (["Low", "Medium", "High", "Critical"] as const)[i % 4],
  status: (["Open", "In Progress", "Blocked", "Done"] as const)[i % 4],
  createdAt: new Date(Date.now() - i * 86400000).toISOString(),
}));

export const WORKFLOWS: WorkflowRun[] = Array.from({ length: 18 }, (_, i) => ({
  id: `wf_${i}`,
  name: ["Crunchbase Sync", "BFSI Scoring", "Enrichment Pipeline", "Weekly Export", "News Ingestion"][i % 5],
  type: (["Ingestion", "Scoring", "Enrichment", "Export"] as const)[i % 4],
  status: (["Success", "Running", "Success", "Success", "Failed", "Queued"] as const)[i % 6],
  startedAt: new Date(Date.now() - i * 1_800_000).toISOString(),
  durationMs: 1200 + Math.floor(Math.random() * 60000),
  recordsProcessed: Math.floor(Math.random() * 5000),
}));

export const SOURCES_LIST: SourceFeed[] = [
  { id: "src_1", name: "Crunchbase", type: "API", status: "Healthy", lastSync: new Date(Date.now() - 600_000).toISOString(), recordsToday: 412, uptime: 99.98 },
  { id: "src_2", name: "Tracxn", type: "API", status: "Healthy", lastSync: new Date(Date.now() - 900_000).toISOString(), recordsToday: 287, uptime: 99.91 },
  { id: "src_3", name: "LinkedIn Insights", type: "Scraper", status: "Degraded", lastSync: new Date(Date.now() - 7_200_000).toISOString(), recordsToday: 91, uptime: 96.4 },
  { id: "src_4", name: "Partner Deal Flow", type: "Partner", status: "Healthy", lastSync: new Date(Date.now() - 86_400_000).toISOString(), recordsToday: 14, uptime: 100 },
  { id: "src_5", name: "News API", type: "API", status: "Healthy", lastSync: new Date(Date.now() - 300_000).toISOString(), recordsToday: 1242, uptime: 99.7 },
  { id: "src_6", name: "Legacy Scraper", type: "Scraper", status: "Down", lastSync: new Date(Date.now() - 172_800_000).toISOString(), recordsToday: 0, uptime: 81.2 },
];

export function getActivityForStartup(startupId: string): ActivityEvent[] {
  return Array.from({ length: 8 }, (_, i) => ({
    id: `act_${startupId}_${i}`,
    startupId,
    type: (["note", "status", "score", "assignment", "tag"] as const)[i % 5],
    actor: ["Aarav Mehta", "Priya Nair", "System", "Rohit Sen", "AI Engine"][i % 5],
    message: [
      "Added a research note on go-to-market strategy.",
      "Status updated to 'In Review'.",
      "BFSI relevance score recomputed to 82.",
      "Assigned to Digital Banking team.",
      "Tagged as 'High Priority Watchlist'.",
    ][i % 5],
    at: new Date(Date.now() - i * 7_200_000).toISOString(),
  }));
}

// Aggregations
export function sectorDistribution() {
  const map = new Map<string, number>();
  STARTUPS.forEach((s) => map.set(s.sector, (map.get(s.sector) ?? 0) + 1));
  return Array.from(map, ([name, value]) => ({ name, value }));
}

export function cityDistribution() {
  const map = new Map<string, number>();
  STARTUPS.forEach((s) => map.set(s.city, (map.get(s.city) ?? 0) + 1));
  return Array.from(map, ([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value);
}

export function stageTrends() {
  return STAGES.map((stage) => ({
    stage,
    count: STARTUPS.filter((s) => s.fundingStage === stage).length,
    avgFunding: Math.round(
      STARTUPS.filter((s) => s.fundingStage === stage).reduce((a, b) => a + b.totalFundingUSD, 0) /
        Math.max(1, STARTUPS.filter((s) => s.fundingStage === stage).length) / 1_000_000
    ),
  }));
}

export function bfsiDistribution() {
  const buckets = [
    { range: "0-20", min: 0, max: 20 },
    { range: "20-40", min: 20, max: 40 },
    { range: "40-60", min: 40, max: 60 },
    { range: "60-80", min: 60, max: 80 },
    { range: "80-100", min: 80, max: 101 },
  ];
  return buckets.map((b) => ({
    range: b.range,
    count: STARTUPS.filter((s) => s.bfsiScore >= b.min && s.bfsiScore < b.max).length,
  }));
}

export function pipelineFunnel() {
  return STATUSES.map((status) => ({
    stage: status,
    count: STARTUPS.filter((s) => s.status === status).length,
  }));
}
