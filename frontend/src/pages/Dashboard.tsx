import React, { useEffect, useState } from 'react';
import { Sparkles, Globe, MapPin } from 'lucide-react';

const rawApiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const API_URL = rawApiUrl.endsWith("/") 
  ? (rawApiUrl.endsWith("/api/") ? rawApiUrl.slice(0, -1) : rawApiUrl + "api") 
  : (rawApiUrl.endsWith("/api") ? rawApiUrl : rawApiUrl + "/api");

interface Startup {
  id: number;
  startup_name: string;
  description: string;
  source: string;
  source_url: string;
  city: string;
  country: string;
  funding_stage?: string;
}

const Dashboard: React.FC = () => {
  const [startups, setStartups] = useState<Startup[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchStartups() {
      try {
        const response = await fetch(`${API_URL}/startups`);
        if (response.ok) {
          const data = await response.json();
          if (data && data.length > 0) {
            setStartups(data);
          }
        }
      } catch (err) {
        console.error("Failed to fetch startups from API:", err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchStartups();
  }, []);

  const displayStartups = startups;

  return (
    <div className="space-y-6">
      {/* Premium Header */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Intelligence Stream</h2>
          <p className="text-slate-500 text-sm mt-1">Real-time startup scraping, classification, and bank partnership assessment.</p>
        </div>
        <div className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 bg-amber-500/10 text-amber-600 rounded-full w-fit">
          <span className="h-2 w-2 bg-amber-500 rounded-full animate-ping"></span>
          Live Stream
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-500"></div>
        </div>
      ) : displayStartups.length === 0 ? (
        <div className="text-center py-16 bg-white border border-slate-200/80 rounded-xl p-8">
          <Sparkles className="h-8 w-8 text-slate-400 mx-auto" />
          <h3 className="font-bold text-slate-800 mt-4">No Active Startups</h3>
          <p className="text-slate-500 text-sm mt-1">Run a scrape task to retrieve live data from active streams.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {displayStartups.map((startup, index) => (
            <div key={index} className="group bg-white rounded-xl border border-slate-200/80 hover:border-amber-500/40 p-6 shadow-sm hover:shadow-md transition-all flex flex-col justify-between">
              <div>
                {/* Meta details */}
                <div className="flex items-center justify-between gap-4">
                  <span className="text-[10px] font-bold tracking-widest text-slate-450 uppercase">
                    {startup.source}
                  </span>
                  <div className="flex items-center gap-1 text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                    <MapPin size={10} />
                    {startup.city || "India"}
                  </div>
                </div>
                
                {/* Clean Name */}
                <h3 className="text-base font-bold text-slate-900 mt-3 group-hover:text-amber-500 transition-colors">
                  {startup.startup_name}
                </h3>
                
                {/* Detailed excerpt */}
                <p className="text-slate-500 text-xs mt-3 leading-relaxed line-clamp-3">
                  {startup.description || "No description available."}
                </p>
              </div>

              {/* Action footer */}
              <div className="border-t border-slate-100 pt-4 mt-6 flex items-center justify-between">
                <span className="text-[11px] font-medium text-slate-400">Stream Status</span>
                {startup.source_url ? (
                  <a 
                    href={startup.source_url} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="text-xs font-semibold text-amber-500 hover:text-amber-600 inline-flex items-center gap-1"
                  >
                    View Source <Globe size={12} />
                  </a>
                ) : (
                  <span className="text-xs font-semibold text-slate-500">Local Cache</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Dashboard;
