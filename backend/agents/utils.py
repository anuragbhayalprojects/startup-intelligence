import os
import json
import requests
import time
import inspect
from typing import Any
from backend.rag.retriever import get_retriever
from backend.utils.tracing import generate_uuid, log_prompt_ledger

from backend.utils.config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT

def clean_llm_response(response_text: str) -> str:
    """Extracts JSON block from the LLM response text."""
    if not response_text:
        return ""
    
    # 1. Look for ```json ... ```
    json_start = response_text.find('```json')
    if json_start != -1:
        json_start += 7
        json_end = response_text.find('```', json_start)
        if json_end != -1:
            return response_text[json_start:json_end].strip()

    # 2. Look for general ``` ... ```
    raw_start = response_text.find('```')
    if raw_start != -1:
        raw_start += 3
        raw_end = response_text.find('```', raw_start)
        if raw_end != -1:
            content = response_text[raw_start:raw_end].strip()
            if content.startswith('{') or content.startswith('['):
                return content

    # 3. Fallback: find outermost curly braces or square brackets
    first_brace = response_text.find('{')
    last_brace = response_text.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return response_text[first_brace:last_brace+1].strip()

    first_bracket = response_text.find('[')
    last_bracket = response_text.rfind(']')
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        return response_text[first_bracket:last_bracket+1].strip()

    return response_text.strip()

def call_ollama(prompt: str, json_format: bool = True, num_ctx: int = 4096, temperature: float = 0.0) -> Any:
    """
    Calls the AI backend (OpenRouter primary, Ollama fallback) and returns a parsed response.

    This function maintains its original signature for full backward compatibility with
    all existing agent callers. Routing is now handled transparently by backend.ai.router.

    Routing decision:
      - OPENROUTER_ENABLED=true AND OPENROUTER_API_KEY set  → OpenRouter (cloud)
      - OPENROUTER_ENABLED=false OR key absent              → Ollama (local)
      - Any OpenRouter failure (timeout, rate limit, etc.)  → Ollama fallback

    Telemetry is logged to obs_prompt_ledger via the router.
    """
    # Detect the agent calling this function from the stack frame
    agent_name = "AIRouter"
    for frame_info in inspect.stack():
        self_obj = frame_info.frame.f_locals.get("self")
        if self_obj and hasattr(self_obj, "__class__"):
            cls_name = self_obj.__class__.__name__
            if "Agent" in cls_name or cls_name.endswith("Agent"):
                agent_name = cls_name
                break

    try:
        # Delegate to the new centralized AI router
        from backend.ai.router import route_completion
        result, routing_meta = route_completion(
            prompt=prompt,
            task="enrichment_products",   # default task for legacy callers
            json_format=json_format,
            num_ctx=num_ctx,
            temperature=temperature,
            agent_name=agent_name,
        )
        return result
    except Exception as e:
        # Ultimate safety net — if router itself fails, fall back to direct Ollama
        import requests as _requests
        print(f"⚠️ [call_ollama] Router delegation failed ({e}), using direct Ollama call")
        try:
            from backend.utils.ollama_helper import ensure_ollama_running
            ensure_ollama_running()
        except Exception:
            pass

        prompt_id = "PRMPT_" + generate_uuid()
        start_time = time.perf_counter()
        text = ""
        parsed_json = {}

        try:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": num_ctx, "temperature": temperature},
            }
            if json_format:
                payload["format"] = "json"

            resp = _requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=OLLAMA_TIMEOUT,
            )
            resp.raise_for_status()
            text = resp.json().get("response", "").strip()
            if json_format:
                cleaned = clean_llm_response(text)
                parsed_json = json.loads(cleaned)
                return parsed_json
            return text
        except requests.exceptions.ConnectionError:
            print("⚠️ Ollama AI service is offline. Returning empty fallback response.")
            return {} if json_format else ""
        except Exception as ex:
            print(f"⚠️ Ollama API call failed: {ex}")
            return {} if json_format else ""
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            ledger_parsed = parsed_json if (json_format and parsed_json) else {"response_text": text}
            log_prompt_ledger(
                prompt_id=prompt_id,
                agent_name=agent_name,
                prompt_template=prompt,
                injected_context="",
                raw_response=text,
                parsed_response=ledger_parsed,
                duration_ms=duration_ms,
            )


def get_rag_context(query: str, category_filter: str = None, top_k: int = 3) -> str:
    """Retrieves relevant chunk contents from the RAG store as text."""
    retriever = get_retriever()
    results = retriever.retrieve(query, top_k=top_k * 2)
    
    # Filter by category if requested
    if category_filter:
        results = [r for r in results if r["category"].lower() == category_filter.lower()]
        
    results = results[:top_k]
    
    context_blocks = []
    for r in results:
        block = (
            f"Source: {os.path.basename(r['filepath'])} ({r['category']}) > {r['header']}\n"
            f"Content: {r['content']}"
        )
        context_blocks.append(block)
        
    return "\n\n---\n\n".join(context_blocks)
