import httpx
import logging
from typing import List, Dict, Any

logger = logging.getLogger("startup_intelligence.model_registry")

import os
import json

# Default fallback list in case config is unreadable
DEFAULT_TIER_1_MODELS = [
    "google/gemma-2-9b-it:free",
    "meta-llama/llama-3-8b-instruct:free",
    "qwen/qwen-2-7b-instruct:free",
    "microsoft/phi-3-medium-128k-instruct:free"
]

class ModelRegistry:
    def __init__(self, openrouter_base_url: str = "https://openrouter.ai/api/v1"):
        self.openrouter_base_url = openrouter_base_url.rstrip("/")
        self._cached_tier2_models: List[str] = []
        
        # Load Tier 1 models and Tier 2 allowed providers from model_routing.json
        self.tier1_models = DEFAULT_TIER_1_MODELS
        self.allowed_providers = []
        try:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "config",
                "model_routing.json"
            )
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.tier1_models = cfg.get("tier_1_priority_models", DEFAULT_TIER_1_MODELS)
                    self.allowed_providers = cfg.get("tier_2_allowed_providers", [])
        except Exception as e:
            logger.warning(f"Failed to load registry configurations from config: {e}")

    def get_tier1_models(self) -> List[str]:
        return list(self.tier1_models)

    async def discover_tier2_models(self) -> List[str]:
        """
        Dynamically queries OpenRouter's /models endpoint and filters for active endpoints
        ending in :free or where pricing prompt/completion equals 0.0, and whose provider prefix
        is present in tier_2_allowed_providers.
        """
        if self._cached_tier2_models:
            return self._cached_tier2_models

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.openrouter_base_url}/models")
                response.raise_for_status()
                data = response.json().get("data", [])
                
                discovered = []
                for model in data:
                    model_id = model.get("id", "")
                    pricing = model.get("pricing", {})
                    
                    prompt_price = float(pricing.get("prompt", 0.0))
                    completion_price = float(pricing.get("completion", 0.0))
                    
                    is_free = (
                        model_id.endswith(":free") or 
                        (prompt_price == 0.0 and completion_price == 0.0)
                    )
                    
                    if is_free:
                        # Extract provider prefix, e.g. "google" from "google/gemma-2-9b-it:free"
                        provider_prefix = model_id.split("/")[0] if "/" in model_id else ""
                        
                        # Filter by allowed providers list if configured
                        if self.allowed_providers and provider_prefix not in self.allowed_providers:
                            continue
                            
                        if model_id not in self.tier1_models and model_id not in discovered:
                            discovered.append(model_id)
                
                self._cached_tier2_models = discovered
                logger.info(f"Discovered {len(discovered)} free models dynamically from OpenRouter matching allowed providers.")
                return self._cached_tier2_models
        except Exception as e:
            logger.error(f"Failed to dynamically discover Tier 2 models from OpenRouter: {e}")
            return []
