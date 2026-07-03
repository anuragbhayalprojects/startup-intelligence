import os
import time
import logging
import httpx
from typing import Any, Dict, Optional
from backend.ai.providers.base_provider import BaseProvider
from backend.ai.types import AIRequest, AIResponse
from backend.ai.gateway.response_validator import validate_and_repair
from backend.ai.utils.token_optimizer import estimate_tokens

logger = logging.getLogger("startup_intelligence.ollama_provider")

class OllamaProvider(BaseProvider):
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT", "60.0"))

    async def generate(self, request: AIRequest) -> AIResponse:
        model = request.model or "qwen2.5:3b"
        
        payload = {
            "model": model,
            "prompt": request.prompt,
            "stream": False,
            "options": {
                "num_ctx": request.num_ctx,
                "temperature": request.temperature,
            }
        }
        if request.json_format:
            payload["format"] = "json"

        start_time = time.perf_counter()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                resp_data = response.json()
                raw_text = resp_data.get("response", "").strip()
                
                # Estimate tokens
                prompt_tokens = estimate_tokens(request.prompt)
                completion_tokens = estimate_tokens(raw_text)
                usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
                
                parsed_content = validate_and_repair(
                    raw_text,
                    required_schema_keys=request.required_schema_keys,
                    json_format=request.json_format
                )
                
                latency = (time.perf_counter() - start_time) * 1000
                return AIResponse(
                    content=parsed_content,
                    provider="ollama",
                    model=model,
                    latency_ms=round(latency, 2),
                    usage=usage
                )
                
        except Exception as e:
            logger.error(f"Ollama provider failed: {e}")
            latency = (time.perf_counter() - start_time) * 1000
            return AIResponse(
                content={} if request.json_format else "",
                provider="ollama",
                model=model,
                fallback_used=True,
                fallback_reason=str(e),
                latency_ms=round(latency, 2)
            )
