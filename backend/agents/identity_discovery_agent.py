"""
backend/agents/identity_discovery_agent.py
--------------------------------------------
Phase 2: Identity Discovery — resolves startup website URL, crawls content,
and populates raw_source_payload for the v2 enrichment pipeline.

v2 additions (gated by use_v2_pipeline flag in pipeline_config.json):
  - Runs discover_all_evidence() → field-bucketed search_snippets
  - Runs collect_source_payload() → dynamic crawled_pages dict
  - Writes both into state.article_data["raw_source_payload"]

v1 path (unchanged):
  - discover_search_evidence() → discovered_snippets (legacy flat format)
  - crawl_startup_targets() → crawled_content (legacy flat dict)

Both paths always run to maintain full backward compatibility.
"""

import json
import os
import logging
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.utils.search import discover_search_evidence, WebSearchOrchestrator
from backend.utils.crawler import crawl_startup_targets

logger = logging.getLogger("startup_intelligence.identity_discovery")

_PIPELINE_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "pipeline_config.json"
)


def _load_pipeline_config() -> dict:
    """Loads pipeline_config.json with fallback."""
    try:
        if os.path.exists(_PIPELINE_CONFIG_PATH):
            with open(_PIPELINE_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"[IdentityDiscovery] Failed to load pipeline_config.json: {e}")
    return {}


class IdentityDiscoveryAgent(BaseAgent):
    """
    Phase 2a: Gathers URL candidates, crawls text, runs discovery searches,
    and populates both v1 (crawled_content) and v2 (raw_source_payload) state.

    v2 path: uses WebSearchOrchestrator.discover_all_evidence() + source_collector
    v1 path: uses discover_search_evidence() + crawl_startup_targets()
    Both paths always run for full backward compatibility.
    """

    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, f"[IdentityDiscovery] Starting discovery for '{state.startup_name}'...")

        # Clean startup name
        cleaned_name = state.startup_name.strip()
        state.startup_name = cleaned_name

        # Check if already exists in DB with resolved website to bypass search/crawl
        try:
            from backend.services.supabase_service import check_existing_startup
            existing = check_existing_startup(state.startup_name)
            if existing and existing.get("website"):
                self.log_audit(state, f"[IdentityDiscovery] Startup '{state.startup_name}' already exists in DB. Bypassing search & crawl.")
                print(f"⚡ [IdentityDiscovery] Cache hit: '{state.startup_name}' already exists. Bypassing web search.")
                
                snippets_v1 = {
                    "official_website": [{"title": state.startup_name, "url": existing["website"]}],
                    "linkedin": [{"title": state.startup_name, "url": existing.get("linkedin_url", "") or ""}]
                }
                state.article_data["discovered_snippets"] = snippets_v1
                state.identity["website"] = existing["website"]
                state.identity["identity_confidence"] = existing.get("identity_confidence", 100)
                state.identity["verification_status"] = existing.get("status", "VERIFIED")
                
                if "crawled_content" not in state.article_data:
                    state.article_data["crawled_content"] = {}
                state.article_data["crawled_content"]["homepage"] = {
                    "text_content": existing.get("description", "") or ""
                }
                return state
        except Exception as e:
            logger.warning(f"Error checking cache in IdentityDiscoveryAgent: {e}")

        pipeline_cfg = _load_pipeline_config()
        use_v2 = pipeline_cfg.get("v2_pipeline", {}).get("use_v2_pipeline", False)

        orchestrator = WebSearchOrchestrator()

        # ------------------------------------------------------------------
        # Step 1: Web search evidence collection
        # ------------------------------------------------------------------

        # v1 path (always runs — provides discovered_snippets in legacy format)
        snippets_v1 = discover_search_evidence(state.startup_name)
        state.article_data["discovered_snippets"] = snippets_v1

        # v2 path: field-bucketed snippets (runs only when use_v2_pipeline=true)
        field_bucketed_snippets: dict = {}
        if use_v2:
            print(f"🔍 [IdentityDiscovery] v2: running field-bucketed discovery for '{state.startup_name}'...")
            try:
                field_bucketed_snippets = orchestrator.discover_all_evidence(state.startup_name)
                total_snippets = sum(len(v) for v in field_bucketed_snippets.values())
                print(f"  ✅ Discovered {total_snippets} snippets across {len(field_bucketed_snippets)} field buckets")
            except Exception as e:
                logger.warning(f"[IdentityDiscovery] v2 discovery failed: {e}")
                field_bucketed_snippets = {}

        # ------------------------------------------------------------------
        # Step 2: Resolve candidate website URL
        # ------------------------------------------------------------------
        candidate_website = ""
        official_websites = snippets_v1.get("official_website", [])
        if official_websites:
            candidate_website = official_websites[0].get("url", "")

        # Also try from field-bucketed snippets if v1 found nothing
        if not candidate_website and field_bucketed_snippets:
            for rec in field_bucketed_snippets.get("official_website", []):
                url = rec.get("url", "")
                if url and "linkedin.com" not in url and "twitter.com" not in url:
                    candidate_website = url
                    break

        candidate_linkedin = ""
        linkedins = snippets_v1.get("linkedin", [])
        if linkedins:
            candidate_linkedin = linkedins[0].get("url", "")

        # ------------------------------------------------------------------
        # Step 3: Crawl website — v1 path (crawled_content)
        # ------------------------------------------------------------------
        crawled_content = {}
        if candidate_website:
            try:
                crawled_content = crawl_startup_targets(candidate_website)
                state.article_data["crawled_content"] = crawled_content
            except Exception as e:
                self.log_audit(state, f"v1 crawl failed: {e}")

        # ------------------------------------------------------------------
        # Step 4: Crawl website — v2 path (raw_source_payload)
        # ------------------------------------------------------------------
        if use_v2:
            print(f"🌐 [IdentityDiscovery] v2: running source_collector for '{state.startup_name}'...")
            try:
                from backend.pipeline.source_collector import collect_source_payload
                raw_source_payload = collect_source_payload(
                    startup_name=state.startup_name,
                    website_url=candidate_website or None,
                    search_snippets=field_bucketed_snippets,
                    use_playwright_fallback=True,
                    orchestrator=orchestrator,
                )
                state.article_data["raw_source_payload"] = raw_source_payload

                pages = raw_source_payload.get("crawl_metadata", {}).get("pages_crawled", [])
                print(f"  ✅ v2 source_collector: pages_crawled={pages}")

                # Sync social links from v2 crawled_pages back into v1 crawled_content
                # so LinkedIn extraction below still works
                homepage_v2 = raw_source_payload.get("crawled_pages", {}).get("homepage", {})
                if homepage_v2 and not crawled_content.get("homepage"):
                    state.article_data.setdefault("crawled_content", {})["homepage"] = homepage_v2

            except Exception as e:
                logger.warning(f"[IdentityDiscovery] v2 source_collector failed: {e}")
                # Ensure raw_source_payload always exists (even if empty)
                state.article_data["raw_source_payload"] = {
                    "crawled_pages": crawled_content,
                    "search_snippets": field_bucketed_snippets,
                    "crawl_metadata": {"pages_crawled": [], "playwright_used": False, "website_url": candidate_website},
                }
        else:
            # v2 disabled: still write raw_source_payload as a passthrough so
            # _run_v2_enrichment() has a non-null dict to read from if flag changes
            state.article_data["raw_source_payload"] = {
                "crawled_pages": crawled_content if isinstance(crawled_content, dict) else {},
                "search_snippets": {},
                "crawl_metadata": {"pages_crawled": [], "playwright_used": False, "website_url": candidate_website},
            }

        # ------------------------------------------------------------------
        # Step 5: Resolve LinkedIn URL (from website footer first)
        # ------------------------------------------------------------------
        footer_linkedin = ""
        linkedin_source = "search_discovery"
        linkedin_evidence = "Found LinkedIn company page URL via web search."
        linkedin_confidence = 85 if candidate_linkedin else 0

        # Check v2 crawled_pages first (more accurate)
        crawled_pages_v2 = state.article_data.get("raw_source_payload", {}).get("crawled_pages", {})
        if isinstance(crawled_pages_v2, dict):
            for key in ("homepage", "about", "privacy", "terms", "contact"):
                page_data = crawled_pages_v2.get(key, {})
                if isinstance(page_data, dict):
                    loc_linkedin = page_data.get("social_links", {}).get("linkedin")
                    if loc_linkedin and "/company/" in loc_linkedin.lower():
                        footer_linkedin = loc_linkedin
                        linkedin_source = f"website_{key}_footer_v2"
                        linkedin_evidence = f"Extracted LinkedIn company URL from v2 {key} page footer."
                        linkedin_confidence = 100
                        break

        # Fallback: check v1 crawled_content
        if not footer_linkedin and isinstance(crawled_content, dict):
            for key in ("homepage", "about", "privacy", "terms"):
                page_data = crawled_content.get(key, {})
                if isinstance(page_data, dict):
                    loc_linkedin = page_data.get("social_links", {}).get("linkedin")
                    if loc_linkedin:
                        footer_linkedin = loc_linkedin
                        linkedin_source = f"website_{key}_footer"
                        linkedin_evidence = f"Extracted LinkedIn company URL from {key} page footer."
                        linkedin_confidence = 100
                        break

        if footer_linkedin:
            candidate_linkedin = footer_linkedin

        # ------------------------------------------------------------------
        # Step 6: Write resolved identity fields into state
        # ------------------------------------------------------------------
        state.identity["website"] = {
            "value": candidate_website,
            "confidence": 90 if candidate_website else 0,
            "source": "search_discovery",
            "source_url": candidate_website,
            "evidence_text": f"Found domain through search query matching startup {state.startup_name}"
        }

        state.identity["linkedin_company_url"] = {
            "value": candidate_linkedin,
            "confidence": linkedin_confidence,
            "source": linkedin_source,
            "source_url": candidate_linkedin,
            "evidence_text": linkedin_evidence
        }

        # Sync flat field for backward compat
        state.startup_features.linkedin_company_url = candidate_linkedin

        self.log_audit(
            state,
            f"IdentityDiscovery completed. "
            f"website={candidate_website}, "
            f"linkedin={candidate_linkedin}, "
            f"v2={'enabled' if use_v2 else 'disabled'}"
        )
        return state
