
import { useEffect, useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { Startup } from "../types";
import { Link } from "react-router-dom";

const API_URL = import.meta.env.VITE_API_URL;

export default function Home() {
  const [latestStartups, setLatestStartups] = useState<Startup[]>([]);

  useEffect(() => {
    async function fetchLatestStartups() {
      try {
        const response = await fetch(`${API_URL}/startups?limit=5`); // Example: fetching latest 5
        if (!response.ok) {
          throw new Error("Failed to fetch startups");
        }
        const data = await response.json();
        setLatestStartups(data);
      } catch (err) {
        console.error(err);
      }
    }
    fetchLatestStartups();
  }, []);

  return (
    <>
      <PageHeader title="Dashboard" />
      <div className="-mx-4 -mt-4 p-4 bg-gray-50 border-b border-gray-200">
        <h2 className="text-lg font-semibold">Welcome to your Startup Intelligence OS</h2>
        <p className="text-sm text-gray-600">Here is an overview of the latest startups and your team's activity.</p>
      </div>

      <div className="mt-8">
        <h3 className="text-lg font-semibold">Recently Added Startups</h3>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {latestStartups.map((s) => (
            <Link to={`/startups/${s.id}`} key={s.id} className="block p-4 border rounded-lg hover:shadow-md">
              <div className="font-bold">{s.startup_name}</div>
              <p className="text-sm text-gray-600 truncate">{s.description}</p>
              <div className="text-xs text-gray-500 mt-2">Source: {s.source}</div>
            </Link>
          ))}
        </div>
      </div>
    </>
  );
}
