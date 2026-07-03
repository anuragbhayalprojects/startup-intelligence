import re
import json
import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("startup_intelligence.response_validator")

def repair_json_string(raw_text: str) -> str:
    """
    Applies regex and structural repairs to raw text containing JSON.
    """
    text = raw_text.strip()
    
    # 1. Strip Markdown wrapper backticks
    if text.startswith("```"):
        # Match ```json ... ``` or similar
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    # 2. Escape unescaped literal newline/tab characters inside quote-bounded string values
    # We can iterate through the string and find all substrings inside double quotes.
    # Note: simple state machine is safer than regex for unescaped newlines inside quotes.
    chars = list(text)
    in_string = False
    escaped = False
    for i in range(len(chars)):
        c = chars[i]
        if escaped:
            escaped = False
            continue
        if c == '\\':
            escaped = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string and c == '\n':
            chars[i] = '\\n'
        elif in_string and c == '\t':
            chars[i] = '\\t'
    text = "".join(chars)

    # 3. Fix trailing commas in lists/maps
    text = re.sub(r",\s*([\]}])", r"\1", text)

    # 4. Balance unclosed curly braces ({})
    open_braces = text.count("{")
    close_braces = text.count("}")
    if open_braces > close_braces:
        text += "}" * (open_braces - close_braces)
    
    # Balance unclosed brackets ([])
    open_brackets = text.count("[")
    close_brackets = text.count("]")
    if open_brackets > close_brackets:
        text += "]" * (open_brackets - close_brackets)

    return text

def enforce_schema_contract(
    payload: Dict[str, Any], 
    required_keys: Union[List[str], Dict[str, Any]]
) -> Dict[str, Any]:
    """
    If required_schema_keys are specified but missing from the parsed payload,
    dynamically backfill safe default initializers (empty lists [], zero 0, or empty strings "")
    to prevent downstream KeyErrors.
    """
    if not isinstance(payload, dict):
        return payload

    if isinstance(required_keys, dict):
        # If a dictionary of defaults is provided
        for key, default_val in required_keys.items():
            if key not in payload:
                payload[key] = default_val
            elif isinstance(default_val, dict) and isinstance(payload[key], dict):
                payload[key] = enforce_schema_contract(payload[key], default_val)
    elif isinstance(required_keys, list):
        # Guess default based on name
        for key in required_keys:
            if key not in payload:
                # Heuristics for default type
                lower_key = key.lower()
                if any(x in lower_key for x in ["list", "array", "details", "rounds", "competitors", "tags", "founders", "products", "services"]):
                    payload[key] = []
                elif any(x in lower_key for x in ["count", "score", "year", "amount", "id", "confidence", "rating"]):
                    payload[key] = 0
                else:
                    payload[key] = ""
    return payload

def validate_and_repair(
    raw_text: str,
    required_schema_keys: Optional[Union[List[str], Dict[str, Any]]] = None,
    json_format: bool = True
) -> Any:
    """
    Main entrypoint for response validation & repair.
    """
    if not json_format:
        return raw_text

    repaired = repair_json_string(raw_text)
    try:
        parsed = json.loads(repaired)
    except Exception as e:
        logger.warning(f"JSON parsing failed after initial repair: {e}. Trying raw text cleanup.")
        # Fallback: find first '{' and last '}'
        try:
            start_idx = repaired.find("{")
            end_idx = repaired.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                parsed = json.loads(repaired[start_idx:end_idx+1])
            else:
                raise ValueError("No json block found")
        except Exception as e2:
            logger.error(f"JSON extraction fallback failed: {e2}")
            # If all else fails, return a dictionary with raw text as content or raise
            return {"raw_response": raw_text, "error": str(e2)}

    if required_schema_keys:
        parsed = enforce_schema_contract(parsed, required_schema_keys)

    return parsed
