# News Processing Pipeline

# Final Workflow

NEWS ARTICLE
↓
ARTICLE INGESTION
↓
ARTICLE CLEANING
↓
AI LAYER #1:
STARTUP EXTRACTION
↓
startup_mentions JSONB
↓
FOR EACH STARTUP:
↓
DYNAMIC SEARCH GENERATION
↓
SEARCH EXECUTION
↓
TEMPLATE FALLBACK SEARCHES
↓
RAW SOURCE COLLECTION
↓
RAW SOURCE JSONB STORAGE
↓
CONTENT CLEANING & SEGMENTATION
↓
CLEANED SOURCE JSONB STORAGE
↓
AI LAYER #2:
WEBSITE + LINKEDIN RESOLUTION
↓
CANONICAL STARTUP IDENTIFIED
↓
AI LAYER #3:
MODULAR ENRICHMENT
↓
SECTION-WISE COMPANY INTELLIGENCE JSONB
↓
STORE IN startups TABLE
↓
FRONTEND COMPANY INTELLIGENCE TAB

---

# Startup Extraction Structure

```json
[
  {
    "startup_name": "",
    "article_context": "",
    "source_description": ""
  }
]
```

---

# Important Rules

* Process ONE startup independently
* Avoid multi-startup enrichment contamination
* Avoid heavy claim extraction
* Avoid unnecessary relationship graphs
* Keep extraction lightweight and structured
