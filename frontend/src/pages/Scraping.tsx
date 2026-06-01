import { useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { Button } from '../components/ui/button'; // Assuming you have a Button component
import { Input } from '../components/ui/input'; // Assuming you have an Input component
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'; // Assuming a Select component
import { Loader2, CheckCircle, AlertTriangle } from 'lucide-react';

const rawApiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const API_URL = rawApiUrl.endsWith("/") 
  ? (rawApiUrl.endsWith("/api/") ? rawApiUrl.slice(0, -1) : rawApiUrl + "api") 
  : (rawApiUrl.endsWith("/api") ? rawApiUrl : rawApiUrl + "/api");

export default function Scraping() {
    const [source, setSource] = useState('zyte');
    const [numStartups, setNumStartups] = useState(10);
    const [isLoading, setIsLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState<string | null>(null);

    const handleScrape = async () => {
        setIsLoading(true);
        setResult(null);
        setError(null);

        try {
            const response = await fetch(`${API_URL}/scrape`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ source, num_startups: numStartups }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Scraping failed');
            }

            setResult(data);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <>
            <PageHeader title="Scraping Console" description="Run scrapers to gather fresh startup data."/>

            <SectionCard title="Scraper Configuration">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label htmlFor="source" className="block text-sm font-medium text-gray-700 mb-1">Source</label>
                        <Select value={source} onValueChange={setSource}>
                            <SelectTrigger>
                                <SelectValue placeholder="Select a source" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="zyte">Zyte</SelectItem>
                                <SelectItem value="inc42">Inc42</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div>
                         <label htmlFor="numStartups" className="block text-sm font-medium text-gray-700 mb-1">Number of Startups</label>
                         <Input 
                            id="numStartups"
                            type="number"
                            value={numStartups}
                            onChange={(e) => setNumStartups(parseInt(e.target.value, 10))}
                            min="1"
                            max="100"
                         />
                    </div>
                    <div className="md:self-end">
                        <Button onClick={handleScrape} disabled={isLoading} className="w-full md:w-auto">
                            {isLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : null}
                            {isLoading ? 'Scraping...' : 'Start Scraping'}
                        </Button>
                    </div>
                </div>
            </SectionCard>

            {result && (
                 <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-md">
                    <div className="flex items-center gap-3">
                        <CheckCircle className="h-5 w-5 text-green-600"/>
                        <p className="text-sm text-green-800">{result.message}</p>
                    </div>
                 </div>
            )}

            {error && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
                    <div className="flex items-center gap-3">
                        <AlertTriangle className="h-5 w-5 text-red-600"/>
                        <p className="text-sm text-red-800">Error: {error}</p>
                    </div>
                </div>
            )}
        </>
    );
}
