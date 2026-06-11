import os
import sys
import json
from dotenv import load_dotenv

PROJECT_ROOT = "/Users/anurag/Projects/startup-intelligence"
sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Ensure Ollama base URL and model are correct
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "qwen2.5:3b"
os.environ["FORCE_STARTUP_PIPELINE_RUN"] = "true"

from backend.workflows.agent_orchestrator import AgentOrchestrator

def trace_run():
    from backend.utils.tracing import set_trace_id, generate_trace_id, log_trace
    trace_id = generate_trace_id()
    set_trace_id(trace_id)
    log_trace(startup_name="Inc42 Audit Run", article_url="Inc42 Mock Articles")
    print(f"🎬 Starting Detailed Workflow Trace for 2 Inc42 Articles...")
    print(f"🔑 GLOBAL TRACE ID FOR THIS RUN: {trace_id}")
    
    # 1. Mock Inc42 Article 1: FinBox (FinTech / Embedded Lending Infrastructure)
    article_1 = {
        "startup_name": "Fintech Startup FinBox Raises $15Mn To Expand Product Suite",
        "description": "Bengaluru-based embedded finance infrastructure platform FinBox has raised $15 million in its Series A funding round to scale its product suite and expand its underwriting footprint.",
        "source": "Inc42",
        "source_url": "https://inc42.com/features/finbox-funding-series-a",
        "published_at": "2026-06-10T12:00:00Z",
        "paragraphs": [
            "Bengaluru-based embedded finance infrastructure platform FinBox has raised $15 million in its Series A funding round to scale its product suite and expand its underwriting footprint.",
            "FinBox offers embedded lending infrastructure and digital credit underwriting tools for non-banking financial companies (NBFCs) and digital platforms. The platform enables non-financial businesses to launch credit products such as Buy Now Pay Later (BNPL), personal loans, and business loans.",
            "The funding round was led by outbound investors and saw participation from prominent angel investors."
        ]
    }
    
    # 2. Mock Inc42 Article 2: Incuspaze (PropTech / Coworking / Managed Office Spaces)
    article_2 = {
        "startup_name": "Proptech Startup Incuspaze Raises $8Mn In Series A Funding led by India Contextual Fund",
        "description": "Co-working space provider Incuspaze has raised $8 million in its maiden institutional funding round to expand its managed office portfolio across major Tier-I and Tier-II Indian cities.",
        "source": "Inc42",
        "source_url": "https://inc42.com/funding/incuspaze-funding-series-a",
        "published_at": "2026-06-10T12:00:00Z",
        "paragraphs": [
            "Co-working space provider Incuspaze has raised $8 million in its maiden institutional funding round led by India Contextual Fund.",
            "Founded in 2016, Incuspaze provides managed office spaces and flexible coworking solutions tailored for enterprise clients. The new capital will be used to expand its footprint and enhance its tech-driven workspace management platform.",
            "The company caters to enterprises, startups, and MSMEs, providing flexible workspace configurations with premium amenities."
        ]
    }
    
    orchestrator = AgentOrchestrator()
    articles = [article_1, article_2]
    
    for idx, art in enumerate(articles, 1):
        print(f"\n==============================================================")
        print(f"📊 PROCESSING ARTICLE {idx}: {art['startup_name']}")
        print(f"==============================================================")
        
        # We manually run each step to log exact input and output
        # Step 0: Initialize State
        from backend.models.startup_state import StartupState
        state = StartupState(
            startup_name=art["startup_name"].split(" Raises ")[0].split(" raises ")[0].split(" in ")[0].strip(),
            article_data={
                "headline": art.get("startup_name", ""),
                "description": art.get("description", ""),
                "source": art.get("source", "Unknown"),
                "source_url": art.get("source_url", ""),
                "paragraphs": art.get("paragraphs", [])
            }
        )
        print(f"--- [STARTING STATE] ---")
        print(f"Input Startup Name: {state.startup_name}")
        print(f"Input Article Headline: {state.article_data.get('headline')}")
        print(f"Input Article URL: {state.article_data.get('source_url')}")
        
        # Step 1: Identity Discovery
        print(f"\n⚡ Running IdentityDiscoveryAgent...")
        print(f"Input to IdentityDiscoveryAgent: {state.startup_name}")
        state = orchestrator.identity_discovery_agent.run(state)
        print(f"Output from IdentityDiscoveryAgent: {state.identity}")
        
        # Step 2: Identity Resolution
        print(f"\n⚡ Running IdentityResolutionAgent...")
        print(f"Input to IdentityResolutionAgent: {state.identity}")
        state = orchestrator.identity_resolution_agent.run(state)
        print(f"Output from IdentityResolutionAgent: {state.identity}")
        
        # Step 3: Legal Name Agent
        print(f"\n⚡ Running LegalNameAgent...")
        print(f"Input to LegalNameAgent: {state.identity}")
        state = orchestrator.legal_name_agent.run(state)
        print(f"Output from LegalNameAgent: {state.identity}")
        
        # Step 4: Description Generator Agent
        print(f"\n⚡ Running DescriptionGeneratorAgent...")
        print(f"Input to DescriptionGeneratorAgent: {state.article_data.get('description')}")
        state = orchestrator.desc_agent.run(state)
        print(f"Output from DescriptionGeneratorAgent: {state.article_data.get('business_description')}")
        
        # Step 5: Product Intelligence Agent
        print(f"\n⚡ Running ProductIntelligenceAgent...")
        print(f"Input to ProductIntelligenceAgent (Website/snippets): {state.identity.get('website')}")
        state = orchestrator.product_agent.run(state)
        print(f"Output from ProductIntelligenceAgent (Products): {state.market_intelligence.get('products')}")
        
        # Step 6: Industry Classification Agent
        print(f"\n⚡ Running IndustryClassificationAgent...")
        print(f"Input to IndustryClassificationAgent: {state.market_intelligence.get('products')}")
        state = orchestrator.industry_classification_agent.run(state)
        print(f"Output from IndustryClassificationAgent (Taxonomy): {state.market_intelligence.get('industry_classification')}")
        
        # Step 7: Competitor Intelligence Agent
        print(f"\n⚡ Running CompetitorIntelligenceAgent...")
        print(f"Input to CompetitorIntelligenceAgent (Products): {state.market_intelligence.get('products')}")
        state = orchestrator.competitor_agent.run(state)
        print(f"Output from CompetitorIntelligenceAgent: {state.market_intelligence.get('competitors')}")
        
        # Step 8: Opportunity Mapping Agent
        print(f"\n⚡ Running OpportunityMappingAgent...")
        print(f"Input to OpportunityMappingAgent: {state.article_data.get('description')}")
        state = orchestrator.opportunity_agent.run(state)
        print(f"Output from OpportunityMappingAgent: {state.market_intelligence.get('opportunity_mapping')}")
        
        # Step 9: Funding Intelligence Agent
        print(f"\n⚡ Running FundingIntelligenceAgent...")
        print(f"Input to FundingIntelligenceAgent: {state.article_data.get('description')}")
        state = orchestrator.funding_agent.run(state)
        print(f"Output from FundingIntelligenceAgent: {state.market_intelligence.get('funding')}")
        
        # Step 10: Business Problem Agent
        print(f"\n⚡ Running BusinessProblemAgent...")
        print(f"Input to BusinessProblemAgent: sector={state.startup_features.sector}, subsector={state.startup_features.subsector}")
        state = orchestrator.biz_prob_agent.run(state)
        print(f"Output from BusinessProblemAgent (Matched problems): {state.startup_features.business_problems}")
        
        # Step 11: Relevance Agent
        print(f"\n⚡ Running RelevanceAgent...")
        print(f"Input to RelevanceAgent: business_problems={state.startup_features.business_problems}")
        state = orchestrator.relevance_agent.run(state)
        print(f"Output from RelevanceAgent (Relevance score): {state.relevance.get('score')}")
        
        # Step 12: Strategic Fit Agent
        print(f"\n⚡ Running StrategicFitAgent...")
        print(f"Input to StrategicFitAgent: relevance={state.relevance.get('score')}")
        state = orchestrator.fit_agent.run(state)
        print(f"Output from StrategicFitAgent (Fit score): {state.strategic_fit.get('score')}")
        
        # Step 13: Signal Agent
        print(f"\n⚡ Running SignalAgent...")
        print(f"Input to SignalAgent: description={state.article_data.get('description')}")
        state = orchestrator.signal_agent.run(state)
        print(f"Output from SignalAgent (Signals score): {state.signals.get('score')}")
        
        # Step 14: Recommendation Agent
        print(f"\n⚡ Running RecommendationAgent...")
        print(f"Input to RecommendationAgent: fit={state.strategic_fit.get('score')}")
        state = orchestrator.rec_agent.run(state)
        print(f"Output from RecommendationAgent: {state.recommendation}")
        
        # Step 15: Scoring Calculations & Band mapping
        from backend.services.scoring_service import ScoringService
        
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
            relevance_score=state.relevance.get("score", 0),
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
        
        print(f"\n📊 [FINAL SCORES & BAND]")
        print(f"Final Priority Score: {final_priority}")
        print(f"Final Confidence Score: {final_confidence}")
        print(f"Final Urgency Band: {band}")
        
        # Step 16: DB Persist
        print(f"\n⚡ Persisting to Supabase database...")
        orchestrator.persist_to_database(state)
        print(f"🎉 Process completed and saved to database for '{state.startup_name}'!")

if __name__ == "__main__":
    trace_run()
