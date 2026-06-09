import os
import json
import requests
from backend.rag.retriever import get_retriever

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

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
    """Calls Ollama API synchronously and parses response."""
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": num_ctx,
                "temperature": temperature
            }
        }
        if json_format:
            payload["format"] = "json"

        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=40.0
        )
        resp.raise_for_status()
        text = resp.json().get("response", "").strip()
        
        if json_format:
            cleaned = clean_llm_response(text)
            return json.loads(cleaned)
        return text
    except requests.exceptions.ConnectionError:
        print("⚠️ Ollama AI service is offline. Returning empty fallback response.")
        return {} if json_format else ""
    except Exception as e:
        print(f"⚠️ Ollama API call failed: {e}")
        # Return fallback empty structures on JSON error
        return {} if json_format else ""

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
