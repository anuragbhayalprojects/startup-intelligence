# =============================================================================
# DEPRECATED — COMPATIBILITY ONLY
# This agent has been superseded by: backend.enrichment.identity_enricher.IdentityEnricher
# as part of the modular enrichment refactor (feature/modular-company-intelligence-refactor).
#
# STATUS: Removed from AgentOrchestrator execution path. Retained for:
#   - Regression comparison during migration safety period
#   - Import compatibility with any external scripts still using this class
#
# DO NOT extend or add new logic here. Use the replacement module above.
# This file will be removed after migration safety period ends.
# =============================================================================
import os
import json
import re
from jinja2 import Template
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.agents.utils import call_ollama

class LegalNameAgent(BaseAgent):
    """
    Extracts corporate legal name, location (hq, city, state, country), founded year,
    and founders / leadership details using structural LLM prompts.
    """

    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, f"[LegalNameAgent] Resolving corporate identity details for '{state.startup_name}'...")
        
        # 1. Consolidate crawled content and search snippets
        crawled_data = state.article_data.get("crawled_content", {})
        homepage_text = crawled_data.get("homepage", {}).get("text_content", "")
        about_text = crawled_data.get("about", {}).get("text_content", "")
        
        search_snippets = ""
        snippets = state.article_data.get("discovered_snippets", {})
        for cat, records in snippets.items():
            for rec in records:
                search_snippets += f"- Title: {rec.get('title')}\n  Snippet: {rec.get('snippet')}\n"
                
        # Gather original news article details
        article_headline = state.article_data.get("headline") or ""
        article_desc = state.article_data.get("description") or ""
        article_paragraphs = " ".join(state.article_data.get("paragraphs") or [])
        
        search_context = (
            f"=== TARGET STARTUP NAME ===\n"
            f"{state.startup_name}\n\n"
            f"=== SOURCE NEWS ARTICLE ===\n"
            f"Headline: {article_headline}\n"
            f"Description: {article_desc}\n"
            f"Content: {article_paragraphs}\n\n"
            f"=== WEBSITE CRAWLED TEXT ===\n{homepage_text[:1500]}\n{about_text[:1500]}\n\n"
            f"=== SEARCH SNIPPETS ===\n{search_snippets[:2000]}\n"
        )
        
        # 2. Extract Corporate Identity & Founders (single LLM call)
        corp_identity = {}
        try:
            corp_prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/corporate_identity_prompt.txt")
            with open(corp_prompt_path, "r", encoding="utf-8") as f:
                corp_template = Template(f.read())
            corp_prompt = corp_template.render(
                startup_name=state.startup_name,
                headline=state.article_data.get("headline", ""),
                search_context=search_context
            )
            corp_identity = call_ollama(corp_prompt, json_format=True) or {}
        except Exception as e:
            self.log_audit(state, f"Corporate identity/leadership LLM extraction failed: {e}")
            
        # 3. Map values to state fields
        legal_name = corp_identity.get("legal_name") or ""
        # Regex fallback for legal name if LLM returned nothing
        if not legal_name:
            for text in [homepage_text, about_text, search_snippets]:
                if text:
                    legal_pattern = re.compile(r"\b([A-Z][a-zA-Z\s,]{2,40}?\s+(?:Pvt\.?\s*Ltd\.?|Private\s+Limited|Inc\.?|LLC))\b")
                    match = legal_pattern.search(text)
                    if match:
                        legal_name = match.group(1).strip()
                        break
                        
        state.identity["legal_name"] = {
            "value": legal_name,
            "confidence": 90 if legal_name else 0,
            "source": "LegalNameAgent",
            "source_url": "",
            "evidence_text": "Resolved via LLM identity parsing."
        }
        
        # Location mapping
        hq = corp_identity.get("headquarters") or "Unknown"
        state.identity["headquarters"] = hq
        state.startup_features.headquarters = hq
        
        city = corp_identity.get("city") or "Unknown"
        state.identity["city"] = city
        state.startup_features.city = city
        
        state_val = corp_identity.get("state") or "Unknown"
        state.identity["state"] = state_val
        state.startup_features.state = state_val
        
        country = corp_identity.get("country") or "India"
        state.identity["country"] = country
        state.startup_features.country = country
        
        # Founded year mapping
        founded = corp_identity.get("founded_year")
        if founded:
            try:
                state.identity["founded_year"] = int(founded)
                state.startup_features.founded_year = int(founded)
            except Exception:
                pass
                
        # Founders mapping
        founders_list = corp_identity.get("founders") or []
        if isinstance(founders_list, list):
            state.startup_features.leadership = founders_list
            if founders_list:
                primary = founders_list[0]
                state.startup_features.founder_name = primary.get("name") or "Unknown"
                state.startup_features.founder_linkedin_url = primary.get("linkedin_url") or ""
                
        self.log_audit(
            state,
            f"LegalNameAgent processing completed.",
            metadata={
                "legal_name": legal_name,
                "headquarters": hq,
                "founded_year": state.startup_features.founded_year,
                "founders_count": len(founders_list)
            }
        )
        return state
