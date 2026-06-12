import os
import json
from jinja2 import Template
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.agents.utils import call_ollama
from backend.utils.crawler import crawl_product_pages

class ProductIntelligenceAgent(BaseAgent):
    """
    Crawls solutions/product subpages and extracts product details, fallbacks to LinkedIn or snippets.
    """

    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, "[ProductIntelligenceAgent] Crawling solutions and products content...")
        
        website = state.identity.get("website", "")
        scraped_products_text = ""
        
        # Fallback level 1/2: Crawl subpages
        if website:
            try:
                scraped_products_text = crawl_product_pages(website)
            except Exception as e:
                self.log_audit(state, f"Solution/Product crawl error: {e}")
                
        # Fallback level 3: Homepage content
        if not scraped_products_text:
            scraped_products_text = state.article_data.get("crawled_content", {}).get("homepage", {}).get("text_content", "")
            
        # Fallback level 4: Web search snippets evidence
        search_snippets = ""
        snippets = state.article_data.get("discovered_snippets", {})
        for cat, records in snippets.items():
            for rec in records:
                search_snippets += f"- {rec.get('title')}: {rec.get('snippet')}\n"

        prompt_template = """You are a senior product analyst on the Startup Engagement and Investment Team. Analyze the company's product pages or search snippets and extract their product and services intelligence to evaluate pilot alignment.

Startup Details:
Startup Name: {{ startup_name }}
News Article Headline: {{ headline }}

Evidence:
=== Crawled product subpages / Homepage ===
{{ scraped_products_text }}

=== Search snippets ===
{{ search_snippets }}

Identify:
1. Product offerings (names, descriptions).
2. Service offerings.
3. Industries served.
4. Target customer segments.

Return ONLY a valid JSON object matching the following structure:
{
  "products": [
    {
      "name": "Product Name",
      "type": "Software / Service / hardware",
      "description": "Short description of what it does.",
      "target_audience": "e.g. BFSI / Retail / Healthcare",
      "evidence_url": "URL if available or homepage"
    }
  ],
  "services": ["Service 1", "Service 2"],
  "industries_served": ["Industry 1"],
  "target_customers": ["B2B", "Enterprise", "Corporate"]
}
"""
        try:
            prompt = Template(prompt_template).render(
                startup_name=state.startup_name,
                headline=state.article_data.get("headline", ""),
                scraped_products_text=scraped_products_text,
                search_snippets=search_snippets
            )
            extracted = call_ollama(prompt, json_format=True)
            
            state.market_intelligence["products"] = {
                "value": extracted.get("products", []),
                "confidence": 90 if scraped_products_text else 60
            }
            
            # Map elements to state
            state.startup_features.business_models = extracted.get("target_customers", [])
            self.log_audit(state, f"Extracted {len(extracted.get('products', []))} products.")
        except Exception as e:
            self.log_audit(state, f"Product extraction failed: {e}")
            
        return state
