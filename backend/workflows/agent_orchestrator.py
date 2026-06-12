import os
import json
from datetime import datetime, timezone
from backend.models.startup_state import StartupState
from backend.models.startup_features import StartupFeatures
from backend.agents.identity_discovery_agent import IdentityDiscoveryAgent
from backend.agents.identity_resolution_agent import IdentityResolutionAgent
from backend.agents.legal_name_agent import LegalNameAgent
from backend.agents.description_generator_agent import DescriptionGeneratorAgent
from backend.agents.product_intelligence_agent import ProductIntelligenceAgent
from backend.agents.industry_classification_agent import IndustryClassificationAgent
from backend.agents.competitor_intelligence_agent import CompetitorIntelligenceAgent
from backend.agents.funding_intelligence_agent import FundingIntelligenceAgent
from backend.agents.opportunity_mapping_agent import OpportunityMappingAgent
from backend.agents.enrichment_agent import EnrichmentAgent
from backend.agents.classification_agent import ClassificationAgent
from backend.agents.market_intelligence_agent import MarketIntelligenceAgent
from backend.agents.business_problem_agent import BusinessProblemAgent
from backend.agents.relevance_agent import RelevanceAgent
from backend.agents.strategic_fit_agent import StrategicFitAgent
from backend.agents.signal_agent import SignalAgent
from backend.agents.recommendation_agent import RecommendationAgent
from backend.services.explanation_service import ExplanationService
from backend.services.scoring_service import ScoringService
from backend.services.supabase_service import (
    supabase,
    upsert_startup,
    save_startup_analysis,
    save_funding_rounds
)

class AgentOrchestrator:
    def __init__(self):
        # Step 0a/0b: Identity resolution (runs before all enrichment)
        self.identity_discovery_agent = IdentityDiscoveryAgent()
        self.identity_resolution_agent = IdentityResolutionAgent()
        self.legal_name_agent = LegalNameAgent()
        
        # Downstream Intelligence Agents
        self.desc_agent = DescriptionGeneratorAgent()
        self.product_agent = ProductIntelligenceAgent()
        self.industry_classification_agent = IndustryClassificationAgent()
        self.competitor_agent = CompetitorIntelligenceAgent()
        self.funding_agent = FundingIntelligenceAgent()
        self.opportunity_agent = OpportunityMappingAgent()
        
        # Legacy fallback compatibility agents
        self.enrich_agent = EnrichmentAgent()
        self.class_agent = ClassificationAgent()
        self.market_intel_agent = MarketIntelligenceAgent()
        self.biz_prob_agent = BusinessProblemAgent()
        self.relevance_agent = RelevanceAgent()
        self.fit_agent = StrategicFitAgent()
        self.signal_agent = SignalAgent()
        self.rec_agent = RecommendationAgent()

    def run_pipeline(self, raw_startup: dict) -> StartupState:
        """
        Executes the sequential multi-agent orchestration workflow.
        Input raw_startup dictionary keys: startup_name, description, source, source_url.
        """
        print(f"🎬 Starting Orchestrated Multi-Agent Run for '{raw_startup.get('startup_name')}'...")
        
        # Initialize typed state
        state = StartupState(
            startup_name=raw_startup.get("startup_name", "Unknown"),
            article_data={
                "headline": raw_startup.get("headline") or raw_startup.get("startup_name", ""),
                "description": raw_startup.get("description", ""),
                "source": raw_startup.get("source", "Unknown"),
                "source_url": raw_startup.get("source_url", "")
            }
        )
        
        # Attempt to pre-populate startup_id from existing DB record
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
            "metadata": {}
        })

        # ---------------------------------------------------------
        # Phase 1: Entity Discovery & Resolution
        # ---------------------------------------------------------
        state = self.identity_discovery_agent.run(state)
        state = self.legal_name_agent.run(state)
        state = self.identity_resolution_agent.run(state)

        # ---------------------------------------------------------
        # Playwright Fallback Check for dynamic JS-heavy sites
        # ---------------------------------------------------------
        confidence = state.identity.get("identity_confidence", 0)
        website_url = ""
        website_field = state.identity.get("website")
        if isinstance(website_field, dict):
            website_url = website_field.get("value") or ""
        elif isinstance(website_field, str):
            website_url = website_field

        existing_text = state.article_data.get("text_content", "") or state.article_data.get("crawled_content", {}).get("homepage", {}).get("text_content", "")
        
        # Load trigger rule threshold (default: confidence < 50, min text len < 200)
        low_trust_threshold = 50
        playwright_min_text_len = 200
        rules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "crawler_rules.json")
        if os.path.exists(rules_path):
            try:
                with open(rules_path, "r", encoding="utf-8") as f:
                    rules_cfg = json.load(f)
                    low_trust_threshold = rules_cfg.get("low_trust_threshold", low_trust_threshold)
                    playwright_min_text_len = rules_cfg.get("playwright_min_text_len", playwright_min_text_len)
            except Exception:
                pass

        if confidence < low_trust_threshold and website_url and len(existing_text) < playwright_min_text_len:
            print(f"🔄 [AgentOrchestrator] Trust score is low ({confidence}) and website text content is sparse ({len(existing_text)} chars). Triggering dynamic Playwright fallback...")
            import time
            import gc
            
            # GC and sleep to safeguard Macbook Air M2 8GB RAM memory floor
            gc.collect()
            time.sleep(1.0)
            
            start_time = time.perf_counter()
            playwright_success = False
            dynamic_html = ""
            
            try:
                # Lazy load playwright sync module inside dynamic execution path to reduce baseline RAM footprint
                from playwright.sync_api import sync_playwright
                
                playwright_timeout = 5000
                if os.path.exists(rules_path):
                    try:
                        with open(rules_path, "r", encoding="utf-8") as f:
                            rules_cfg = json.load(f)
                            playwright_timeout = rules_cfg.get("playwright_timeout_ms", playwright_timeout)
                    except Exception:
                        pass
                
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.set_default_navigation_timeout(playwright_timeout)
                    
                    # Navigate and wait for DOM network idle state
                    page.goto(website_url, wait_until="networkidle")
                    dynamic_html = page.content()
                    browser.close()
                    playwright_success = True
            except Exception as pe:
                print(f"⚠️ Playwright fallback crawl failed: {pe}")
                state.errors.append(f"Playwright fallback crawl failed: {str(pe)}")
            finally:
                # Force browser cleanup GC
                gc.collect()
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                
                # Tracing telemetry hook integration
                try:
                    from backend.utils.tracing import log_agent_execution, generate_uuid
                    exec_id = "EXE_" + generate_uuid()
                    log_agent_execution(
                        exec_id=exec_id,
                        agent_name="PlaywrightFallback",
                        input_payload={"website": website_url, "previous_confidence": confidence},
                        output_payload={"success": playwright_success, "html_length": len(dynamic_html) if dynamic_html else 0},
                        duration_ms=duration_ms
                    )
                except Exception as te:
                    print(f"⚠️ Tracing logger failed for PlaywrightFallback: {te}")
            
            # If dynamic content was fetched successfully, extract clean text using website density rules
            if dynamic_html:
                try:
                    from backend.utils.crawler import extract_clean_text_from_html
                    clean_text = extract_clean_text_from_html(dynamic_html)
                    
                    # Truncate to first 3000 characters and write back to state
                    truncated_text = clean_text[:3000]
                    state.article_data["text_content"] = truncated_text
                    
                    # Sync to crawled_content block so downstream agents see it
                    if "crawled_content" not in state.article_data:
                        state.article_data["crawled_content"] = {}
                    if "homepage" not in state.article_data["crawled_content"]:
                        state.article_data["crawled_content"]["homepage"] = {}
                    
                    state.article_data["crawled_content"]["homepage"]["text_content"] = truncated_text
                    
                    # Re-run Phase 1 agents to re-compute trust index
                    state = self.legal_name_agent.run(state)
                    state = self.identity_resolution_agent.run(state)
                    print(f"✅ Re-ran Phase 1 verification. New identity trust score is: {state.identity.get('identity_confidence', 0)}")
                except Exception as re:
                    print(f"⚠️ Failed to parse dynamic html or re-verify: {re}")
                    state.errors.append(f"Playwright post-crawl processing failed: {str(re)}")

        # Log resolution status and proceed with downstream enrichment
        status = state.identity.get("verification_status", "NEEDS_REVIEW")
        confidence = state.identity.get("identity_confidence", 0)
        
        # Abort Phase 2 processing on active semantic mismatch
        if status == "MISMATCHED":
            mismatch_reason = state.identity.get("mismatch_reason", "Active contradiction between sources.")
            self.log_orchestrator_completion(state, f"⚠️ Semantic mismatch detected: {mismatch_reason}. Aborting pipeline enrichment.")
            
            # Set state scoring variables to 10/0/Ignore
            state.confidence_score = 10
            state.recommendation_score = 10
            state.priority_band = "Ignore"
            state.relevance["score"] = 0
            state.strategic_fit["score"] = 0
            state.signals["score"] = 0
            
            state.startup_features.startup_status = "Needs Review"
            state.recommendation["recommended_action"] = "Needs Review"
            
            # Store standardized production-grade analysis_json payload metadata
            state.market_intelligence["enrichment_version"] = "2.0"
            state.market_intelligence["last_enriched_at"] = datetime.now(timezone.utc).isoformat()
            state.market_intelligence["last_verified_at"] = datetime.now(timezone.utc).isoformat()
            
            self.persist_to_database(state)
            return state

        self.log_orchestrator_completion(state, f"Identity status: '{status}' (Confidence: {confidence}). Continuing pipeline enrichment...")

        # ---------------------------------------------------------
        # Phase 2: Downstream Intelligence modules
        # ---------------------------------------------------------
        state = self.desc_agent.run(state)
        state = self.product_agent.run(state)
        state = self.industry_classification_agent.run(state)
        state = self.competitor_agent.run(state)
        state = self.opportunity_agent.run(state)
        
        # Funding is optional and non-blocking
        state = self.funding_agent.run(state)

        # Legacy backward compatibility mappings (scoring & evaluation hooks)
        state = self.biz_prob_agent.run(state)
        state = self.relevance_agent.run(state)

        # Gated check for fitting assessment
        relevance_score = state.relevance.get("score", 0)
        if relevance_score >= 20:
            state = self.fit_agent.run(state)
            state = self.signal_agent.run(state)
            state = self.rec_agent.run(state)
        else:
            state = self.rec_agent.run(state)

        # Compute deployability score
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

        # Calculate final scores & priority band
        final_priority = ScoringService.calculate_priority_score(
            relevance_score=relevance_score,
            strategic_fit_score=state.strategic_fit.get("score", 0),
            deployability_score=deployability_score,
            signal_score=state.signals.get("score", 0)
        )
        
        final_confidence = ScoringService.calculate_confidence_score(state)
        rec_score = ScoringService.calculate_recommendation_score(final_priority, final_confidence)
        band = ScoringService.map_priority_band(final_priority)
        
        state.confidence_score = final_confidence
        state.recommendation_score = rec_score
        state.priority_band = band

        # Store standardized production-grade analysis_json payload
        state.market_intelligence["enrichment_version"] = "2.0"
        state.market_intelligence["last_enriched_at"] = datetime.now(timezone.utc).isoformat()
        state.market_intelligence["last_verified_at"] = datetime.now(timezone.utc).isoformat()
        
        # Calculate explanations
        explanations = ExplanationService.generate_explanations(state)
        self.log_orchestrator_completion(state, f"Pipeline execution completed. Priority: {final_priority}, Recommendation: {rec_score}, Band: {band}")
        
        # Save records to master database tables
        self.persist_to_database(state)
        return state

    def log_orchestrator_completion(self, state: StartupState, message: str):
        state.audit_trail.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "Orchestrator",
            "message": message,
            "metadata": {
                "identity_confidence": state.identity.get("identity_confidence", 0),
                "verification_status": state.identity.get("verification_status", "NEEDS_REVIEW")
            }
        })

    def persist_to_database(self, state: StartupState):
        """Upsert master values to Postgres/Supabase tables."""
        try:
            # Recalculate deployability and final priority score for database storage
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
                signal_score=state.signals.get("score", 0)
            )

            payload = {
                "startup_name": state.startup_name,
                "website": state.identity.get("website", {}).get("value", ""),
                "linkedin_url": state.identity.get("linkedin_company_url", {}).get("value", ""),
                "linkedin_company_url": state.identity.get("linkedin_company_url", {}).get("value", ""),
                "legal_name": state.identity.get("legal_name", {}).get("value", ""),
                "description": state.article_data.get("business_description") or state.article_data.get("description", ""),
                "industry": state.startup_features.industry,
                "sector": state.startup_features.sector,
                "subsector": state.startup_features.subsector,
                "priority_band": state.priority_band,
                "relevance_score": state.relevance.get("score", 0),
                "confidence_score": state.confidence_score,
                "recommendation_score": state.recommendation_score,
                "city": state.identity.get("city") or "Unknown",
                "state": state.identity.get("state") or "Unknown",
                "country": state.identity.get("country") or "India",
                "headquarters": state.identity.get("headquarters") or state.startup_features.headquarters or "Unknown",
                "founded_year": state.identity.get("founded_year") or state.startup_features.founded_year,
                "funding_stage": state.startup_features.startup_stage,
                "status": state.startup_features.startup_status or "Screening",
                "verification_notes": state.identity.get("verification_notes") or ""
            }
            res = upsert_startup(payload)
            if res:
                if isinstance(res, list) and len(res) > 0:
                    state.startup_id = res[0]["id"]
                elif isinstance(res, dict) and "id" in res:
                    state.startup_id = res["id"]
                
            # Insert/Update into startup_analysis
            if state.startup_id:
                # Build a standard structured analysis payload fully compatible with the frontend
                analysis_payload = {
                    "summary": {
                        "one_liner": state.article_data.get("business_description") or state.article_data.get("description", ""),
                        "business_model": "",  # Can be filled or derived
                        "verification_notes": state.identity.get("verification_notes") or "",
                        "mismatch_reason": state.identity.get("mismatch_reason") or ""
                    },
                    "verification_notes": state.identity.get("verification_notes") or "",
                    "mismatch_reason": state.identity.get("mismatch_reason") or "",
                    "bfsi_relevance": {
                        "is_relevant": state.relevance.get("score", 0) >= 30,
                        "relevance_score": state.relevance.get("score", 0),
                        "use_cases": state.market_intelligence.get("opportunity_mapping", {}).get("value", [])
                    },
                    "strategic_fit": {
                        "enterprise_readiness": state.strategic_fit.get("score", 50),
                        "partnership_opportunity": state.recommendation.get("recommended_action", "Monitor"),
                        "integration_feasibility": state.startup_features.deployability or "Medium"
                    },
                    "scoring": {
                        "overall_priority_score": final_priority,
                        "risk_assessment": ""
                    },
                    "classification": {
                        "industry": state.startup_features.industry or "Unknown",
                        "sector": state.startup_features.sector or "Unknown",
                        "subsector": state.startup_features.subsector or "Unknown",
                        "business_models": state.startup_features.business_models or [],
                        "industry_relevance": state.startup_features.relevant_entities or [],
                        "tags": state.startup_features.tags or []
                    },
                    "founders": state.startup_features.leadership or (
                        [{"name": state.startup_features.founder_name, "role": "Founder", "brief_details": "", "linkedin_url": state.startup_features.founder_linkedin_url}]
                        if state.startup_features.founder_name and state.startup_features.founder_name != "Unknown" else []
                    ),
                    "linkedin_reachout_message": state.recommendation.get("linkedin_reachout_message", ""),
                    "email_reachout_message": state.recommendation.get("email_reachout_message", ""),
                    "market_intelligence": state.market_intelligence,
                    
                    # Store extra top-level fields for safety
                    "relevance_score": state.relevance.get("score", 0),
                    "confidence_score": state.confidence_score,
                    "recommendation_score": state.recommendation_score,
                    "priority_band": state.priority_band,
                    "matched_entities": state.startup_features.relevant_entities or [],
                    "matched_business_teams": state.startup_features.business_teams or [],
                    "matched_business_problems": state.startup_features.business_problems or [],
                    "positive_signals": state.startup_features.positive_signals or [],
                    "negative_signals": state.startup_features.negative_signals or [],
                    
                    # Explicit sync of geographic and startup info
                    "city": state.identity.get("city") or "Unknown",
                    "state": state.identity.get("state") or "Unknown",
                    "country": state.identity.get("country") or "India",
                    "headquarters": state.identity.get("headquarters") or state.startup_features.headquarters or "Unknown",
                    "founded_year": state.identity.get("founded_year") or state.startup_features.founded_year,
                    "startup_stage": state.startup_features.startup_stage,
                    "status": state.startup_features.startup_status or "Screening"
                }
                save_startup_analysis(state.startup_id, analysis_payload)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"⚠️ Orchestrator database persistence failed: {e}")
