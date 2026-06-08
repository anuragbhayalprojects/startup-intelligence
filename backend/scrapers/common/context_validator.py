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

def extract_clean_paragraphs(html_text: str) -> list[str]:
    """
    Parses HTML text and extracts a list of cleaned, filtered paragraphs
    using selectors and filters from content_filters.json.
    """
    from bs4 import BeautifulSoup
    
    filters = load_content_filters()
    selectors = filters.get("article_body_selectors", [])
    blocked_phrases = filters.get("blocked_phrases", [])
    blocked_patterns = filters.get("blocked_patterns", [])
    footer_keywords = filters.get("footer_keywords", [])
    min_length = filters.get("min_paragraph_length", 65)
    
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
    paragraphs = []
    
    for p in raw_paragraphs:
        # Skip elements that look like widgets or headers
        if p.get("class") and any(c in p.get("class") for c in ["wp-block-post-excerpt__excerpt", "widget-title", "footer"]):
            continue
            
        text = p.get_text(strip=True)
        if len(text) < min_length:
            continue
            
        # Check blocked phrases
        if any(phrase.lower() in text.lower() for phrase in blocked_phrases):
            continue
            
        # Check footer keywords
        if any(kw.lower() in text.lower() for kw in footer_keywords):
            continue
            
        # Check regex patterns
        is_blocked = False
        for pattern in blocked_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                is_blocked = True
                break
        if is_blocked:
            continue
            
        paragraphs.append(text)
        
    return paragraphs

