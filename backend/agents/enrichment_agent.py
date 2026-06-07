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
                website_query = f"{clean_name} official website"
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
            founders_query = f'"{clean_name}" founders co-founders LinkedIn'
            if filter_str:
                founders_query += f" ({filter_str})"
                
            try:
                founders_snippets = search_duckduckgo(founders_query)
                if not founders_snippets or "No search results" in founders_snippets:
                    founders_snippets = search_duckduckgo(f'"{clean_name}" founders OR co-founders')
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
