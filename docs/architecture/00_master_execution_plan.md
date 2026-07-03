# Startup Intelligence OS — Master Refactor Execution Plan

## Objective

Refactor the existing Startup Intelligence OS into a modular, scalable, frontend-driven company intelligence architecture while preserving and reusing the existing working logic wherever possible.

---

# Mandatory Constraints

1. Reuse existing logic wherever possible
2. Refactor before rebuilding
3. Preserve existing working flows
4. Suggest alternatives before replacing major components
5. Minimize AI calls
6. Keep architecture modular
7. Externalize configs/prompts/templates
8. Maintain frontend compatibility
9. Avoid unnecessary database normalization
10. Use Graphify heavily before execution

---

# Existing Tables To Reuse

* startups
* startup_news

No unnecessary relational table expansion.

Prefer:

* JSONB
* modular payloads
* metadata objects
* extensible structures

---

# Final Architecture Goals

The final system must provide:

* accurate startup resolution
* frontend-ready company intelligence
* modular enrichment
* field-level re-enrichment
* minimal AI calls
* OpenRouter-first AI routing
* local-model fallback resilience
* scalable JSONB architecture
* clean execution traceability
* strong observability
* future extensibility

---

# Core Workflow

NEWS ARTICLE
→ ARTICLE CLEANING
→ STARTUP EXTRACTION
→ SINGLE STARTUP PROCESSING
→ DYNAMIC SEARCH
→ RAW SOURCE COLLECTION
→ CONTENT CLEANING
→ WEBSITE + LINKEDIN RESOLUTION
→ MODULAR ENRICHMENT
→ COMPANY INTELLIGENCE JSONB
→ FRONTEND COMPANY INTELLIGENCE TAB

---

# AI Layer Strategy

## AI Layer #1

Startup extraction

## AI Layer #2

Website + LinkedIn resolution

## AI Layer #3

Modular enrichment

Expected:
~4–6 AI calls per startup maximum.

---

# Execution Requirements

Before any major change:

1. Analyze current implementation
2. Generate Graphify outputs
3. Determine reuse opportunities
4. Suggest alternate approaches if necessary
5. Then proceed carefully

DO NOT blindly rebuild working logic.
