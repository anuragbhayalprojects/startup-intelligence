# Developer Extension Blueprint Guide

This guide explains how to extend **Startup Intelligence OS**, providing step-by-step instructions for adding new AI agents, custom scrapers, database tables, and scoring parameters.

---

## 1. Adding a New RSS Scraper Target

To add a new RSS venture feed source:

1.  **Configure source parameters**: Open `backend/config/sources.json` and append a new source configuration object:
    ```json
    {
      "name": "TechSprout",
      "url": "https://techsprout.in/feed/",
      "type": "rss",
      "enabled": true
    }
    ```
2.  **Define parsing rules**:
    *   If the RSS feed uses non-standard XML tags, add custom parsing rules inside `backend/pipeline/news_aggregator.py`.
    *   Add custom regular expressions in `content_filters.json` to filter out newsletter sign-up links, disclaimers, or ads.

---

## 2. Adding a New Modular AI Enricher Section (v2 Parallel Pipeline)

To add a new enricher section (e.g., *Patent & IP Registry Enricher*):

1.  **Create Enricher Class**: Create a new class file under `backend/enrichment/` inheriting from `BaseEnricher`:
    ```python
    from backend.enrichment.base_enricher import BaseEnricher

    class PatentEnricher(BaseEnricher):
        def enrich_v2(self, startup_name, crawled_pages, all_snippets, orchestrator, **kwargs) -> dict:
            # Implement extraction logic using search snippets or website crawls
            # Call prompt gateways
            return {"patents_count": 0, "registered_trademarks": []}
    ```
2.  **Register class in Orchestrator**:
    *   Import and instantiate the class inside `_run_v2_enrichment` in `backend/workflows/agent_orchestrator.py`.
    *   Add the task to the parallel threads dictionary (`parallel_tasks`) to run it concurrently inside the ThreadPoolExecutor.
    *   Merge results into the `company_intelligence` state object.

---

## 3. Adding a New Priority Scoring Metric

To modify or add a new evaluation metric:

1.  **Define parameter variables**: Open `scoring_rules.json` and declare the new parameter's target weight (ensuring the sum of weights equals $1.0$):
    ```json
    {
      "weights": {
        "relevance": 0.30,
        "strategic_fit": 0.20,
        "deployability": 0.20,
        "signal_score": 0.15,
        "new_metric_weight": 0.15
      }
    }
    ```
2.  **Implement evaluation logic**:
    *   Update `ScoringService` inside `backend/services/scoring_service.py` to parse the new key from `company_intelligence`.
    *   Compute the metric's subscore ($0$ to $100$) and apply the weight vector in the final calculation.

---

## 4. Registering a New API Endpoint

To add a new route:

1.  **Define router path**: Open the appropriate router script in `backend/api/routes/` or create a new router file. Register the path:
    ```python
    @router.get("/startups/{startup_id}/patents")
    async def get_startup_patents(startup_id: str):
        # Implement DB lookup query logic
        return {"id": startup_id, "patents": []}
    ```
2.  **Include Router in Main**: If you created a new router file, import and register it inside `backend/main.py`:
    ```python
    from backend.api.routes import patents
    app.include_router(patents.router, prefix="/api")
    ```

---

## 5. Adding a New Database Table

To add a new table (e.g. `startup_patents`):

1.  **Write SQL migration script**: Create a SQL script inside `database/migrations/`:
    ```sql
    CREATE TABLE startup_patents (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        startup_id uuid REFERENCES startups(id) ON DELETE CASCADE,
        patent_number varchar UNIQUE NOT NULL,
        title text,
        granted_at date,
        created_at timestamptz DEFAULT now()
    );
    -- Enable Row Level Security (RLS)
    ALTER TABLE startup_patents ENABLE ROW LEVEL SECURITY;
    CREATE POLICY "Allow public read access" ON startup_patents FOR SELECT USING (true);
    ```
2.  **Run SQL query**: Apply the SQL script in your **Supabase dashboard SQL Editor**.
3.  **Update Python models**: Declare the new model and properties inside `backend/models/`.
