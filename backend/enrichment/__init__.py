"""
backend/enrichment/__init__.py
--------------------------------
Modular enrichment package for Startup Intelligence OS — v2.

Enrichment modules (AI Layer 3):

  v2 Enrichers (search-first, parallel, field-bucketed):
    CorporateEnricher     — legal name, HQ, founded year, website, linkedin, one-liner
    IdentityEnricher      — founders and leadership team (founders only, no corporate facts)
    ProductEnricher       — products, industry, business model, taxonomy
    FundingEnricher       — funding rounds, investors, valuation stage
    CompetitorEnricher    — direct/indirect competitors, competitive summary
    IntelligenceEnricher  — BFSI strategic analysis, relevance scoring, opportunities

Each v2 enricher:
  - Implements enrich_v2(startup_name, crawled_pages, all_snippets, orchestrator)
  - Uses BaseEnricher._detect_missing_fields() + _run_fallback() for automatic fallback
  - Returns a flat section dict (not nested company_intelligence keys)
  - v1 enrich() / enrich_from_state() bridges preserved for backward compatibility

The v2 pipeline runs enrichers in parallel via ThreadPoolExecutor (5 workers).
Feature flag: pipeline_config.json → v2_pipeline.use_v2_pipeline: true
"""

from backend.enrichment.base_enricher import BaseEnricher
from backend.enrichment.corporate_enricher import CorporateEnricher
from backend.enrichment.identity_enricher import IdentityEnricher
from backend.enrichment.product_enricher import ProductEnricher
from backend.enrichment.funding_enricher import FundingEnricher
from backend.enrichment.competitor_enricher import CompetitorEnricher
from backend.enrichment.intelligence_enricher import IntelligenceEnricher

__all__ = [
    "BaseEnricher",
    "CorporateEnricher",
    "IdentityEnricher",
    "ProductEnricher",
    "FundingEnricher",
    "CompetitorEnricher",
    "IntelligenceEnricher",
]
