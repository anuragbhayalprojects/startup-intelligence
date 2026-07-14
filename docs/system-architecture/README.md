# Startup Intelligence OS — Master Architecture Suite

## 1. Overview
This is the master entry point and technical architecture documentation suite for **Startup Intelligence OS**, a retrieval-first, AI-powered intelligence platform built for the **Startup Engagement & Investments team at ICICI Group**. 

Rather than a generic database client, this platform implements a modular, high-volume pipeline that aggregates real-time startup news feeds, groups duplicate coverage, isolates relevant startup entities, resolves their company details, enriches their corporate profile, and computes a multi-dimensional strategic relevance score to match them with business teams and Relationship Managers.

---

## 2. Business Objectives & Vision
*   **Venture Discovery**: Automatically surface and track fast-growing startups in target sectors (FinTech, InsurTech, WealthTech, SaaS, DeepTech) long before they reach mature public fundraising rounds.
*   **ICICI Business Alignment**: Automatically match discovered startups to specific corporate business units (e.g. Retail Banking, Wealth Management, ICICI Prudential, ICICI Securities) and strategic focus areas based on a deterministic evaluation rubric.
*   **Investment & Partnership Pipeline**: Shorten the discovery-to-engagement lifecycle for Relationship Managers (RMs) and investment analyst teams by providing rich, pre-vetted corporate intelligence profiles.

---

## 3. Core Architectural Principles
*   **Retrieval-First AI Architecture**: Rather than feeding raw, unformatted web dumps directly to expensive LLMs, the platform runs a structured scraping and cleaning process first. Text is segmented and retrieved via keyword/vector similarity matches, keeping LLM prompts tight, focused, and low-cost.
*   **Deterministic Logic Preference**: AI is reserved strictly for tasks requiring cognitive reasoning (e.g. classification alignment, unstructured name extraction, and strategic synthesis). Computations, scoring formulas, Jaccard deduplication, and relationship assignments are calculated deterministically in code.
*   **Externalized Prompts & Rules**: Prompts, scoring weights, relationship mappings, and scraping filters are completely decoupled from code into `.txt` and `.json` files for hot-reloading and modular optimization.
*   **Local-First Execution**: The platform routes reasoning tasks to a local Ollama model (e.g., `qwen2.5:3b`) by default, with automatic failover to cloud models (e.g. OpenRouter/Claude) when local latency thresholds are exceeded.

---

## 4. Technology Stack
*   **Frontend**: React (Vite, TypeScript, Tailwind CSS, Lucide icons, Recharts).
*   **Backend**: Python (FastAPI, BeautifulSoup4, Requests, Pydantic, HTTPX).
*   **Database & Telemetry**: Supabase (PostgreSQL, Real-Time tables, RLS policies, JSONB storage schemas).
*   **AI Gateway & Model Engine**: Local Ollama Server (`qwen2.5:3b` default model) + OpenRouter Client (cloud fallbacks).

---

## 5. System Block Diagram

```mermaid
graph TD
    subgraph Web Client (Frontend)
        UI[React Dashboard]
        Logs[Real-Time Terminals]
        Drawer[News Side-Drawer Reader]
    end

    subgraph API & Pipeline Layer (Backend)
        Router[FastAPI Routing Server]
        Aggregator[News Aggregator Engine]
        Deduplicator[Semantic Deduplicator]
        Processor[News Ingestion Pipeline]
        Orchestrator[Agent Orchestrator Workflow]
        Scraper[Common Context Scrapers]
    end

    subgraph AI Gateway & Models
        Gateway[AI Gateway Router]
        LocalOllama[("Local Ollama Qwen2.5")]
        CloudOR[OpenRouter Cloud API]
    end

    subgraph Storage & Telemetry
        DB[("Supabase PostgreSQL")]
        RLS[Row Level Security]
        Obs[Observability Traces]
    end

    subgraph External Feeds
        RSS[RSS / Google News Feeds]
        Playwright[Dynamic Playwright Browser]
    end

    %% Flow Connections %%
    RSS -->|RSS Fetch| Aggregator
    UI -->|Manual Trigger| Router
    Router -->|Background Ingestion| Processor
    Aggregator --> Deduplicator
    Deduplicator -->|Semantic Check| Gateway
    Processor -->|Scrape URL| Scraper
    Scraper -->|Playwright Crawl| Playwright
    Processor -->|Enrich Startup| Orchestrator
    Orchestrator -->|Reasoning Tasks| Gateway
    Gateway -->|Default Route| LocalOllama
    Gateway -->|Failover Route| CloudOR
    Orchestrator -->|Save Data| DB
    Processor -->|Telemetry Log| Obs
    Obs --> DB
    DB -->|Fetch Grid| UI
    Logs -->|Event Stream| Router
```

---

## 6. Technical Documentation Catalog

Follow the detailed structural logs of each sub-module using the links below:

1.  **[Repository Architecture](file:///Users/anurag/Projects/startup-intelligence/docs/system-architecture/repository-architecture.md)**: Repository folder layout, class responsibilities, dependencies, and code boundaries.
2.  **[Startup Intelligence Lifecycle](file:///Users/anurag/Projects/startup-intelligence/docs/system-architecture/intelligence-lifecycle.md)**: Visual mapping of the end-to-end 20-stage business lifecycle from raw news RSS feed to resolved, vetted registry records.
3.  **[Request Lifecycle & Sequences](file:///Users/anurag/Projects/startup-intelligence/docs/system-architecture/request-lifecycle.md)**: Sequence execution loops tracing client requests, background async threads, and database telemetry mutations.
4.  **[AI Layer & Prompt Engineering](file:///Users/anurag/Projects/startup-intelligence/docs/system-architecture/ai-architecture.md)**: Gateway model routing, failover thresholds, prompt configurations, and vector embeddings cache mechanics.
5.  **[Processing Pipeline Deep-Dive](file:///Users/anurag/Projects/startup-intelligence/docs/system-architecture/processing-pipeline.md)**: Discovery, Resolution, and Enrichment phases, Jaccard headlines deduplication, and the strategic evaluation scoring rubric.
6.  **[Database Architecture & Schema](file:///Users/anurag/Projects/startup-intelligence/docs/system-architecture/database-schema.md)**: ER diagram representation, table constraints, RLS policies, and structured JSONB schemas.
7.  **[Configuration Registry](file:///Users/anurag/Projects/startup-intelligence/docs/system-architecture/config-registry.md)**: Complete catalog of environment variables, scoring weights, time scheduling rates, and hot-reloading boundaries.
8.  **[Trigger Event Catalog](file:///Users/anurag/Projects/startup-intelligence/docs/system-architecture/trigger-catalogue.md)**: Events matrix detailing startup checks, scheduled cron ingestion loops, manual resolution inputs, and UI button actions.
9.  **[Local Development Setup Guide](file:///Users/anurag/Projects/startup-intelligence/docs/system-architecture/local-deployment.md)**: Setup instructions for Python venv, Node packages, Ollama model pulling, and Supabase migrations.
10. **[Future Extension Guide](file:///Users/anurag/Projects/startup-intelligence/docs/system-architecture/future-extension.md)**: Blueprints for developers adding new scoring rubrics, AI agents, scraping sources, or dashboard pages.
