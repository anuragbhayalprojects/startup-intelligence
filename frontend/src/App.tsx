import { useEffect, useState } from "react";
import API from "./services/api";

interface Startup {
  id: string;
  startup_name: string;
  sector: string;
  city: string;
  country: string;
  source: string;
  analysis: any;
}

function App() {

  const [startups, setStartups] = useState<Startup[]>([]);

  useEffect(() => {

    fetchStartups();

  }, []);

  const fetchStartups = async () => {

    try {

      const response = await API.get("/startups");

      setStartups(response.data);

    } catch (error) {

      console.error(error);

    }

  };

  return (

    <div className="min-h-screen bg-black text-white p-8">

      <h1 className="text-4xl font-bold mb-8">
        Startup Intelligence OS
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

        {startups.map((startup) => (

          <div
            key={startup.id}
            className="bg-zinc-900 border border-zinc-800 rounded-xl p-6"
          >

            <h2 className="text-2xl font-semibold mb-2">
              {startup.startup_name}
            </h2>

            <p className="text-zinc-400 mb-2">
              {startup.sector}
            </p>

            <p className="text-zinc-400 mb-2">
              {startup.city}, {startup.country}
            </p>

            <p className="text-sm text-green-400 mb-4">
              Source: {startup.source}
            </p>

            <div className="text-sm text-zinc-300">
              {startup.analysis?.summary || "No summary available"}
            </div>

          </div>

        ))}

      </div>

    </div>

  );

}

export default App;