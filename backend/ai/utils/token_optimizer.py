import json
from typing import Any, Dict, Union

PROTECTED_KEYS = {
    "rag_context",
    "application_ethos",
    "system_directives",
    "query_embeddings"
}

def estimate_tokens(text: str) -> int:
    """
    Heuristic Token Estimation:
    - structured JSON/Graphify inputs: chars / 3.1
    - plain-text narrative prose: chars / 4.0
    """
    text = text.strip()
    # Simple check for JSON/Graphify structure
    is_structured = False
    if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
        try:
            json.loads(text)
            is_structured = True
        except ValueError:
            pass
    
    # Alternatively, look for significant structural markers like lots of curly braces/brackets/quotes
    if not is_structured:
        brace_count = text.count("{") + text.count("}") + text.count("[") + text.count("]")
        if brace_count > 10 and (text.count(":") > 5 or text.count(",") > 5):
            is_structured = True

    chars = len(text)
    if is_structured:
        return int(chars / 3.1)
    else:
        return int(chars / 4.0)

def compact_text(text: str, task: str) -> str:
    """
    Selective Compaction for raw scraping text.
    For 'extraction' tasks: head/tail split-slicing (first 2000 and last 2000 chars).
    For other tasks: aggressively truncate to 500 characters.
    """
    if len(text) <= 500:
        return text
    
    if "extraction" in task.lower():
        if len(text) > 4000:
            return f"{text[:2000]}\n\n[... TRUNCATED CONTEXT ...]\n\n{text[-2000:]}"
        return text
    else:
        return text[:500] + "\n[... TRUNCATED ...]"

def optimize_context(context: Dict[str, Any], task: str) -> Dict[str, Any]:
    """
    Walks through the context dictionary and compacts heavy raw scraping fields
    while preserving protected keys.
    """
    optimized = {}
    for key, value in context.items():
        if key in PROTECTED_KEYS:
            optimized[key] = value
        elif isinstance(value, str):
            # Target heavy raw scraping fields like article_body, article_text, html_content, etc.
            if key in {"article_body", "body", "text", "html_content", "raw_content", "raw_text"}:
                optimized[key] = compact_text(value, task)
            else:
                optimized[key] = value
        elif isinstance(value, dict):
            optimized[key] = optimize_context(value, task)
        elif isinstance(value, list):
            optimized[key] = [
                optimize_context(item, task) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            optimized[key] = value
    return optimized
