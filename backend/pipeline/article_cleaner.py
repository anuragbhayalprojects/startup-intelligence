"""
backend/pipeline/article_cleaner.py
--------------------------------------
Deterministic article cleaning and startup name extraction.

Extracted from backend/workflows/startup_pipeline.py for modular reuse.
All functions maintain their original signatures for backward compatibility.

Responsibilities:
  - Load external config: name_resolution_rules.json, headline_patterns.json
  - Clean raw headline strings to extract brand names (clean_string)
  - Validate and filter extracted startup names (get_clean_startup_name)
  - Detect duplicate news events (is_news_duplicate, are_headlines_describing_same_event)
  - Route dedup AI calls through the new AI router (deduplication task)
"""

from __future__ import annotations

import re
import os
import json
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Config loading (cached)
# ---------------------------------------------------------------------------

_NAME_RULES_CACHE: Optional[dict] = None
_HEADLINE_PATTERNS_CACHE: Optional[dict] = None

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def load_name_resolution_rules() -> dict:
    """
    Loads name resolution rules from backend/config/name_resolution_rules.json.
    Results are cached in-process to avoid repeated file I/O.
    """
    global _NAME_RULES_CACHE
    if _NAME_RULES_CACHE is not None:
        return _NAME_RULES_CACHE
    config_path = _CONFIG_DIR / "name_resolution_rules.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            _NAME_RULES_CACHE = json.load(f)
    except Exception as e:
        print(f"⚠️ [ArticleCleaner] Could not load name_resolution_rules.json: {e}")
        _NAME_RULES_CACHE = {}
    return _NAME_RULES_CACHE


def load_headline_patterns() -> dict:
    """
    Loads regex patterns from backend/config/headline_patterns.json.
    Results are cached in-process to avoid repeated file I/O.
    """
    global _HEADLINE_PATTERNS_CACHE
    if _HEADLINE_PATTERNS_CACHE is not None:
        return _HEADLINE_PATTERNS_CACHE
    config_path = _CONFIG_DIR / "headline_patterns.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            _HEADLINE_PATTERNS_CACHE = json.load(f)
    except Exception as e:
        print(f"⚠️ [ArticleCleaner] Could not load headline_patterns.json: {e}")
        _HEADLINE_PATTERNS_CACHE = {}
    return _HEADLINE_PATTERNS_CACHE


# ---------------------------------------------------------------------------
# String cleaning
# ---------------------------------------------------------------------------

def clean_string(text: str) -> str:
    """
    Core string cleaning utility that strips action verbs, possessives,
    and descriptive prefixes to isolate the actual startup brand name.
    Config-driven via name_resolution_rules.json.
    """
    if not text:
        return ""

    rules = load_name_resolution_rules()
    verbs = rules.get("verbs", [])
    prefixes = rules.get("prefixes", [])

    # Pre-process compound hyphenated company suffixes
    text = re.sub(r'\b(\w+)-(owned|backed|funded|incubated|acquired|led|run)\b', r'\1 \2', text, flags=re.IGNORECASE)

    # 1. Split at common action verbs / financial descriptors
    if verbs:
        verbs_sorted = sorted(verbs, key=len, reverse=True)
        verbs_pattern = r'\b(' + '|'.join(re.escape(v) for v in verbs_sorted) + r')\b'
        match = re.split(verbs_pattern, text, maxsplit=1, flags=re.IGNORECASE)
        part = match[0] if match else text
    else:
        part = text

    # 2. Split at possessive indicators
    part = re.split(r"['']s?\b", part)[0]

    # 3. Strip starting auxiliary words or descriptive prefixes
    if prefixes:
        prefixes_sorted = sorted(prefixes, key=len, reverse=True)
        prefixes_pattern = r'^(' + '|'.join(re.escape(p).replace(r'\ ', r'\s+') for p in prefixes_sorted) + r')\s+'
        cleaned = re.sub(prefixes_pattern, '', part.strip(), flags=re.IGNORECASE)
    else:
        cleaned = part.strip()

    # 4. Strip special characters
    cleaned = re.sub(r"[''\"`₹$%\+\-\[\]\(\)]", "", cleaned).strip()

    # 5. Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # 6. Strip standard suffixes (e.g. Pvt Ltd, India, Global, etc.) from the end
    suffixes = rules.get("suffixes", [])
    if suffixes:
        suffixes_sorted = sorted(suffixes, key=len, reverse=True)
        suffixes_pattern = r'\s+\b(' + '|'.join(re.escape(s) for s in suffixes_sorted) + r')\b$'
        cleaned = re.sub(suffixes_pattern, '', cleaned, flags=re.IGNORECASE).strip()

    return cleaned


# ---------------------------------------------------------------------------
# Startup name validation and extraction
# ---------------------------------------------------------------------------

def get_clean_startup_name(
    headline: str,
    extracted_name: Optional[str],
    source: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Optional[str]:
    """
    Cleans the news headline to extract only the actual startup brand name.
    Uses AI extracted name as primary, with a robust mapped lookup fallback.

    Filtering rules are loaded dynamically from:
        backend/config/name_resolution_rules.json
        backend/config/headline_patterns.json
    """
    rules = load_name_resolution_rules()

    generic_placeholders = rules.get("generic_placeholders", [])
    replacements = rules.get("replacements", {})
    investor_names = set(rules.get("investor_names", []))
    bad_terms = set(rules.get("bad_terms", []))
    locations = set(rules.get("locations", []))
    generic_words = set(rules.get("generic_words", []))
    product_split_terms = rules.get("product_split_terms", [])

    def _truncate_at_product_term(name: str) -> str:
        words = name.split()
        if len(words) < 3:
            return name
        for i, word in enumerate(words[1:], start=1):
            if word.lower() in product_split_terms:
                truncated = " ".join(words[:i])
                if truncated:
                    return truncated
        return name

    def is_invalid_startup_name(name: str) -> bool:
        if not name:
            return True
        name_lower = name.lower().strip()

        if source:
            src_lower = source.lower().strip()
            if name_lower == src_lower or src_lower in name_lower or name_lower in src_lower:
                return True
        if source_url:
            domain = (
                source_url.replace("https://", "").replace("http://", "")
                .replace("www.", "").split("/")[0].split(".")[0].lower()
            )
            if domain and (name_lower == domain or domain in name_lower or name_lower in domain):
                return True

        if len(name_lower) < 3:
            return True

        if (
            name_lower.startswith("ex ")
            or name_lower.startswith("former ")
            or name_lower.startswith("ex-")
            or name_lower.startswith("exmirae")
            or name_lower.startswith("exceo")
            or name_lower.startswith("exfounder")
            or name_lower.startswith("exvp")
            or name_lower.startswith("exdirector")
        ):
            return True

        if name_lower.startswith("ex") and len(name_lower) > 2:
            rest = name_lower[2:].strip()
            if rest in investor_names or any(inv in rest for inv in investor_names) or rest in bad_terms:
                return True

        tokens = re.findall(r'\b\w+\b', name_lower)

        if any(inv in tokens for inv in investor_names):
            return True
        if "and" in tokens or "or" in tokens or "&" in name_lower or "," in name_lower:
            return True
        if any(t in tokens for t in bad_terms) or any(t in name_lower for t in bad_terms):
            return True
        if any(loc in tokens for loc in locations):
            return True
        if any(w in tokens for w in generic_words):
            return True
        if name_lower in [p.lower() for p in generic_placeholders]:
            return True

        return False

    # 1. Try AI-extracted name first
    if extracted_name:
        extracted_name = _truncate_at_product_term(extracted_name.strip())
        cleaned_ai = clean_string(extracted_name)
        if cleaned_ai and not is_invalid_startup_name(cleaned_ai.lower().strip()):
            if len(cleaned_ai.split()) <= 4 and len(cleaned_ai) <= 30:
                if cleaned_ai.lower() not in ["and", "to", "for", "with", "the"]:
                    ai_key = cleaned_ai.lower().strip()
                    if ai_key in replacements:
                        return replacements[ai_key]
                    return cleaned_ai

    # 2. Layered fallback: Headline pattern matching
    patterns_config = load_headline_patterns()
    for pattern_entry in patterns_config.get("patterns", []):
        rx = pattern_entry.get("regex")
        groups = pattern_entry.get("groups", [1])
        match = re.match(rx, headline, re.IGNORECASE)
        if match:
            for g in groups:
                try:
                    candidate = match.group(g)
                    candidate_clean = clean_string(candidate)
                    if candidate_clean and not is_invalid_startup_name(candidate_clean):
                        final_key = candidate_clean.lower().strip()
                        if final_key in replacements:
                            return replacements[final_key]
                        return candidate_clean
                except IndexError:
                    continue

    # 3. Last resort fallback: clean string from headline (first 2 words)
    cleaned_fallback = clean_string(headline)
    words = cleaned_fallback.split()
    if len(words) > 0:
        candidate = " ".join(words[:2])
        if not is_invalid_startup_name(candidate):
            final_key = candidate.lower().strip()
            if final_key in replacements:
                return replacements[final_key]
            return candidate

    return None


# ---------------------------------------------------------------------------
# Deduplication helpers — route through AI router for cloud capability
# ---------------------------------------------------------------------------

def are_headlines_describing_same_event(headline1: str, headline2: str) -> bool:
    """
    Asks the AI (via router) if two headlines describe the exact same corporate event.
    Routes through AIRouter for OpenRouter/Ollama selection.
    """
    prompt = f"""You are a precise semantic news deduplication assistant.
Your job is to determine if two headlines from different sources are reporting on the exact same corporate event (such as a funding round, launch, acquisition, or leadership change for a startup).

Note:
1. Different sources may describe the same event with different word order or focus.
2. The monetary amount and the company names matching is a very strong indicator of the same funding event.

Headline 1: "{headline1}"
Headline 2: "{headline2}"

Based on the rules, are these two headlines describing the same corporate event?
Respond with only a single word: YES or NO. Do not explain."""

    try:
        from backend.ai.router import call_ai
        result = call_ai(prompt=prompt, task="deduplication", json_format=False, num_ctx=512, temperature=0.0)
        return "yes" in str(result).lower()
    except Exception:
        # Graceful fallback to direct Ollama
        try:
            import requests
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
            response = requests.post(
                f"{base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False, "options": {"num_ctx": 512, "temperature": 0.0}},
                headers={"Content-Type": "application/json"},
                timeout=5.0,
            )
            response.raise_for_status()
            result = response.json().get("response", "").strip().lower()
            return "yes" in result
        except Exception:
            return False


def are_news_events_describing_same_story(
    headline1: str, desc1: str, headline2: str, desc2: str
) -> bool:
    """
    Asks the AI if two news events (headlines + descriptions) describe the same story.
    Routes through AIRouter for OpenRouter/Ollama selection.
    """
    prompt = f"""You are a precise semantic news deduplication assistant.
Your job is to determine if two news events (each having a headline and a description/summary) from different sources are reporting on the exact same corporate event or story (such as a funding round, launch, acquisition, policy update, or leadership change for a startup).

Note:
1. Different sources may describe the same event with different word order or focus.
2. If both headlines and descriptions are talking about the exact same underlying event, they are duplicates.
3. If they describe completely different events (e.g. one is a funding round from 2024, and the other is a different event in 2026), they are NOT duplicates.

News Event 1:
Headline: "{headline1}"
Context/Description: "{desc1}"

News Event 2:
Headline: "{headline2}"
Context/Description: "{desc2}"

Based on the rules, do these two news events describe the same corporate event or story?
Respond with only a single word: YES or NO. Do not explain."""

    try:
        from backend.ai.router import call_ai
        result = call_ai(prompt=prompt, task="deduplication", json_format=False, num_ctx=1024, temperature=0.0)
        return "yes" in str(result).lower()
    except Exception:
        try:
            import requests
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
            response = requests.post(
                f"{base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False, "options": {"num_ctx": 1024, "temperature": 0.0}},
                headers={"Content-Type": "application/json"},
                timeout=8.0,
            )
            response.raise_for_status()
            result = response.json().get("response", "").strip().lower()
            return "yes" in result
        except Exception:
            return False


def is_news_duplicate(
    new_headline: str,
    new_description: str,
    existing_news: list,
    source_url: str = "",
) -> bool:
    """
    Determines if a new headline is a duplicate of any existing news.
    Only returns True for exact identical headlines or source URL matches.
    """
    if not existing_news:
        return False

    clean_new_headline = new_headline.strip().lower()
    clean_new_url = source_url.strip().lower() if source_url else ""

    for news in existing_news:
        exist_headline = (news.get("headline") or "").strip().lower()
        exist_url = (news.get("source_url") or "").strip().lower()

        if clean_new_headline == exist_headline:
            return True
        if clean_new_url and clean_new_url == exist_url:
            return True

    return False
