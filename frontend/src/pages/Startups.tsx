
import { useEffect, useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { Link } from "react-router-dom";
import { Startup } from "../types";

const rawApiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const API_URL = rawApiUrl.endsWith("/") 
  ? (rawApiUrl.endsWith("/api/") ? rawApiUrl.slice(0, -1) : rawApiUrl + "api") 
  : (rawApiUrl.endsWith("/api") ? rawApiUrl : rawApiUrl + "/api");

export default function Startups() {
  const [startups, setStartups] = useState<Startup[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchStartups() {
      try {
        const response = await fetch(`${API_URL}/startups`);
        if (!response.ok) {
          throw new Error("Failed to fetch startups");
        }
        const data = await response.json();
        setStartups(data);
      } catch (err: any) {
        setError(err.message || String(err));
      } finally {
        setIsLoading(false);
      }
    }
    fetchStartups();
  }, []);

  return (
    <>
      <PageHeader title="Startups" />
      {isLoading ? (
        <p>Loading...</p>
      ) : error ? (
        <p>Error: {error}</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {startups.map((s) => (
            <Link to={`/startups/${s.id}`} key={s.id} className="block p-4 border rounded-lg hover:shadow-md">
              <div className="font-bold">{s.startup_name}</div>
              <p className="text-sm text-gray-600">{s.description}</p>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
