import json
import os
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.utils.search import discover_search_evidence
from backend.utils.crawler import crawl_startup_targets

class IdentityDiscoveryAgent(BaseAgent):
    """
    Step 0a: Gathers URL candidates, crawls text, performs domain validation,
    and runs LegalNameAgent to discover identity parameters.
    """

    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, f"[IdentityDiscovery] Starting discovery for '{state.startup_name}'...")
        
        # Clean the startup name to get the operating brand name
        cleaned_name = state.startup_name
        try:
            name_clean_prompt = f"""You are a precise data parsing assistant.
Analyze the company name '{state.startup_name}' and extract the clean operating brand name.
Exclude descriptive prefixes like "Fintech Startup", "Proptech Startup", "Edtech", "Gourmet", "Logistics", "Foodtech", "SaaS", "Enterprise", etc.
Exclude suffixes like "Pvt Ltd", "Inc", "Solutions", "Technologies", or generic terms.
Return ONLY a valid JSON block containing the "brand_name" key. Do not output any notes, commentary, or wrapper text.

JSON Schema:
{{
  "brand_name": "BrandName"
}}

Begin parsing:
"""
            from backend.agents.utils import call_ollama
            res = call_ollama(name_clean_prompt, json_format=True)
            if res and res.get("brand_name"):
                cleaned_name = res["brand_name"].strip()
                self.log_audit(state, f"Cleaned startup name from '{state.startup_name}' to '{cleaned_name}'")
                state.startup_name = cleaned_name
        except Exception as e:
            self.log_audit(state, f"Failed to clean startup name: {e}")

        # 1. Run multi-query search loop
        snippets = discover_search_evidence(state.startup_name)
        state.article_data["discovered_snippets"] = snippets
        
        # 2. Pick candidate website domain
        candidate_website = ""
        official_websites = snippets.get("official_website", [])
        if official_websites:
            candidate_website = official_websites[0].get("url", "")
            
        candidate_linkedin = ""
        linkedins = snippets.get("linkedin", [])
        if linkedins:
            candidate_linkedin = linkedins[0].get("url", "")
            
        # 3. Crawl homepage & identity subpages
        crawled_content = {}
        if candidate_website:
            try:
                crawled_content = crawl_startup_targets(candidate_website)
            except Exception as e:
                self.log_audit(state, f"Crawling targets failed: {e}")
                
        state.article_data["crawled_content"] = crawled_content
        
        # Populate basic resolved fields
        state.identity["website"] = {
            "value": candidate_website,
            "confidence": 90 if candidate_website else 0,
            "source": "search_discovery",
            "source_url": candidate_website,
            "evidence_text": f"Found domain through search query matching startup {state.startup_name}"
        }
        
        state.identity["linkedin_company_url"] = {
            "value": candidate_linkedin,
            "confidence": 85 if candidate_linkedin else 0,
            "source": "search_discovery",
            "source_url": candidate_linkedin,
            "evidence_text": f"Found LinkedIn company page URL"
        }
        
        # Sync simple flat variables for backward compatibility
        state.startup_features.linkedin_company_url = candidate_linkedin
        
        self.log_audit(state, f"IdentityDiscovery completed. Website candidate: {candidate_website}, LinkedIn candidate: {candidate_linkedin}")
        return state
