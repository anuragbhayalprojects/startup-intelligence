import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Globe, Linkedin, Sparkles, Loader2, AlertTriangle, Calendar, ExternalLink, Newspaper } from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { Startup, StartupAnalysis } from "../types";

const formatUrl = (url: string | undefined | null): string => {
  if (!url) return "";
  const trimmed = url.trim();
  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }
  return `https://${trimmed}`;
};
const rawApiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const API_URL = rawApiUrl.endsWith("/") 
  ? (rawApiUrl.endsWith("/api/") ? rawApiUrl.slice(0, -1) : rawApiUrl + "api") 
  : (rawApiUrl.endsWith("/api") ? rawApiUrl : rawApiUrl + "/api");

export default function StartupDetails() {
  const { id } = useParams<{ id: string }>();
  const [startup, setStartup] = useState<Startup | null>(null);
  const [analysis, setAnalysis] = useState<StartupAnalysis | null>(null);
  const [recentNews, setRecentNews] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const response = await fetch(`${API_URL}/startup/${id}`);
        if (!response.ok) {
          throw new Error("Startup not found");
        }
        const data = await response.json();
        setStartup(data);

        // Use embedded news or fetch separately
        if (data.recent_news && Array.isArray(data.recent_news) && data.recent_news.length > 0) {
          setRecentNews(data.recent_news);
        }

        if (data.startup_analyses && data.startup_analyses.length > 0) {
          setAnalysis(data.startup_analyses[0].analysis_data);
        } else if (data.startup_analysis && data.startup_analysis.length > 0) {
          setAnalysis(data.startup_analysis[0].analysis_json || data.startup_analysis[0].analysis_data);
        }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, [id]);

  // Fallback separate fetch for news if not embedded
  useEffect(() => {
    if (recentNews.length > 0 || !id) return;
    fetch(`${API_URL}/startup/${id}/news`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data && Array.isArray(data.news)) {
          setRecentNews(data.news);
        }
      })
      .catch(() => {});
  }, [id, recentNews.length]);

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/analyze/${id}`, { method: "POST" });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Analysis failed");
      }
      const newAnalysis = await response.json();
      setAnalysis(newAnalysis.analysis_data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  if (isLoading) {
    return <div className="text-center py-20"><Loader2 className="h-8 w-8 animate-spin mx-auto" /></div>;
  }

  if (error && !startup) {
    return (
      <div className="text-center py-20">
        <AlertTriangle className="h-8 w-8 text-destructive mx-auto" />
        <h2 className="text-lg font-semibold mt-4">{error}</h2>
        <Link to="/startups" className="text-sm text-primary mt-2 inline-block">← Back to startups</Link>
      </div>
    );
  }

  if (!startup) {
    return null;
  }

  return (
    <>
      <Link to="/startups" className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1 mb-4">
        <ArrowLeft className="h-3 w-3" /> Back to startups
      </Link>

      <PageHeader
        title={startup.startup_name}
        description={startup.description}
        action={
          <div className="flex items-center gap-2">
            <a href={startup.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 h-9 px-3 rounded-md border border-border text-sm hover:bg-muted">
              <Globe className="h-4 w-4" /> Source
            </a>
            <button onClick={handleAnalyze} disabled={isAnalyzing} className="inline-flex items-center gap-2 h-9 px-3 rounded-md bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-50">
              {isAnalyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} 
              {isAnalyzing ? "Analyzing..." : "Analyze Startup"}
            </button>
          </div>
        }
      />

      {error && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive-foreground p-4 rounded-md mb-4">
          <h4 className="font-semibold">Analysis Error</h4>
          <p className="text-sm">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <SectionCard title="Startup Details" className="lg:col-span-2">
          <p className="text-sm text-muted-foreground">{startup.description}</p>
        </SectionCard>
        
        <SectionCard title="Source">
          <p className="text-sm">{startup.source}</p>
          <p className="text-xs text-muted-foreground">Data retrieved from {startup.source}</p>
        </SectionCard>
      </div>

      {/* Recent News Feed */}
      <SectionCard title="" className="mt-4">
        <div className="space-y-3">
          <h3 className="text-sm font-bold flex items-center gap-2">
            <Newspaper className="h-4 w-4 text-amber-500" />
            Recent News & Updates
          </h3>

          {recentNews.length > 0 ? (
            <div className="space-y-3">
              {recentNews.map((item: any, idx: number) => {
                const dateStr = item.published_at
                  ? new Date(item.published_at).toLocaleDateString("en-IN", {
                      day: "numeric", month: "short", year: "numeric"
                    })
                  : "";
                return (
                  <div
                    key={item.id || idx}
                    className="p-3 bg-muted/40 border border-border rounded-lg space-y-1.5"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-xs font-semibold leading-snug flex-1">{item.headline}</p>
                      {dateStr && (
                        <span className="flex items-center gap-1 text-[10px] text-muted-foreground font-mono whitespace-nowrap">
                          <Calendar className="h-3 w-3" />{dateStr}
                        </span>
                      )}
                    </div>
                    {item.summary && (
                      <p className="text-xs text-muted-foreground leading-relaxed">{item.summary}</p>
                    )}
                    {item.source_url && (
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline font-medium"
                      >
                        {item.source || "Read article"} <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                );
              })}
            </div>
          ) : startup.description ? (
            <p className="text-sm text-muted-foreground leading-relaxed">{startup.description}</p>
          ) : (
            <p className="text-xs text-muted-foreground italic">
              No news history yet. Events will appear here after discovery runs.
            </p>
          )}
        </div>
      </SectionCard>

      {analysis ? (
        <AnalysisSection analysis={analysis} />
      ) : (
        <div className="text-center py-12 border border-dashed rounded-lg mt-4">
          <Sparkles className="h-6 w-6 text-muted-foreground mx-auto"/>
          <p className="mt-2 text-sm font-medium text-muted-foreground">No analysis available for this startup.</p>
          <p className="mt-1 text-xs text-muted-foreground">Click the 'Analyze Startup' button to generate one.</p>
        </div>
      )}
    </>
  );
}

const AnalysisSection = ({ analysis }: { analysis: any }) => {
  return (
    <div className="mt-4 space-y-4">
      <SectionCard title="AI Analysis Summary">
        <p className="text-sm"><strong>One-Liner:</strong> {analysis?.summary?.one_liner || "N/A"}</p>
        <p className="text-sm mt-2"><strong>Business Model:</strong> {analysis?.summary?.business_model || "N/A"}</p>
        <p className="text-sm mt-2"><strong>Target Audience:</strong> {analysis?.summary?.target_audience || "N/A"}</p>
      </SectionCard>

      {Array.isArray(analysis?.founders) && analysis.founders.length > 0 && (
        <SectionCard title="Founding Leadership">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {analysis.founders.map((founder: any, index: number) => (
              <div key={index} className="p-4 bg-muted/30 rounded-lg border border-border flex items-start gap-3">
                <div className="w-9 h-9 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs uppercase flex-shrink-0">
                  {founder?.name ? founder.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2) : "FD"}
                </div>
                <div className="space-y-1 text-left">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="font-semibold text-sm text-foreground">{founder?.name || "Founder"}</span>
                    {founder?.linkedin_url && (
                      <a
                        href={formatUrl(founder.linkedin_url)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:text-blue-600 inline-flex items-center"
                        title="LinkedIn Profile"
                      >
                        <Linkedin className="h-3.5 w-3.5" />
                      </a>
                    )}
                    <span className="text-[10px] bg-secondary text-secondary-foreground px-2 py-0.5 rounded font-medium">{founder?.role || "Founder"}</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">{founder?.brief_details || ""}</p>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SectionCard title="BFSI Relevance">
          <p className="text-sm"><strong>Relevant:</strong> {analysis?.bfsi_relevance?.is_relevant ? 'Yes' : 'No'}</p>
          <p className="text-sm mt-2"><strong>Relevance Score:</strong> {analysis?.bfsi_relevance?.relevance_score || 0}/100</p>
        </SectionCard>
        <SectionCard title="Strategic Fit">
          <p className="text-sm"><strong>Enterprise Readiness:</strong> {analysis?.strategic_fit?.enterprise_readiness || 0}/100</p>
          <p className="text-sm mt-2"><strong>Integration Feasibility:</strong> {analysis?.strategic_fit?.integration_feasibility || "N/A"}</p>
        </SectionCard>
      </div>

      <SectionCard title="Use Cases">
        <div className="space-y-3">
          {(analysis?.bfsi_relevance?.use_cases || []).map((uc: any, index: number) => (
            <div key={index} className="p-3 rounded-md bg-muted/50">
              <p className="font-semibold text-sm">{uc?.icici_entity || "N/A"}</p>
              <p className="text-sm mt-1"><strong>Use Case:</strong> {uc?.use_case || "N/A"}</p>
              <p className="text-sm mt-1"><strong>Potential Impact:</strong> {uc?.potential_impact || "N/A"}</p>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Scoring & Classification">
        <p className="text-sm"><strong>Overall Priority Score:</strong> {analysis?.scoring?.overall_priority_score || 0}/100</p>
        <p className="text-sm mt-2"><strong>Risk Assessment:</strong> {Array.isArray(analysis?.scoring?.risk_assessment) ? analysis.scoring.risk_assessment.join(", ") : analysis?.scoring?.risk_assessment || "N/A"}</p>
        <p className="text-sm mt-4"><strong>Industry:</strong> {analysis?.classification?.industry || "N/A"}</p>
        <p className="text-sm mt-1"><strong>Sector:</strong> {analysis?.classification?.sector || "N/A"}</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {(analysis?.classification?.tags || []).map((tag: string) => <StatusBadge key={tag} tone="info">{tag}</StatusBadge>)}
        </div>
      </SectionCard>
    </div>
  );
};
