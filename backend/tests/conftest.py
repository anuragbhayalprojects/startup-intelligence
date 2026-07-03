import pytest
import json
import inspect
from unittest.mock import MagicMock, patch

# Mock responses for Ollama prompts based on calling Agent/Helper
def get_mock_ollama_response(prompt: str, is_json: bool = True) -> str:
    prompt_lower = prompt.lower()
    
    # 1. Stack trace inspection to identify the calling Agent
    caller_agent = None
    for frame_info in inspect.stack():
        self_obj = frame_info.frame.f_locals.get("self")
        if self_obj and hasattr(self_obj, "__class__"):
            cls_name = self_obj.__class__.__name__
            if "Agent" in cls_name or cls_name.endswith("Agent") or "Enricher" in cls_name or cls_name.endswith("Enricher"):
                caller_agent = cls_name
                break
                
    if caller_agent:
        if caller_agent == "IdentityDiscoveryAgent":
            if "whiskers" in prompt_lower:
                return json.dumps({"brand_name": "Whiskers Cat Diary"})
            elif "securepay" in prompt_lower:
                return json.dumps({"brand_name": "SecurePay Claims Fraud Guard"})
            elif "cred" in prompt_lower:
                return json.dumps({"brand_name": "Cred"})
            return json.dumps({"brand_name": "TestAI"})
            
        elif caller_agent == "LegalNameAgent":
            return json.dumps({
                "legal_name": "TestAI Private Limited",
                "headquarters": "Bangalore, India",
                "city": "Bangalore",
                "state": "Karnataka",
                "country": "India",
                "founded_year": 2020,
                "founders": [{"name": "John Doe", "linkedin_url": "https://linkedin.com/in/johndoe"}]
            })
            
        elif caller_agent == "IdentityResolutionAgent":
            # Check target startup names first to avoid matching system prompt examples of "Cred"
            if "whiskers" in prompt_lower:
                return json.dumps({
                    "alignment_status": "ALIGNED",
                    "canonical_name": "Whiskers Cat Diary",
                    "mismatch_reason": ""
                })
            elif "securepay" in prompt_lower:
                return json.dumps({
                    "alignment_status": "ALIGNED",
                    "canonical_name": "SecurePay Claims Fraud Guard",
                    "mismatch_reason": ""
                })
            elif "cred.club" in prompt_lower or "headline: cred" in prompt_lower:
                return json.dumps({
                    "alignment_status": "MISMATCHED",
                    "canonical_name": "Cred",
                    "mismatch_reason": "The website describes a luxury fashion app, but the news details a fintech app."
                })
            else:
                return json.dumps({
                    "alignment_status": "ALIGNED",
                    "canonical_name": "TestAI",
                    "mismatch_reason": ""
                })
                
        elif caller_agent == "DescriptionGeneratorAgent":
            return "TestAI is a claims fraud guard and workflow automation startup."
            
        elif caller_agent == "ProductIntelligenceAgent":
            return json.dumps({
                "products_and_solutions": [{"name": "Workflow AI", "description": "Automate processes"}]
            })
            
        elif caller_agent in ("IndustryClassificationAgent", "ClassificationAgent"):
            return json.dumps({
                "industry": "Software",
                "sector": "AI",
                "subsector": "Workflow Automation"
            })
            
        elif caller_agent == "CompetitorIntelligenceAgent":
            return json.dumps({
                "competitors": [{"name": "Competitor AI", "description": "Competitor details"}]
            })
            
        elif caller_agent == "OpportunityMappingAgent":
            return json.dumps({
                "use_cases": [{"title": "Fraud Detection", "description": "Detect fraud"}]
            })
            
        elif caller_agent == "FundingIntelligenceAgent":
            return json.dumps({
                "funding_stages": [{"stage": "Seed", "amount": 1000000}]
            })
            
        elif caller_agent == "BusinessProblemAgent":
            return json.dumps({
                "mappings": [
                    {
                        "problem_id": "Acquisition_Cost",
                        "entity": "ICICI Bank",
                        "business_team": "Retail Banking",
                        "relevance_explanation": "Test AI helps reduce customer acquisition costs."
                    }
                ]
            })
            
        elif caller_agent == "RelevanceAgent":
            score = 10 if "whiskers" in prompt_lower or "cat diary" in prompt_lower else 80
            return json.dumps({
                "dimensions": {
                    "strategic_relevance": {"score": score, "reason": "Strategic fit"},
                    "deployability": {"score": score, "reason": "Deployability"},
                    "traction": {"score": score, "reason": "Traction"},
                    "growth_signals": {"score": score, "reason": "Growth"},
                    "team_quality": {"score": score, "reason": "Team"},
                    "funding_signals": {"score": score, "reason": "Funding"}
                },
                "entity_relevance": {"score": score}
            })
            
        elif caller_agent == "StrategicFitAgent":
            return json.dumps({
                "score": 80,
                "breakdown": {
                    "deployability": {"score": 80, "reason": "high"}
                }
            })
            
        elif caller_agent == "SignalAgent":
            return json.dumps({
                "score": 80,
                "list_detected": [{"type": "expansion", "details": "expanded to new region"}]
            })
            
        elif caller_agent == "RecommendationAgent":
            return json.dumps({
                "score": 80,
                "recommended_action": "Founder Meeting",
                "use_cases": ["fraud detection"],
                "email_reachout_message": "Email reachout message details",
                "linkedin_reachout_message": "LinkedIn message details"
            })
            
        elif caller_agent == "IdentityEnricher":
            return json.dumps({
                "basic_information": {
                    "hq_city": "Bangalore",
                    "hq_state": "Karnataka",
                    "country": "India",
                    "founded_year": 2020
                },
                "founders_details": [
                    {"name": "John Doe", "linkedin_url": "https://linkedin.com/in/johndoe"}
                ]
            })
            
        elif caller_agent == "ProductEnricher":
            return json.dumps({
                "business_profile": {
                    "industry": "Software",
                    "sector": "AI",
                    "subsector": "Workflow Automation",
                    "business_models": ["B2B SaaS"],
                    "tags": ["AI", "automation"],
                    "description": "TestAI description"
                }
            })
            
        elif caller_agent == "FundingEnricher":
            return json.dumps({
                "latest_stage": "Seed",
                "total_funding": "$1M",
                "latest_round_date": "2023-06",
                "rounds": [
                    {
                        "stage": "Seed",
                        "amount": "$1M",
                        "date": "2023-06",
                        "lead_investor": "Investor A",
                        "co_investors": [],
                        "valuation": None
                    }
                ],
                "key_investors": ["Investor A"],
                "funding_source": "ai_search_enrichment"
            })
            
        elif caller_agent == "IntelligenceEnricher":
            score = 10 if "whiskers" in prompt_lower or "cat diary" in prompt_lower else 80
            recommended_action = "Ignore / Monitor" if score < 20 else "Founder Meeting"
            return json.dumps({
                "competitors": [
                    {
                        "name": "Competitor AI",
                        "positioning": "Competitor details",
                        "category": "Direct"
                    }
                ],
                "bfsi_relevance": {
                    "is_relevant": score >= 50,
                    "relevance_score": score,
                    "relevance_reasoning": "Reason for relevance",
                    "use_cases": [
                        {
                            "icici_entity": "ICICI Bank",
                            "use_case": "Specific use case description",
                            "potential_impact": "Expected business impact"
                        }
                    ]
                },
                "strategic_fit": {
                    "enterprise_readiness": score,
                    "partnership_opportunity": "Partnership",
                    "integration_feasibility": "High",
                    "key_risks": ["Risk 1"]
                },
                "scoring": {
                    "overall_priority_score": score,
                    "risk_assessment": "Low"
                },
                "recommended_action": recommended_action,
                "action_rationale": "Rationale"
            })
            
    # 2. Heuristics fallback for pipeline helpers / non-agent callers
    if "yes or no" in prompt_lower:
        return "YES"
    elif "extract operating startup" in prompt_lower or "discover_startup_names" in prompt_lower or "extract all featured" in prompt_lower:
        return '{"startups": [{"name": "TestAI", "description": "Factual summary of the corporate news event."}]}'
    elif "summary" in prompt_lower or "summarize" in prompt_lower:
        return "Factual summary of the corporate news event."
        
    if is_json:
        return "{}"
    return "Fallback plain text response."

def mock_get(url, *args, **kwargs):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    url_lower = url.lower()
    
    if "duckduckgo.com" in url_lower:
        mock_resp.text = "[1] Title: TestAI Official Website\nURL: https://testai.com\nSnippet: SecurePay claims fraud guard and workflow automation startup.\n[2] Title: TestAI LinkedIn\nURL: https://linkedin.com/company/testai\nSnippet: TestAI on LinkedIn.\n"
    elif "google.com" in url_lower:
        mock_resp.text = "[1] Title: TestAI Official Website\nURL: https://testai.com\nSnippet: SecurePay claims fraud guard and workflow automation startup.\n"
    else:
        mock_resp.text = "<html><body><h1>TestAI</h1><p>SecurePay is a fintech startup that provides automated fraud detection and claims security software.</p></body></html>"
        
    return mock_resp

def mock_post(url, *args, **kwargs):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    url_lower = url.lower()
    
    if "11434" in url_lower:
        payload = kwargs.get("json", {})
        prompt = payload.get("prompt", "")
        is_json = payload.get("format") == "json"
        
        mock_resp.json.return_value = {"response": get_mock_ollama_response(prompt, is_json)}
    else:
        mock_resp.json.return_value = {}
        
    return mock_resp

def mock_head(url, *args, **kwargs):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    return mock_resp

def mock_session_request(self, method, url, *args, **kwargs):
    method = method.upper()
    if method == "GET":
        return mock_get(url, *args, **kwargs)
    elif method == "POST":
        return mock_post(url, *args, **kwargs)
    elif method == "HEAD":
        return mock_head(url, *args, **kwargs)
    else:
        resp = MagicMock()
        resp.status_code = 200
        return resp

# Mock for search_duckduckgo
def mock_search_duckduckgo(query: str) -> str:
    return "[1] Title: TestAI Official Website\nURL: https://testai.com\nSnippet: SecurePay claims fraud guard and workflow automation startup.\n[2] Title: TestAI LinkedIn\nURL: https://linkedin.com/company/testai\nSnippet: TestAI on LinkedIn.\n"

# Mock for search_google
def mock_search_google(query: str) -> str:
    return "[1] Title: TestAI Official Website\nURL: https://testai.com\nSnippet: SecurePay claims fraud guard and workflow automation startup.\n"

# Mock for crawl_startup_targets
def mock_crawl_startup_targets(homepage_url: str) -> dict:
    return {
        "homepage": {
            "text_content": "SecurePay is a fintech startup that provides automated fraud detection and claims security software."
        },
        "about": {
            "text_content": "About us: SecurePay was founded in 2020 to protect insurance companies from fraud."
        },
        "privacy": {},
        "terms": {}
    }

# Mock for crawl_product_pages
def mock_crawl_product_pages(homepage_url: str) -> str:
    return "SecurePay provides Claims Fraud Guard software for automating insurance claims fraud verification."

# Mock for async OllamaProvider generate method to avoid real async network queries to Ollama server
async def mock_ollama_provider_generate(*args, **kwargs):
    from backend.ai.types import AIResponse
    from backend.ai.utils.token_optimizer import estimate_tokens
    from backend.ai.gateway.response_validator import validate_and_repair
    
    if len(args) >= 2:
        request = args[1]
    else:
        request = args[0]
        
    prompt = request.prompt
    is_json = request.json_format
    
    prompt_tokens = estimate_tokens(prompt)
    raw_text = get_mock_ollama_response(prompt, is_json)
    completion_tokens = estimate_tokens(raw_text)
    
    parsed_content = validate_and_repair(
        raw_text,
        required_schema_keys=request.required_schema_keys,
        json_format=request.json_format
    )
    
    return AIResponse(
        content=parsed_content,
        provider="ollama",
        model=request.model or "qwen2.5:3b",
        latency_ms=10.0,
        usage={
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    )

@pytest.fixture(autouse=True)
def mock_network_and_ollama():
    """Globally mock all outgoing HTTP, local Ollama, search, and crawl requests to speed up tests."""
    with patch("requests.get", side_effect=mock_get), \
         patch("requests.post", side_effect=mock_post), \
         patch("requests.head", side_effect=mock_head), \
         patch("requests.Session.request", side_effect=mock_session_request), \
         patch("time.sleep", return_value=None), \
         patch("backend.utils.search.search_duckduckgo", side_effect=mock_search_duckduckgo), \
         patch("backend.utils.search.search_google", side_effect=mock_search_google), \
         patch("backend.utils.crawler.crawl_startup_targets", side_effect=mock_crawl_startup_targets), \
         patch("backend.utils.crawler.crawl_product_pages", side_effect=mock_crawl_product_pages), \
         patch("backend.ai.providers.ollama_provider.OllamaProvider.generate", side_effect=mock_ollama_provider_generate):
        
        # Also patch curl_cffi requests if it is installed
        try:
            from curl_cffi import requests as curl_cffi_requests
            with patch("curl_cffi.requests.get", side_effect=mock_get), \
                 patch("curl_cffi.requests.post", side_effect=mock_post), \
                 patch("curl_cffi.requests.head", side_effect=mock_head), \
                 patch("curl_cffi.requests.Session.request", side_effect=mock_session_request):
                yield
        except ImportError:
            yield

@pytest.fixture(autouse=True)
def mock_supabase_db():
    """Mock all Supabase database execute calls during tests to prevent live DB mutations and timeouts."""
    with patch("backend.services.supabase_service.supabase") as mock_supabase:
        # Create a mock response object
        mock_response = MagicMock()
        mock_response.data = [{"id": 123, "startup_name": "Test Startup", "website": "https://test.com"}]
        
        # Configure execute() to return our mock response
        mock_supabase.table.return_value.select.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value.update.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value.delete.return_value.execute.return_value = mock_response
        
        # Mock order and limit chainings
        mock_supabase.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
        
        yield mock_supabase
