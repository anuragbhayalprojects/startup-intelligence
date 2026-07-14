import React, { useState, useEffect, useRef } from "react";
import {
  Globe,
  Search,
  Filter,
  RefreshCw,
  Mail,
  Plus,
  Calendar,
  Layers,
  ChevronRight,
  BookOpen,
  CornerDownRight,
  Loader2,
  AlertCircle,
  X,
  Sliders,
  Terminal
} from "lucide-react";
import { NewsArticle, NewsSource, Startup } from "../types";
import NewsDrawer from "../components/NewsDrawer";
import AddSourceModal from "../components/AddSourceModal";
import { SourceLogo } from "../components/SourceLogo";

interface NewsDashboardProps {
  apiUrl: string;
  onSelectStartupByName: (name: string) => void;
}

export default function NewsDashboard({ apiUrl, onSelectStartupByName }: NewsDashboardProps) {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [sources, setSources] = useState<NewsSource[]>([]);
  const [industries, setIndustries] = useState<string[]>([]);
  
  // Loading states
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [sendingDigest, setSendingDigest] = useState(false);
  const [showAddSource, setShowAddSource] = useState(false);
  const [showSyncModal, setShowSyncModal] = useState(false);
  
  // Sync Status Polling
  const [actionStartup, setActionStartup] = useState<{ name: string; articleId: number } | null>(null);

  const handleResolveStartup = async (startupName: string, articleId: number, enrich: boolean) => {
    setActionStartup(null);
    try {
      const res = await fetch(`${apiUrl}/news/resolve-startup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          article_id: articleId,
          startup_name: startupName,
          enrich: enrich
        })
      });
      
      if (res.ok) {
        if (enrich) {
          alert(`Startup "${startupName}" added successfully. Full AI Agent enrichment has been launched in the background!`);
        } else {
          alert(`Startup "${startupName}" added to the workspace repository with basic details.`);
        }
        fetchArticles();
      } else {
        const err = await res.json();
        alert(`Failed to add startup: ${err.detail || "Unknown error"}`);
      }
    } catch (e) {
      console.error(e);
      alert("Failed to connect to backend server.");
    }
  };

  // Sync Status Polling
  const [syncStatus, setSyncStatus] = useState<{
    active: boolean;
    current_step: string;
    discovered_count: number;
    logs?: string[];
    last_news_sync?: {
      completed_at: string;
      processed_count: number;
      saved_count: number;
      articles: string[];
    } | null;
  } | null>(null);
  const [showSyncSuccessBanner, setShowSyncSuccessBanner] = useState(false);
  
  // Interactive console log stream variables
  const newsTerminalRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (newsTerminalRef.current) {
      newsTerminalRef.current.scrollTop = newsTerminalRef.current.scrollHeight;
    }
  }, [syncStatus?.logs]);
  
  // Drawer state
  const [selectedArticle, setSelectedArticle] = useState<NewsArticle | null>(null);

  // Read/Unread state
  const [readArticleIds, setReadArticleIds] = useState<number[]>(() => {
    try {
      const saved = localStorage.getItem("read_news_article_ids");
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      return [];
    }
  });

  const handleOpenArticle = (art: NewsArticle) => {
    setSelectedArticle(art);
    if (!readArticleIds.includes(art.id)) {
      const updated = [...readArticleIds, art.id];
      setReadArticleIds(updated);
      localStorage.setItem("read_news_article_ids", JSON.stringify(updated));
    }
  };

  const handleMarkAllRead = () => {
    const allIds = articles.map(a => a.id);
    const uniqueRead = Array.from(new Set([...readArticleIds, ...allIds]));
    setReadArticleIds(uniqueRead);
    localStorage.setItem("read_news_article_ids", JSON.stringify(uniqueRead));
  };

  // Filters State
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [industryFilter, setIndustryFilter] = useState("");
  const [startupFilter, setStartupFilter] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  const fetchSources = async () => {
    try {
      const res = await fetch(`${apiUrl}/news/sources`);
      if (res.ok) {
        const data = await res.json();
        setSources(data || []);
      }
    } catch (e) {
      console.error("Failed to load news sources:", e);
    }
  };

  const fetchIndustries = async () => {
    try {
      const res = await fetch(`${apiUrl}/scrape/pipeline-config`); // fallback check
      const config_res = await fetch(`${apiUrl}/news/sources`); // check standard
      // Load standard static industries for V1
      setIndustries([
        "Financial Services",
        "Artificial Intelligence",
        "Enterprise Software",
        "Cybersecurity",
        "Healthcare & Life Sciences",
        "Commerce & Retail",
        "Transportation & Logistics",
        "Real Estate & Construction",
        "DeepTech"
      ]);
    } catch (e) {
      console.error("Failed to load industry configurations:", e);
    }
  };

  const fetchArticles = async () => {
    setLoading(true);
    try {
      // Build query string
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      if (sourceFilter) params.append("source", sourceFilter);
      if (categoryFilter) params.append("category", categoryFilter);
      if (industryFilter) params.append("industry", industryFilter);
      if (startupFilter) params.append("startup", startupFilter);
      if (fromDate) params.append("from_date", fromDate);
      if (toDate) params.append("to_date", toDate);
      params.append("limit", "100");

      const res = await fetch(`${apiUrl}/news?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setArticles(data.articles || []);
      }
    } catch (e) {
      console.error("Failed to load news articles:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSources();
    fetchIndustries();
  }, []);

  useEffect(() => {
    fetchArticles();
  }, [search, sourceFilter, categoryFilter, industryFilter, startupFilter, fromDate, toDate]);

  // Poll scraping status for background news ingestion runs
  useEffect(() => {
    let intervalId: any;
    
    const checkStatus = async () => {
      try {
        const res = await fetch(`${apiUrl}/scrape/status`);
        if (res.ok) {
          const data = await res.json();
          
          setSyncStatus(prev => {
            // Show success banner if a new sync completed log is received
            if (data.last_news_sync && (!prev?.last_news_sync || prev.last_news_sync.completed_at !== data.last_news_sync.completed_at)) {
              setShowSyncSuccessBanner(true);
              fetchArticles();
            }
            return data;
          });
        }
      } catch (e) {
        console.error("Failed to fetch sync status:", e);
      }
    };

    checkStatus();
    intervalId = setInterval(checkStatus, 3000);

    return () => clearInterval(intervalId);
  }, []);

  // Scraper Trigger
  const handleTriggerScraper = async (selectedSources: string[], articleLimit: number) => {
    setScraping(true);
    try {
      const res = await fetch(`${apiUrl}/news/trigger`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          limit_per_source: articleLimit,
          sources: selectedSources.length > 0 ? selectedSources : null
        })
      });
      if (res.ok) {
        setShowSyncSuccessBanner(false); // Hide any previous run's banner
      }
    } catch (e) {
      alert("Failed to initiate scraper pipeline.");
    } finally {
      setScraping(false);
    }
  };

  // Digest Trigger
  const handleTriggerDigest = async (edition: string) => {
    setSendingDigest(true);
    try {
      const res = await fetch(`${apiUrl}/news/digest/trigger`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ edition }),
      });
      if (res.ok) {
        alert(`HTML Email digest successfully dispatched (${edition} Edition)! Check your Gmail inbox.`);
      }
    } catch (e) {
      alert("Failed to dispatch digest.");
    } finally {
      setSendingDigest(false);
    }
  };

  return (
    <div className="space-y-6 text-left" id="news-dashboard-view">
      {/* Title Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white p-6 rounded-xl border border-slate-200/80 shadow-sm" id="news-header">
        <div>
          <span className="bg-amber-100 text-amber-800 text-[10px] font-bold px-2 py-1 rounded-full uppercase tracking-wider">
            ICICI Bank Corporate Vetting
          </span>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight mt-2 flex items-center gap-2">
            Fintech & Startup News Intelligence <Globe className="text-amber-500" size={22} />
          </h2>
          <p className="text-slate-500 text-sm mt-1">
            Aggregated coverage from startup media, regulatory changes, and query-based Google feeds.
          </p>
        </div>
        
        {/* Scraper / Digest Action buttons */}
        <div className="flex flex-wrap gap-2.5">
          <button
            onClick={() => setShowAddSource(true)}
            className="bg-white hover:bg-slate-50 text-slate-700 text-xs px-3.5 py-2 rounded-lg font-bold border border-slate-200 shadow-sm transition-all flex items-center gap-1.5 cursor-pointer"
          >
            <Plus size={14} /> Add RSS Source
          </button>
          
          <button
            onClick={() => setShowSyncModal(true)}
            disabled={scraping || (syncStatus?.active ?? false)}
            className="bg-amber-500 hover:bg-amber-600 disabled:bg-amber-300 text-slate-900 text-xs px-3.5 py-2 rounded-lg font-bold shadow-sm transition-all flex items-center gap-1.5 cursor-pointer border-0"
          >
            {(scraping || syncStatus?.active) ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
            Sync News Feed
          </button>

          <div className="relative group">
            <button
              disabled={sendingDigest}
              className="bg-slate-900 hover:bg-slate-800 disabled:bg-slate-750 text-white text-xs px-3.5 py-2 rounded-lg font-bold shadow-sm transition-all flex items-center gap-1.5 cursor-pointer border-0"
            >
              {sendingDigest ? <Loader2 size={13} className="animate-spin" /> : <Mail size={13} />}
              Send Digest
            </button>
            <div className="absolute right-0 top-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg py-1.5 z-20 hidden group-hover:block w-36">
              <button
                onClick={() => handleTriggerDigest("Morning")}
                className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 font-medium text-slate-700 border-0 cursor-pointer bg-transparent"
              >
                ☀️ Morning Edition
              </button>
              <button
                onClick={() => handleTriggerDigest("Evening")}
                className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 font-medium text-slate-700 border-0 cursor-pointer bg-transparent"
              >
                🌙 Evening Edition
              </button>
              <button
                onClick={() => handleTriggerDigest("Manual")}
                className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 font-medium text-slate-700 border-0 cursor-pointer bg-transparent"
              >
                ⚙️ Manual Draft
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Sync Active Progress Banner */}
      {syncStatus?.active && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3 shadow-sm animate-pulse" id="sync-active-banner">
          <Loader2 className="text-amber-500 animate-spin mt-0.5 shrink-0" size={18} />
          <div className="flex-1 min-w-0">
            <h4 className="text-xs font-bold text-amber-800 uppercase tracking-wider">Sync Ingestion Active</h4>
            <p className="text-sm text-amber-700 font-medium mt-1">
              Currently running: <span className="font-bold underline">{syncStatus.current_step}</span>
            </p>
            <p className="text-xs text-amber-600/80 mt-1">
              Startup mentions resolved so far in this run: <span className="font-bold">{syncStatus.discovered_count}</span>
            </p>
          </div>
        </div>
      )}

      {/* Sync Terminal Log Stream - Permanently Visible */}
      <div className="space-y-2 text-left bg-white border border-slate-200 rounded-xl p-4 shadow-sm animate-fade-in">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-bold uppercase tracking-wide">
            <Terminal size={12} className="text-slate-400" />
            <span>Interactive Log Console Stream</span>
            {syncStatus?.active && (
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-ping"></span>
            )}
          </div>
          {syncStatus?.active && (
            <span className="text-[9px] font-semibold text-amber-700 bg-amber-100/70 px-2 py-0.5 rounded animate-pulse">
              INGESTION RUNNING
            </span>
          )}
        </div>

        <div 
          ref={newsTerminalRef}
          className="bg-slate-900 border border-slate-800 rounded-xl p-4 h-48 overflow-y-auto font-mono text-[11px] leading-relaxed text-slate-300 shadow-inner select-text custom-scrollbar"
          style={{
            boxShadow: "inset 0 4px 6px -1px rgb(0 0 0 / 0.2), inset 0 2px 4px -2px rgb(0 0 0 / 0.2)"
          }}
        >
          {(!syncStatus?.logs || syncStatus.logs.length === 0) ? (
            <div className="text-slate-500 italic h-full flex items-center justify-center">
              No recent news sync runs recorded in this session. Click "Sync News Feed" to start.
            </div>
          ) : (
            <div className="space-y-1">
              {syncStatus.logs.map((log, index) => {
                let lineClass = "text-slate-300";
                if (log.includes("❌") || log.includes("Error") || log.includes("Failed")) lineClass = "text-rose-400 font-semibold";
                else if (log.includes("✨") || log.includes("Completed") || log.includes("Saved")) lineClass = "text-emerald-400 font-semibold";
                else if (log.includes("🔄") || log.includes("Starting") || log.includes("Extracting") || log.includes("🔗")) lineClass = "text-amber-400";
                return (
                  <div key={index} className={lineClass}>
                    {log}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Sync Completed Success Banner */}
      {showSyncSuccessBanner && syncStatus?.last_news_sync && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 shadow-sm animate-slide-in" id="sync-success-banner">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="bg-emerald-100 text-emerald-800 p-1.5 rounded-lg font-bold text-xs mt-0.5 shrink-0">
                ✓
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-xs font-bold text-emerald-800 uppercase tracking-wider">Ingestion Sync Completed!</h4>
                <p className="text-sm text-emerald-700 font-medium mt-1">
                  Processed <span className="font-bold">{syncStatus.last_news_sync.processed_count}</span> raw stories. Saved <span className="font-bold">{syncStatus.last_news_sync.saved_count}</span> new canonical articles to workspace database.
                </p>
                
                {syncStatus.last_news_sync.articles && syncStatus.last_news_sync.articles.length > 0 && (
                  <div className="mt-3">
                    <span className="text-[10px] text-emerald-600 font-bold uppercase tracking-wider block">Newly Aggregated Articles:</span>
                    <ul className="mt-1.5 space-y-1 pl-4 list-disc text-xs text-emerald-700/90 font-medium">
                      {syncStatus.last_news_sync.articles.map((art, aIdx) => (
                        <li key={aIdx}>{art}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
            <button 
              onClick={() => setShowSyncSuccessBanner(false)}
              className="text-emerald-500 hover:text-emerald-750 p-1 hover:bg-emerald-100 rounded transition-colors cursor-pointer border-0 bg-transparent"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Dynamic Filters Pane */}
      <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-4" id="news-filters-pane">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-2 text-slate-400">
          <Filter size={15} />
          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Filter News Grid</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          {/* Search Input */}
          <div className="space-y-1 md:col-span-2">
            <label htmlFor="news-search" className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Search</label>
            <div className="relative">
              <input
                id="news-search"
                type="text"
                placeholder="Keywords, headline content..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg py-2 pl-8 pr-3 focus:ring-1 focus:ring-amber-500 focus:outline-none"
              />
              <Search className="absolute left-2.5 top-2.5 text-slate-400" size={14} />
            </div>
          </div>

          {/* Category Dropdown */}
          <div className="space-y-1">
            <label htmlFor="news-category" className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Category</label>
            <select
              id="news-category"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg py-2 px-2.5 focus:ring-1 focus:ring-amber-500 focus:outline-none"
            >
              <option value="">All Categories</option>
              <option value="startup_media">Startup Media</option>
              <option value="business_media">Business Media</option>
              <option value="technology">Technology</option>
              <option value="government">Government & Policy</option>
              <option value="aggregator">Aggregators</option>
            </select>
          </div>

          {/* Source Dropdown */}
          <div className="space-y-1">
            <label htmlFor="news-source" className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Source</label>
            <select
              id="news-source"
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg py-2 px-2.5 focus:ring-1 focus:ring-amber-500 focus:outline-none"
            >
              <option value="">All Sources</option>
              {Array.from(new Set(sources.map((s) => s.name))).map((src_name) => (
                <option key={src_name} value={src_name}>
                  {src_name}
                </option>
              ))}
            </select>
          </div>

          {/* Industry Filter */}
          <div className="space-y-1">
            <label htmlFor="news-industry" className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Industry</label>
            <select
              id="news-industry"
              value={industryFilter}
              onChange={(e) => setIndustryFilter(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg py-2 px-2.5 focus:ring-1 focus:ring-amber-500 focus:outline-none"
            >
              <option value="">All Industries</option>
              {industries.map((ind) => (
                <option key={ind} value={ind}>
                  {ind}
                </option>
              ))}
            </select>
          </div>

          {/* Date Picker Fields */}
          <div className="space-y-1">
            <label htmlFor="news-from" className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">From Date</label>
            <input
              id="news-from"
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg py-1.5 px-2 focus:ring-1 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          <div className="space-y-1">
            <label htmlFor="news-to" className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">To Date</label>
            <input
              id="news-to"
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg py-1.5 px-2 focus:ring-1 focus:ring-amber-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Startup Specific Search */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 pt-2">
          <div className="space-y-1">
            <label htmlFor="news-startup-filter" className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Mentioned Startup</label>
            <input
              id="news-startup-filter"
              type="text"
              placeholder="e.g. PhonePe"
              value={startupFilter}
              onChange={(e) => setStartupFilter(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg py-2 px-3 focus:ring-1 focus:ring-amber-500 focus:outline-none"
            />
          </div>
          
          {/* Active Filter Badges */}
          <div className="md:col-span-3 flex items-end justify-end pb-1.5 gap-2">
            {articles.length > 0 && articles.some(a => !readArticleIds.includes(a.id)) && (
              <button
                onClick={handleMarkAllRead}
                className="text-[10px] bg-amber-50 hover:bg-amber-100 text-amber-700 font-bold px-3 py-1.5 rounded-lg border border-amber-200/70 cursor-pointer transition-colors flex items-center gap-1 shadow-sm"
              >
                ✓ Mark all as read
              </button>
            )}

            {(search || sourceFilter || categoryFilter || industryFilter || startupFilter || fromDate || toDate) && (
              <button
                onClick={() => {
                  setSearch("");
                  setSourceFilter("");
                  setCategoryFilter("");
                  setIndustryFilter("");
                  setStartupFilter("");
                  setFromDate("");
                  setToDate("");
                }}
                className="text-[10px] bg-slate-100 hover:bg-slate-200 text-slate-655 text-slate-600 font-bold px-3 py-1.5 rounded-lg border-0 cursor-pointer transition-colors"
              >
                Clear All Filters
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Row List Grid */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden" id="news-grid-container">
        {loading ? (
          <div className="p-16 text-center space-y-3">
            <Loader2 className="animate-spin text-amber-500 mx-auto" size={28} />
            <p className="text-xs text-slate-455 text-slate-500">Querying Supabase registry feeds...</p>
          </div>
        ) : articles.length === 0 ? (
          <div className="p-16 text-center space-y-3">
            <AlertCircle className="text-slate-350 mx-auto" size={32} />
            <h4 className="font-bold text-slate-800 text-sm">No Articles Found</h4>
            <p className="text-xs text-slate-455 text-slate-500">No coverage matches your selected filter criteria. Try expanding date ranges or keywords.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {articles.map((art) => {
              const pubDate = art.published_at ? new Date(art.published_at) : new Date();
              const dateStr = pubDate.toLocaleDateString(undefined, { day: "numeric", month: "short" });
              const timeStr = pubDate.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
              const isUnread = !readArticleIds.includes(art.id);

              return (
                <div
                  key={art.id}
                  onClick={() => handleOpenArticle(art)}
                  className={`p-5 flex items-start gap-5 hover:bg-slate-50/50 cursor-pointer transition-all hover:pl-6 text-left group border-l-2 ${
                    isUnread ? "bg-amber-50/15 border-l-amber-500 pl-6" : "border-l-transparent"
                  }`}
                >
                  {/* Left Column: Date & Time */}
                  <div className="w-24 shrink-0 text-left flex items-start gap-1.5">
                    {isUnread && (
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse mt-1 shrink-0" title="Unread" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className={`text-xs font-bold font-mono tracking-tight ${isUnread ? "text-amber-800" : "text-slate-900"}`}>{dateStr}</p>
                      <p className="text-[10px] text-slate-400 font-mono mt-0.5">{timeStr}</p>
                      <span className="inline-block mt-2 text-[9px] bg-slate-100 text-slate-500 font-bold px-1.5 py-0.5 rounded uppercase tracking-wider">
                        {art.category.replace("_", " ")}
                      </span>
                    </div>
                  </div>

                  {/* Middle Column: Headline, Summary, Mentions */}
                  <div className="flex-1 min-w-0 space-y-2">
                    {/* Headline */}
                    <h3 className="font-bold text-slate-900 text-xs sm:text-sm group-hover:text-amber-600 transition-colors leading-snug">
                      {art.headline}
                    </h3>

                    {/* AI Summary */}
                    <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">
                      {art.summary || "No AI summary compiled."}
                    </p>

                    {/* Startup Mentions & Similar Sources */}
                    <div className="flex flex-wrap items-center gap-3 pt-1 text-[10px]">
                      {art.startups_mentioned && art.startups_mentioned.length > 0 && (
                        <div className="flex items-center gap-1.5">
                          <span className="text-slate-400 font-bold uppercase tracking-wider">Mentioned:</span>
                          <div className="flex flex-wrap gap-1">
                            {art.startups_mentioned.map((s, sIdx) => (
                              <span
                                key={sIdx}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (s.id) {
                                    onSelectStartupByName(s.name);
                                  } else {
                                    setActionStartup({ name: s.name, articleId: art.id });
                                  }
                                }}
                                className={`font-bold px-2 py-0.5 rounded transition-all cursor-pointer ${
                                  s.id
                                    ? "bg-blue-50 text-blue-600 border border-blue-100/50 hover:bg-blue-100"
                                    : "bg-slate-50 text-slate-500 border border-slate-200/60 border-dashed hover:bg-slate-100 hover:text-slate-700"
                                }`}
                              >
                                {s.name}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Similar Sources counts */}
                      {art.similar_sources && art.similar_sources.length > 0 && (
                        <div className="flex items-center gap-1 text-slate-400">
                          <Layers size={10} />
                          <span className="font-semibold">
                            +{art.similar_sources.length} similar coverage ({art.similar_sources.map(s=>s.source).join(", ")})
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right Column: Multiple Clickable Source Logos & Read Details */}
                  <div className="w-48 shrink-0 flex flex-col items-end gap-2 text-right justify-between self-stretch animate-fade-in">
                    <div className="flex flex-wrap items-center justify-end gap-1.5 max-w-full">
                      {/* Primary Source */}
                      <a
                        href={art.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        title={`Primary Source: ${art.source}`}
                        className="bg-slate-50 hover:bg-slate-100 border border-slate-200/80 rounded-lg p-1.5 flex items-center justify-center transition-colors shadow-sm"
                      >
                        <SourceLogo source={art.source} url={art.source_url} />
                      </a>
                      
                      {/* Similar Sources (Deduplicated by publisher name) */}
                      {(() => {
                        const renderedSources = new Set<string>([art.source.toLowerCase()]);
                        return art.similar_sources && art.similar_sources.filter(sim => {
                          const srcLower = sim.source.toLowerCase();
                          if (renderedSources.has(srcLower)) {
                            return false;
                          }
                           renderedSources.add(srcLower);
                           return true;
                        }).map((sim, sIdx) => (
                          <a
                            key={sIdx}
                            href={sim.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            title={`Similar Coverage: ${sim.source}`}
                            className="bg-slate-50 hover:bg-slate-100 border border-slate-200/80 rounded-lg p-1.5 flex items-center justify-center transition-colors shadow-sm"
                          >
                            <SourceLogo source={sim.source} url={sim.url} />
                          </a>
                        ));
                      })()}
                    </div>
                    
                    <span className="text-slate-350 group-hover:text-amber-500 transition-colors flex items-center gap-1 text-[11px] font-semibold">
                      Read Details <ChevronRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Side reader panel */}
      {selectedArticle && (
        <NewsDrawer
          article={selectedArticle}
          onClose={() => setSelectedArticle(null)}
          onSelectStartupByName={(name) => {
            const mention = selectedArticle.startups_mentioned?.find(
              (m) => m.name.toLowerCase() === name.toLowerCase()
            );
            if (mention && mention.id) {
              onSelectStartupByName(name);
              setSelectedArticle(null);
            } else {
              setActionStartup({ name, articleId: selectedArticle.id });
            }
          }}
        />
      )}

      {/* Add Custom Source form */}
      {showAddSource && (
        <AddSourceModal
          onClose={() => setShowAddSource(false)}
          onSourceAdded={() => {
            fetchSources();
            fetchArticles();
          }}
          apiUrl={apiUrl}
        />
      )}

      {/* Add Startup Action Modal (for unlinked startup mentions) */}
      {actionStartup && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 animate-fade-in" id="add-startup-action-modal">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-md overflow-hidden animate-zoom-in text-left">
            <div className="p-5 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
              <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2">
                🚀 Add Startup to Workspace
              </h3>
              <button
                onClick={() => setActionStartup(null)}
                className="text-slate-400 hover:text-slate-650 p-1 hover:bg-slate-100 rounded-lg transition-colors border-0 cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <p className="text-xs text-slate-500 leading-relaxed">
                Startup <span className="font-bold text-slate-800 underline">"{actionStartup.name}"</span> was discovered in the news but is not registered in your workspace repository yet. 
                Select how you want to add this startup:
              </p>
              
              <div className="space-y-3 pt-2">
                <button
                  onClick={() => handleResolveStartup(actionStartup.name, actionStartup.articleId, false)}
                  className="w-full bg-white hover:bg-slate-50 text-slate-800 border border-slate-250 rounded-xl p-4 text-left transition-all hover:border-slate-350 group cursor-pointer"
                >
                  <span className="font-bold text-xs block text-slate-950 group-hover:text-amber-600 transition-colors">📂 Add Basic Info Only</span>
                  <span className="text-[10px] text-slate-500 block mt-1 leading-normal">
                    Registers the startup instantly using only the news summary and title. Bypasses deep AI crawling.
                  </span>
                </button>
                
                <button
                  onClick={() => handleResolveStartup(actionStartup.name, actionStartup.articleId, true)}
                  className="w-full bg-gradient-to-r from-amber-500/10 to-orange-500/10 hover:from-amber-500/20 hover:to-orange-500/20 text-slate-800 border border-amber-250 rounded-xl p-4 text-left transition-all group cursor-pointer"
                >
                  <span className="font-bold text-xs block text-amber-800 flex items-center gap-1">
                    ✨ Add & Enrich Profile (AI Agent)
                  </span>
                  <span className="text-[10px] text-slate-600 block mt-1 leading-normal">
                    Registers the startup and launches the multi-agent search, dynamic crawling, and deep corporate intelligence analysis in the background.
                  </span>
                </button>
              </div>
            </div>
            
            <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end gap-2">
              <button
                onClick={() => setActionStartup(null)}
                className="bg-white border border-slate-200 text-slate-700 text-xs px-4 py-2 rounded-lg font-bold hover:bg-slate-50 cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sync parameters config modal */}
      {showSyncModal && (
        <SyncConfigModal
          sources={sources}
          onClose={() => setShowSyncModal(false)}
          onStartSync={(selectedIds, limit) => handleTriggerScraper(selectedIds, limit)}
        />
      )}
    </div>
  );
}

interface SyncConfigModalProps {
  sources: NewsSource[];
  onClose: () => void;
  onStartSync: (selected: string[], limit: number) => void;
}

function SyncConfigModal({ sources, onClose, onStartSync }: SyncConfigModalProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [articleLimit, setArticleLimit] = useState(5);

  const handleToggle = (id: string) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    setSelectedIds(sources.map(s => s.id));
  };

  const handleDeselectAll = () => {
    setSelectedIds([]);
  };

  const categories = Array.from(new Set(sources.map(s => s.category)));

  const getCategoryLabel = (cat: string) => {
    switch (cat) {
      case "startup_media": return "Startup Media";
      case "business_media": return "Business & Financial Media";
      case "technology": return "Technology & Global Tech";
      case "government": return "Government & Regulatory";
      case "aggregator": return "Aggregators & Search Indexes";
      default: return cat.replace("_", " ");
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onStartSync(selectedIds, articleLimit);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 animate-fade-in" id="sync-config-modal">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-2xl overflow-hidden animate-zoom-in text-left flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50 shrink-0">
          <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2">
            <Sliders className="text-amber-500" size={16} /> Sync Ingestion Parameters
          </h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-655 p-1 hover:bg-slate-100 rounded-lg transition-colors border-0 cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>

        {/* Scrollable list of sources */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          <div className="flex justify-between items-center bg-slate-50 p-3 rounded-lg border border-slate-150">
            <div className="space-y-0.5">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Global Ingestion Limit</span>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min="1"
                  max="30"
                  value={articleLimit}
                  onChange={(e) => setArticleLimit(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-20 bg-white border border-slate-200 text-slate-800 text-xs rounded-lg py-1.5 px-3 focus:ring-1 focus:ring-amber-500 focus:outline-none"
                />
                <span className="text-xs text-slate-500 font-medium">Articles parsed per feed URL</span>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleSelectAll}
                className="bg-white hover:bg-slate-100 text-slate-700 text-[10px] px-2.5 py-1.5 rounded font-bold border border-slate-200 cursor-pointer"
              >
                Select All
              </button>
              <button
                type="button"
                onClick={handleDeselectAll}
                className="bg-white hover:bg-slate-100 text-slate-700 text-[10px] px-2.5 py-1.5 rounded font-bold border border-slate-200 cursor-pointer"
              >
                Deselect All
              </button>
            </div>
          </div>

          <div className="space-y-4">
            <label className="text-xs font-bold text-slate-700 block">Select Active Ingestion Sources ({selectedIds.length} Selected)</label>
            
            {categories.map(cat => {
              const catSources = sources.filter(s => s.category === cat);
              if (catSources.length === 0) return null;
              
              return (
                <div key={cat} className="space-y-2">
                  <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-slate-100 pb-1">
                    {getCategoryLabel(cat)}
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {catSources.map(source => (
                      <label
                        key={source.id}
                        className={`flex items-start gap-2.5 p-2 rounded-lg border cursor-pointer transition-all ${
                          selectedIds.includes(source.id)
                            ? "bg-amber-50/45 border-amber-200"
                            : "bg-white hover:bg-slate-50 border-slate-150"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(source.id)}
                          onChange={() => handleToggle(source.id)}
                          className="mt-0.5 rounded text-amber-500 focus:ring-amber-500 cursor-pointer"
                        />
                        <div className="min-w-0">
                          <span className="text-xs font-bold text-slate-800 block truncate leading-tight">{source.name}</span>
                          <span className="text-[9px] text-slate-450 truncate block mt-0.5">{source.rss_url}</span>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/50 flex justify-end gap-2 shrink-0">
          <button
            onClick={onClose}
            className="bg-white hover:bg-slate-100 text-slate-700 text-xs px-4 py-2 rounded-lg font-bold border border-slate-200 transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={selectedIds.length === 0}
            className="bg-amber-500 hover:bg-amber-600 disabled:bg-amber-300 text-slate-900 text-xs px-4 py-2 rounded-lg font-bold shadow-sm transition-colors cursor-pointer border-0"
          >
            Begin Feed Ingestion
          </button>
        </div>
      </div>
    </div>
  );
}
