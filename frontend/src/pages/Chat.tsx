import React, { useState, useRef, useEffect } from 'react';
import { Bot, Send, Sparkles, User, RefreshCw, MessageSquare } from 'lucide-react';

const rawApiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const API_URL = rawApiUrl.endsWith("/") 
  ? (rawApiUrl.endsWith("/api/") ? rawApiUrl.slice(0, -1) : rawApiUrl + "api") 
  : (rawApiUrl.endsWith("/api") ? rawApiUrl : rawApiUrl + "/api");

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const QUICK_PROMPTS = [
  "Summarize registered LendingTech ventures",
  "Which startups have a priority score ≥ 90?",
  "List active InsurTech pilots and their assigned FPRs"
];

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Hello! I am the ICICI Startup Intelligence Assistant. Ask me anything about our startup registry, sectors, priority scores, or FPR outreach assignments.' }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSendMessage = async (textToSend: string) => {
    if (!textToSend.trim() || loading) return;

    const newHistory: Message[] = [...messages, { role: 'user', content: textToSend }];
    setMessages(newHistory);
    setInputValue('');
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          history: newHistory
        })
      });

      if (!response.ok) {
        throw new Error('Failed to get reply from AI assistant.');
      }

      const data = await response.json();
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }]);
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `⚠️ Error: ${e.message || 'Could not communicate with the local model.'}` }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = () => {
    setMessages([
      { role: 'assistant', content: 'Hello! I am the ICICI Startup Intelligence Assistant. Ask me anything about our startup registry, sectors, priority scores, or FPR outreach assignments.' }
    ]);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] bg-slate-50 border border-slate-200/80 rounded-xl overflow-hidden shadow-sm" id="chat-container">
      {/* Header */}
      <div className="p-4 bg-slate-900 border-b border-indigo-650 flex justify-between items-center text-white">
        <div className="flex items-center gap-2.5 text-left">
          <div className="p-2 bg-indigo-500/20 rounded-lg text-indigo-450 border border-indigo-500/30">
            <Bot size={18} className="animate-pulse" />
          </div>
          <div>
            <h3 className="font-bold text-xs uppercase tracking-wider">ICICI Neural Assistant</h3>
            <p className="text-[10px] text-slate-400">Powered by local qwen2.5:3b • Database Context Active</p>
          </div>
        </div>
        <button
          onClick={handleClearHistory}
          className="text-xs text-slate-400 hover:text-white transition-all bg-transparent border-0 cursor-pointer flex items-center gap-1 font-semibold"
        >
          <RefreshCw size={13} />
          Clear Chat
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-white/40">
        {messages.map((message, index) => {
          const isUser = message.role === 'user';
          return (
            <div key={index} className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
              <div className={`flex gap-3 max-w-xl ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start`}>
                {/* Avatar */}
                <div className={`p-2 rounded-lg text-xs font-bold border ${
                  isUser 
                    ? 'bg-blue-50 text-blue-600 border-blue-200/40' 
                    : 'bg-indigo-50 text-indigo-600 border-indigo-200/40'
                }`}>
                  {isUser ? <User size={14} /> : <Bot size={14} />}
                </div>

                {/* Message Content */}
                <div className={`rounded-xl px-4 py-2.5 text-xs text-left shadow-sm leading-relaxed border ${
                  isUser 
                    ? 'bg-slate-900 text-white border-slate-800' 
                    : 'bg-slate-50 text-slate-800 border-slate-150'
                }`}>
                  <p className="whitespace-pre-line">{message.content}</p>
                </div>
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex justify-start animate-fade-in">
            <div className="flex gap-3 max-w-xl items-start">
              <div className="p-2 rounded-lg bg-indigo-50 text-indigo-650 border border-indigo-200/40">
                <Bot size={14} className="animate-spin" />
              </div>
              <div className="bg-slate-50 text-slate-500 border border-slate-150 rounded-xl px-4 py-2.5 text-xs text-left flex items-center gap-2">
                <span className="flex h-1.5 w-1.5 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-indigo-500"></span>
                </span>
                <span>AI is compiling response from Supabase registry...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts */}
      {messages.length === 1 && (
        <div className="p-4 bg-slate-50 border-t border-slate-150 text-left">
          <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider mb-2 flex items-center gap-1">
            <Sparkles size={12} className="text-amber-500" /> Suggested Queries
          </p>
          <div className="flex flex-wrap gap-2">
            {QUICK_PROMPTS.map((qp, idx) => (
              <button
                key={idx}
                onClick={() => handleSendMessage(qp)}
                className="bg-white border border-slate-200 hover:border-slate-350 text-slate-700 text-[11px] font-semibold px-3 py-1.5 rounded-lg transition-all shadow-sm cursor-pointer flex items-center gap-1.5"
              >
                <MessageSquare size={12} className="text-slate-400" />
                {qp}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="p-4 bg-white border-t border-slate-200">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage(inputValue);
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            className="flex-1 bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-xl p-3 focus:ring-1 focus:ring-indigo-500 focus:outline-none placeholder-slate-400"
            placeholder="Query registered fintechs, ask for sector metrics, or look up FPR owners..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !inputValue.trim()}
            className="bg-indigo-650 hover:bg-indigo-700 disabled:opacity-40 border-0 text-white rounded-xl p-3 flex items-center justify-center transition-all cursor-pointer shadow-md"
          >
            <Send size={15} />
          </button>
        </form>
      </div>
    </div>
  );
}
