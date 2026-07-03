import os
import time
import asyncio
import logging
import httpx
from typing import Any, Dict, Optional
from backend.ai.providers.base_provider import BaseProvider
from backend.ai.types import AIRequest, AIResponse
from backend.ai.gateway.response_validator import validate_and_repair
from backend.ai.utils.token_optimizer import estimate_tokens

logger = logging.getLogger("startup_intelligence.openrouter_provider")

import json

class OpenRouterProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "").strip()
        self.base_url = (base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")).rstrip("/")
        
        # Load defaults
        self.timeout = float(os.getenv("OPENROUTER_TIMEOUT", "30.0"))
        self.max_attempts = 4
        self.base_delay = 4.0
        self.jitter_percentage = 0.25
        
        try:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "config",
                "model_routing.json"
            )
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    settings = cfg.get("openrouter_settings", {})
                    self.timeout = float(settings.get("timeout_seconds", self.timeout))
                    self.max_attempts = int(settings.get("max_retries", self.max_attempts))
                    self.base_delay = float(settings.get("base_delay_seconds", self.base_delay))
                    self.jitter_percentage = float(settings.get("jitter_percentage", self.jitter_percentage))
        except Exception as e:
            logger.warning(f"Failed to load openrouter_settings: {e}")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/startup-intelligence-os",
            "X-Title": "Startup Intelligence OS Gateway"
        }

    async def generate(self, request: AIRequest) -> AIResponse:
        model = request.model or "google/gemma-2-9b-it:free"
        headers = self._get_headers()
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
        }
        if request.json_format:
            payload["response_format"] = {"type": "json_object"}

        start_time = time.perf_counter()
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(1, self.max_attempts + 1):
                try:
                    logger.info(f"OpenRouter attempt {attempt} for model {model}")
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers=headers
                    )
                    
                    if response.status_code == 429:
                        # Parse Retry-After header
                        retry_after = response.headers.get("Retry-After")
                        sleep_seconds = 0.0
                        if retry_after:
                            try:
                                sleep_seconds = float(retry_after)
                            except ValueError:
                                pass
                        
                        if sleep_seconds <= 0.0:
                            import random
                            base_backoff = self.base_delay * (attempt ** 2)
                            # Apply random jitter based on configured percentage
                            min_multiplier = max(0.0, 1.0 - self.jitter_percentage)
                            max_multiplier = 1.0 + self.jitter_percentage
                            sleep_seconds = base_backoff * random.uniform(min_multiplier, max_multiplier)
                        
                        logger.warning(
                            f"OpenRouter rate limit hit (429). Attempt {attempt}/{self.max_attempts}. "
                            f"Sleeping for {sleep_seconds}s. Retry-After header: {retry_after}"
                        )
                        if attempt < self.max_attempts:
                            await asyncio.sleep(sleep_seconds)
                            continue
                        else:
                            response.raise_for_status()

                    response.raise_for_status()
                    
                    # Parse response
                    resp_data = response.json()
                    choices = resp_data.get("choices", [])
                    if not choices:
                        raise ValueError("Empty choices in response")
                    
                    raw_text = choices[0]["message"]["content"]
                    
                    # Estimate tokens/usage
                    usage = resp_data.get("usage", {})
                    if not usage:
                        prompt_toks = estimate_tokens(request.prompt)
                        completion_toks = estimate_tokens(raw_text)
                        usage = {
                            "prompt_tokens": prompt_toks,
                            "completion_tokens": completion_toks,
                            "total_tokens": prompt_toks + completion_toks
                        }
                    
                    # Validate and repair JSON if needed
                    parsed_content = validate_and_repair(
                        raw_text,
                        required_schema_keys=request.required_schema_keys,
                        json_format=request.json_format
                    )
                    
                    latency = (time.perf_counter() - start_time) * 1000
                    return AIResponse(
                        content=parsed_content,
                        provider="openrouter",
                        model=model,
                        latency_ms=round(latency, 2),
                        usage=usage
                    )

                except Exception as e:
                    logger.error(f"OpenRouter error on attempt {attempt}: {e}")
                    
                    # Do not retry on permanent client errors (400, 401, 403, 404)
                    is_permanent = False
                    if isinstance(e, httpx.HTTPStatusError):
                        if e.response.status_code in [400, 401, 403, 404]:
                            is_permanent = True
                            logger.warning(f"Permanent HTTP error {e.response.status_code} detected. Aborting retries for model {model}.")
                    
                    if attempt < self.max_attempts and not is_permanent:
                        sleep_seconds = self.base_delay * (attempt ** 2)
                        # Apply jitter to non-429 exceptions as well
                        import random
                        min_multiplier = max(0.0, 1.0 - self.jitter_percentage)
                        max_multiplier = 1.0 + self.jitter_percentage
                        sleep_seconds = sleep_seconds * random.uniform(min_multiplier, max_multiplier)
                        await asyncio.sleep(sleep_seconds)
                    else:
                        latency = (time.perf_counter() - start_time) * 1000
                        return AIResponse(
                            content={} if request.json_format else "",
                            provider="openrouter",
                            model=model,
                            fallback_used=True,
                            fallback_reason=str(e),
                            latency_ms=round(latency, 2)
                        )
        
        latency = (time.perf_counter() - start_time) * 1000
        return AIResponse(
            content={} if request.json_format else "",
            provider="openrouter",
            model=model,
            fallback_used=True,
            fallback_reason="Max attempts reached without response",
            latency_ms=round(latency, 2)
        )
