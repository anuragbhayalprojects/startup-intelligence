import { useEffect, useState } from "react";
import { fetchStartups } from "../lib/api";

export default function Startups() {
  const [startups, setStartups] = useState([]);

  useEffect(() => {
    async function loadData() {
      const data = await fetchStartups();
      setStartups(data);
    }

    loadData();
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">
        Startup Intelligence Dashboard
      </h1>

      <div className="grid gap-4">
        {startups.map((startup: any) => (
          <div
            key={startup.id}
            className="border rounded-lg p-4 shadow"
          >
            <h2 className="text-xl font-semibold">
              {startup.startup_name}
            </h2>

            <p>Sector: {startup.sector}</p>
            <p>City: {startup.city}</p>
            <p>Stage: {startup.funding_stage}</p>
            <p>BFSI Score: {startup.bfsi_score}</p>
          </div>
        ))}
      </div>
    </div>
  );
}