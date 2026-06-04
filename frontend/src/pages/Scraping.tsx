import { useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { Loader2, CheckCircle, AlertTriangle, Search, Filter } from 'lucide-react';

const rawApiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const API_URL = rawApiUrl.endsWith("/") 
  ? (rawApiUrl.endsWith("/api/") ? rawApiUrl.slice(0, -1) : rawApiUrl + "api") 
  : (rawApiUrl.endsWith("/api") ? rawApiUrl : rawApiUrl + "/api");

const INDUSTRIES = [
  "Financial Services",
  "Artificial Intelligence",
  "Enterprise Software",
  "Cybersecurity",
  "Healthcare & Life Sciences",
  "Education",
  "Commerce & Retail",
  "Consumer Internet",
  "Real Estate & Construction",
  "Transportation & Logistics",
  "Manufacturing & Industrial",
  "Energy & Sustainability",
  "Agriculture & Food",
  "Telecom & Connectivity",
  "Government & Defense",
  "DeepTech"
];

export default function Scraping() {
    const [selectedSources, setSelectedSources] = useState<string[]>(["Inc42"]);
    const [limit, setLimit] = useState(5);
    const [industry, setIndustry] = useState("Financial Services");
    const [sector, setSector] = useState("");
    const [subsector, setSubsector] = useState("");
    const [keywords, setKeywords] = useState("");
    
    const [isLoading, setIsLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    const handleSourceToggle = (src: string) => {
        if (selectedSources.includes(src)) {
            setSelectedSources(selectedSources.filter(s => s !== src));
        } else {
            setSelectedSources([...selectedSources, src]);
        }
    };

    const handleScrape = async () => {
        if (selectedSources.length === 0) {
            setError("Please select at least one source.");
            return;
        }
        
        setIsLoading(true);
        setResult(null);
        setError(null);

        try {
            const response = await fetch(`${API_URL}/scrape`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    sources: selectedSources, 
                    limit: limit,
                    industry: selectedSources.includes("Custom Web Search") ? industry : "",
                    sector: selectedSources.includes("Custom Web Search") ? sector : "",
                    subsector: selectedSources.includes("Custom Web Search") ? subsector : "",
                    keywords: selectedSources.includes("Custom Web Search") ? keywords : ""
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Discovery pipeline failed.');
            }

            setResult(data);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const isCustomActive = selectedSources.includes("Custom Web Search");

    return (
        <div className="space-y-6">
            <PageHeader title="Discovery & Scraper Console" description="Run automatic scrapers or trigger custom web searches to find and enrich new startups."/>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Configuration Card */}
                <div className="lg:col-span-2 space-y-6">
                    <SectionCard title="Discovery Parameters">
                        <div className="space-y-6">
                            
                            {/* Sources Checkboxes */}
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                                    Target Discovery Sources
                                </label>
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    {["Inc42", "Entrackr", "Custom Web Search"].map((src) => (
                                        <label 
                                            key={src} 
                                            className={`flex items-center gap-3 p-3 rounded-xl border text-xs font-semibold cursor-pointer transition-all ${
                                                selectedSources.includes(src)
                                                    ? "bg-amber-50 border-amber-300 text-amber-900 shadow-sm"
                                                    : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
                                            }`}
                                        >
                                            <input 
                                                type="checkbox" 
                                                checked={selectedSources.includes(src)} 
                                                onChange={() => handleSourceToggle(src)}
                                                className="rounded text-amber-500 focus:ring-amber-400 border-slate-350"
                                            />
                                            <span>{src}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            {/* Startups Scrape Count Limit */}
                            <div>
                                <div className="flex justify-between items-center mb-1">
                                    <label htmlFor="limit" className="block text-xs font-bold text-slate-500 uppercase tracking-wider">
                                        Discovery Volume Limit
                                    </label>
                                    <span className="text-xs bg-slate-100 text-slate-600 font-bold px-2 py-0.5 rounded font-mono">
                                        {limit} Startups / Articles
                                    </span>
                                </div>
                                <input 
                                    id="limit"
                                    type="range"
                                    value={limit}
                                    onChange={(e) => setLimit(parseInt(e.target.value, 10))}
                                    min="1"
                                    max="20"
                                    className="w-full accent-amber-500 h-1.5 bg-slate-200 rounded-lg cursor-pointer"
                                />
                                <span className="text-[10px] text-slate-400">Limits discovery runs to conserve Ollama model inference speed.</span>
                            </div>

                            {/* Custom Search Query Builder Fields */}
                            {isCustomActive && (
                                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/80 space-y-4 animate-fade-in">
                                    <div className="flex items-center gap-2 border-b border-slate-200 pb-2 mb-2">
                                        <Filter size={14} className="text-amber-500" />
                                        <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                                            Custom Web Search Criteria
                                        </h4>
                                    </div>
                                    
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-xs font-semibold text-slate-600 mb-1">Target Industry</label>
                                            <select 
                                                value={industry} 
                                                onChange={(e) => setIndustry(e.target.value)}
                                                className="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg p-2.5 focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none transition-all"
                                            >
                                                {INDUSTRIES.map(ind => (
                                                    <option key={ind} value={ind}>{ind}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-xs font-semibold text-slate-600 mb-1">Sector (e.g. InsurTech)</label>
                                            <input 
                                                type="text" 
                                                value={sector}
                                                onChange={(e) => setSector(e.target.value)}
                                                placeholder="e.g. InsurTech, WealthTech"
                                                className="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg p-2.5 focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none transition-all"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-semibold text-slate-600 mb-1">Sub Sector (e.g. UPI Infrastructure)</label>
                                            <input 
                                                type="text" 
                                                value={subsector}
                                                onChange={(e) => setSubsector(e.target.value)}
                                                placeholder="e.g. Claims Automation"
                                                className="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg p-2.5 focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none transition-all"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-semibold text-slate-600 mb-1">Custom Keywords</label>
                                            <input 
                                                type="text" 
                                                value={keywords}
                                                onChange={(e) => setKeywords(e.target.value)}
                                                placeholder="e.g. AI-driven fraud detection"
                                                className="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg p-2.5 focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none transition-all"
                                            />
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Trigger Button */}
                            <div className="flex justify-end pt-2 border-t border-slate-100">
                                <button 
                                    onClick={handleScrape} 
                                    disabled={isLoading || selectedSources.length === 0} 
                                    className="px-6 py-3 bg-amber-500 hover:bg-amber-600 disabled:bg-slate-300 disabled:cursor-not-allowed text-white text-xs font-bold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-amber-500/10 active:scale-95 transition-all"
                                >
                                    {isLoading ? (
                                        <>
                                            <Loader2 className="h-4 w-4 animate-spin"/>
                                            <span>Processing Pipelines...</span>
                                        </>
                                    ) : (
                                        <>
                                            <Search size={15}/>
                                            <span>Trigger Venture Discovery</span>
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    </SectionCard>
                </div>

                {/* Info Panel / Results Card */}
                <div className="space-y-6">
                    <SectionCard title="Discovery Pipeline Info">
                        <div className="text-slate-600 text-xs space-y-4">
                            <p>
                                The **Discovery Pipeline** runs in two distinct phases powered by our local AI analysis models:
                            </p>
                            <ol className="list-decimal pl-4 space-y-2">
                                <li>
                                    <strong>Pass 1: Name Discovery</strong>
                                    <br/>
                                    Scraped headlines or web search updates are parsed to identify and isolate *all* startup brand names mentioned.
                                </li>
                                <li>
                                    <strong>Pass 2: Attribute Enrichment</strong>
                                    <br/>
                                    Each verified startup runs targeted web queries on Crunchbase, PitchBook, and Tracxn to extract co-founder names, website URLs, and investment rounds.
                                </li>
                            </ol>
                            <p className="p-3 bg-slate-50 border border-slate-250/70 rounded-lg text-[10px] text-slate-400">
                                Note: Runs on a local <strong>qwen2.5:3b</strong> instance. Large volumes may take several seconds.
                            </p>
                        </div>
                    </SectionCard>
                </div>
            </div>

            {/* Results Renders */}
            {result && (
                 <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl shadow-sm animate-fade-in">
                    <div className="flex gap-3">
                        <CheckCircle className="h-5 w-5 text-emerald-600 flex-shrink-0 mt-0.5"/>
                        <div>
                            <h4 className="font-bold text-sm text-emerald-900">Discovery Run Completed</h4>
                            <p className="text-xs text-emerald-800 mt-1">{result.message}</p>
                        </div>
                    </div>
                 </div>
            )}

            {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-xl shadow-sm animate-fade-in">
                    <div className="flex gap-3">
                        <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5"/>
                        <div>
                            <h4 className="font-bold text-sm text-red-900">Pipeline Execution Error</h4>
                            <p className="text-xs text-red-800 mt-1">{error}</p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
