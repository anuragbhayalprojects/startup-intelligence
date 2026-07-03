"""
backend/pipeline/content_segmenter.py
-----------------------------------------
Content segmentation and BM25 extraction for Startup Intelligence OS.

Two layers:
  v2 (new): segment_for_enricher() — BM25 over crawled_pages dict, query strings
            from search_queries.json via WebSearchOrchestrator.
  v1 (legacy): segment_source_payload() / format_segmented_payload_for_enrichment()
               — retained for backward compatibility with old pipeline path.

BM25 chunking parameters (chunk_size_chars, character_budget_per_pass, etc.)
remain in scraper_config.json. Semantic query strings have moved to
search_queries.json v2.0.
"""

from __future__ import annotations

import os
import json
import re
import logging
from typing import Optional

logger = logging.getLogger("startup_intelligence.content_segmenter")

_SCRAPER_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "config", "scraper_config.json"
)


def _load_bm25_settings() -> dict:
    """Loads BM25 chunking settings from scraper_config.json with fallback defaults."""
    defaults = {
        "chunk_size_chars": 1000,
        "chunk_overlap_chars": 150,
        "character_budget_per_pass": 6000,
        "max_chunks_selected": 6,
    }
    try:
        if os.path.exists(_SCRAPER_CONFIG_PATH):
            with open(_SCRAPER_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**defaults, **data.get("bm25_settings", {})}
    except Exception as e:
        logger.warning(f"[ContentSegmenter] Failed to load scraper_config.json: {e}")
    return defaults


# ---------------------------------------------------------------------------
# v2 — BM25 segment_for_enricher (primary entry point for v2 pipeline)
# ---------------------------------------------------------------------------

def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Splits text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def _bm25_score(chunk: str, query_terms: list[str]) -> float:
    """Lightweight BM25-approximated scoring (TF-based, no external deps)."""
    chunk_lower = chunk.lower()
    score = 0.0
    chunk_len = len(chunk_lower.split())
    if chunk_len == 0:
        return 0.0
    for term in query_terms:
        tf = chunk_lower.count(term.lower())
        if tf > 0:
            score += (tf / chunk_len) * (1.0 + len(term) / 10.0)
    return score


def segment_for_enricher(
    crawled_pages: dict,
    enricher_key: str,
    orchestrator=None,
    relevant_page_roles: Optional[list[str]] = None,
) -> str:
    """
    v2 entry point: BM25-based text extraction for a specific enricher.

    Reads the BM25 query string for the enricher from WebSearchOrchestrator
    (which reads search_queries.json). Selects top-N text chunks from the
    relevant crawled pages and returns a formatted context string.

    Parameters
    ----------
    crawled_pages       : dict of page_role -> page_record (from source_collector)
    enricher_key        : BM25 query key: corporate_query | identity_query | product_query |
                          competitor_query | funding_query
    orchestrator        : optional WebSearchOrchestrator instance
    relevant_page_roles : optional list of page roles to restrict search to

    Returns
    -------
    str — top-ranked chunks concatenated, ready for LLM prompt injection
    """
    if orchestrator is None:
        from backend.utils.search import WebSearchOrchestrator
        orchestrator = WebSearchOrchestrator()

    bm25_cfg = _load_bm25_settings()
    chunk_size = bm25_cfg["chunk_size_chars"]
    overlap = bm25_cfg["chunk_overlap_chars"]
    budget = bm25_cfg["character_budget_per_pass"]
    max_chunks = bm25_cfg["max_chunks_selected"]

    query_string = orchestrator.get_bm25_query(enricher_key)
    if not query_string:
        logger.warning(f"[ContentSegmenter] No BM25 query for key='{enricher_key}'")
        return ""

    query_terms = query_string.lower().split()

    # Concatenate relevant page texts
    all_text_parts = []
    for role, page_record in crawled_pages.items():
        if not isinstance(page_record, dict):
            continue
        if relevant_page_roles and not any(prefix in role for prefix in relevant_page_roles):
            continue
        text = page_record.get("text_content", "") or ""
        footer = page_record.get("footer_text", "") or ""
        if text or footer:
            all_text_parts.append(f"[PAGE: {role}] {text} {footer}")

    if not all_text_parts:
        return ""

    full_text = "\n\n".join(all_text_parts)
    chunks = _chunk_text(full_text, chunk_size, overlap)

    # Score and rank chunks
    scored = [(chunk, _bm25_score(chunk, query_terms)) for chunk in chunks]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Select top-N within budget
    selected = []
    total_chars = 0
    for chunk, score in scored[:max_chunks]:
        if total_chars + len(chunk) > budget:
            break
        selected.append(chunk)
        total_chars += len(chunk)

    result = "\n\n---\n\n".join(selected)
    logger.info(
        f"[ContentSegmenter] BM25 for key='{enricher_key}': "
        f"{len(chunks)} chunks → {len(selected)} selected, {total_chars} chars"
    )
    return result



# Max chars per section (config-driven fallbacks)
_MAX_CHARS_PER_SECTION = 1200
_MAX_TOTAL_CHARS = 5000


def _clean_text(text: str) -> str:
    """Normalizes whitespace and strips excess noise from text."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def _extract_funding_snippets(search_snippets: dict) -> str:
    """Extracts funding-related text from search snippet records."""
    funding_text_parts = []
    funding_keywords = ["raised", "funding", "series", "seed", "invested", "investor", "round", "crores", "million"]

    for category, records in search_snippets.items():
        if not isinstance(records, list):
            continue
        for rec in records:
            snippet = rec.get("snippet", "") or ""
            title = rec.get("title", "") or ""
            combined = (title + " " + snippet).lower()
            if any(kw in combined for kw in funding_keywords):
                funding_text_parts.append(f"[{category.upper()}] {title}: {snippet}")

    return "\n".join(funding_text_parts[:10])  # Cap at 10 funding references


def _extract_social_presence(search_snippets: dict) -> str:
    """Extracts LinkedIn and social media presence text."""
    social_parts = []
    for category, records in search_snippets.items():
        if category not in ("linkedin", "social_profiles"):
            continue
        if not isinstance(records, list):
            continue
        for rec in records:
            title = rec.get("title", "") or ""
            snippet = rec.get("snippet", "") or ""
            url = rec.get("url", "") or ""
            social_parts.append(f"Title: {title}\nURL: {url}\nSnippet: {snippet}")

    return "\n\n".join(social_parts[:5])


def segment_source_payload(raw_payload: dict) -> dict:
    """
    Segments raw_source_payload into a structured cleaned_source_payload.

    Parameters
    ----------
    raw_payload : dict
        Output from source_collector.collect_source_payload()

    Returns
    -------
    dict
        Cleaned and segmented content by canonical section name.
    """
    segmented: dict = {
        "homepage": "",
        "about_page": "",
        "products_services": "",
        "founders_team": "",
        "funding_investors": "",
        "contact_us": "",
        "social_presence": "",
        "seo_metadata": {},
        "total_content_chars": 0,
    }

    # 1. Homepage
    homepage = _clean_text(raw_payload.get("homepage_text", ""))
    segmented["homepage"] = homepage[:_MAX_CHARS_PER_SECTION]

    # 2. About page
    about = _clean_text(raw_payload.get("about_page_text", ""))
    segmented["about_page"] = about[:_MAX_CHARS_PER_SECTION]

    # 3. Products / services page
    products = _clean_text(raw_payload.get("products_page_text", ""))
    segmented["products_services"] = products[:_MAX_CHARS_PER_SECTION]

    # 4. Team / founders page
    team = _clean_text(raw_payload.get("team_page_text", ""))
    segmented["founders_team"] = team[:_MAX_CHARS_PER_SECTION]

    # 5. Contact page
    contact = _clean_text(raw_payload.get("contact_page_text", ""))
    segmented["contact_us"] = contact[:500]  # Less critical — short cap

    # 6. Funding intelligence from search snippets
    search_snippets = raw_payload.get("search_snippets", {})
    funding_text = _extract_funding_snippets(search_snippets)

    # Also include LinkedIn snippets if they mention funding
    linkedin_snippets = raw_payload.get("linkedin_snippets", "")
    combined_funding = "\n".join(filter(None, [funding_text, linkedin_snippets[:400]]))
    segmented["funding_investors"] = combined_funding[:_MAX_CHARS_PER_SECTION]

    # 7. Social presence
    social = _extract_social_presence(search_snippets)
    linkedin = raw_payload.get("linkedin_snippets", "")
    combined_social = "\n".join(filter(None, [social, linkedin]))
    segmented["social_presence"] = combined_social[:800]

    # 8. SEO metadata (passed through directly)
    segmented["seo_metadata"] = raw_payload.get("seo_metadata", {})

    # 9. Calculate total content size for metadata/observability
    total_chars = sum(len(str(v)) for v in segmented.values() if isinstance(v, str))
    segmented["total_content_chars"] = total_chars

    logger.info(
        f"[ContentSegmenter] Segmented {total_chars} chars across "
        f"{sum(1 for v in segmented.values() if isinstance(v, str) and v)} non-empty sections"
    )
    return segmented


def format_segmented_payload_for_enrichment(
    segmented: dict,
    sections: Optional[list] = None,
    max_chars: int = 4500,
) -> str:
    """
    Formats a segmented payload into a single prompt-ready enrichment context string.

    Parameters
    ----------
    segmented : dict
        Output from segment_source_payload()
    sections : list, optional
        Which sections to include. Defaults to all non-empty sections.
    max_chars : int
        Maximum total characters in output.

    Returns
    -------
    str
        Formatted multi-section context ready for LLM prompt injection.
    """
    section_labels = {
        "homepage": "HOMEPAGE",
        "about_page": "ABOUT PAGE",
        "products_services": "PRODUCTS & SERVICES",
        "founders_team": "FOUNDERS & TEAM",
        "funding_investors": "FUNDING & INVESTORS",
        "contact_us": "CONTACT",
        "social_presence": "LINKEDIN & SOCIAL",
    }

    if sections is None:
        sections = list(section_labels.keys())

    parts = []
    if segmented.get("seo_metadata"):
        meta = segmented["seo_metadata"]
        meta_text = f"Title: {meta.get('title', '')}\nDescription: {meta.get('meta_description', '') or meta.get('og_description', '')}"
        parts.append(f"=== SEO METADATA ===\n{meta_text}")

    for section_key in sections:
        text = segmented.get(section_key, "")
        if not text:
            continue
        label = section_labels.get(section_key, section_key.upper())
        parts.append(f"=== {label} ===\n{text}")

    combined = "\n\n".join(parts)
    return combined[:max_chars]
