import React, { useState } from "react";
import { X, Globe, Plus, Loader2, CheckCircle2 } from "lucide-react";

interface AddSourceModalProps {
  onClose: () => void;
  onSourceAdded: () => void;
  apiUrl: string;
}

export default function AddSourceModal({ onClose, onSourceAdded, apiUrl }: AddSourceModalProps) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [category, setCategory] = useState("startup_media");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response = await fetch(`${apiUrl}/news/sources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, url, category }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to add RSS source.");
      }

      setSuccess(true);
      setTimeout(() => {
        onSourceAdded();
        onClose();
      }, 1500);
    } catch (err: any) {
      setError(err.message || "An unexpected network error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 animate-fade-in" id="add-source-modal">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-md overflow-hidden animate-zoom-in text-left">
        {/* Header */}
        <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2">
            <Globe className="text-amber-500" size={16} /> Register Custom RSS Feed
          </h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 hover:bg-slate-100 rounded-lg transition-colors border-0 cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>

        {/* Content Body */}
        {success ? (
          <div className="p-8 text-center flex flex-col items-center justify-center space-y-3">
            <CheckCircle2 size={44} className="text-emerald-500 animate-bounce" />
            <h4 className="font-bold text-slate-800 text-sm">Source Added Successfully</h4>
            <p className="text-xs text-slate-500">The new RSS target is validated and persisted in sources.json.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {error && (
              <div className="bg-red-50 text-red-700 text-xs p-3 rounded-lg border border-red-100">
                {error}
              </div>
            )}

            {/* Source Name */}
            <div className="space-y-1.5">
              <label htmlFor="source-name" className="text-xs font-bold text-slate-700">Source Name</label>
              <input
                id="source-name"
                type="text"
                placeholder="e.g. YourStory FinTech"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg py-2 px-3 focus:ring-1 focus:ring-amber-500 focus:border-amber-500 focus:outline-none"
              />
            </div>

            {/* Feed URL */}
            <div className="space-y-1.5">
              <label htmlFor="source-url" className="text-xs font-bold text-slate-700">RSS / XML Feed URL</label>
              <input
                id="source-url"
                type="url"
                placeholder="https://example.com/rss"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
                className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg py-2 px-3 focus:ring-1 focus:ring-amber-500 focus:border-amber-500 focus:outline-none"
              />
            </div>

            {/* Category Selector */}
            <div className="space-y-1.5">
              <label htmlFor="source-category" className="text-xs font-bold text-slate-700">Source Category</label>
              <select
                id="source-category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                required
                className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg py-2 px-3 focus:ring-1 focus:ring-amber-500 focus:border-amber-500 focus:outline-none"
              >
                <option value="startup_media">Startup Media</option>
                <option value="business_media">Business Media</option>
                <option value="technology">Technology</option>
                <option value="government">Government & Regulatory</option>
                <option value="aggregator">Aggregators</option>
              </select>
            </div>

            {/* Submit Toolbar */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={onClose}
                className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs px-4 py-2 rounded-lg font-bold transition-colors border-0 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="bg-amber-500 hover:bg-amber-600 disabled:bg-amber-300 text-slate-900 text-xs px-4 py-2 rounded-lg font-bold shadow-sm transition-colors flex items-center gap-1.5 cursor-pointer border-0"
              >
                {loading ? (
                  <>
                    <Loader2 size={13} className="animate-spin" /> Validating...
                  </>
                ) : (
                  <>
                    <Plus size={14} /> Add Source
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
