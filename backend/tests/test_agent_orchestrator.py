import pytest
from backend.workflows.agent_orchestrator import AgentOrchestrator
from backend.models.startup_state import StartupState

def test_orchestrator_initialization():
    orchestrator = AgentOrchestrator()
    assert orchestrator.enrich_agent is not None
    assert orchestrator.class_agent is not None
    assert orchestrator.biz_prob_agent is not None
    assert orchestrator.relevance_agent is not None
    assert orchestrator.fit_agent is not None
    assert orchestrator.signal_agent is not None
    assert orchestrator.rec_agent is not None

def test_pipeline_relevance_gating_low_relevance():
    # Test a completely irrelevant startup to verify the Relevance Gating Rule (<50 score)
    # The gating rule should bypass Strategic Fit and Signal agents, setting recommended action to Ignore/Monitor
    irrelevant_startup = {
        "startup_name": "Gourmet Recipe Generator",
        "description": "An online platform generating personalized cooking recipes and grocery lists for home chefs.",
        "source": "Manual Test",
        "source_url": "https://recipes-generator-example.com"
    }
    
    orchestrator = AgentOrchestrator()
    state = orchestrator.run_pipeline(irrelevant_startup)
    
    assert state.relevance["score"] < 50
    assert state.relevance["gating_bypassed"] is True
    assert state.recommendation["recommended_action"] == "Ignore / Monitor"
    
    # Confirm strategic fit and signals were skipped (contain default/zero values)
    assert state.strategic_fit["score"] == 0
    assert len(state.signals["list_detected"]) == 0
    assert any("Relevance Score < 50" in log["message"] for log in state.audit_trail)

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
    assert state.relevance["gating_bypassed"] is False
    assert state.strategic_fit["score"] > 0
    assert len(state.recommendation["use_cases"]) > 0
    
    # Final recommendation action should be mapped
    assert state.recommendation["recommended_action"] in [
        "Founder Meeting", "Business Introduction", "POC", "Strategic Investment Review", "Monitor"
    ]
    # Check that audit trail has records from Strategic Fit and Signals
    assert any("FitAgent" in log["agent"] or "StrategicFitAgent" in log["agent"] for log in state.audit_trail)
    assert any("SignalAgent" in log["agent"] for log in state.audit_trail)
