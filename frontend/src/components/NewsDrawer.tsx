import React, { useState, useEffect } from "react";
import { X, ExternalLink, Calendar, Layers, Sparkles, Tag, ArrowRight, CornerDownRight } from "lucide-react";
import { NewsArticle } from "../types";
import { SourceLogo } from "./SourceLogo";

interface NewsDrawerProps {
  article: NewsArticle | null;
  onClose: () => void;
  onSelectStartupByName: (name: string) => void;
}

export default function NewsDrawer({ article, onClose, onSelectStartupByName }: NewsDrawerProps) {
  const [width, setWidth] = useState<number>(() => {
    const saved = localStorage.getItem("news_drawer_width");
    return saved ? parseInt(saved, 10) : 550;
  });
  const [isResizing, setIsResizing] = useState(false);

  useEffect(() => {
    if (!article) return;
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const newWidth = window.innerWidth - e.clientX;
      if (newWidth > 350 && newWidth < window.innerWidth - 100) {
        setWidth(newWidth);
        localStorage.setItem("news_drawer_width", newWidth.toString());
      }
    };
    const handleMouseUp = () => setIsResizing(false);

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing, article]);

  if (!article) return null;

  // Format date/time
  const pubDate = article.published_at ? new Date(article.published_at) : new Date();
  const dateStr = pubDate.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
  const timeStr = pubDate.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });

  return (
    <div className="fixed inset-0 z-50 flex justify-end transition-opacity duration-300 bg-slate-900/40 backdrop-blur-sm animate-fade-in" id="news-drawer-overlay">
      {/* Background click to close */}
      <div className="flex-1 cursor-pointer" onClick={onClose}></div>

      {/* Resizing bar */}
      <div
        className="w-1.5 cursor-col-resize hover:bg-amber-500/50 bg-slate-200/50 transition-colors flex items-center justify-center relative"
        onMouseDown={(e) => {
          e.preventDefault();
          setIsResizing(true);
        }}
      >
        <div className="absolute h-10 w-1 bg-slate-400 rounded-full opacity-60"></div>
      </div>

      {/* Drawer content panel */}
      <div
        className="bg-white h-full shadow-2xl flex flex-col border-l border-slate-200 animate-slide-in text-left relative overflow-hidden"
        style={{ width: `${width}px` }}
      >
        {/* Header toolbar */}
        <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-2">
            <span className="text-[10px] bg-amber-100 text-amber-800 font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
              {article.category.replace("_", " ")}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <a
              href={article.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-500 hover:text-slate-800 p-1.5 hover:bg-slate-100 rounded-lg transition-colors flex items-center gap-1 text-xs font-semibold cursor-pointer border border-transparent"
            >
              Original Source <ExternalLink size={14} />
            </a>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-600 p-1.5 hover:bg-slate-100 rounded-lg transition-colors border-0 cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Scrollable details container */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Article Meta */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-400 font-medium">
            <span className="flex items-center gap-1.5 font-bold text-slate-500">
              🌍 <SourceLogo source={article.source} url={article.source_url} />
            </span>
            <span className="h-1 w-1 bg-slate-300 rounded-full"></span>
            <span className="flex items-center gap-1">
              <Calendar size={13} /> {dateStr} at {timeStr}
            </span>
          </div>

          {/* Headline */}
          <h1 className="text-xl font-bold text-slate-900 tracking-tight leading-snug">
            {article.headline}
          </h1>

          {/* Startups Mentioned Section */}
          {article.startups_mentioned && article.startups_mentioned.length > 0 && (
            <div className="bg-blue-50/50 p-4 rounded-xl border border-blue-100/50 space-y-2">
              <h4 className="text-[10px] font-bold text-blue-800 uppercase tracking-widest flex items-center gap-1.5">
                🚀 Resolved Startup Mentions
              </h4>
              <div className="flex flex-wrap gap-2 pt-1">
                {article.startups_mentioned.map((s, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSelectStartupByName(s.name)}
                    className="bg-blue-100 hover:bg-blue-200 text-blue-700 font-bold text-xs px-3 py-1 rounded-lg flex items-center gap-1 cursor-pointer transition-colors border-0"
                  >
                    {s.name} <ArrowRight size={12} />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* AI Summary Section */}
          {article.summary && (
            <div className="bg-slate-50 p-5 rounded-xl border border-slate-100 space-y-2.5">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                <Sparkles className="text-amber-500" size={14} /> AI Executive Summary
              </h4>
              <p className="text-xs text-slate-655 text-slate-700 leading-relaxed font-medium">
                {article.summary}
              </p>
            </div>
          )}

          {/* Similar Sources (Duplicates merged) */}
          {article.similar_sources && article.similar_sources.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                <Layers size={13} /> Merged Coverage ({article.similar_sources.length})
              </h4>
              <div className="space-y-2 divide-y divide-slate-50">
                {article.similar_sources.map((sim, idx) => (
                  <div key={idx} className="pt-2 flex items-start gap-2.5 text-xs text-left">
                    <CornerDownRight size={13} className="text-slate-350 shrink-0 mt-0.5" />
                    <div>
                      <a
                        href={sim.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-bold text-slate-700 hover:text-blue-600 leading-relaxed block"
                      >
                        {sim.headline}
                      </a>
                      <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block mt-0.5">
                        {sim.source} {sim.published_at && `• ${new Date(sim.published_at).toLocaleDateString()}`}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Full Cleaped Content Section */}
          <div className="space-y-3 pt-2">
            <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
              📝 Full Ingested Article
            </h4>
            <div className="text-slate-600 text-xs leading-relaxed space-y-3.5 whitespace-pre-wrap bg-white rounded-lg border border-slate-100 p-5 shadow-sm">
              {article.content || article.summary || "No full content parsed for this news feed item."}
            </div>
          </div>
        </div>

        {/* Footer toolbar */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/50 flex justify-end">
          <button
            onClick={onClose}
            className="bg-slate-900 text-white hover:bg-slate-800 text-xs px-4 py-2 rounded-lg font-bold shadow-sm transition-colors border-0 cursor-pointer"
          >
            Close Reader
          </button>
        </div>
      </div>
    </div>
  );
}
