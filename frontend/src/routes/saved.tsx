import { createFileRoute, Link } from "@tanstack/react-router";
import { Bookmark } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { StartupTable } from "@/components/StartupTable";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { STARTUPS } from "@/lib/mock-data";
import { useSavedStartups } from "@/store/saved-startups";

export const Route = createFileRoute("/saved")({
  head: () => ({ meta: [{ title: "Saved Startups · ICICI SIOS" }] }),
  component: SavedPage,
});

function SavedPage() {
  const { saved } = useSavedStartups();
  const list = STARTUPS.filter((s) => saved.has(s.id));

  return (
    <>
      <PageHeader
        title="Saved Startups"
        description="Your personal watchlist of bookmarked startups."
      />
      {list.length === 0 ? (
        <EmptyState
          icon={Bookmark}
          title="No saved startups yet"
          description="Bookmark startups from the Explorer or detail pages to track them here."
          action={
            <Link to="/startups">
              <Button>Browse Explorer</Button>
            </Link>
          }
        />
      ) : (
        <StartupTable data={list} pageSize={10} />
      )}
    </>
  );
}
