import { useEffect, useState } from "react";
import { fetchStartups } from "../lib/api";

export default function Startups() {
  const [startups, setStartups] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await fetchStartups();

        console.log("RAW API RESPONSE:", data);
        console.log("IS ARRAY:", Array.isArray(data));

        // ✅ SAFE GUARD (this fixes your crash)
        setStartups(Array.isArray(data) ? data : []);

      } catch (error) {
        console.error("Fetch error:", error);
        setStartups([]);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  if (loading) {
    return <div className="p-6">Loading startups...</div>;
  }

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">
        Startup Intelligence Dashboard
      </h1>

      <div className="grid gap-4">
        {Array.isArray(startups) && startups.length > 0 ? (
          startups.map((startup: any) => (
            <div key={startup.id} className="border rounded-lg p-4 shadow">
              <h2 className="text-xl font-semibold">
                {startup.startup_name}
              </h2>

              <p>Sector: {startup.sector}</p>
              <p>City: {startup.city}</p>
              <p>Stage: {startup.funding_stage}</p>
              <p>BFSI Score: {startup.bfsi_score}</p>
            </div>
          ))
        ) : (
          <div className="text-red-500">
            No startups found or API returned invalid data
          </div>
        )}
      </div>
    </div>
  );
}