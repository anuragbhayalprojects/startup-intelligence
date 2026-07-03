import os
import time
import logging
from typing import Any, Dict, List, Optional
from backend.ai.types import AIRequest, AIResponse
from backend.ai.registry.model_registry import ModelRegistry
from backend.ai.providers.openrouter_provider import OpenRouterProvider
from backend.ai.providers.ollama_provider import OllamaProvider
from backend.ai.utils.token_optimizer import optimize_context

logger = logging.getLogger("startup_intelligence.ai_gateway")

class AIGateway:
    def __init__(self):
        self.registry = ModelRegistry()
        self.openrouter_provider = OpenRouterProvider()
        self.ollama_provider = OllamaProvider()

    def record_telemetry(self, request: AIRequest, response: AIResponse):
        """
        Records routing decisions and outcome to obs_prompt_ledger to keep legacy
        obs_prompt_ledger and frontend observability working.
        """
        try:
            from backend.utils.tracing import generate_uuid, log_prompt_ledger
            
            prompt_id = "PRMPT_" + generate_uuid()
            
            # Format raw response
            if isinstance(response.content, (dict, list)):
                raw_response_str = str(response.content)
            else:
                raw_response_str = str(response.content)
            
            legacy_parsed = response.to_legacy_dict()
            
            log_prompt_ledger(
                prompt_id=prompt_id,
                agent_name=request.agent_name,
                prompt_template=request.prompt,
                injected_context=f"task={request.task} provider={response.provider} model={response.model}",
                raw_response=raw_response_str,
                parsed_response=legacy_parsed,
                duration_ms=response.latency_ms
            )
            logger.info(f"Recorded legacy telemetry for prompt {prompt_id}")
        except Exception as e:
            logger.debug(f"Telemetry recording failed (non-critical): {e}")

    async def route(self, request: AIRequest) -> AIResponse:
        """
        Routes the request using the multi-tier model list.
        Tier 1: Explicit high-accuracy free models sequentially.
        Tier 2: Dynamically discovered active free models.
        Tier 3: Local Ollama (qwen2.5:3b) as fallback.
        """
        start_time = time.perf_counter()
        
        # Determine candidate models to try
        candidates: List[tuple[str, str]] = []  # List of (provider, model_name)
        
        # Check master switch for OpenRouter enablement
        is_openrouter_enabled = os.getenv("OPENROUTER_ENABLED", "true").lower() == "true"
        
        # If user explicitly requests a model, try that first
        if request.model:
            # Detect provider from model name
            provider = "ollama" if "qwen2.5" in request.model or "ollama" in request.model else "openrouter"
            if provider != "openrouter" or is_openrouter_enabled:
                candidates.append((provider, request.model))
        
        if is_openrouter_enabled:
            # Tier 1 models (OpenRouter)
            for m in self.registry.get_tier1_models():
                if not request.model or m != request.model:
                    candidates.append(("openrouter", m))
                    
            # Tier 2 models (OpenRouter)
            try:
                tier2 = await self.registry.discover_tier2_models()
                for m in tier2:
                    if m not in [c[1] for c in candidates]:
                        candidates.append(("openrouter", m))
            except Exception as e:
                logger.warning(f"Could not discover Tier 2 models: {e}")
            
        # Tier 3 fallback (Ollama)
        fallback_model = "qwen2.5:3b"
        if fallback_model not in [c[1] for c in candidates]:
            candidates.append(("ollama", fallback_model))

        last_error = None
        fallback_used = False
        
        # Iterate candidates sequentially
        for idx, (provider, model_name) in enumerate(candidates):
            req_copy = request.model_copy()
            req_copy.model = model_name
            
            # Context compaction check: compact if the prompt text contains large sections
            # We can also compact context dictionary if passed. Since prompt is string, let's keep it.
            
            try:
                logger.info(f"Gateway routing to {provider} using {model_name}")
                if provider == "openrouter":
                    # Check if API key is present; if not, skip OpenRouter models
                    if not self.openrouter_provider.api_key:
                        raise ValueError("OpenRouter API key is missing")
                    response = await self.openrouter_provider.generate(req_copy)
                else:
                    response = await self.ollama_provider.generate(req_copy)
                
                # Check if response had fallback/errors
                if response.fallback_used:
                    last_error = response.fallback_reason
                    fallback_used = True
                    continue # Try next candidate
                
                # If we succeeded on a model other than the first requested, mark fallback
                if idx > 0 or fallback_used:
                    response.fallback_used = True
                    response.fallback_reason = last_error or "Fallback to next model in sequence"
                
                latency = (time.perf_counter() - start_time) * 1000
                response.latency_ms = round(latency, 2)
                
                # Record telemetry
                self.record_telemetry(request, response)
                return response
                
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}")
                last_error = str(e)
                fallback_used = True
                continue

        # If all candidates fail, return final error response
        latency = (time.perf_counter() - start_time) * 1000
        fail_response = AIResponse(
            content={} if request.json_format else "",
            provider="none",
            model="none",
            fallback_used=True,
            fallback_reason=f"All cloud and local routes exhausted. Last error: {last_error}",
            latency_ms=round(latency, 2)
        )
        self.record_telemetry(request, fail_response)
        return fail_response
