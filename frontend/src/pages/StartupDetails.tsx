import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Globe, Users, Calendar, MapPin, DollarSign, Linkedin, Sparkles, Loader2, AlertTriangle } from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { formatUSD } from "../lib/format";
import { Startup, StartupAnalysis } from "../types";

const API_URL = import.meta.env.VITE_API_URL;

export default function StartupDetails() {
  const { id } = useParams<{ id: string }>();
  const [startup, setStartup] = useState<Startup | null>(null);
  const [analysis, setAnalysis] = useState<StartupAnalysis | null>(null);
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
        if (data.startup_analyses && data.startup_analyses.length > 0) {
          setAnalysis(data.startup_analyses[0].analysis_data);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, [id]);

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
    } catch (err) {
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
    return null; // Or a more specific not found component
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

const AnalysisSection = ({ analysis }: { analysis: StartupAnalysis }) => {
    return (
        <div className="mt-4 space-y-4">
            <SectionCard title="AI Analysis Summary">
                <p className="text-sm"><strong>One-Liner:</strong> {analysis.summary.one_liner}</p>
                <p className="text-sm mt-2"><strong>Business Model:</strong> {analysis.summary.business_model}</p>
                <p className="text-sm mt-2"><strong>Target Audience:</strong> {analysis.summary.target_audience}</p>
            </SectionCard>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <SectionCard title="BFSI Relevance">
                    <p className="text-sm"><strong>Relevant:</strong> {analysis.bfsi_relevance.is_relevant ? 'Yes' : 'No'}</p>
                    <p className="text-sm mt-2"><strong>Relevance Score:</strong> {analysis.bfsi_relevance.relevance_score}/100</p>
                </SectionCard>
                <SectionCard title="Strategic Fit">
                    <p className="text-sm"><strong>Enterprise Readiness:</strong> {analysis.strategic_fit.enterprise_readiness}/100</p>
                    <p className="text-sm mt-2"><strong>Integration Feasibility:</strong> {analysis.strategic_fit.integration_feasibility}</p>
                </SectionCard>
            </div>

             <SectionCard title="Use Cases">
                <div className="space-y-3">
                    {analysis.bfsi_relevance.use_cases.map((uc, index) => (
                        <div key={index} className="p-3 rounded-md bg-muted/50">
                            <p className="font-semibold text-sm">{uc.icici_entity}</p>
                            <p className="text-sm mt-1"><strong>Use Case:</strong> {uc.use_case}</p>
                            <p className="text-sm mt-1"><strong>Potential Impact:</strong> {uc.potential_impact}</p>
                        </div>
                    ))}
                </div>
            </SectionCard>

            <SectionCard title="Scoring & Classification">
                <p className="text-sm"><strong>Overall Priority Score:</strong> {analysis.scoring.overall_priority_score}/100</p>
                 <p className="text-sm mt-2"><strong>Risk Assessment:</strong> {analysis.scoring.risk_assessment}</p>
                <p className="text-sm mt-4"><strong>Primary Sector:</strong> {analysis.classification.primary_sector}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                    {analysis.classification.sub_sectors.map(tag => <StatusBadge key={tag} tone="info">{tag}</StatusBadge>)}
                </div>
            </SectionCard>
        </div>
    )
}
