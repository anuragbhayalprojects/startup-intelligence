import re
import os
import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "content_filters.json"

def load_content_filters() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ [ContextValidator] Failed to load content_filters.json: {e}")
        return {}

def extract_entities(text: str) -> set[str]:
    """
    Extracts potential startup entities (capitalized words and alphanumeric tokens)
    from a piece of text.
    """
    if not text:
        return set()
    # Find capitalized words (e.g., Incuspaze, iKeva)
    caps = re.findall(r'\b[A-Z][a-zA-Z0-9]*\b', text)
    # Find alphanumeric words (e.g., Cars24)
    alphanumeric = re.findall(r'\b[a-zA-Z0-9]*\d+[a-zA-Z0-9]*\b', text)
    
    entities = set()
    for w in caps + alphanumeric:
        w_clean = w.strip().lower()
        # Filter out short or standard common words if they slip in
        if len(w_clean) > 1 and w_clean not in ["the", "ipo", "crore", "crores", "lakh", "lakhs", "series", "seed"]:
            entities.add(w_clean)
    return entities

def validate_article_context(headline: str, paragraphs: list[str]) -> tuple[float, bool]:
    """
    Validates if the scraped paragraphs match the context of the article headline.
    Checks the overlap of headline entities in the paragraphs.
    
    Returns:
        (confidence_score: float, bad_context: bool)
    """
    filters = load_content_filters()
    threshold = filters.get("context_validation_threshold", 0.30)
    
    headline_entities = extract_entities(headline)
    if not headline_entities:
        # If we can't extract any entities from the headline, don't flag it as bad context immediately
        return 1.0, False
        
    combined_text = " ".join(paragraphs).lower()
    
    # Count how many headline entities are mentioned in the article text
    matched = 0
    for entity in headline_entities:
        # Match as whole word/substring
        if re.search(r'\b' + re.escape(entity) + r'\b', combined_text):
            matched += 1
            
    confidence_score = matched / len(headline_entities) if headline_entities else 0.0
    bad_context = confidence_score < threshold
    
    return confidence_score, bad_context

def _is_boilerplate(text: str, filters: dict) -> bool:
    """
    Returns True if the paragraph is identified as non-article boilerplate
    using three layered rule-based checks:
      1. Disclaimer / legal / financial language patterns
      2. Author bio signals
      3. CTA (call-to-action) and subscription bait patterns
    All patterns are loaded from content_filters.json for easy maintenance.
    """
    text_lower = text.lower().strip()

    # Layer 1 — Legal / disclaimer patterns
    for pattern in filters.get("disclaimer_patterns", []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True

    # Layer 2 — Author bio signals
    for pattern in filters.get("author_bio_signals", []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True

    # Layer 3 — CTA / subscription / engagement bait
    for pattern in filters.get("cta_signals", []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True

    return False


def extract_clean_paragraphs(html_text: str) -> list[str]:
    """
    Parses HTML text and extracts a list of cleaned, filtered paragraphs
    using selectors and filters from content_filters.json.

    Filtering layers applied (in order):
      1. CSS selector scoping — target known article-body containers
      2. CSS class blocklist — skip widget/footer paragraph elements
      3. Minimum length threshold — discard stub paragraphs
      4. Blocked phrases — exact substring matches (from config)
      5. Footer keywords — site-nav / meta page phrases
      6. Blocked patterns — regex matches (ads, sponsored labels)
      7. Boilerplate detection — legal disclaimers, author bios, CTAs
      8. Position heuristic — short paragraphs in the last 20% are likely footers
      9. Max paragraph cap — truncate to max_stored_paragraphs (default 10)
    """
    from bs4 import BeautifulSoup
    
    filters = load_content_filters()
    selectors = filters.get("article_body_selectors", [])
    blocked_phrases = filters.get("blocked_phrases", [])
    blocked_patterns = filters.get("blocked_patterns", [])
    footer_keywords = filters.get("footer_keywords", [])
    min_length = filters.get("min_paragraph_length", 65)
    max_stored = filters.get("max_stored_paragraphs", 10)
    footer_ratio = filters.get("footer_position_ratio", 0.75)
    short_footer_max = filters.get("short_footer_max_length", 130)
    
    soup = BeautifulSoup(html_text, "html.parser")
    
    # Try finding scoped article content first
    container = None
    for selector in selectors:
        container = soup.select_one(selector)
        if container:
            break
            
    # Fallback to full document soup if no container matches
    source_element = container if container else soup
    
    raw_paragraphs = source_element.find_all("p")
    total_raw = len(raw_paragraphs)
    paragraphs = []
    
    for idx, p in enumerate(raw_paragraphs):
        # Layer 2 — Skip elements that look like widgets or headers
        if p.get("class") and any(c in p.get("class") for c in ["wp-block-post-excerpt__excerpt", "widget-title", "footer"]):
            continue
            
        text = p.get_text(strip=True)

        # Layer 3 — Minimum length
        if len(text) < min_length:
            continue
            
        # Layer 4 — Blocked phrases (exact substring)
        if any(phrase.lower() in text.lower() for phrase in blocked_phrases):
            continue
            
        # Layer 5 — Footer keywords
        if any(kw.lower() in text.lower() for kw in footer_keywords):
            continue
            
        # Layer 6 — Blocked regex patterns
        is_blocked = False
        for pattern in blocked_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                is_blocked = True
                break
        if is_blocked:
            continue

        # Layer 7 — Boilerplate: disclaimer / author bio / CTA detection
        if _is_boilerplate(text, filters):
            continue

        # Layer 8 — Position heuristic: short paragraph in the bottom 20% is likely footer
        if total_raw > 0 and (idx / total_raw) >= footer_ratio and len(text) <= short_footer_max:
            continue
            
        paragraphs.append(text)

    # Layer 9 — Max paragraph cap: keep only the first N substantive paragraphs
    return paragraphs[:max_stored]
