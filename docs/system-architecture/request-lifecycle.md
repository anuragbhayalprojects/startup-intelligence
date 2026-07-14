# Request Lifecycle & Sequence Flows

This document traces the request, processing, and database execution lifecycle for the two primary operations in the **Startup Intelligence OS**: Manual News Feed Ingestion and Single Startup Enrichment.

---

## 1. News Ingestion Workflow (Manual Sync Feed)

This workflow traces the sequence of operations when a user triggers a manual sync of news feeds from the React dashboard.

### sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as "Analyst (User)"
    participant UI as "React Client (Dashboard)"
    participant API as "FastAPI Router (/news/trigger)"
    participant Proc as NewsProcessor
    participant Agg as NewsAggregator
    participant Dedup as Deduplicator
    participant GW as "AI Gateway (Ollama/OR)"
    participant DB as "Supabase DB"

    User->>UI: Click "Sync News Feed"
    UI->>API: POST /api/news/trigger (selected_sources, limit)
    Note over API: Generates request-level TRACE_ID
    API->>DB: INSERT root trace to obs_traces
    API-->>UI: 200 OK (Status: Sync Active)
    Note over UI: Renders Live Log Console & Spinner
    
    rect rgb(240, 248, 255)
        Note over API: Spawns Ingestion Thread
        API->>Proc: run_ingestion_pipeline(sources, limit)
        Proc->>Agg: fetch_all_raw_articles()
        Agg-->>Proc: Raw RSS feed objects list
        Proc->>Dedup: cluster_and_deduplicate(raw_articles)
        
        loop Duplicate Check
            Dedup->>Dedup: Jaccard overlap check (Syntactic)
            opt Moderate Overlap (0.30 - 0.60)
                Dedup->>GW: are_contexts_describing_same_event()
                GW-->>Dedup: Boolean Match Response
            end
        end
        Dedup-->>Proc: Clean Canonical Stories List
        
        loop For Each Canonical Story
            Proc->>Proc: Fetch web page & apply 9-layer filter
            Proc->>GW: discover_startup_names(headline, clean_paragraphs)
            Note over GW: Runs single-pass prompt (names + summary)
            GW-->>Proc: JSON (startups[], ai_summary)
            Proc->>DB: INSERT/UPDATE news_articles table
            Proc->>DB: UPDATE sync status logs (real-time stream)
        end
    end
    
    Proc->>API: Execution Completed
    Note over API: Reset sync status active = false
    UI->>API: GET /api/news/sync/status (polling tick)
    API-->>UI: Ingestion Idle (completed_at timestamp)
    UI->>User: Renders Ingestion Sync Success Banner
```

---

## 2. Startup Resolution & Enrichment Workflow ("Add & Enrich Profile")

This workflow traces the sequence of operations when an analyst clicks **"Add & Enrich Profile"** for a discovered startup mention inside an article drawer.

### sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as "Analyst (User)"
    participant UI as "React Client (News Drawer)"
    participant API as "FastAPI Router (/resolve-startup)"
    participant DB as "Supabase DB"
    participant Orch as AgentOrchestrator
    participant Discovery as IdentityDiscoveryAgent
    participant Resolution as IdentityResolutionAgent
    participant Enricher as "Parallel Modular Enrichers"

    User->>UI: Click "Add & Enrich Profile"
    UI->>API: POST /api/news/resolve-startup (startup_name, article_id, enrich=true)
    
    rect rgb(255, 248, 240)
        Note over API: Synchronous Database Setup
        API->>DB: INSERT into startups table (Basic placeholder)
        DB-->>API: Returns startup_id
        API->>DB: UPDATE startups status = "Enriching"
        API->>DB: UPDATE news_articles (Link startup_id to mentions)
        API->>DB: INSERT into startup_news (Link news history)
    end
    
    API-->>UI: 200 OK (resolving startup_id, website)
    Note over UI: Instantly renders SOLID badge with redirect arrow in Drawer
    
    rect rgb(240, 255, 240)
        Note over API: Spawns Background Task Thread
        API->>API: Generate TRACE_ID for background worker
        API->>DB: INSERT root trace in obs_traces
        API->>Orch: run_pipeline(startup_id, startup_name, enrich=true)
        
        Orch->>Discovery: run(state)
        Note over Discovery: Web search / crawls homepage
        Discovery-->>Orch: Discovered raw crawled text
        
        Orch->>Resolution: run(state)
        Note over Resolution: Vets website matching context
        Resolution-->>Orch: Confidence score & status
        
        opt Confidence Score >= 20%
            Orch->>Enricher: Parallel Thread Pool Exec (5 workers)
            Note over Enricher: Runs Corporate, Identity, Products, Funding, Competitors
            Enricher-->>Orch: Bucketed JSON patches
            Orch->>Orch: Compute priority score & Strategic alignment
            Orch->>DB: UPDATE startups table (company_intelligence JSONB)
            Orch->>DB: INSERT into startup_analysis
        end
    end
    
    Note over Orch: Task completed & status updated
```

---

## 3. Observability & Database Mutation Telemetry

Every write transaction executed during these lifecycles is intercepted by the backend tracing utility class:
1.  **Intercepted Execute**: When a repository script invokes `.execute()` on the Supabase client builder, the wrapper `wrap_supabase_client` intercepts the method call.
2.  **Generate transaction ID**: Generates a random transaction ID prefix `TXN_[a-z0-9]{16}`.
3.  **Trace context binding**: Fetches the active `trace_id` from the thread's `ContextVar` namespace.
4.  **Telemetry log**: Inserts a log record into the `obs_db_mutations` table capturing:
    *   Target database table name (e.g. `startups`).
    *   Operation action type (`INSERT`, `UPDATE`, `DELETE`, `SELECT`).
    *   Count of database rows affected.
    *   Query transaction execution duration (latency in milliseconds).
5.  **Failure tolerance**: DB logging operations are wrapped in safe try-except blocks. If the observability log fails, the primary database transaction execution continues unaffected.

---

## 4. Code References & Cross-Links
*   For API routes registration, see **[Backend Architecture](file:///Users/anurag/Projects/startup-intelligence/docs/system-architecture/backend-architecture.md)**.
*   For DB schemas, see **[Database Architecture](file:///Users/anurag/Projects/startup-intelligence/docs/system-architecture/database-schema.md)**.
