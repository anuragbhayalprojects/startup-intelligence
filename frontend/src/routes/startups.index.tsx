import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/PageHeader";
import { StartupTable } from "@/components/StartupTable";
import { STARTUPS } from "@/lib/mock-data";

export const Route = createFileRoute("/startups/")({
  head: () => ({ meta: [{ title: "Startup Explorer · ICICI SIOS" }] }),
  component: Explorer,
});

function Explorer() {
  return (
    <>
      <PageHeader
        title="Startup Explorer"
        description="Discover, filter and analyse the full universe of tracked startups. Search across sectors, cities, funding stages and assigned teams."
      />
      <StartupTable data={STARTUPS} pageSize={12} />
    </>
  );
}
