import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Search,
  Sparkles,
  ClipboardList,
  BarChart3,
  Workflow,
  Radio,
  Bookmark,
  Settings,
  Bell,
  Building2,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";

const NAV = [
  { to: "/", label: "Executive Dashboard", icon: LayoutDashboard },
  { to: "/startups", label: "Startup Explorer", icon: Search },
  { to: "/insights", label: "AI Insights", icon: Sparkles },
  { to: "/assignments", label: "Assignments", icon: ClipboardList },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/workflow", label: "Workflow Monitor", icon: Workflow },
  { to: "/sources", label: "Sources Monitor", icon: Radio },
  { to: "/saved", label: "Saved Startups", icon: Bookmark },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <aside className="hidden lg:flex w-64 shrink-0 flex-col bg-sidebar text-sidebar-foreground border-r border-sidebar-border">
        <div className="px-5 py-5 border-b border-sidebar-border">
          <div className="flex items-center gap-2.5">
            <div className="size-9 rounded-lg bg-primary grid place-items-center text-primary-foreground font-bold shadow-elegant">
              IC
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold text-sidebar-foreground">ICICI Group</div>
              <div className="text-[11px] text-sidebar-foreground/60">Startup Intelligence OS</div>
            </div>
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV.map((item) => {
            const active =
              item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
            const Icon = item.icon;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors",
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                    : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                )}
              >
                <Icon className="size-4" />
                <span className="truncate">{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="px-3 py-3 border-t border-sidebar-border">
          <div className="flex items-center gap-2.5 px-2 py-2">
            <Avatar className="size-8">
              <AvatarFallback className="bg-primary text-primary-foreground text-xs">AM</AvatarFallback>
            </Avatar>
            <div className="leading-tight min-w-0">
              <div className="text-sm font-medium truncate">Aarav Mehta</div>
              <div className="text-[11px] text-sidebar-foreground/60 truncate">Ventures Team</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b border-border bg-card/80 backdrop-blur sticky top-0 z-10 flex items-center px-4 lg:px-6 gap-3">
          <div className="lg:hidden flex items-center gap-2">
            <div className="size-7 rounded-md bg-primary grid place-items-center text-primary-foreground font-bold text-xs">IC</div>
            <span className="font-semibold text-sm">ICICI SIOS</span>
          </div>
          <div className="flex-1 max-w-md relative">
            <Search className="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search startups, insights, teams..."
              className="pl-9 h-9 bg-background"
            />
          </div>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" className="size-9">
              <Bell className="size-4" />
            </Button>
            <Button variant="ghost" size="icon" className="size-9">
              <Building2 className="size-4" />
            </Button>
          </div>
        </header>
        <main className="flex-1 px-4 lg:px-8 py-6 max-w-[1600px] w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
