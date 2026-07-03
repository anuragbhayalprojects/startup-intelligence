"""
backend/ai/router.py
---------------------
Central AI Router for Startup Intelligence OS.

Implements OpenRouter-first routing with graceful Ollama fallback.

Routing logic:
  1. OPENROUTER_ENABLED env var is the master switch (defaults to true)
  2. If enabled AND API key is present → route to OpenRouter
  3. If disabled OR key is missing OR any fallback trigger fires → route to Ollama
  4. System NEVER hard-fails on missing API key — always falls back gracefully

Config is loaded from backend/config/model_routing.json and retry_policies.json.
All routing decisions are traced to obs_prompt_ledger for observability.
"""

from __future__ import annotations

import os
import json
import time
import logging
import inspect
from typing import Any, Optional

logger = logging.getLogger("startup_intelligence.ai_router")

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
_ROUTING_CFG_PATH = os.path.join(_CONFIG_DIR, "model_routing.json")
_RETRY_CFG_PATH = os.path.join(_CONFIG_DIR, "retry_policies.json")


def _load_json(path: str, fallback: dict) -> dict:
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"[AIRouter] Failed to load config {path}: {e}")
    return fallback


_routing_cfg: dict = _load_json(_ROUTING_CFG_PATH, {})
_retry_cfg: dict = _load_json(_RETRY_CFG_PATH, {})


# ---------------------------------------------------------------------------
# Runtime routing state
# ---------------------------------------------------------------------------

def _is_openrouter_enabled() -> bool:
    """
    OPENROUTER_ENABLED is the master switch.
    Reads from environment at call time (supports runtime toggling).
    """
    env_val = os.getenv("OPENROUTER_ENABLED", "true").strip().lower()
    return env_val in ("1", "true", "yes", "on")


def _get_openrouter_api_key() -> Optional[str]:
    """Returns the OpenRouter API key, or None if not configured."""
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    return key if key else None


def _get_ollama_base_url() -> str:
    cfg_url = _routing_cfg.get("ollama", {}).get("default_base_url", "http://localhost:11434")
    return os.getenv("OLLAMA_BASE_URL", cfg_url).rstrip("/")


def _get_ollama_model(task: str = "enrichment_products") -> str:
    cfg_model = _routing_cfg.get("ollama", {}).get("models", {}).get(task, "qwen2.5:3b")
    return os.getenv("OLLAMA_MODEL", cfg_model)


# ---------------------------------------------------------------------------
# Primary routing function (Bridged to backend/ai/gateway/ai_gateway.py)
# ---------------------------------------------------------------------------

import asyncio
import threading
from concurrent.futures import Future
from backend.ai.gateway.ai_gateway import AIGateway
from backend.ai.types import AIRequest

_gateway_instance = AIGateway()

def run_async(coro):
    """Safe runner that works in both sync and running async loop contexts."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    res_future = Future()
    
    def run_in_thread():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            val = new_loop.run_until_complete(coro)
            res_future.set_result(val)
        except Exception as ex:
            res_future.set_exception(ex)
        finally:
            new_loop.close()

    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()
    return res_future.result()


def route_completion(
    prompt: str,
    task: str = "enrichment_products",
    json_format: bool = True,
    num_ctx: int = 4096,
    temperature: float = 0.0,
    agent_name: str = "AIRouter",
) -> tuple[Any, dict]:
    """
    Routes an AI completion request using the new AIGateway.
    
    Returns
    -------
    (result, routing_meta) where:
        result       : parsed JSON dict (if json_format=True) or raw string
        routing_meta : dict with provider, model, fallback_used, duration_ms, etc.
    """
    # Under new routing logic, model=None requests sequential fallback list (Tier 1 -> Tier 2 -> Ollama)
    # If openrouter is explicitly disabled or api key is missing, we bypass cloud tiers and request local ollama model directly.
    model_name = None
    if not (_is_openrouter_enabled() and _get_openrouter_api_key()):
        model_name = _get_ollama_model(task)

    req = AIRequest(
        prompt=prompt,
        model=model_name,
        task=task,
        json_format=json_format,
        num_ctx=num_ctx,
        temperature=temperature,
        agent_name=agent_name
    )

    response = run_async(_gateway_instance.route(req))

    routing_meta = {
        "provider": response.provider,
        "model": response.model,
        "task": task,
        "fallback_used": response.fallback_used,
        "fallback_reason": response.fallback_reason,
        "duration_ms": response.latency_ms,
    }

    return response.content, routing_meta


def call_ai(
    prompt: str,
    task: str = "enrichment_products",
    json_format: bool = True,
    num_ctx: int = 4096,
    temperature: float = 0.0,
) -> Any:
    """
    Primary public API. Drop-in replacement for call_ollama().
    
    Routes to the new AIGateway.
    Returns parsed JSON dict or raw string depending on json_format.
    
    Never raises — returns empty dict/string on failure.
    """
    # Auto-detect agent name from call stack
    agent_name = "AIRouter"
    for frame_info in inspect.stack():
        self_obj = frame_info.frame.f_locals.get("self")
        if self_obj and hasattr(self_obj, "__class__"):
            cls_name = self_obj.__class__.__name__
            if "Agent" in cls_name or "Enricher" in cls_name:
                agent_name = cls_name
                break

    result, _ = route_completion(
        prompt=prompt,
        task=task,
        json_format=json_format,
        num_ctx=num_ctx,
        temperature=temperature,
        agent_name=agent_name,
    )
    return result


def get_routing_status() -> dict:
    """
    Returns current routing status for health checks and observability endpoints.
    """
    api_key = _get_openrouter_api_key()
    enabled = _is_openrouter_enabled()
    
    tier1_models = _gateway_instance.registry.get_tier1_models()
    first_tier1 = tier1_models[0] if tier1_models else "google/gemma-2-9b-it:free"
    
    return {
        "openrouter_enabled": enabled,
        "openrouter_key_configured": api_key is not None,
        "active_provider": "openrouter" if (enabled and api_key) else "ollama",
        "openrouter_model_extraction": first_tier1,
        "openrouter_model_enrichment": first_tier1,
        "ollama_model": _get_ollama_model("enrichment_products"),
        "ollama_base_url": _get_ollama_base_url(),
    }

