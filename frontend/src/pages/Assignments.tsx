import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge, statusTone, priorityTone } from "../components/StatusBadge";
import { assignments } from "../data/mock";

export default function Assignments() {
  return (
    <>
      <PageHeader title="Assignments" description="Who's working with whom — across M&A, Partnerships, Innovation and Risk." />

      <SectionCard>
        <div className="overflow-x-auto -mx-5">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-muted-foreground border-b border-border">
                <th className="px-5 py-3 font-medium">Startup</th>
                <th className="px-5 py-3 font-medium">Team</th>
                <th className="px-5 py-3 font-medium">Owner</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Priority</th>
                <th className="px-5 py-3 font-medium">Updated</th>
              </tr>
            </thead>
            <tbody>
              {assignments.map((a) => (
                <tr key={a.id} className="border-b border-border hover:bg-muted/30">
                  <td className="px-5 py-3">
                    <Link to={`/startups/${a.startupId}`} className="font-medium hover:text-primary">
                      {a.startupName}
                    </Link>
                  </td>
                  <td className="px-5 py-3 text-muted-foreground">{a.team}</td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-7 w-7 rounded-full bg-primary/10 text-primary text-[11px] font-semibold flex items-center justify-center">
                        {a.owner.split(" ").map((n) => n[0]).join("")}
                      </div>
                      {a.owner}
                    </div>
                  </td>
                  <td className="px-5 py-3"><StatusBadge tone={statusTone(a.status)}>{a.status}</StatusBadge></td>
                  <td className="px-5 py-3"><StatusBadge tone={priorityTone(a.priority)}>{a.priority}</StatusBadge></td>
                  <td className="px-5 py-3 text-muted-foreground">{a.updatedAt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </>
  );
}
