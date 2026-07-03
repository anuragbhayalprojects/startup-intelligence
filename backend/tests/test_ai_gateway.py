import pytest
import asyncio
from backend.ai.types import AIRequest, AIResponse
from backend.ai.utils.token_optimizer import estimate_tokens, compact_text, optimize_context
from backend.ai.gateway.response_validator import validate_and_repair, repair_json_string, enforce_schema_contract
from backend.ai.registry.model_registry import ModelRegistry
from backend.ai.gateway.ai_gateway import AIGateway

def test_token_estimation():
    # Structured JSON
    json_text = '{"key": "value", "another": [1, 2, 3]}'
    est_structured = estimate_tokens(json_text)
    assert est_structured == int(len(json_text) / 3.1)

    # Narrative Prose
    prose_text = "This is a long narrative sentence explaining the startup architecture."
    est_prose = estimate_tokens(prose_text)
    assert est_prose == int(len(prose_text) / 4.0)

def test_rag_preservation():
    context = {
        "rag_context": "important rag information that should not be touched",
        "application_ethos": "ethos description",
        "system_directives": "directives",
        "query_embeddings": [0.1, 0.2, 0.3],
        "article_body": "A very long raw scraping article content " * 100
    }
    optimized = optimize_context(context, task="extraction")
    
    # RAG context and others preserved
    assert optimized["rag_context"] == context["rag_context"]
    assert optimized["application_ethos"] == context["application_ethos"]
    assert optimized["system_directives"] == context["system_directives"]
    assert optimized["query_embeddings"] == context["query_embeddings"]
    
    # Heavy field compacted
    assert len(optimized["article_body"]) < len(context["article_body"])
    assert "[... TRUNCATED CONTEXT ...]" in optimized["article_body"]

def test_json_repairs():
    # Markdown backticks stripping
    raw_md = "```json\n{\"name\": \"test\"}\n```"
    assert repair_json_string(raw_md) == "{\"name\": \"test\"}"

    # Trailing commas
    trailing_comma = '{"list": [1, 2,], "val": 3,}'
    assert repair_json_string(trailing_comma) == '{"list": [1, 2], "val": 3}'

    # Unescaped newlines in quotes
    unescaped_newline = '{"desc": "line 1\nline 2"}'
    assert '\\n' in repair_json_string(unescaped_newline)

    # Unbalanced braces
    unbalanced = '{"name": "test"'
    assert repair_json_string(unbalanced) == '{"name": "test"}'

def test_schema_contract_enforcement():
    payload = {"name": "Test Startup"}
    required_keys = ["name", "founder_list", "funding_amount", "description"]
    
    enforced = enforce_schema_contract(payload, required_keys)
    assert enforced["name"] == "Test Startup"
    assert enforced["founder_list"] == []
    assert enforced["funding_amount"] == 0
    assert enforced["description"] == ""

@pytest.mark.anyio
async def test_ai_gateway_routing():
    gateway = AIGateway()
    # Test route method returns AIResponse with fallback used when OpenRouter key is empty or invalid
    req = AIRequest(
        prompt="Explain quantum computing in one sentence",
        json_format=False,
        temperature=0.0
    )
    
    # We should run it. If Ollama is running local fallback should succeed or gracefully fail.
    response = await gateway.route(req)
    assert response.provider in ["ollama", "openrouter", "none"]
    assert isinstance(response.fallback_used, bool)
