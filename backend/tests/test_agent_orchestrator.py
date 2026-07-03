import pytest
from backend.workflows.agent_orchestrator import AgentOrchestrator
from backend.models.startup_state import StartupState

def test_orchestrator_initialization():
    orchestrator = AgentOrchestrator()
    assert orchestrator.identity_discovery_agent is not None
    assert orchestrator.identity_resolution_agent is not None
    assert orchestrator.legal_name_agent is not None
    assert orchestrator.identity_enricher is not None
    assert orchestrator.product_enricher is not None
    assert orchestrator.funding_enricher is not None
    assert orchestrator.intelligence_enricher is not None

def test_pipeline_relevance_gating_low_relevance():
    # Test a completely irrelevant startup to verify low relevance mapping (<20 score)
    irrelevant_startup = {
        "startup_name": "Whiskers Cat Diary",
        "description": "A personal daily diary and photo gallery of a domestic cat named Whiskers living in a small suburban apartment.",
        "source": "Manual Test",
        "source_url": "https://whiskers-cat-example.com"
    }
    
    orchestrator = AgentOrchestrator()
    state = orchestrator.run_pipeline(irrelevant_startup)
    
    assert state.relevance["score"] < 20
    assert state.recommendation["recommended_action"] == "Ignore / Monitor"

def test_pipeline_full_run_high_relevance():
    # Test a highly relevant startup to verify full multi-agent execution
    relevant_startup = {
        "startup_name": "SecurePay Claims Fraud Guard",
        "description": "An AI-powered cybersecurity and claims fraud detection software company that helps insurance companies identify fraudulent insurance claims automatically using advanced deep learning models.",
        "source": "Manual Test",
        "source_url": "https://fraudguard-example.com"
    }
    
    orchestrator = AgentOrchestrator()
    state = orchestrator.run_pipeline(relevant_startup)
    
    # High relevance fintech description should result in score >= 50
    assert state.relevance["score"] >= 50
    assert state.strategic_fit["score"] > 0
    assert len(state.recommendation["use_cases"]) > 0
    
    # Final recommendation action should be mapped
    assert state.recommendation["recommended_action"] in [
        "Founder Meeting", "Business Introduction", "POC", "Strategic Investment Review", "Monitor"
    ]
    # Check that audit trail has records from IntelligenceEnricher
    assert any("IntelligenceEnricher" in log["agent"] for log in state.audit_trail)

def test_pipeline_semantic_alignment_mismatch():
    # Test a startup where Phase 1 semantic mismatch check flags a contradiction
    mismatched_startup = {
        "startup_name": "Cred",
        "description": "Cred raises $100M in Series D for its credit card bill payment platform.",
        "source": "Manual Test",
        "source_url": "https://cred.club"
    }
    
    orchestrator = AgentOrchestrator()
    
    from unittest.mock import patch
    with patch("backend.agents.utils.call_ollama") as mock_call:
        mock_call.side_effect = [
            {
                "alignment_status": "MISMATCHED",
                "canonical_name": "Cred",
                "mismatch_reason": "The website describes a luxury fashion app, but the news details a fintech app."
            }
        ]
        
        state = orchestrator.run_pipeline(mismatched_startup)
        
        # Verify it aborted and mapped properly
        assert state.identity["verification_status"] == "MISMATCHED"
        assert state.confidence_score == 10
        assert state.priority_band == "Ignore"
        assert state.relevance["score"] == 0
        assert state.strategic_fit["score"] == 0
        assert state.startup_features.startup_status == "Needs Review"
        assert state.recommendation["recommended_action"] == "Needs Review"
        assert any("Semantic mismatch detected" in log["message"] for log in state.audit_trail)

