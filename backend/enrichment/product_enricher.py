"""
backend/enrichment/product_enricher.py
-----------------------------------------
AI Layer 3 — Product & Industry Enrichment Module.

Enriches: products_services, business_profile

Consolidates logic previously spread across:
  - ProductIntelligenceAgent (product extraction)
  - IndustryClassificationAgent (taxonomy classification)
  - DescriptionGeneratorAgent (one-liner + description)

Uses a single combined AI call to extract:
  - Product/service list with descriptions and target customers
  - Business description and one-liner
  - Industry/sector/subsector classification
  - Business models and industry relevance tags
  - Taxonomy tags from startup_sector_mappings.json

Supports standalone re-enrichment via /api/startups/{id}/enrich/products.
"""

from __future__ import annotations

import os
import json
import time
import logging
from typing import Optional

from backend.enrichment.base_enricher import BaseEnricher

logger = logging.getLogger("startup_intelligence.enrichment.products")

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")

class ProductEnricher(BaseEnricher):
    """
    Product & Industry Enricher — extracts products, business model, industry taxonomy.

    Consolidates ProductIntelligenceAgent + IndustryClassificationAgent +
    DescriptionGeneratorAgent into a single AI call. ~1 AI call per enrichment.

    v2: enrich_v2() uses crawled_pages + field-bucketed snippets.
    v1: enrich() / enrich_from_state() retained for backward compatibility.
    """

    section_name = "products"
    ai_task = "enrichment_products"
    prompt_file = "enrichment_products_prompt.txt"
    critical_fields = ["products"]

    def enrich_v2(
        self,
        startup_name: str,
        crawled_pages: dict,
        all_snippets: dict,
        orchestrator=None,
        clean_name: str = "",
        brand_name: str = "",
    ) -> dict:
        """
        v2 enrichment: builds context from products/solutions/homepage pages + snippets.
        Calls LLM and runs fallback if products list is empty.
        """
        if orchestrator is None:
            from backend.utils.search import WebSearchOrchestrator
            orchestrator = WebSearchOrchestrator()

        start = time.perf_counter()
        self.log(f"enrich_v2 starting for '{startup_name}'")

        source_context = self._get_bm25_context(
            crawled_pages=crawled_pages,
            enricher_bm25_key="product_query",
            orchestrator=orchestrator,
            relevant_page_roles=["products", "solutions", "platform", "services", "homepage"],
        )
        snippet_context = self._get_snippet_context(
            search_snippets=all_snippets,
            field_keys=["products_and_solutions"],
            max_chars=2000,
        )
        taxonomy_context = self._load_taxonomy()
        prompt = self.render_prompt(
            startup_name=startup_name,
            source_context=source_context or "No crawled content available.",
            taxonomy_context=taxonomy_context[:1000],
        )
        raw = self.call_ai(prompt=prompt, json_format=True, num_ctx=6000)
        duration_ms = (time.perf_counter() - start) * 1000

        if not raw or not isinstance(raw, dict):
            self.log(f"No product data returned for '{startup_name}'", level="warning")
            return {"products": [], "business_profile": {}}

        result_v1 = self._map_to_ci_schema(startup_name, raw, {})
        # Expose as flat v2 section
        result = {
            "products": result_v1.get("products_services", []),
            "business_profile": result_v1.get("business_profile", {}),
        }
        self.log_result(startup_name, result, duration_ms)

        missing = self._detect_missing_fields(result)
        if missing:
            self.log(f"Empty products list — triggering fallback search")
            result = self._run_fallback(
                startup_name=startup_name,
                missing_field_keys=["products_and_solutions"],
                orchestrator=orchestrator,
                clean_name=clean_name or startup_name,
                brand_name=brand_name,
                existing_result=result,
            )
        return result



    def _load_taxonomy(self) -> str:
        """Loads startup_sector_mappings.json and returns a compact JSON string."""
        taxonomy_path = os.path.join(_CONFIG_DIR, "startup_sector_mappings.json")
        try:
            with open(taxonomy_path, "r") as f:
                data = json.load(f)
            # Return compact representation (industries + business models + tags only)
            compact = {
                "industry_relevance": data.get("industry_relevance", [])[:20],
                "business_models": data.get("business_models", [])[:15],
                "sectors": list(data.get("sectors", {}).keys())[:20],
            }
            return json.dumps(compact, indent=None)
        except Exception as e:
            logger.warning(f"[ProductEnricher] Failed to load taxonomy: {e}")
            return "{}"

    def enrich(
        self,
        startup_name: str,
        source_context: str,
        existing_data: Optional[dict] = None,
        **kwargs,
    ) -> dict:
        """
        Extracts product and industry intelligence from source context.

        Returns
        -------
        dict with keys: products_services, business_profile
        """
        start_time = time.perf_counter()
        self.log(f"Enriching products/industry for '{startup_name}'")

        taxonomy_context = self._load_taxonomy()
        prompt = self.render_prompt(
            startup_name=startup_name,
            source_context=source_context[:2500],
            taxonomy_context=taxonomy_context[:1000],
        )

        raw = self.call_ai(prompt=prompt, json_format=True, num_ctx=6000)

        duration_ms = (time.perf_counter() - start_time) * 1000

        if not raw or not isinstance(raw, dict):
            self.log(f"No product data returned for '{startup_name}'", level="warning")
            return {}

        result = self._map_to_ci_schema(startup_name, raw, existing_data or {})
        self.log_result(startup_name, result, duration_ms)
        return result

    def _map_to_ci_schema(self, startup_name: str, raw: dict, existing: dict) -> dict:
        """Maps AI output to company_intelligence section schema."""
        # Business profile section
        business_profile = {
            "one_liner": raw.get("one_liner") or "",
            "description": raw.get("description") or "",
            "business_model": raw.get("business_model") or "",
            "target_audience": raw.get("target_audience") or "",
            "industry": raw.get("industry") or "",
            "sector": raw.get("sector") or "",
            "subsector": raw.get("subsector") or "",
            "tags": raw.get("tags") or [],
            "business_models": raw.get("business_models") or [],
        }

        # Normalize via taxonomy mapper (reuse existing logic)
        try:
            from backend.utils.taxonomy_mapper import (
                normalize_taxonomy,
                normalize_business_models,
                normalize_industry_relevance,
                get_canonical_tags,
            )
            industry, sector, subsector = normalize_taxonomy(
                startup_name,
                business_profile["industry"],
                business_profile["sector"],
                business_profile["subsector"],
            )
            business_profile["industry"] = industry
            business_profile["sector"] = sector
            business_profile["subsector"] = subsector
            business_profile["business_models"] = normalize_business_models(
                startup_name, business_profile["business_models"]
            )
            business_profile["tags"] = get_canonical_tags(startup_name, business_profile["tags"])
        except Exception as e:
            logger.debug(f"[ProductEnricher] Taxonomy normalization failed: {e}")

        # Products section
        products = []
        for p in (raw.get("products") or []):
            if isinstance(p, dict) and p.get("name"):
                products.append({
                    "name": p.get("name", ""),
                    "category": p.get("category", ""),
                    "description": p.get("description", ""),
                    "target_customer": p.get("target_customer", ""),
                    "deployment_model": p.get("deployment_model", ""),
                })

        return {
            "business_profile": business_profile,
            "products_services": products,
        }

    def enrich_from_state(self, state) -> dict:
        """Compatibility bridge for AgentOrchestrator pipeline integration."""
        startup_name = state.startup_name
        
        # Check if new dynamic website extractor already ran
        profile = state.article_data.get("company_profile")
        if profile:
            self.log(f"Using pre-extracted products & taxonomy from new CompanyWebsiteExtractor for '{startup_name}'")
            products = [
                {
                    "name": getattr(p, "name", ""),
                    "category": getattr(p, "category", "") or "",
                    "description": getattr(p, "description", ""),
                    "target_customer": getattr(p, "target_customer", "") or "",
                    "deployment_model": getattr(p, "deployment_model", "") or ""
                }
                for p in getattr(profile, "products_and_solutions", [])
            ]
            
            raw = {
                "one_liner": getattr(profile, "one_liner", None),
                "description": getattr(profile, "description", None),
                "business_model": getattr(profile, "business_model", None),
                "target_audience": getattr(profile, "target_audience", None),
                "industry": getattr(profile, "industry", None),
                "sector": getattr(profile, "sector", None),
                "subsector": getattr(profile, "subsector", None),
                "tags": getattr(profile, "tags", []),
                "business_models": getattr(profile, "business_models", []),
                "products": []
            }
            
            result = self._map_to_ci_schema(startup_name, raw, state.article_data.get("company_intelligence", {}))
            result["products_services"] = products
            return result

        crawled = state.article_data.get("crawled_content")
        if not isinstance(crawled, dict):
            crawled = {}
            state.article_data["crawled_content"] = crawled

        # Check if products text content is missing/empty, and crawl dynamically if website is available
        products_text = ""
        products_text = crawled.get("products", {}).get("text_content", "")
            
        if not products_text:
            website_url = ""
            website_field = state.identity.get("website")
            if isinstance(website_field, dict):
                website_url = website_field.get("value") or ""
            elif isinstance(website_field, str):
                website_url = website_field
            
            if website_url:
                try:
                    from backend.utils.crawler import crawl_product_pages
                    print(f"🔍 [ProductEnricher] Dynamically crawling product pages for '{startup_name}' at {website_url}...")
                    products_text = crawl_product_pages(website_url)
                    if products_text:
                        if "products" not in crawled:
                            crawled["products"] = {}
                        crawled["products"]["text_content"] = products_text
                        state.article_data["crawled_content"] = crawled
                except Exception as e:
                    logger.warning(f"[ProductEnricher] Dynamic product crawling failed: {e}")

        context_parts = []
        
        # Inject website URL
        website_url = state.identity.get("website") or ""
        if isinstance(website_url, dict):
            website_url = website_url.get("value") or ""
        if website_url:
            context_parts.append(f"TARGET WEBSITE URL:\n{website_url}")

        if isinstance(crawled, dict):
            for page_key in ("homepage", "products", "about", "contact"):
                page_data = crawled.get(page_key, {})
                if not isinstance(page_data, dict):
                    continue
                
                p_title = page_data.get("title") or ""
                p_desc = page_data.get("meta_description") or ""
                p_text = page_data.get("text_content") or ""
                
                if p_title or p_desc:
                    context_parts.append(f"WEBSITE {page_key.upper()} METADATA:\n- Title: {p_title}\n- Meta Description: {p_desc}")
                    
                if p_text:
                    context_parts.append(f"{page_key.upper()} BODY TEXT:\n{p_text[:2500]}")

        news_text = state.article_data.get("text_content") or state.article_data.get("description") or ""
        if news_text:
            context_parts.append(f"NEWS ARTICLE:\n{news_text[:1200]}")

        source_context = "\n\n".join(context_parts)
        return self.enrich(
            startup_name=startup_name,
            source_context=source_context,
            existing_data=state.article_data.get("company_intelligence", {}),
        )
