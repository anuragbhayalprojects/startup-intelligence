# Build & Run Tools Registry

This document lists all the languages, frameworks, developer tools, libraries, and utilities used to build, test, and run the **Startup Intelligence OS**.

---

## 1. Core Development Platforms & Runtimes

*   **Python (v3.10 / v3.11)**: Core backend programming language. Provides virtual environment boundary execution hooks (`venv`).
*   **Node.js (v18 / v20)**: Frontend JavaScript compilation runtime engine and package ecosystem manager (`npm`).

---

## 2. Backend & Scraping Stack

*   **FastAPI**: Modern, high-performance web framework for Python API routing. Implements path routing, validation error handling, and background thread mappings.
*   **Uvicorn**: Lightning-fast ASGI web server implementation used to run FastAPI applications locally and in production.
*   **BeautifulSoup4 / lxml**: Fast HTML parsing libraries used inside news scrapers to sanitize body paragraphs.
*   **Playwright**: Headless browser automation library used to execute JavaScript rendering on websites and bypass anti-scraping paywalls.
*   **Feedparser**: Parsing library used to fetch and standardize unstructured RSS/XML venture news feeds.

---

## 3. AI & Search Integration

*   **Ollama Server**: Local AI inference engine used to serve open-source language models.
    *   **Default Model**: `qwen2.5:3b` (fast, lightweight reasoning).
*   **OpenRouter Client API**: Cloud gateway interface used for failover models routing (e.g. Gemini, Mistral) when Ollama latency limits are exceeded.
*   **Jaccard Similarity Algorithm**: Mathematical metric used to calculate syntactic overlap between article headlines.
*   **RAG Local Vector Cache**: Local filesystem JSON cache (`rag_embeddings.json`) storing calculated text chunk vector representations to reduce embedding calls.

---

## 4. Frontend & Layout Engine

*   **Vite**: Frontend build tool and dev server providing hot module replacement (HMR).
*   **React (v18)**: Component-based UI rendering layer.
*   **TypeScript**: Static typechecker for frontend logic components.
*   **Tailwind CSS**: Utility-first styling framework used to build premium SaaS dashboards.
*   **Lucide React**: Clean vector icon suite for sidebar panels, badges, and triggers.
*   **Recharts**: Interactive data charting library used to render priority score distributions.

---

## 5. Storage, Database, & Telemetry

*   **Supabase Client SDK**: Javascript & Python APIs connecting to the remote database cluster.
*   **PostgreSQL**: Relational database engine containing RLS (Row Level Security) schemas.
*   **Database Migrations Engine**: Sequential SQL migration scripts executed inside the Supabase SQL Editor.
*   **Tracing Middleware**: Intercepts backend CRUD method requests to monitor latencies and log telemetry trace schemas.

---

## 6. Development, Linting, & Build Utilities

*   **git**: Version control management tool.
*   **pytest**: Unit-testing framework for routing scripts, scraping filters, and Jaccard calculations.
*   **compileall**: Python standard library utility used to verify clean compilation of all backend modules.
*   **Graphify**: Knowledge graph generation tool used to map codebase dependencies, calculate coupling paths, and fetch structured code contexts.
