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
                "headline": raw_startup.get("startup_name", ""),
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

        # Log resolution status and proceed with downstream enrichment
        status = state.identity.get("verification_status", "NEEDS_REVIEW")
        confidence = state.identity.get("identity_confidence", 0)
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
        if relevance_score >= 30:
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
                "status": state.startup_features.startup_status or "Screening"
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
                        "business_model": ""  # Can be filled or derived
                    },
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
