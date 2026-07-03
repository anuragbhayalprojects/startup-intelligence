# =============================================================================
# DEPRECATED — COMPATIBILITY ONLY
# This agent has been superseded by: backend.enrichment.identity_enricher.IdentityEnricher + backend.enrichment.product_enricher.ProductEnricher
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
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.services.tracxn_service import fetch_tracxn_startup_data
from backend.utils.search import search_duckduckgo, load_priority_sources
from backend.ai.startup_analyzer import collect_funding_snippets, extract_funding_rounds
from backend.workflows.startup_pipeline import get_clean_website

class EnrichmentAgent(BaseAgent):
    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, f"Starting Enrichment process for startup '{state.startup_name}'...")
        
        try:
            clean_name = state.startup_name
            
            # 1. Fetch Tracxn verified profile first
            tracxn_profile = fetch_tracxn_startup_data(clean_name) or {}
            website = tracxn_profile.get("website", "")
            
            # 2. Search official website if not in Tracxn
            website_snippets = ""
            if not website:
                from backend.utils.search import load_search_queries
                config = load_search_queries()
                website_query_tmpl = config.get("enrichment_agent", {}).get("website_query", "{clean_name} official website")
                website_query = website_query_tmpl.format(clean_name=clean_name)
                try:
                    website_snippets = search_duckduckgo(website_query)
                except Exception as e:
                    website_snippets = f"Website search failed: {e}"
            else:
                website_snippets = f"Verified official website retrieved: {website}"

            # 3. Search for founders
            founders_snippets = ""
            sources = load_priority_sources()
            site_filters = [f"site:{s['domain']}" for s in sources if s.get("domain")]
            if website:
                clean_dom = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                if clean_dom:
                    site_filters.insert(0, f"site:{clean_dom}")
                    
            filter_str = " OR ".join(site_filters)
            from backend.utils.search import load_search_queries
            config = load_search_queries()
            founders_query_tmpl = config.get("enrichment_agent", {}).get("founders_query_base", '"{clean_name}" founders co-founders LinkedIn')
            founders_query = founders_query_tmpl.format(clean_name=clean_name)
            if filter_str:
                founders_query += f" ({filter_str})"
                
            try:
                founders_snippets = search_duckduckgo(founders_query)
                if not founders_snippets or "No search results" in founders_snippets:
                    founders_fallback_tmpl = config.get("enrichment_agent", {}).get("founders_fallback", '"{clean_name}" founders OR co-founders')
                    founders_fallback_query = founders_fallback_tmpl.format(clean_name=clean_name)
                    founders_snippets = search_duckduckgo(founders_fallback_query)
            except Exception as e:
                founders_snippets = f"Founders search failed: {e}"

            # 4. Search for funding
            funding_snippets = ""
            try:
                funding_snippets = collect_funding_snippets(clean_name, website)
            except Exception as e:
                funding_snippets = f"Funding snippets retrieval failed: {e}"

            # 5. Extract structured funding rounds using prompt
            funding_data = {}
            try:
                funding_data = extract_funding_rounds(clean_name, funding_snippets)
            except Exception as e:
                state.errors.append(f"Funding extraction failed: {e}")

            # 6. Resolve website domain
            final_website = get_clean_website(clean_name, website or (funding_data.get("startup_website") if funding_data else ""))

            # Save raw gathered snippets and resolved metadata to article_data
            state.article_data["enriched_raw"] = {
                "website_snippets": website_snippets,
                "founders_snippets": founders_snippets,
                "funding_snippets": funding_snippets,
                "resolved_website": final_website,
                "tracxn_profile": tracxn_profile,
                "extracted_funding": funding_data
            }

            # 7. Generate Description, One-Liner and Corporate Identity details using local LLM
            search_context = (
                f"=== WEBSITE SEARCH CONTEXT ===\n{website_snippets}\n\n"
                f"=== FOUNDERS & LEADERSHIP SEARCH CONTEXT ===\n{founders_snippets}\n\n"
                f"=== FUNDING & METRICS SEARCH CONTEXT ===\n{funding_snippets}\n\n"
            )

            from jinja2 import Template
            from backend.agents.utils import call_ollama

            # Generate 250-300 words description
            description = ""
            try:
                desc_prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/description_generation_prompt.txt")
                with open(desc_prompt_path, "r", encoding="utf-8") as f:
                    desc_template = Template(f.read())
                desc_prompt = desc_template.render(
                    startup_name=clean_name,
                    headline=state.article_data.get("headline", ""),
                    search_context=search_context
                )
                description = call_ollama(desc_prompt, json_format=False)
                if description:
                    description = description.strip()
            except Exception as e:
                self.log_audit(state, f"Failed to generate 250-300 words description: {e}")
            
            if description:
                state.article_data["description"] = description

            # Generate 1-2 liner summary of startup
            one_liner = ""
            try:
                ol_prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/startup_one_liner_prompt.txt")
                with open(ol_prompt_path, "r", encoding="utf-8") as f:
                    ol_template = Template(f.read())
                ol_prompt = ol_template.render(
                    startup_name=clean_name,
                    headline=state.article_data.get("headline", ""),
                    search_context=search_context
                )
                one_liner = call_ollama(ol_prompt, json_format=False)
                if one_liner:
                    one_liner = one_liner.strip()
            except Exception as e:
                self.log_audit(state, f"Failed to generate 1-2 liner summary: {e}")
            
            if one_liner:
                state.article_data["startup_one_liner"] = one_liner

            # Extract corporate identity details (headquarters, founded_year, city, state, country, legal_name) if not in Tracxn
            corp_identity = {}
            if not tracxn_profile or not tracxn_profile.get("headquarters") or not tracxn_profile.get("founded_year") or not state.identity.get("city") or not state.identity.get("state") or state.identity.get("city") == "Unknown" or state.identity.get("state") == "Unknown":
                try:
                    corp_prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/corporate_identity_prompt.txt")
                    with open(corp_prompt_path, "r", encoding="utf-8") as f:
                        corp_template = Template(f.read())
                    corp_prompt = corp_template.render(
                        startup_name=clean_name,
                        headline=state.article_data.get("headline", ""),
                        search_context=search_context
                    )
                    corp_identity = call_ollama(corp_prompt, json_format=True) or {}
                except Exception as e:
                    self.log_audit(state, f"Failed to extract corporate identity: {e}")

            # Update headquarters and founded_year
            extracted_hq = corp_identity.get("headquarters")
            extracted_founded = corp_identity.get("founded_year")
            
            if extracted_hq and extracted_hq != "Unknown":
                state.startup_features.headquarters = extracted_hq
                state.identity["headquarters"] = extracted_hq
            elif tracxn_profile.get("headquarters"):
                state.startup_features.headquarters = tracxn_profile.get("headquarters")
                state.identity["headquarters"] = tracxn_profile.get("headquarters")

            if extracted_founded:
                try:
                    state.startup_features.founded_year = int(extracted_founded)
                    state.identity["founded_year"] = int(extracted_founded)
                except Exception:
                    pass
            elif tracxn_profile.get("founded_year"):
                try:
                    state.startup_features.founded_year = int(tracxn_profile.get("founded_year"))
                    state.identity["founded_year"] = int(tracxn_profile.get("founded_year"))
                except Exception:
                    pass

            # Update city, state, country, legal_name
            if corp_identity.get("city") and corp_identity.get("city") != "Unknown":
                state.identity["city"] = corp_identity.get("city")
            elif tracxn_profile.get("city"):
                state.identity["city"] = tracxn_profile.get("city")
                
            if corp_identity.get("state") and corp_identity.get("state") != "Unknown":
                state.identity["state"] = corp_identity.get("state")
            elif tracxn_profile.get("state"):
                state.identity["state"] = tracxn_profile.get("state")
                
            if corp_identity.get("country") and corp_identity.get("country") != "India":
                state.identity["country"] = corp_identity.get("country")
            elif tracxn_profile.get("country"):
                state.identity["country"] = tracxn_profile.get("country")
                
            if corp_identity.get("legal_name"):
                state.identity["legal_name"] = corp_identity.get("legal_name")

            # Update initial startup stage
            if funding_data and funding_data.get("latest_stage"):
                state.startup_features.startup_stage = funding_data.get("latest_stage")
            elif tracxn_profile.get("funding_stage"):
                state.startup_features.startup_stage = tracxn_profile.get("funding_stage")

            # Update founder details from Tracxn if available
            founders_list = tracxn_profile.get("founders", [])
            if founders_list and isinstance(founders_list, list):
                primary = founders_list[0]
                if isinstance(primary, dict):
                    f_name = primary.get("name")
                    f_linkedin = primary.get("linkedin_url") or primary.get("linkedin")
                    if f_name:
                        state.startup_features.founder_name = f_name
                    if f_linkedin:
                        state.startup_features.founder_linkedin_url = f_linkedin

            self.log_audit(
                state, 
                f"Successfully enriched startup '{clean_name}'. Resolved website: {final_website or 'None'}",
                metadata={
                    "has_tracxn": bool(tracxn_profile),
                    "latest_stage": state.startup_features.startup_stage,
                    "rounds_extracted": len(funding_data.get("rounds", [])) if funding_data else 0
                }
            )

        except Exception as e:
            state.errors.append(f"EnrichmentAgent failed: {str(e)}")
            self.log_audit(state, f"EnrichmentAgent failed: {str(e)}", metadata={"error": True})

        return state
