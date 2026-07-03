# =============================================================================
# DEPRECATED — COMPATIBILITY ONLY
# This agent has been superseded by: backend.enrichment.product_enricher.ProductEnricher
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
from jinja2 import Template
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.agents.utils import call_ollama

class DescriptionGeneratorAgent(BaseAgent):
    """
    Generates a structured factual description of the company (100-150 words).
    Must NOT contain funding metadata or competitor discussions.
    """

    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, "[DescriptionGeneratorAgent] Generating factual master description...")
        
        # Consolidate website/snippets context
        crawled_data = state.article_data.get("crawled_content", {})
        homepage_text = crawled_data.get("homepage", {}).get("text_content", "")
        about_text = crawled_data.get("about", {}).get("text_content", "")
        
        search_snippets = ""
        snippets = state.article_data.get("discovered_snippets", {})
        for cat, records in snippets.items():
            for rec in records:
                search_snippets += f"- Title: {rec.get('title')}\n  Snippet: {rec.get('snippet')}\n"

        prompt_template = """You are a senior analyst on the Startup Engagement and Investment Team.
Your task is to generate a comprehensive, objective, and factual business description for {{ startup_name }} to support our strategic partnership review.

Startup Details:
Startup Name: {{ startup_name }}
News Article Headline: {{ headline }}

Requirements:
1. length: 100-150 words.
2. Structure: Overview of operations, core product/services suite, target customers, and market positioning.
3. Restrictions: Do NOT mention funding rounds, investors, capital raised, or direct competitors.
4. Factual constraint: Rely only on the evidence below. Do not hallucinate details.

Evidence Context:
=== Crawled homepage text ===
{{ homepage_text }}

=== Crawled about page text ===
{{ about_text }}

=== Search Snippets ===
{{ search_snippets }}

Return only the text description in your output. No formatting wrappers.
"""
        try:
            prompt = Template(prompt_template).render(
                startup_name=state.startup_name,
                headline=state.article_data.get("headline", ""),
                homepage_text=homepage_text,
                about_text=about_text,
                search_snippets=search_snippets
            )
            description = call_ollama(prompt, json_format=False)
            if description:
                state.article_data["business_description"] = description.strip()
                self.log_audit(state, "Generated master company description.")
        except Exception as e:
            self.log_audit(state, f"Description generation failed: {e}")
            
        return state
