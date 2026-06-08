import os
import json
from datetime import datetime
from backend.models.startup_state import StartupState
from backend.models.startup_features import StartupFeatures
from backend.agents.identity_discovery_agent import IdentityDiscoveryAgent
from backend.agents.identity_resolution_agent import IdentityResolutionAgent
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
        # Step 1+: Enrichment and analysis agents
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
            "timestamp": datetime.now().isoformat(),
            "agent": "Orchestrator",
            "message": "Initialized StartupState.",
            "metadata": {}
        })

        # Step 0a: Identity Discovery (registry-first, deterministic)
        state = self.identity_discovery_agent.run(state)

        # Step 0b: Identity Resolution (confidence gate + DB persistence)
        state = self.identity_resolution_agent.run(state)

        # Step 1: Enrichment (now identity-aware — state.identity is pre-populated)
        state = self.enrich_agent.run(state)
        
        # Step 2: Classification
        state = self.class_agent.run(state)
        
        # Step 3: Business Problem Mapping
        state = self.biz_prob_agent.run(state)
        
        # Step 4: Relevance Assessment
        state = self.relevance_agent.run(state)

        # Step 5: Relevance Gate Rule Check
        relevance_score = state.relevance.get("score", 0)
        if relevance_score >= 50:
            # Run remaining downstream analysis
            state = self.market_intel_agent.run(state)
            state = self.fit_agent.run(state)
            state = self.signal_agent.run(state)
            state = self.rec_agent.run(state)
        else:
            # Gated: Bypassed Market Intelligence, Strategic Fit, and Signal Agents
            state = self.rec_agent.run(state)

        # Calculate deployability score
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
        
        confidence = ScoringService.calculate_confidence_score(state)
        rec_score = ScoringService.calculate_recommendation_score(final_priority, confidence)
        band = ScoringService.map_priority_band(final_priority)
        
        state.confidence_score = confidence
        state.recommendation_score = rec_score
        state.priority_band = band

        # Calculate final explanations
        explanations = ExplanationService.generate_explanations(state)

        state.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "agent": "Orchestrator",
            "message": f"Pipeline execution completed. Priority: {final_priority}, Recommendation: {rec_score}, Confidence: {confidence}, Band: {band}",
            "metadata": {
                "final_priority": final_priority,
                "confidence_score": confidence,
                "recommendation_score": rec_score,
                "priority_band": band,
                "explanations": explanations
            }
        })

        # Save to database
        self._persist_state(state, final_priority, explanations)

        return state

    def _persist_state(self, state: StartupState, final_score: int, explanations: dict):
        """Formats state data into database-compatible columns and performs upsert."""
        try:
            print(f"💾 Persisting orchestrator state to database for '{state.startup_name}'...")
            
            # 1. Upsert basic startup details
            hq_val = state.article_data.get("enriched_raw", {}).get("tracxn_profile", {}).get("headquarters") or state.startup_features.headquarters or "Unknown"
            # Resolve identity-derived website (identity agent > enrichment fallback)
            resolved_website = (
                state.identity.get("website")
                or state.article_data.get("enriched_raw", {}).get("resolved_website", "")
            )

            products_services_val = explanations.get("relevance", {}).get("reasons", [""])[0] if explanations.get("relevance", {}).get("reasons") else ""
            startup_payload = {
                "startup_name": state.startup_name,
                "website": resolved_website,
                "description": state.article_data.get("description", ""),
                "source": state.article_data.get("source", "Unknown"),
                "source_url": state.article_data.get("source_url", ""),
                "industry": "Financial Services",  # Default industry
                "sector": state.startup_features.sector,
                "subsector": state.startup_features.subsector,
                "funding_stage": state.startup_features.startup_stage,
                "business_models": state.article_data.get("enriched_raw", {}).get("tracxn_profile", {}).get("business_models", []),
                "tags": state.article_data.get("enriched_raw", {}).get("tracxn_profile", {}).get("tags", []),
                "startup_status": state.recommendation.get("recommended_action") or "Screening",
                "headquarters": hq_val,
                "startup_stage": state.startup_features.startup_stage,
                # Identity-resolved fields
                "linkedin_url": state.identity.get("linkedin_company_url", "") or state.startup_features.linkedin_company_url or "",
                "founder_name": state.identity.get("primary_founder_name", "") or state.startup_features.founder_name or "",
                "founder_linkedin_url": state.identity.get("primary_founder_linkedin", "") or state.startup_features.founder_linkedin_url or "",
                "founded_year": state.startup_features.founded_year,
                # New database migration v7 columns
                "brand_name": state.identity.get("brand_name") or state.startup_name,
                "legal_name": state.identity.get("legal_name") or "",
                "company_profile": state.article_data.get("description", ""),
                "products_services": products_services_val,
                "identity_confidence": state.identity.get("identity_confidence", 0.0),
                "hq_city": state.identity.get("city") or "Unknown",
                "hq_country": state.identity.get("country") or "India"
            }
            
            # Perform upsert
            upsert_res = upsert_startup(startup_payload)
            if not upsert_res:
                print("⚠️ Upsert returned empty list. Basic startup write bypassed.")
                return
                
            startup_id = upsert_res[0]["id"]
            state.startup_id = startup_id

            # 2. Format a backward-compatible analysis_json object
            tracxn_profile = state.article_data.get("enriched_raw", {}).get("tracxn_profile", {})
            
            # Map use cases format
            raw_use_cases = state.recommendation.get("use_cases", [])
            use_cases = []
            for uc in raw_use_cases:
                use_cases.append({
                    "use_case": uc.get("use_case", ""),
                    "icici_entity": uc.get("icici_entity", "ICICI Bank"),
                    "potential_impact": uc.get("potential_impact", "")
                })

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

            analysis_json = {
                "classification": {
                    "sector": state.startup_features.sector,
                    "subsector": state.startup_features.subsector,
                    "industry": "Financial Services",
                    "business_models": state.article_data.get("enriched_raw", {}).get("tracxn_profile", {}).get("business_models", []),
                    "industry_relevance": state.startup_features.relevant_entities,
                    "tags": state.article_data.get("enriched_raw", {}).get("tracxn_profile", {}).get("tags", [])
                },
                "summary": {
                    "one_liner": explanations.get("relevance", {}).get("reasons", [""])[0] if explanations.get("relevance", {}).get("reasons") else "",
                    "business_model": state.article_data.get("description", ""),
                    "target_audience": "BFSI & Corporate Enterprises"
                },
                "bfsi_relevance": {
                    "relevance_score": state.relevance.get("score", 0),
                    "use_cases": use_cases,
                    "is_relevant": state.relevance.get("score", 0) >= 50
                },
                "strategic_fit": {
                    "enterprise_readiness": state.strategic_fit.get("breakdown", {}).get("deployability", {}).get("score", 0),
                    "integration_feasibility": state.startup_features.deployability,
                    "partnership_opportunity": state.strategic_fit.get("breakdown", {}).get("business_problem_relevance", {}).get("reason", "")
                },
                "scoring": {
                    "overall_priority_score": final_score,
                    "risk_assessment": state.strategic_fit.get("breakdown", {}).get("ecosystem_influence", {}).get("reason", "")
                },
                "founders": tracxn_profile.get("founders") or [],
                "startup_website": state.article_data.get("enriched_raw", {}).get("resolved_website", ""),
                "email_reachout_message": state.recommendation.get("email_reachout_message", ""),
                "linkedin_reachout_message": state.recommendation.get("linkedin_reachout_message", ""),
                "audit_trail": state.audit_trail,
                
                # Upgraded Scoring & RAG fields
                "relevance_score": state.relevance.get("score", 0),
                "signal_score": state.signals.get("score", 0),
                "deployability_score": deployability_score,
                "recommendation_score": state.recommendation_score,
                "confidence_score": state.confidence_score,
                "recommended_action": state.recommendation.get("recommended_action") or "Monitor",
                "priority_band": state.priority_band,
                "matched_entities": state.startup_features.relevant_entities,
                "matched_business_teams": state.startup_features.business_teams,
                "matched_business_problems": state.startup_features.business_problems,
                "positive_signals": state.startup_features.positive_signals,
                "negative_signals": state.startup_features.negative_signals,
                "audit_summary": {
                    "errors": state.errors,
                    "audit_trail_length": len(state.audit_trail)
                },
                "knowledge_version": "1.0",
                "analysis_version": "1.0",
                "market_intelligence": state.market_intelligence,
                "headquarters": hq_val,
                "startup_stage": state.startup_features.startup_stage
            }

            # Save startup analysis details
            save_startup_analysis(startup_id, analysis_json)

            # 3. Save funding rounds in dedicated columns
            funding_data = state.article_data.get("enriched_raw", {}).get("extracted_funding", {})
            if funding_data and funding_data.get("rounds"):
                try:
                    analysis_row = supabase.table("startup_analysis").select("id").eq("startup_id", startup_id).execute()
                    analysis_id = analysis_row.data[0]["id"] if analysis_row.data else None
                    save_funding_rounds(startup_id, funding_data, analysis_id)
                except Exception as fe:
                    print(f"⚠️ Failed to save orchestrator funding columns: {fe}")

            # 4. Save audit log entries to activity log database
            for entry in state.audit_trail:
                try:
                    activity_notes = f"Agent: {entry['agent']}. {entry['message']}"
                    activity_payload = {
                        "startup_id": startup_id,
                        "activity_type": "Multi-Agent Run",
                        "activity_notes": activity_notes
                    }
                    supabase.table("startup_activity_logs").insert(activity_payload).execute()
                except Exception as ae:
                    print(f"⚠️ Failed to log audit trace step: {ae}")

            print(f"✅ State successfully persisted for '{state.startup_name}' (ID: {startup_id}).")

        except Exception as e:
            print(f"❌ Persist state failed: {e}")
            state.errors.append(f"Persist state failed: {str(e)}")
