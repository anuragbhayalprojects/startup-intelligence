# Database Refactor Strategy

## Core Principle

Reuse existing tables aggressively.

Avoid unnecessary normalization.

---

# Existing Tables

## startups

Purpose:
Canonical Company Intelligence Store

### Recommended Fields

```sql
company_intelligence JSONB
validation_metadata JSONB
aliases JSONB
enrichment_metadata JSONB
```

---

## startup_news

Purpose:
News Processing + Source Intelligence Store

### Recommended Fields

```sql
startup_mentions JSONB
raw_source_payload JSONB
cleaned_source_payload JSONB
resolution_metadata JSONB
pipeline_status JSONB
```

---

# JSONB-First Architecture

Use JSONB for:

* source payloads
* enrichment sections
* confidence metadata
* aliases
* AI traces
* retry metadata

This allows:

* schema flexibility
* modular enrichment
* partial updates
* re-enrichment
* easier debugging

---

# Avoid

* excessive relational joins
* highly normalized schemas
* unnecessary entity tables
* graph databases at current stage
