import { Routes, Route, Link } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import Dashboard from "./pages/Dashboard";
import Startups from "./pages/Startups";
import StartupDetails from "./pages/StartupDetails";
import Analytics from "./pages/Analytics";
import Assignments from "./pages/Assignments";
import Sources from "./pages/Sources";
import Workflow from "./pages/Workflow";
import Settings from "./pages/Settings";

function NotFound() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold">404</h1>
        <p className="mt-2 text-sm text-muted-foreground">Page not found.</p>
        <Link to="/" className="mt-6 inline-flex rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
          Go home
        </Link>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/startups" element={<Startups />} />
        <Route path="/startups/:id" element={<StartupDetails />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/assignments" element={<Assignments />} />
        <Route path="/sources" element={<Sources />} />
        <Route path="/workflow" element={<Workflow />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </AppShell>
  );
}
