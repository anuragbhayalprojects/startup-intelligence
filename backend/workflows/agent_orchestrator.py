"""
backend/workflows/agent_orchestrator.py
-----------------------------------------
Agent Orchestrator — Startup Intelligence OS v3.0

Refactored as part of: feature/modular-company-intelligence-refactor

Architecture:
  AI Layer 1  — Startup name extraction (upstream, in startup_pipeline.py)
  AI Layer 2  — Resolution engine (IdentityDiscovery + IdentityResolution)
  AI Layer 3  — Modular enrichment (IdentityEnricher, ProductEnricher,
                 FundingEnricher, IntelligenceEnricher via enrichment/ package)

Design decisions:
  - Legacy agents (15 individual agents) are REMOVED from the execution path
  - Their logic is now consolidated into 4 enrichment modules (~4–6 AI calls total)
  - analysis_json (startup_analysis table) is still written for frontend compatibility
  - company_intelligence JSONB (startups table) is also written (dual-write)
  - Playwright fallback preserved exactly as-is (no changes)
  - Scoring and ExplanationService preserved (no changes)
  - All scoring thresholds and config remain externalized
"""

import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from backend.models.startup_state import StartupState
from backend.models.startup_features import StartupFeatures

# ---------------------------------------------------------------------------
# AI Layer 2: Resolution agents (kept — not part of enrichment refactor)
# ---------------------------------------------------------------------------
from backend.agents.identity_discovery_agent import IdentityDiscoveryAgent
from backend.agents.identity_resolution_agent import IdentityResolutionAgent
from backend.agents.legal_name_agent import LegalNameAgent

# ---------------------------------------------------------------------------
# AI Layer 3: Modular enrichment engine (v1 + v2)
# ---------------------------------------------------------------------------
from backend.enrichment.identity_enricher import IdentityEnricher
from backend.enrichment.product_enricher import ProductEnricher
from backend.enrichment.funding_enricher import FundingEnricher
from backend.enrichment.intelligence_enricher import IntelligenceEnricher
# v2 new enrichers
from backend.enrichment.corporate_enricher import CorporateEnricher
from backend.enrichment.competitor_enricher import CompetitorEnricher

# ---------------------------------------------------------------------------
# Services (unchanged)
# ---------------------------------------------------------------------------
from backend.services.explanation_service import ExplanationService
from backend.services.scoring_service import ScoringService
from backend.services.supabase_service import (
    supabase,
    upsert_startup,
    save_startup_analysis,
    save_funding_rounds,
)


def normalize_city_name(city: str) -> str:
    """Normalizes local suburbs/areas/districts to parent canonical metropolitan cities."""
    if not city:
        return "Unknown"
    c_lower = str(city).lower().strip()
    
    # Mumbai suburbs and areas
    mumbai_areas = [
        "mumbai", "andheri", "bandra", "goregaon", "worli", "thane", "navi mumbai", 
        "powai", "mulund", "malad", "chembur", "colaba", "borivali", "kandivali", 
        "dadar", "parla", "kurla", "ghatkopar", "vikhroli", "juhu"
    ]
    if any(area in c_lower for area in mumbai_areas):
        return "Mumbai"
        
    # Bangalore areas
    bangalore_areas = [
        "bangalore", "bengaluru", "koramangala", "hsr", "whitefield", "electronic city", 
        "indiranagar", "jayanagar", "jp nagar", "bellandur", "marathahalli", "yeshwanthpur"
    ]
    if any(area in c_lower for area in bangalore_areas):
        return "Bangalore"
        
    # Delhi NCR areas
    delhi_areas = [
        "delhi", "gurgaon", "gurugram", "noida", "ghaziabad", "faridabad", "dwarka", 
        "saket", "connaught place", "nehru place", "okhla"
    ]
    if any(area in c_lower for area in delhi_areas):
        return "Delhi NCR"
        
    # Hyderabad areas
    hyderabad_areas = [
        "hyderabad", "secunderabad", "gachibowli", "madhapur", "jubilee hills", 
        "banjara hills", "hitech city", "kondapur"
    ]
    if any(area in c_lower for area in hyderabad_areas):
        return "Hyderabad"
        
    # Chennai areas
    chennai_areas = ["chennai", "adyar", "guindy", "velachery", "t nagar", "omr"]
    if any(area in c_lower for area in chennai_areas):
        return "Chennai"
        
    # Pune areas
    pune_areas = ["pune", "hinjewadi", "baner", "koregaon", "wakad", "hadapsar", "kothrud"]
    if any(area in c_lower for area in pune_areas):
        return "Pune"
        
    # Capitalize first letter of each word for clean display
    words = [w.capitalize() for w in city.split()]
    return " ".join(words)


class AgentOrchestrator:
    def __init__(self):
        # --- AI Layer 2: Resolution (unchanged) ---
        self.identity_discovery_agent = IdentityDiscoveryAgent()
        self.identity_resolution_agent = IdentityResolutionAgent()
        self.legal_name_agent = LegalNameAgent()

        # --- AI Layer 3: Modular enrichment (v1 path, backward compat) ---
        self.identity_enricher = IdentityEnricher()
        self.product_enricher = ProductEnricher()
        self.funding_enricher = FundingEnricher()
        self.intelligence_enricher = IntelligenceEnricher()

        # --- v2 Enrichers (parallel execution path) ---
        self.corporate_enricher = CorporateEnricher()
        self.competitor_enricher = CompetitorEnricher()

        # --- Load pipeline feature flags ---
        self._pipeline_cfg = self._load_pipeline_config()

    @staticmethod
    def _load_pipeline_config() -> dict:
        """Loads pipeline_config.json for v2 feature flags."""
        cfg_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "config", "pipeline_config.json"
        )
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ [Orchestrator] Failed to load pipeline_config.json: {e}")
        return {}

    def _is_v2_enabled(self) -> bool:
        """Returns True if the v2 parallel pipeline is enabled via feature flag."""
        return bool(
            self._pipeline_cfg.get("v2_pipeline", {}).get("use_v2_pipeline", False)
        )

    def run_pipeline(self, raw_startup: dict) -> StartupState:
        """
        Executes the 3-layer orchestration workflow.

        AI Layer 1: Upstream — startup name extraction (done before this is called)
        AI Layer 2: Resolution — identity discovery, website resolution (~1 AI call)
        AI Layer 3: Enrichment — modular company intelligence (~3-5 AI calls)

        Input raw_startup dict keys: startup_name, description, source, source_url.
        """
        print(f"🎬 Starting Orchestrated Run for '{raw_startup.get('startup_name')}'...")

        # Initialize typed state
        state = StartupState(
            startup_name=raw_startup.get("startup_name", "Unknown"),
            article_data={
                "headline": raw_startup.get("headline") or raw_startup.get("startup_name", ""),
                "description": raw_startup.get("description", ""),
                "text_content": raw_startup.get("text_content") or raw_startup.get("description", ""),
                "news_summary": raw_startup.get("news_summary") or "",
                "source": raw_startup.get("source", "Unknown"),
                "source_url": raw_startup.get("source_url", ""),
            },
        )

        # Pre-populate startup_id from existing DB record
        try:
            existing = supabase.table("startups").select("id").eq(
                "startup_name", raw_startup.get("startup_name", "")
            ).execute()
            if existing.data:
                state.startup_id = existing.data[0]["id"]
        except Exception:
            pass

        state.audit_trail.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "Orchestrator",
            "message": "Initialized StartupState.",
            "metadata": {},
        })

        # ---------------------------------------------------------------
        # Phase 1: Identity Discovery & Consolidation
        # ---------------------------------------------------------------
        # 1. Deterministic URL discovery and crawler footer link extraction
        state = self.identity_discovery_agent.run(state)

        # Retrieve resolved website URL
        website_url = ""
        website_field = state.identity.get("website")
        if isinstance(website_field, dict):
            website_url = website_field.get("value") or ""
        elif isinstance(website_field, str):
            website_url = website_field

        # In v2: source_collector (called inside IdentityDiscoveryAgent) already handles
        # all crawling. CompanyWebsiteExtractor and the early identity LLM call are v1-only.
        company_intelligence: dict = {}
        is_testing = "PYTEST_CURRENT_TEST" in os.environ
        force_run = os.environ.get("FORCE_STARTUP_PIPELINE_RUN") == "true"

        if not self._is_v2_enabled():
            # v1 only: Run dynamic company website extractor and chunk indexer
            if website_url and (not is_testing or force_run):
                try:
                    from backend.scrapers.company_website.extractor import CompanyWebsiteExtractor
                    from backend.ai.router import run_async

                    print(f"🌐 [Orchestrator] v1: Running CompanyWebsiteExtractor for '{state.startup_name}'...")
                    extractor = CompanyWebsiteExtractor()
                    profile = run_async(extractor.extract(state.startup_name, website_url))
                    state.article_data["company_profile"] = profile
                    print(f"✅ [Orchestrator] Dynamic web extraction completed.")
                except Exception as ex:
                    print(f"⚠️ [Orchestrator] CompanyWebsiteExtractor run failed: {ex}")

            # v1 only: Consolidated Identity & Corporate Parameters extraction (1 LLM call)
            try:
                identity_patch = self.identity_enricher.enrich_from_state(state)
                company_intelligence.update(identity_patch)
                state.article_data["company_intelligence"] = dict(company_intelligence)
                self._sync_identity_to_state(state, company_intelligence)
                print(f"✅ [Orchestrator] v1 Identity enrichment complete for '{state.startup_name}'")
                state.audit_trail.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "agent": "IdentityEnricher",
                    "message": "v1: Completed consolidated identity extraction.",
                    "metadata": {}
                })
            except Exception as e:
                print(f"⚠️ [Orchestrator] Identity extraction failed: {e}")
                state.errors.append(f"IdentityEnricher: {str(e)}")
        else:
            print(f"⚡ [Orchestrator] v2 pipeline: skipping CompanyWebsiteExtractor + v1 IdentityEnricher (handled by _run_v2_enrichment)")


        # 3. Deterministic scoring & Semantic alignment check (1 LLM call)
        state = self.identity_resolution_agent.run(state)

        # ---------------------------------------------------------------
        # Playwright Fallback (preserved exactly — no changes)
        # ---------------------------------------------------------------
        confidence = state.identity.get("identity_confidence", 0)
        website_url = ""
        website_field = state.identity.get("website")
        if isinstance(website_field, dict):
            website_url = website_field.get("value") or ""
        elif isinstance(website_field, str):
            website_url = website_field

        existing_text = (
            state.article_data.get("text_content", "")
            or state.article_data.get("crawled_content", {})
            .get("homepage", {})
            .get("text_content", "")
        )

        low_trust_threshold = 50
        playwright_min_text_len = 200
        rules_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "config", "crawler_rules.json"
        )
        if os.path.exists(rules_path):
            try:
                with open(rules_path, "r", encoding="utf-8") as f:
                    rules_cfg = json.load(f)
                    low_trust_threshold = rules_cfg.get("low_trust_threshold", low_trust_threshold)
                    playwright_min_text_len = rules_cfg.get(
                        "playwright_min_text_len", playwright_min_text_len
                    )
            except Exception:
                pass

        if confidence < low_trust_threshold and website_url and len(existing_text) < playwright_min_text_len:
            print(
                f"🔄 [AgentOrchestrator] Trust score is low ({confidence}) and website text content "
                f"is sparse ({len(existing_text)} chars). Triggering dynamic Playwright fallback..."
            )
            import time
            import gc

            gc.collect()
            time.sleep(1.0)

            start_time = time.perf_counter()
            playwright_success = False
            dynamic_html = ""

            try:
                from playwright.sync_api import sync_playwright

                playwright_timeout = 5000
                if os.path.exists(rules_path):
                    try:
                        with open(rules_path, "r", encoding="utf-8") as f:
                            rules_cfg = json.load(f)
                            playwright_timeout = rules_cfg.get(
                                "playwright_timeout_ms", playwright_timeout
                            )
                    except Exception:
                        pass

                with sync_playwright() as p:
                    browser = None
                    try:
                        browser = p.chromium.launch(headless=True)
                        page = browser.new_page()
                        page.set_default_navigation_timeout(playwright_timeout)
                        page.goto(website_url, wait_until="networkidle")
                        dynamic_html = page.content()
                        playwright_success = True
                    finally:
                        if browser:
                            try:
                                browser.close()
                            except Exception:
                                pass

            except Exception as pe:
                print(f"⚠️ Playwright fallback crawl failed: {pe}")
                state.errors.append(f"Playwright fallback crawl failed: {str(pe)}")
            finally:
                gc.collect()
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                try:
                    from backend.utils.tracing import log_agent_execution, generate_uuid
                    exec_id = "EXE_" + generate_uuid()
                    log_agent_execution(
                        exec_id=exec_id,
                        agent_name="PlaywrightFallback",
                        input_payload={"website": website_url, "previous_confidence": confidence},
                        output_payload={
                            "success": playwright_success,
                            "html_length": len(dynamic_html) if dynamic_html else 0,
                        },
                        duration_ms=duration_ms,
                    )
                except Exception as te:
                    print(f"⚠️ Tracing logger failed for PlaywrightFallback: {te}")

            if dynamic_html:
                try:
                    from backend.utils.crawler import extract_clean_text_from_html
                    clean_text = extract_clean_text_from_html(dynamic_html)
                    truncated_text = clean_text[:3000]
                    state.article_data["text_content"] = truncated_text
                    if "crawled_content" not in state.article_data:
                        state.article_data["crawled_content"] = {}
                    if "homepage" not in state.article_data["crawled_content"]:
                        state.article_data["crawled_content"]["homepage"] = {}
                    state.article_data["crawled_content"]["homepage"]["text_content"] = truncated_text

                    if not self._is_v2_enabled():
                        # v1 only: Rerun modular identity enrichment with the newly crawled content
                        identity_patch = self.identity_enricher.enrich_from_state(state)
                        company_intelligence.update(identity_patch)
                        state.article_data["company_intelligence"] = dict(company_intelligence)
                        self._sync_identity_to_state(state, company_intelligence)

                    # Always re-run resolution scoring (lightweight, no LLM)
                    state = self.identity_resolution_agent.run(state)
                    print(
                        f"✅ Re-ran Phase 1 verification. New identity trust score is: "
                        f"{state.identity.get('identity_confidence', 0)}"
                    )
                except Exception as re_err:
                    print(f"⚠️ Failed to parse dynamic html or re-verify: {re_err}")
                    state.errors.append(f"Playwright post-crawl processing failed: {str(re_err)}")


        # Log resolution status
        status = state.identity.get("verification_status", "NEEDS_REVIEW")
        confidence = state.identity.get("identity_confidence", 0)

        # Abort on active semantic mismatch (preserved exactly)
        if status == "MISMATCHED":
            mismatch_reason = state.identity.get("mismatch_reason", "Active contradiction between sources.")
            self.log_orchestrator_completion(
                state, f"⚠️ Semantic mismatch detected: {mismatch_reason}. Aborting pipeline enrichment."
            )
            state.confidence_score = 10
            state.recommendation_score = 10
            state.priority_band = "Ignore"
            state.relevance["score"] = 0
            state.strategic_fit["score"] = 0
            state.signals["score"] = 0
            state.startup_features.startup_status = "Needs Review"
            state.recommendation["recommended_action"] = "Needs Review"
            state.market_intelligence["enrichment_version"] = "3.0"
            state.market_intelligence["last_enriched_at"] = datetime.now(timezone.utc).isoformat()
            state.market_intelligence["last_verified_at"] = datetime.now(timezone.utc).isoformat()
            self.persist_to_database(state)
            return state

        self.log_orchestrator_completion(
            state, f"Identity status: '{status}' (Confidence: {confidence}). Running modular enrichment..."
        )

        # ---------------------------------------------------------------
        # AI LAYER 3: Modular Enrichment
        # v2: parallel enrichers via ThreadPoolExecutor (use_v2_pipeline=true)
        # v1: legacy serial enrichers (use_v2_pipeline=false, backward compat)
        # ---------------------------------------------------------------

        if self._is_v2_enabled():
            print(f"🚀 [Orchestrator] v2 parallel enrichment pipeline enabled")
            company_intelligence = self._run_v2_enrichment(state, company_intelligence)
        else:
            # ---- v1 serial path (unchanged) ----
            # 3b. Product/industry enrichment (~1 AI call)
            try:
                product_patch = self.product_enricher.enrich_from_state(state)
                company_intelligence.update(product_patch)
                state.article_data["company_intelligence"] = dict(company_intelligence)
                print(f"✅ [Orchestrator] Product enrichment complete for '{state.startup_name}'")
                state.audit_trail.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "agent": "ProductEnricher",
                    "message": "Completed product and sector classification enrichment.",
                    "metadata": {}
                })
            except Exception as e:
                print(f"⚠️ [Orchestrator] Product enrichment failed: {e}")
                state.errors.append(f"ProductEnricher: {str(e)}")

            # 3c. Funding enrichment (~1 AI call)
            try:
                funding_patch = self.funding_enricher.enrich_from_state(state)
                company_intelligence.update(funding_patch)
                state.article_data["company_intelligence"] = dict(company_intelligence)
                if funding_patch:
                    print(f"✅ [Orchestrator] Funding enrichment complete for '{state.startup_name}'")
                    state.audit_trail.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "agent": "FundingEnricher",
                        "message": "Completed funding history and investor enrichment.",
                        "metadata": {}
                    })
            except Exception as e:
                print(f"⚠️ [Orchestrator] Funding enrichment failed (non-blocking): {e}")
                state.errors.append(f"FundingEnricher: {str(e)}")

            # 3d. Intelligence enrichment (~1 AI call)
            try:
                intelligence_patch = self.intelligence_enricher.enrich_from_state(state)
                company_intelligence.update(intelligence_patch)
                state.article_data["company_intelligence"] = dict(company_intelligence)
                print(f"✅ [Orchestrator] Intelligence enrichment complete for '{state.startup_name}'")
                state.audit_trail.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "agent": "IntelligenceEnricher",
                    "message": "Completed competitive and strategic intelligence enrichment.",
                    "metadata": {}
                })
            except Exception as e:
                print(f"⚠️ [Orchestrator] Intelligence enrichment failed: {e}")
                state.errors.append(f"IntelligenceEnricher: {str(e)}")

        # Promote enriched intelligence into state fields for scoring compatibility
        self._sync_intelligence_to_state(state, company_intelligence)

        # ---------------------------------------------------------------
        # Scoring (unchanged — uses state.relevance, state.strategic_fit, etc.)
        # ---------------------------------------------------------------
        relevance_score = state.relevance.get("score", 0)
        fit_breakdown = state.strategic_fit.get("breakdown", {})
        deploy_breakdown = fit_breakdown.get("deployability", {})
        if isinstance(deploy_breakdown, dict) and "score" in deploy_breakdown:
            deployability_score = deploy_breakdown["score"]
        else:
            dep_str = str(state.startup_features.deployability).lower()
            if "high" in dep_str:
                deployability_score = 100
            elif "low" in dep_str:
                deployability_score = 10
            else:
                deployability_score = 50

        final_priority = ScoringService.calculate_priority_score(
            relevance_score=relevance_score,
            strategic_fit_score=state.strategic_fit.get("score", 0),
            deployability_score=deployability_score,
            signal_score=state.signals.get("score", 0),
        )
        final_confidence = ScoringService.calculate_confidence_score(state)
        rec_score = ScoringService.calculate_recommendation_score(final_priority, final_confidence)
        band = ScoringService.map_priority_band(final_priority)

        state.confidence_score = final_confidence
        state.recommendation_score = rec_score
        state.priority_band = band

        # Store enrichment metadata in state
        state.market_intelligence["enrichment_version"] = "3.0"
        state.market_intelligence["last_enriched_at"] = datetime.now(timezone.utc).isoformat()
        state.market_intelligence["last_verified_at"] = datetime.now(timezone.utc).isoformat()

        # Calculate explanations
        ExplanationService.generate_explanations(state)
        self.log_orchestrator_completion(
            state,
            f"Pipeline complete. Priority: {final_priority}, Rec: {rec_score}, Band: {band}",
        )

        self.persist_to_database(state)
        return state

    # -----------------------------------------------------------------------
    # v2 Parallel Enrichment Engine
    # -----------------------------------------------------------------------

    def _run_v2_enrichment(self, state: StartupState, company_intelligence: dict) -> dict:
        """
        Runs all 5 parallel enrichers concurrently (ThreadPoolExecutor, 5 workers),
        then runs IntelligenceEnricher serially (needs full context from all 5).

        Enrichers: Corporate, Identity, Product, Funding, Competitor.
        Each enricher reads crawled_pages + field-bucketed search_snippets from
        raw_source_payload (populated by the v2 source_collector).

        Fallback semantics: each enricher self-detects missing fields and fires
        targeted web searches via WebSearchOrchestrator._run_fallback().

        Results are merged into company_intelligence and returned.
        """
        from backend.utils.search import WebSearchOrchestrator

        startup_name = state.startup_name

        # ------------------------------------------------------------------
        # Resolve raw_source_payload (v2 format expected from source_collector)
        # ------------------------------------------------------------------
        raw_payload = state.article_data.get("raw_source_payload", {})
        crawled_pages = raw_payload.get("crawled_pages", {})
        all_snippets = raw_payload.get("search_snippets", {})

        # Fallback: use old crawled_content keys if raw_source_payload is absent
        if not crawled_pages:
            crawled_pages = state.article_data.get("crawled_content", {})

        # Get brand name from existing identity/company_intelligence
        clean_name = (
            company_intelligence.get("basic_information", {}).get("canonical_name")
            or state.startup_name
        )
        brand_name = (
            company_intelligence.get("basic_information", {}).get("canonical_name")
            or clean_name
        )

        orchestrator = WebSearchOrchestrator()

        # Number of parallel workers (externalized in pipeline_config.json)
        max_workers = (
            self._pipeline_cfg
            .get("v2_pipeline", {})
            .get("parallel_enrichment_workers", 5)
        )

        # ------------------------------------------------------------------
        # Define all 5 parallel enricher tasks
        # ------------------------------------------------------------------
        parallel_tasks = {
            "CorporateEnricher": lambda: self.corporate_enricher.enrich_v2(
                startup_name=startup_name,
                crawled_pages=crawled_pages,
                all_snippets=all_snippets,
                orchestrator=orchestrator,
                clean_name=clean_name,
                brand_name=brand_name,
            ),
            "IdentityEnricher": lambda: self.identity_enricher.enrich_v2(
                startup_name=startup_name,
                crawled_pages=crawled_pages,
                all_snippets=all_snippets,
                orchestrator=orchestrator,
                clean_name=clean_name,
                brand_name=brand_name,
            ),
            "ProductEnricher": lambda: self.product_enricher.enrich_v2(
                startup_name=startup_name,
                crawled_pages=crawled_pages,
                all_snippets=all_snippets,
                orchestrator=orchestrator,
                clean_name=clean_name,
                brand_name=brand_name,
            ),
            "FundingEnricher": lambda: self.funding_enricher.enrich_v2(
                startup_name=startup_name,
                crawled_pages=crawled_pages,
                all_snippets=all_snippets,
                orchestrator=orchestrator,
                clean_name=clean_name,
                brand_name=brand_name,
            ),
            "CompetitorEnricher": lambda: self.competitor_enricher.enrich_v2(
                startup_name=startup_name,
                crawled_pages=crawled_pages,
                all_snippets=all_snippets,
                orchestrator=orchestrator,
                clean_name=clean_name,
                brand_name=brand_name,
            ),
        }

        # ------------------------------------------------------------------
        # Execute parallel enrichers
        # ------------------------------------------------------------------
        # ------------------------------------------------------------------
        # Trace-ID propagation fix:
        # ContextVar values are NOT inherited by ThreadPoolExecutor child threads.
        # Capture the current trace_id here and inject it into each worker closure
        # so that _safe_supabase_insert (and obs_prompt_ledger logging) work in
        # the parallel enricher threads.
        # ------------------------------------------------------------------
        import time as _time
        from backend.utils.tracing import (
            get_trace_id as _get_trace_id,
            set_trace_id as _set_trace_id,
            generate_uuid as _gen_uuid,
            log_agent_execution as _log_agent_exec,
        )
        _current_trace_id = _get_trace_id()

        def _make_traced_task(fn, enricher_name: str):
            """
            Wraps an enricher callable to:
              1. Propagate trace_id into the child thread (Obs Gap 2 fix)
              2. Measure wall-clock duration for log_agent_execution (Obs Gap 1)
              3. Return (result, duration_ms, exception) so the main thread can
                 log success/failure without re-raising inside the executor.
            """
            def _traced():
                if _current_trace_id:
                    _set_trace_id(_current_trace_id)
                _t0 = _time.perf_counter()
                try:
                    _result = fn()
                    _dur = (_time.perf_counter() - _t0) * 1000.0
                    return _result, _dur, None
                except Exception as _ex:
                    _dur = (_time.perf_counter() - _t0) * 1000.0
                    return None, _dur, _ex
            return _traced

        print(
            f"⚡ [Orchestrator] Running {len(parallel_tasks)} enrichers in parallel "
            f"(workers={max_workers}) for '{startup_name}'"
        )

        enricher_results: dict = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_name = {
                executor.submit(_make_traced_task(fn, name)): name
                for name, fn in parallel_tasks.items()
            }
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    result, duration_ms, exc = future.result()
                    if exc is not None:
                        raise exc
                    enricher_results[name] = result or {}
                    print(f"  ✅ [{name}] completed ({round(duration_ms)}ms)")
                    state.audit_trail.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "agent": name,
                        "message": "v2 enrichment completed.",
                        "metadata": {"duration_ms": round(duration_ms)},
                    })
                    # Obs Gap 1 fix: log each parallel enricher to obs_agent_executions
                    try:
                        _log_agent_exec(
                            exec_id="EXE_" + _gen_uuid(),
                            agent_name=name,
                            input_payload={"startup_name": startup_name},
                            output_payload={"sections": list(enricher_results[name].keys())},
                            duration_ms=duration_ms,
                        )
                    except Exception as _te:
                        print(f"  ⚠️ Tracing log failed for [{name}]: {_te}")
                except Exception as e:
                    enricher_results[name] = {}
                    print(f"  ⚠️ [{name}] failed: {e}")
                    state.errors.append(f"{name}: {str(e)}")

        # ------------------------------------------------------------------
        # Merge parallel results into company_intelligence
        # ------------------------------------------------------------------
        # Corporate section → basic_information equivalent
        corp = enricher_results.get("CorporateEnricher", {})
        if corp:
            # Merge with existing basic_information (prefer enriched values)
            existing_bi = company_intelligence.get("basic_information", {})
            merged_bi = {**existing_bi, **{k: v for k, v in corp.items() if v is not None}}
            company_intelligence["basic_information"] = merged_bi
            company_intelligence["corporate"] = corp

        # Identity section → founders_details + leadership
        identity = enricher_results.get("IdentityEnricher", {})
        if identity:
            company_intelligence["founders_details"] = identity.get("founders", [])
            company_intelligence["leadership"] = identity.get("leadership", [])

        # Products section
        products = enricher_results.get("ProductEnricher", {})
        if products:
            company_intelligence["products_services"] = products.get("products", [])
            if products.get("business_profile"):
                existing_bp = company_intelligence.get("business_profile", {})
                company_intelligence["business_profile"] = {
                    **existing_bp, **products["business_profile"]
                }

        # Funding section
        funding = enricher_results.get("FundingEnricher", {})
        if funding:
            company_intelligence["funding_details"] = funding

        # Competitor section
        competitors = enricher_results.get("CompetitorEnricher", {})
        if competitors:
            company_intelligence["competitors_section"] = competitors

        state.article_data["company_intelligence"] = dict(company_intelligence)

        # ------------------------------------------------------------------
        # Bug 1 fix: Sync parallel enricher output back into StartupState fields.
        # In v1 this was done inline after IdentityEnricher; in v2 we must call it
        # here after all parallel results are merged so that ScoringService and the
        # DB persistence layer read correct city/founded_year/founders values.
        # ------------------------------------------------------------------
        self._sync_identity_to_state(state, company_intelligence)

        # ------------------------------------------------------------------
        # IntelligenceEnricher runs AFTER all 5 parallel enrichers
        # (sequential — needs full context: products, funding, competitors)
        #
        # Bug 3 fix: call enrich() directly with context built from the parallel
        # enrichers' results (products, funding, competitors) instead of calling
        # enrich_from_state() which previously read a stale/empty crawled_content.
        # ------------------------------------------------------------------
        _intel_start = _time.perf_counter()
        try:
            _products_result = enricher_results.get("ProductEnricher", {})
            _funding_result  = enricher_results.get("FundingEnricher", {})
            _comp_result     = enricher_results.get("CompetitorEnricher", {})
            _corp_result     = enricher_results.get("CorporateEnricher", {})

            # Build source_context from v2 crawled pages (raw_source_payload),
            # with fallback to v1 crawled_content so this works in both modes.
            _crawled_for_intel = raw_payload.get("crawled_pages", {}) or crawled_pages
            _intel_ctx_parts = []
            for _role, _max in (("homepage", 800), ("about", 600), ("products", 500), ("solutions", 400)):
                _page = _crawled_for_intel.get(_role, {})
                _text = _page.get("text_content", "") or _page.get("body_text", "")
                if _text:
                    _intel_ctx_parts.append(f"{_role.upper()}:\n{_text[:_max]}")
            _article_desc = state.article_data.get("description", "")
            if _article_desc:
                _intel_ctx_parts.append(f"NEWS ARTICLE:\n{_article_desc[:400]}")
            _intel_source_context = "\n\n".join(_intel_ctx_parts)

            # Synthesised business profile from parallel enrichers
            _bp = _products_result.get("business_profile", {})
            _intel_business_profile = {
                "sector": _bp.get("sector") or _corp_result.get("sector") or "",
                "business_model": (
                    _bp.get("business_model")
                    or _corp_result.get("business_model")
                    or ""
                ),
                "description": (
                    _bp.get("description")
                    or _corp_result.get("brief_description")
                    or state.article_data.get("description", "")[:200]
                ),
                "products_summary": ", ".join([
                    p.get("name", "")
                    for p in _products_result.get("products", [])[:3]
                    if p.get("name")
                ]),
                "funding_stage": _funding_result.get("latest_stage") or "Unknown",
                "key_competitors": ", ".join([
                    c.get("company_name", "")
                    for c in _comp_result.get("competitors", [])[:3]
                    if c.get("company_name")
                ]),
            }

            intelligence_patch = self.intelligence_enricher.enrich(
                startup_name=startup_name,
                source_context=_intel_source_context,
                existing_data=company_intelligence,
                business_profile=_intel_business_profile,
            )
            _intel_dur = (_time.perf_counter() - _intel_start) * 1000.0
            company_intelligence.update(intelligence_patch)
            state.article_data["company_intelligence"] = dict(company_intelligence)
            print(f"  ✅ [IntelligenceEnricher] completed ({round(_intel_dur)}ms)")
            state.audit_trail.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": "IntelligenceEnricher",
                "message": "v2 strategic intelligence enrichment completed.",
                "metadata": {"duration_ms": round(_intel_dur)},
            })
            # Obs Gap 1 fix: log IntelligenceEnricher to obs_agent_executions
            try:
                _log_agent_exec(
                    exec_id="EXE_" + _gen_uuid(),
                    agent_name="IntelligenceEnricher",
                    input_payload={"startup_name": startup_name},
                    output_payload={"sections": list(intelligence_patch.keys())},
                    duration_ms=_intel_dur,
                )
            except Exception as _te:
                print(f"  ⚠️ Tracing log failed for [IntelligenceEnricher]: {_te}")
        except Exception as e:
            print(f"  ⚠️ [IntelligenceEnricher] failed: {e}")
            state.errors.append(f"IntelligenceEnricher: {str(e)}")

        print(f"✅ [Orchestrator] v2 parallel enrichment complete for '{startup_name}'")
        return company_intelligence

    # -----------------------------------------------------------------------
    # State sync: promotes enricher output into StartupState fields
    # so that ScoringService (which reads state.*) still works unchanged
    # -----------------------------------------------------------------------

    def _sync_identity_to_state(self, state: StartupState, company_intelligence: dict):
        """
        Bridges basic_information and founders_details from early IdentityEnricher
        back into StartupState identity/features fields so that the Resolution agent
        and downstream logic can access resolved parameters.
        """
        basic = company_intelligence.get("basic_information", {})
        if basic:
            if basic.get("legal_name"):
                state.identity["legal_name"] = {
                    "value": basic["legal_name"],
                    "confidence": 95,
                    "source": "IdentityEnricher",
                    "source_url": "",
                    "evidence_text": "Resolved via consolidated IdentityEnricher."
                }
            if basic.get("website_url"):
                state.identity["website"] = {
                    "value": basic["website_url"],
                    "confidence": 95,
                    "source": "IdentityEnricher",
                    "source_url": basic["website_url"],
                    "evidence_text": "Resolved via consolidated IdentityEnricher."
                }
            if basic.get("linkedin_url"):
                state.identity["linkedin_company_url"] = {
                    "value": basic["linkedin_url"],
                    "confidence": 95,
                    "source": "IdentityEnricher",
                    "source_url": basic["linkedin_url"],
                    "evidence_text": "Resolved via consolidated IdentityEnricher."
                }
                state.startup_features.linkedin_company_url = basic["linkedin_url"]
                
            state.identity["city"] = normalize_city_name(basic.get("hq_city") or state.identity.get("city"))
            state.startup_features.city = normalize_city_name(basic.get("hq_city") or state.identity.get("city"))
            
            if basic.get("hq_state"):
                state.identity["state"] = basic["hq_state"]
                state.startup_features.state = basic["hq_state"]
            if basic.get("country"):
                state.identity["country"] = basic["country"]
                state.startup_features.country = basic["country"]
            if basic.get("headquarters"):
                state.identity["headquarters"] = basic["headquarters"]
                state.startup_features.headquarters = basic["headquarters"]
            if basic.get("founded_year"):
                try:
                    state.identity["founded_year"] = int(basic["founded_year"])
                    state.startup_features.founded_year = int(basic["founded_year"])
                except Exception:
                    pass

        founders = company_intelligence.get("founders_details", [])
        if founders:
            state.startup_features.leadership = [
                {"name": f.get("name", ""), "role": f.get("role", ""), "linkedin_url": f.get("linkedin_url", "")}
                for f in founders
            ]
            primary = founders[0]
            if primary.get("name") and primary.get("name") != "Unknown":
                state.startup_features.founder_name = primary.get("name")
                state.identity["primary_founder_name"] = primary.get("name")
            if primary.get("linkedin_url"):
                state.startup_features.founder_linkedin_url = primary.get("linkedin_url")

    def _sync_intelligence_to_state(self, state: StartupState, company_intelligence: dict):
        """
        Bridges company_intelligence enrichment output back into StartupState fields
        so that ScoringService and ExplanationService (which read state.relevance,
        state.strategic_fit, etc.) continue to work without modification.
        """
        bp = company_intelligence.get("business_profile", {})
        if bp:
            state.startup_features.industry = bp.get("industry") or state.startup_features.industry
            state.startup_features.sector = bp.get("sector") or state.startup_features.sector
            state.startup_features.subsector = bp.get("subsector") or state.startup_features.subsector
            state.startup_features.business_models = bp.get("business_models") or state.startup_features.business_models
            state.startup_features.tags = bp.get("tags") or state.startup_features.tags
            if bp.get("description"):
                state.article_data["business_description"] = bp["description"]

        founders = company_intelligence.get("founders_details", [])
        if founders:
            state.startup_features.leadership = [
                {"name": f.get("name", ""), "role": f.get("role", ""), "linkedin_url": f.get("linkedin_url", "")}
                for f in founders
            ]
            primary = founders[0]
            if primary.get("name") and primary.get("name") != "Unknown":
                state.startup_features.founder_name = primary.get("name")
            if primary.get("linkedin_url"):
                state.startup_features.founder_linkedin_url = primary.get("linkedin_url")

        basic = company_intelligence.get("basic_information", {})
        if basic:
            if basic.get("hq_city"):
                state.identity["city"] = normalize_city_name(basic["hq_city"])
            if basic.get("hq_state"):
                state.identity["state"] = basic["hq_state"]
            if basic.get("country"):
                state.identity["country"] = basic["country"]
            if basic.get("founded_year"):
                state.identity["founded_year"] = basic["founded_year"]

        # Sync BFSI relevance from intelligence enricher output
        bfsi = company_intelligence.get("_bfsi_relevance", {})
        if bfsi:
            state.relevance["score"] = bfsi.get("relevance_score", state.relevance.get("score", 0))
            if bfsi.get("use_cases"):
                state.recommendation["use_cases"] = [
                    u.get("use_case") if isinstance(u, dict) else u
                    for u in bfsi["use_cases"]
                ]

        strategic = company_intelligence.get("_strategic_fit", {})
        if strategic:
            state.strategic_fit["score"] = strategic.get("enterprise_readiness", state.strategic_fit.get("score", 50))

        recommendation = company_intelligence.get("_recommendation", {})
        if recommendation:
            state.recommendation["recommended_action"] = recommendation.get(
                "recommended_action", state.recommendation.get("recommended_action", "Monitor")
            )

    # -----------------------------------------------------------------------
    # persist_to_database — dual-write: analysis_json + company_intelligence
    # -----------------------------------------------------------------------
    def persist_to_database(self, state: StartupState):
        """
        Upserts master values to Postgres/Supabase tables.

        Dual-write strategy:
          1. startups table: core fields + company_intelligence JSONB (new)
          2. startup_analysis table: analysis_json (existing, for frontend compat)
        """
        try:
            fit_breakdown = state.strategic_fit.get("breakdown", {})
            deploy_breakdown = fit_breakdown.get("deployability", {})
            if isinstance(deploy_breakdown, dict) and "score" in deploy_breakdown:
                deployability_score = deploy_breakdown["score"]
            else:
                dep_str = str(state.startup_features.deployability).lower()
                if "high" in dep_str:
                    deployability_score = 100
                elif "low" in dep_str:
                    deployability_score = 10
                else:
                    deployability_score = 50

            from backend.services.scoring_service import ScoringService
            final_priority = ScoringService.calculate_priority_score(
                relevance_score=state.relevance.get("score", 0),
                strategic_fit_score=state.strategic_fit.get("score", 0),
                deployability_score=deployability_score,
                signal_score=state.signals.get("score", 0),
            )

            # ------------------------------------------------------------------
            # 1. Build startups table payload
            # ------------------------------------------------------------------
            ci = state.article_data.get("company_intelligence", {})
            basic = ci.get("basic_information", {})
            digital = ci.get("digital_presence", {})
            funding = ci.get("funding_details", {})

            payload = {
                "startup_name": state.startup_name,
                "website": (
                    basic.get("website_url")
                    or state.identity.get("website", {}).get("value", "")
                ),
                "linkedin_url": (
                    basic.get("linkedin_url")
                    or digital.get("linkedin_url")
                    or state.identity.get("linkedin_company_url", {}).get("value", "")
                ),
                "linkedin_company_url": (
                    basic.get("linkedin_url")
                    or state.identity.get("linkedin_company_url", {}).get("value", "")
                ),
                "legal_name": (
                    basic.get("legal_name")
                    or state.identity.get("legal_name", {}).get("value", "")
                ),
                "description": (
                    state.article_data.get("business_description")
                    or ci.get("business_profile", {}).get("description")
                    or state.article_data.get("description", "")
                ),
                "industry": state.startup_features.industry,
                "sector": state.startup_features.sector,
                "subsector": state.startup_features.subsector,
                "priority_band": state.priority_band,
                "relevance_score": state.relevance.get("score", 0),
                "confidence_score": state.confidence_score,
                "recommendation_score": state.recommendation_score,
                "city": normalize_city_name(basic.get("hq_city") or state.identity.get("city")),
                "state": basic.get("hq_state") or state.identity.get("state") or "Unknown",
                "country": basic.get("country") or state.identity.get("country") or "India",
                "headquarters": (
                    basic.get("headquarters")
                    or state.identity.get("headquarters")
                    or state.startup_features.headquarters
                    or "Unknown"
                ),
                "founded_year": (
                    basic.get("founded_year")
                    or state.identity.get("founded_year")
                    or state.startup_features.founded_year
                ),
                "funding_stage": (
                    funding.get("latest_stage")
                    or state.startup_features.startup_stage
                ),
                "status": state.startup_features.startup_status or "Screening",
                "verification_notes": state.identity.get("verification_notes") or "",
            }

            res = upsert_startup(payload)
            if res:
                if isinstance(res, list) and len(res) > 0:
                    state.startup_id = res[0]["id"]
                elif isinstance(res, dict) and "id" in res:
                    state.startup_id = res["id"]

            # ------------------------------------------------------------------
            # 2. Dual-write company_intelligence JSONB (new canonical store)
            # ------------------------------------------------------------------
            if state.startup_id and ci:
                try:
                    # Attach source_metadata
                    now_iso = datetime.now(timezone.utc).isoformat()
                    ci["source_metadata"] = {
                        "schema_version": "1.0",
                        "enrichment_version": "3.0",
                        "last_enriched_at": now_iso,
                        "trigger_article_url": state.article_data.get("source_url", ""),
                        "trigger_headline": state.article_data.get("headline", ""),
                        "enrichment_sections_completed": [
                            s for s in ["identity", "products", "funding", "intelligence"]
                            if any(
                                k in ci
                                for k in {
                                    "identity": ["basic_information", "founders_details"],
                                    "products": ["business_profile", "products_services"],
                                    "funding": ["funding_details"],
                                    "intelligence": ["competitors"],
                                }[s]
                            )
                        ],
                    }

                    # Attach validation_metadata from identity resolution
                    validation_metadata = {
                        "resolution_confidence": state.identity.get("identity_confidence", 0),
                        "verification_status": state.identity.get("verification_status", ""),
                        "last_resolved_at": now_iso,
                        "resolution_source": state.identity.get("resolution_source", ""),
                        "mismatch_reason": state.identity.get("mismatch_reason", ""),
                    }

                    enrichment_metadata = {
                        "enrichment_version": "3.0",
                        "last_enriched_at": now_iso,
                        "sections_completed": ci.get("source_metadata", {}).get(
                            "enrichment_sections_completed", []
                        ),
                    }

                    supabase.table("startups").update({
                        "company_intelligence": ci,
                        "validation_metadata": validation_metadata,
                        "enrichment_metadata": enrichment_metadata,
                    }).eq("id", state.startup_id).execute()

                    print(f"✅ [Orchestrator] Wrote company_intelligence JSONB for startup_id={state.startup_id}")
                except Exception as ci_err:
                    # Non-blocking — analysis_json still written below
                    print(f"⚠️ [Orchestrator] company_intelligence write failed (non-blocking): {ci_err}")
                    state.errors.append(f"CI JSONB write: {str(ci_err)}")

            # ------------------------------------------------------------------
            # 3. analysis_json dual-write (backward-compat with existing frontend)
            # ------------------------------------------------------------------
            if state.startup_id:
                competitors_list = ci.get("competitors", [])
                bfsi_uc = ci.get("_bfsi_relevance", {}).get("use_cases", [])
                
                # Align founders details formatting
                founders_raw = ci.get("founders_details") or state.startup_features.leadership or []
                founders_mapped = []
                for f in founders_raw:
                    if isinstance(f, dict) and f.get("name"):
                        founders_mapped.append({
                            "name": f.get("name", ""),
                            "role": f.get("role", ""),
                            "brief_details": f.get("brief_details") or f.get("background") or f.get("role") or "",
                            "linkedin_url": f.get("linkedin_url") or ""
                        })
                if not founders_mapped and state.startup_features.founder_name and state.startup_features.founder_name != "Unknown":
                    founders_mapped.append({
                        "name": state.startup_features.founder_name,
                        "role": "Founder",
                        "brief_details": "",
                        "linkedin_url": state.startup_features.founder_linkedin_url or ""
                    })

                analysis_payload = {
                    "summary": {
                        "one_liner": (
                            ci.get("business_profile", {}).get("description")
                            or ci.get("business_profile", {}).get("one_liner")
                            or state.article_data.get("business_description", "")
                            or state.article_data.get("description", "")
                        ),
                        "business_model": (
                            ", ".join(ci.get("business_profile", {}).get("business_models", []))
                            if isinstance(ci.get("business_profile", {}).get("business_models"), list)
                            else ci.get("business_profile", {}).get("business_model", "")
                        ),
                        "target_audience": (
                            ci.get("business_profile", {}).get("target_customer")
                            or state.identity.get("target_customer")
                            or "Enterprise / B2B"
                        ),
                        "verification_notes": state.identity.get("verification_notes") or "",
                        "mismatch_reason": state.identity.get("mismatch_reason") or "",
                    },
                    "verification_notes": state.identity.get("verification_notes") or "",
                    "mismatch_reason": state.identity.get("mismatch_reason") or "",
                    "bfsi_relevance": {
                        "is_relevant": state.relevance.get("score", 0) >= 30,
                        "relevance_score": state.relevance.get("score", 0),
                        "use_cases": bfsi_uc or state.market_intelligence.get(
                            "opportunity_mapping", {}
                        ).get("value", []),
                    },
                    "strategic_fit": {
                        "enterprise_readiness": state.strategic_fit.get("score", 50),
                        "partnership_opportunity": state.recommendation.get(
                            "recommended_action", "Monitor"
                        ),
                        "integration_feasibility": state.startup_features.deployability or "Medium",
                    },
                    "scoring": {
                        "overall_priority_score": final_priority,
                        "risk_assessment": ci.get("_scoring", {}).get("risk_assessment", ""),
                    },
                    "classification": {
                        "industry": state.startup_features.industry or "Unknown",
                        "sector": state.startup_features.sector or "Unknown",
                        "subsector": state.startup_features.subsector or "Unknown",
                        "business_models": state.startup_features.business_models or [],
                        "industry_relevance": state.startup_features.relevant_entities or [],
                        "tags": state.startup_features.tags or [],
                    },
                    "founders": founders_mapped,
                    "competitors": competitors_list,
                    "linkedin_reachout_message": state.recommendation.get("linkedin_reachout_message", ""),
                    "email_reachout_message": state.recommendation.get("email_reachout_message", ""),
                    "market_intelligence": state.market_intelligence,
                    "relevance_score": state.relevance.get("score", 0),
                    "confidence_score": state.confidence_score,
                    "recommendation_score": state.recommendation_score,
                    "priority_band": state.priority_band,
                    "recommended_action": state.recommendation.get("recommended_action") or "Monitor",
                    "matched_entities": state.startup_features.relevant_entities or [],
                    "matched_business_teams": state.startup_features.business_teams or [],
                    "matched_business_problems": state.startup_features.business_problems or [],
                    "positive_signals": state.startup_features.positive_signals or [],
                    "negative_signals": state.startup_features.negative_signals or [],
                    "city": normalize_city_name(basic.get("hq_city") or state.identity.get("city")),
                    "state": basic.get("hq_state") or state.identity.get("state") or "Unknown",
                    "country": basic.get("country") or state.identity.get("country") or "India",
                    "headquarters": payload["headquarters"],
                    "founded_year": payload["founded_year"],
                    "startup_stage": state.startup_features.startup_stage,
                    "status": state.startup_features.startup_status or "Screening",
                }
                save_startup_analysis(state.startup_id, analysis_payload)
                
                # Sync company_intelligence products & competitors with market_intelligence columns
                try:
                    from backend.services.supabase_service import sync_company_intelligence_to_market_intelligence
                    sync_company_intelligence_to_market_intelligence(state.startup_id)
                except Exception as sync_err:
                    print(f"⚠️ Failed to sync CI to MI: {sync_err}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"⚠️ Orchestrator database persistence failed: {e}")

    def log_orchestrator_completion(self, state: StartupState, message: str):
        state.audit_trail.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "Orchestrator",
            "message": message,
            "metadata": {
                "identity_confidence": state.identity.get("identity_confidence", 0),
                "verification_status": state.identity.get("verification_status", "NEEDS_REVIEW"),
            },
        })
