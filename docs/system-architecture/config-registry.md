# Configuration & Externalization Registry

This registry lists every configurable setting, thresholds configuration, and file location inside the **Startup Intelligence OS**. Decoupled parameter boundaries allow you to customize pipeline behaviour without editing source code.

---

## 1. Global Configurations Matrix

| Setting Name | Default Value | File Location | Loaded By | Purpose | Hot Reload? | Restart Req? | User Edit? |
|---|---|---|---|---|---|---|---|
| `SUPABASE_URL` | | `.env` | `supabase_service.py` | Target Supabase host endpoint link. | No | Yes | No |
| `SUPABASE_KEY` | | `.env` | `supabase_service.py` | Authenticating API requests to Supabase. | No | Yes | No |
| `OLLAMA_HOST` | `http://localhost:11434` | `.env` | `providers/ollama.py` | Local Ollama engine host. | No | Yes | No |
| `OPENROUTER_API_KEY`| | `.env` | `providers/openrouter.py`| Token keys for cloud routing. | No | Yes | No |
| `use_v2_pipeline` | `true` | `pipeline_config.json` | `agent_orchestrator.py` | Toggle parallel modular enrichment. | Yes | No | No |
| `parallel_workers` | `5` | `pipeline_config.json` | `agent_orchestrator.py` | Thread count for Parallel Enrichers. | Yes | No | No |
| `polling_enabled` | `false` | `scheduler.json` | `scheduler.py` | Toggle background feed scraper loop. | Yes | No | Yes |
| `default_poll_interval_minutes` | `60` | `scheduler.json` | `scheduler.py` | Delay period between feed checks. | Yes | No | No |
| `digest_scheduler_enabled` | `true` | `scheduler.json` | `scheduler.py` | Toggle daily digest emails dispatch. | Yes | No | No |
| `email.frequency` | `"twice_daily"` | `email_config.json` | `email_service.py` | Scheduling frequency of digests. | Yes | No | No |
| `email.times` | `["09:00", "18:00"]` | `email_config.json` | `email_service.py` | Specific daily trigger dispatch times. | Yes | No | No |
| `email.recipient_list` | | `email_config.json` | `email_service.py` | Recipient target emails. | Yes | No | Yes |
| `jaccard_similarity_threshold` | `0.60` | `deduplication_rules.json`| `deduplicator.py` | Auto-merge token overlap match rate. | Yes | No | No |
| `low_trust_threshold` | `50` | `crawler_rules.json` | `agent_orchestrator.py` | Confidence below which Playwright is launched. | Yes | No | No |
| `playwright_min_text_len` | `200` | `crawler_rules.json` | `agent_orchestrator.py` | Min text length triggering Playwright fallback. | Yes | No | No |
| `playwright_timeout_ms` | `5000` | `crawler_rules.json` | `agent_orchestrator.py` | Max wait time for page crawl tasks. | Yes | No | No |
| `weights.relevance` | `0.35` | `scoring_rules.json` | `ScoringService` | Relevance weight in scoring rubric. | Yes | No | No |

---

## 2. Injected System Prompt Templates

Prompt instructions are stored as text files inside `backend/prompts/` and loaded dynamically on agent execution:

*   **`name_discovery_prompt.txt`**: Maps rules for identifying startup names in scraped text.
*   **`ingestion_summary_prompt.txt`**: Governs synthesis and output format of article summaries.
*   **`strategic_analysis_prompt.txt`**: Guides evaluations of strategic fit and partner opportunities.
*   **`competitor_extraction_prompt.txt`**: Directs competitors identification and mapping.

> [!TIP]
> **Modifying Prompts**: You can adjust rules, examples, and output constraints directly in these prompt files. Modified instructions are loaded on the next agent run without requiring a server restart.

---

## 3. Feed Sources Configuration (`backend/config/sources.json`)

Feed sources crawled by the News Aggregator are defined in `sources.json`:

```json
[
  {
    "name": "Inc42",
    "url": "https://inc42.com/feed/",
    "type": "rss",
    "enabled": true
  },
  {
    "name": "Entrackr",
    "url": "https://entrackr.com/feed/",
    "type": "rss",
    "enabled": true
  }
]
```

Adding a new RSS feed target or disabling an existing crawler can be done directly by modifying this file.

---

## 4. Code References & Cross-Links
*   For details on the news sync loop, see **[Trigger Event Catalog](file:///Users/anurag/Projects/startup-intelligence/docs/system-architecture/trigger-catalogue.md)**.
*   For the scoring weight definitions, see **[Processing Pipeline Deep-Dive](file:///Users/anurag/Projects/startup-intelligence/docs/system-architecture/processing-pipeline.md)**.
