import { useState, useEffect, useRef } from 'react';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { Loader2, CheckCircle, AlertTriangle, Search, Filter, Plus, Terminal, Globe, Activity, Wifi, WifiOff } from 'lucide-react';

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

interface ScrapingProps {
  scrapingActive: boolean;
  scrapingLogs: string[];
  scrapingProcessed: string[];
  scrapingCurrentStep: string;
  scrapingTarget: number;
  scrapingProgress: number;
  onStartScrape: (sources: string[], limit: number, filters: any) => Promise<{ success?: boolean; error?: string }>;
}

export default function Scraping({
  scrapingActive,
  scrapingLogs,
  scrapingProcessed,
  scrapingCurrentStep,
  scrapingTarget,
  scrapingProgress,
  onStartScrape
}: ScrapingProps) {
  // Configured Sources
  const [sources, setSources] = useState<any[]>([]);
  const [selectedSources, setSelectedSources] = useState<string[]>(["Inc42"]);
  const [limit, setLimit] = useState(5);
  const [industry, setIndustry] = useState("Financial Services");
  const [sector, setSector] = useState("");
  const [subsector, setSubsector] = useState("");
  const [keywords, setKeywords] = useState("");

  // Add Source UI states
  const [showAddForm, setShowAddForm] = useState(false);
  const [newSourceName, setNewSourceName] = useState("");
  const [newSourceUrl, setNewSourceUrl] = useState("");
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [addSuccess, setAddSuccess] = useState<string | null>(null);

  // Local route trigger state (only for showing trigger errors)
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const terminalRef = useRef<HTMLDivElement | null>(null);

  // Fetch registered sources on load
  const fetchSources = async () => {
    try {
      const response = await fetch(`${API_URL}/scrape/sources`);
      if (response.ok) {
        const data = await response.json();
        setSources(data);
      }
    } catch (err) {
      console.warn("Could not fetch discovery sources list:", err);
      // fallback static options if backend is offline
      setSources([
        { name: "Inc42", url: "https://inc42.com/feed/", is_custom: false },
        { name: "Entrackr", url: "https://entrackr.com/rss", is_custom: false }
      ]);
    }
  };

  useEffect(() => {
    fetchSources();
  }, []);

  // Auto-scroll terminal log console to bottom
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [scrapingLogs]);

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
    setError(null);
    setSuccess(null);

    const filters = {
      industry: selectedSources.includes("Custom Web Search") ? industry : "",
      sector: selectedSources.includes("Custom Web Search") ? sector : "",
      subsector: selectedSources.includes("Custom Web Search") ? subsector : "",
      keywords: selectedSources.includes("Custom Web Search") ? keywords : ""
    };

    const result = await onStartScrape(selectedSources, limit, filters);
    if (result.error) {
      setError(result.error);
    } else {
      setSuccess("Scraper pipeline initiated successfully.");
    }
  };

  const handleAddSourceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSourceName.trim() || !newSourceUrl.trim()) {
      setAddError("Please fill out both target source name and feed URL.");
      return;
    }
    setAddLoading(true);
    setAddError(null);
    setAddSuccess(null);

    try {
      const response = await fetch(`${API_URL}/scrape/sources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newSourceName.trim(),
          url: newSourceUrl.trim()
        })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to save discovery target source.");
      }
      setAddSuccess(`Successfully registered custom source "${newSourceName}"!`);
      setNewSourceName("");
      setNewSourceUrl("");
      setShowAddForm(false);
      fetchSources();
      
      // Auto select the new source
      setSelectedSources(prev => [...prev, data.name || newSourceName]);
    } catch (err: any) {
      setAddError(err.message || "Failed validating custom source feed link.");
    } finally {
      setAddLoading(false);
    }
  };

  const isCustomActive = selectedSources.includes("Custom Web Search");

  // Combine loaded backend sources with Custom Web Search fallback option
  const allAvailableSources = [
    ...sources,
    { name: "Custom Web Search", url: "", is_custom: false }
  ];

  // Calculate progress percent
  const progressPercent = scrapingTarget > 0 
    ? Math.min(Math.round((scrapingProgress / scrapingTarget) * 100), 100)
    : 0;

  return (
    <div className="space-y-6 text-left">
      <PageHeader 
        title="Discovery & Scraper Console" 
        description="Configure target RSS updates, register custom feeds, or run AI-driven web searches to automatically discover and enrich startups."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Scraper Configuration panel */}
        <div className="lg:col-span-2 space-y-6">
          <SectionCard title="Discovery Parameters">
            <div className="space-y-6 text-left">
              
              {/* Checklist header with add target option */}
              <div className="flex justify-between items-center mb-1">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Target Discovery Sources
                </label>
                <button
                  onClick={() => {
                    setShowAddForm(!showAddForm);
                    setAddError(null);
                    setAddSuccess(null);
                  }}
                  className="text-xs text-amber-600 hover:text-amber-700 font-bold flex items-center gap-1 hover:underline transition-all"
                >
                  <Plus size={14} />
                  <span>Register Custom RSS/Feed</span>
                </button>
              </div>

              {/* Add Custom Feed Form Overlay/Block */}
              {showAddForm && (
                <form 
                  onSubmit={handleAddSourceSubmit}
                  className="p-4 bg-slate-50 rounded-xl border border-slate-200/80 space-y-3 animate-fade-in text-left"
                >
                  <div className="flex items-center gap-2 pb-1.5 border-b border-slate-200">
                    <Globe size={14} className="text-amber-500" />
                    <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                      Add Custom Ingestion Target
                    </h4>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                        Source Name
                      </label>
                      <input 
                        type="text"
                        value={newSourceName}
                        onChange={(e) => setNewSourceName(e.target.value)}
                        placeholder="e.g. Inc42 Fintech Feed"
                        className="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg p-2 focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none transition-all"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                        Feed URL (RSS XML Link or Homepage URL)
                      </label>
                      <input 
                        type="url"
                        value={newSourceUrl}
                        onChange={(e) => setNewSourceUrl(e.target.value)}
                        placeholder="e.g. https://inc42.com/feed/"
                        className="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg p-2 focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none transition-all"
                        required
                      />
                    </div>
                  </div>

                  {addError && (
                    <p className="text-[11px] font-semibold text-red-600 flex items-center gap-1">
                      <AlertTriangle size={12} />
                      <span>{addError}</span>
                    </p>
                  )}

                  {addSuccess && (
                    <p className="text-[11px] font-semibold text-emerald-600 flex items-center gap-1">
                      <CheckCircle size={12} />
                      <span>{addSuccess}</span>
                    </p>
                  )}

                  <div className="flex justify-end gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => setShowAddForm(false)}
                      className="px-3 py-1.5 bg-slate-200 hover:bg-slate-250 text-slate-700 text-xs font-bold rounded-lg transition-all"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={addLoading}
                      className="px-4 py-1.5 bg-amber-500 hover:bg-amber-600 disabled:bg-slate-350 text-white text-xs font-bold rounded-lg flex items-center gap-1.5 transition-all shadow-sm"
                    >
                      {addLoading ? (
                        <>
                          <Loader2 size={13} className="animate-spin" />
                          <span>Testing Reachability...</span>
                        </>
                      ) : (
                        <span>Verify & Add Source</span>
                      )}
                    </button>
                  </div>
                </form>
              )}

              {/* Discovery Sources Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {allAvailableSources.map((src) => (
                  <label 
                    key={src.name} 
                    className={`flex items-center gap-3 p-3 rounded-xl border text-xs font-semibold cursor-pointer transition-all ${
                      selectedSources.includes(src.name)
                        ? "bg-amber-50 border-amber-300 text-amber-900 shadow-sm"
                        : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    <input 
                      type="checkbox" 
                      checked={selectedSources.includes(src.name)} 
                      onChange={() => handleSourceToggle(src.name)}
                      className="rounded text-amber-500 focus:ring-amber-400 border-slate-350"
                      disabled={scrapingActive}
                    />
                    <div className="flex flex-col text-left">
                      <span className="font-bold">{src.name}</span>
                      {src.url && (
                        <span className="text-[10px] text-slate-400 font-medium truncate max-w-[150px]">
                          {src.url}
                        </span>
                      )}
                    </div>
                  </label>
                ))}
              </div>

              {/* Discovery limit count input */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label htmlFor="limit" className="block text-xs font-bold text-slate-500 uppercase tracking-wider">
                    Discovery Target Volume Limit
                  </label>
                  <span className="text-xs bg-slate-100 text-slate-600 font-bold px-2 py-0.5 rounded font-mono">
                    {limit} Startups
                  </span>
                </div>
                <input 
                  id="limit"
                  type="range"
                  value={limit}
                  onChange={(e) => setLimit(parseInt(e.target.value, 10))}
                  min="1"
                  max="30"
                  disabled={scrapingActive}
                  className="w-full accent-amber-500 h-1.5 bg-slate-200 rounded-lg cursor-pointer"
                />
                <span className="text-[10px] text-slate-400">
                  The scraper continues running articles until it successfully enriches this number of new fintech ventures.
                </span>
              </div>

              {/* Custom Search Query parameters panel */}
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
                        disabled={scrapingActive}
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
                        disabled={scrapingActive}
                        placeholder="e.g. InsurTech, WealthTech"
                        className="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg p-2.5 focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none transition-all"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-600 mb-1">Sub Sector (e.g. Claims Automation)</label>
                      <input 
                        type="text" 
                        value={subsector}
                        onChange={(e) => setSubsector(e.target.value)}
                        disabled={scrapingActive}
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
                        disabled={scrapingActive}
                        placeholder="e.g. AI-driven fraud detection"
                        className="w-full bg-white border border-slate-200 text-slate-800 text-xs rounded-lg p-2.5 focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none transition-all"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Scrape trigger action button */}
              <div className="flex justify-end pt-2 border-t border-slate-100">
                <button 
                  onClick={handleScrape} 
                  disabled={scrapingActive || selectedSources.length === 0} 
                  className="px-6 py-3 bg-amber-500 hover:bg-amber-600 disabled:bg-slate-300 disabled:cursor-not-allowed text-white text-xs font-bold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-amber-500/10 active:scale-95 transition-all"
                >
                  {scrapingActive ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin"/>
                      <span>Running Discovery Thread...</span>
                    </>
                  ) : (
                    <>
                      <Search size={15}/>
                      <span>Trigger Venture Discovery</span>
                    </>
                  )}
                </button>
              </div>

              {/* Status notifications */}
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs font-semibold rounded-lg flex items-center gap-2">
                  <AlertTriangle size={14} />
                  <span>{error}</span>
                </div>
              )}

              {success && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold rounded-lg flex items-center gap-2">
                  <CheckCircle size={14} className="text-emerald-500" />
                  <span>{success}</span>
                </div>
              )}

            </div>
          </SectionCard>
        </div>

        {/* Info panel */}
        <div className="space-y-6">
          <SectionCard title="Discovery Pipeline Info">
            <div className="text-slate-600 text-xs space-y-4 text-left">
              <p>
                The **Discovery Pipeline** crawls feeds in the background and runs name-extraction prompts on local models:
              </p>
              <ol className="list-decimal pl-4 space-y-2">
                <li>
                  <strong>Background Scrape Ingestion</strong>
                  <br/>
                  FastAPI routes the scraping pipeline as a non-blocking worker thread. Switch tabs at any time without terminating the crawl.
                </li>
                <li>
                  <strong>Target Count Discovery Limit</strong>
                  <br/>
                  The pipeline continues analyzing articles and query results until it achieves your target number of newly registered/enriched database entries.
                </li>
              </ol>
              <p className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-[10px] text-slate-400">
                Note: Operates on your local <strong>qwen2.5:3b</strong> server. Dynamic search queries and document classification may take 10-30 seconds per venture.
              </p>
            </div>
          </SectionCard>
        </div>
      </div>

      {/* Terminal log stream panel & Progress bars */}
      {(scrapingActive || scrapingLogs.length > 0) && (
        <div className="grid grid-cols-1 gap-6 animate-fade-in">
          <SectionCard title="Background Task Logs Console">
            <div className="space-y-4 text-left">
              
              {/* Progress Summary header */}
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-slate-50 border border-slate-200/80 p-4 rounded-xl">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Activity className={`h-4.5 w-4.5 ${scrapingActive ? "text-amber-500 animate-pulse" : "text-slate-400"}`} />
                    <span className="font-bold text-xs text-slate-800">
                      STATUS: {scrapingActive ? "CRAWLING & EXTRACTING" : "IDLE / FINISHED"}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 font-semibold">
                    Current Action: <span className="text-slate-850 font-bold">{scrapingCurrentStep}</span>
                  </p>
                </div>

                <div className="w-full sm:w-64 space-y-1.5">
                  <div className="flex justify-between items-center text-[10px] text-slate-500 font-bold uppercase">
                    <span>Discovered Ventures</span>
                    <span>{scrapingProgress} / {scrapingTarget}</span>
                  </div>
                  <div className="h-2 w-full bg-slate-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-amber-500 transition-all duration-550 ease-out" 
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Logs terminal box */}
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs text-slate-500 font-bold uppercase tracking-wide">
                  <Terminal size={14} />
                  <span>Interactive Log Console Stream</span>
                  {scrapingActive && (
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-ping"></span>
                  )}
                </div>

                <div 
                  ref={terminalRef}
                  className="bg-slate-900 border border-slate-800 rounded-xl p-4 h-64 overflow-y-auto font-mono text-[11px] leading-relaxed text-slate-350 shadow-inner select-text custom-scrollbar"
                  style={{
                    boxShadow: "inset 0 4px 6px -1px rgb(0 0 0 / 0.2), inset 0 2px 4px -2px rgb(0 0 0 / 0.2)"
                  }}
                >
                  {scrapingLogs.length === 0 ? (
                    <div className="text-slate-500 italic h-full flex items-center justify-center">
                      Waiting for discovery run tasks to output log buffers...
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {scrapingLogs.map((log, index) => {
                        // Color styling for logs
                        let lineClass = "text-slate-300";
                        if (log.includes("✨") || log.includes("✅") || log.includes("Successfully")) {
                          lineClass = "text-emerald-400 font-semibold";
                        } else if (log.includes("⚠️") || log.includes("Skipping")) {
                          lineClass = "text-amber-400/90";
                        } else if (log.includes("❌") || log.includes("Failed")) {
                          lineClass = "text-rose-400 font-semibold";
                        } else if (log.includes("🔍") || log.includes("Searching")) {
                          lineClass = "text-sky-400";
                        }
                        
                        return (
                          <div key={index} className={`whitespace-pre-wrap ${lineClass}`}>
                            {log}
                          </div>
                        );
                      })}
                      
                      {/* Blinking block cursor when active */}
                      {scrapingActive && (
                        <div className="inline-block h-3 w-1.5 bg-amber-500 animate-pulse ml-0.5 mt-1" />
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Discovered Startups Checklist summary */}
              {scrapingProcessed.length > 0 && (
                <div className="p-4 bg-emerald-50 border border-emerald-100 rounded-xl space-y-2 text-left">
                  <h5 className="text-xs font-bold text-emerald-950 uppercase tracking-wide">
                    Ventures Discovered in this Session ({scrapingProcessed.length})
                  </h5>
                  <div className="flex flex-wrap gap-2">
                    {scrapingProcessed.map((s, idx) => (
                      <span 
                        key={idx} 
                        className="px-2.5 py-1 bg-white border border-emerald-200 text-emerald-900 text-[11px] font-bold rounded-lg shadow-sm flex items-center gap-1.5 animate-scale-up"
                      >
                        <CheckCircle size={12} className="text-emerald-500" />
                        <span>{s}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

            </div>
          </SectionCard>
        </div>
      )}
    </div>
  );
}
