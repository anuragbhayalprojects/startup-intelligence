# Current State Analysis

# Objective

Before implementing any architectural changes, fully understand the existing codebase and preserve reusable logic.

---

# Mandatory Analysis Areas

## Backend

Analyze:

* APIs
* orchestration flow
* enrichment pipeline
* workers/cron jobs
* Supabase interactions
* caching
* retry handling
* AI integrations
* queue systems

---

## Frontend

Analyze:

* Company Intelligence tab
* rendering structure
* section dependencies
* re-enrichment triggers
* API expectations
* state management

---

## Database

Analyze:

* startups table usage
* startup_news table usage
* JSONB patterns
* indexing strategy
* current relationships
* update frequency

---

## AI Layer Analysis

Inspect:

* current prompts
* model usage
* retry logic
* hallucination handling
* structured extraction patterns
* confidence scoring logic

---

# Graphify Requirements

Generate:

* execution flow graphs
* dependency graphs
* request lifecycle graphs
* enrichment lifecycle graphs
* database update graphs

before refactoring major systems.

---

# Critical Rule

DO NOT replace working logic blindly.

First determine:

* reuse opportunities
* optimization opportunities
* modularization opportunities
* extraction opportunities

before rewriting anything.
