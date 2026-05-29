import { useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { Sun, Moon, Sparkles, Database, Check } from "lucide-react";

export default function Settings() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [aiModel, setAiModel] = useState("gpt-4o");
  const [autoScore, setAutoScore] = useState(true);
  const [supabaseUrl, setSupabaseUrl] = useState("https://your-project.supabase.co");
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const applyTheme = (t: "light" | "dark") => {
    setTheme(t);
    document.documentElement.classList.toggle("dark", t === "dark");
  };

  return (
    <>
      <PageHeader
        title="Settings"
        description="Customize the Intelligence OS to match your workflow."
        action={
          <button
            onClick={() => setSavedAt(new Date().toLocaleTimeString())}
            className="h-9 px-3 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 inline-flex items-center gap-2"
          >
            <Check className="h-4 w-4" /> Save changes
          </button>
        }
      />
      {savedAt && <div className="mb-4"><StatusBadge tone="success">Saved at {savedAt}</StatusBadge></div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SectionCard title="Theme" description="Choose how the Intelligence OS looks.">
          <div className="grid grid-cols-2 gap-3">
            <ThemeOption active={theme === "light"} onClick={() => applyTheme("light")} icon={Sun} label="Light" />
            <ThemeOption active={theme === "dark"} onClick={() => applyTheme("dark")} icon={Moon} label="Dark" />
          </div>
        </SectionCard>

        <SectionCard title="AI Settings" description="Control how the Intelligence engine generates insights.">
          <Field label="Model">
            <select value={aiModel} onChange={(e) => setAiModel(e.target.value)} className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm">
              <option value="gpt-4o">GPT-4o</option>
              <option value="claude-3-7">Claude 3.7 Sonnet</option>
              <option value="gemini-2.5">Gemini 2.5 Pro</option>
            </select>
          </Field>
          <Field label="Auto-score new startups">
            <button
              onClick={() => setAutoScore((v) => !v)}
              className={`h-6 w-11 rounded-full transition-colors relative ${autoScore ? "bg-primary" : "bg-muted"}`}
            >
              <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-background shadow transition-transform ${autoScore ? "translate-x-5" : "translate-x-0.5"}`} />
            </button>
          </Field>
          <Field label="Insight tone">
            <select className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm">
              <option>Analytical (default)</option>
              <option>Executive summary</option>
              <option>Risk-focused</option>
            </select>
          </Field>
        </SectionCard>

        <SectionCard title="Data Backend" description="Connect a Supabase project (frontend-only preview)." className="lg:col-span-2">
          <div className="flex items-center gap-3 mb-4 p-3 rounded-md bg-accent/30">
            <Database className="h-4 w-4 text-primary" />
            <div className="text-xs text-foreground/80">This is a UI preview. Hook to a real Supabase project when ready.</div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Field label="Supabase URL">
              <input value={supabaseUrl} onChange={(e) => setSupabaseUrl(e.target.value)} className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm" />
            </Field>
            <Field label="Anon key">
              <input placeholder="eyJhbGciOi..." className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm" />
            </Field>
            <Field label="Service role (server-only)">
              <input type="password" placeholder="••••••••••••" className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm" />
            </Field>
            <Field label="Default schema">
              <input defaultValue="public" className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm" />
            </Field>
          </div>
          <div className="flex items-center gap-2 mt-4 text-xs text-muted-foreground">
            <Sparkles className="h-3 w-3 text-primary" /> Once connected, Intelligence OS will sync startups, sources, and workflow jobs.
          </div>
        </SectionCard>
      </div>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex items-center justify-between gap-4 py-2 border-b border-border last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <div className="min-w-[200px] flex-1 max-w-sm">{children}</div>
    </label>
  );
}

function ThemeOption({ active, onClick, icon: Icon, label }: { active: boolean; onClick: () => void; icon: typeof Sun; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-md border p-4 flex flex-col items-center gap-2 transition-all ${
        active ? "border-primary bg-primary/5" : "border-border hover:border-primary/40"
      }`}
    >
      <Icon className={`h-5 w-5 ${active ? "text-primary" : "text-muted-foreground"}`} />
      <span className="text-sm font-medium">{label}</span>
    </button>
  );
}
