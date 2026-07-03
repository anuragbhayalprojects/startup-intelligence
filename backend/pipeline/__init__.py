"""
backend/pipeline/__init__.py
------------------------------
Modular pipeline package for Startup Intelligence OS.

Stages:
    ArticleCleaner    — Deterministic article cleaning + name extraction
    SearchEngine      — Dynamic search query generation + DuckDuckGo/Google scraping
    SourceCollector   — Source-centric web content collection (homepage, about, LinkedIn)
    ContentSegmenter  — Structured content cleaning and section segmentation
"""
