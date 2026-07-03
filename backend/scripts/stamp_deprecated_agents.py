"""
Stamps all legacy agent files with a DEPRECATED header comment.
Run from the repo root: python backend/scripts/stamp_deprecated_agents.py
"""
import os
import re

AGENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "agents")

# Map agent file → the new module that replaced it
DEPRECATION_MAP = {
    "legal_name_agent.py": "backend.enrichment.identity_enricher.IdentityEnricher",
    "identity_discovery_agent.py": "backend.enrichment.identity_enricher.IdentityEnricher",
    "identity_resolution_agent.py": "backend.enrichment.identity_enricher.IdentityEnricher",
    "enrichment_agent.py": "backend.enrichment.identity_enricher.IdentityEnricher + backend.enrichment.product_enricher.ProductEnricher",
    "product_intelligence_agent.py": "backend.enrichment.product_enricher.ProductEnricher",
    "industry_classification_agent.py": "backend.enrichment.product_enricher.ProductEnricher",
    "description_generator_agent.py": "backend.enrichment.product_enricher.ProductEnricher",
    "classification_agent.py": "backend.enrichment.product_enricher.ProductEnricher",
    "funding_intelligence_agent.py": "backend.enrichment.funding_enricher.FundingEnricher",
    "competitor_intelligence_agent.py": "backend.enrichment.intelligence_enricher.IntelligenceEnricher",
    "opportunity_mapping_agent.py": "backend.enrichment.intelligence_enricher.IntelligenceEnricher",
    "relevance_agent.py": "backend.enrichment.intelligence_enricher.IntelligenceEnricher",
    "strategic_fit_agent.py": "backend.enrichment.intelligence_enricher.IntelligenceEnricher",
    "signal_agent.py": "backend.enrichment.intelligence_enricher.IntelligenceEnricher",
    "recommendation_agent.py": "backend.enrichment.intelligence_enricher.IntelligenceEnricher",
    "market_intelligence_agent.py": "backend.enrichment.product_enricher.ProductEnricher + backend.enrichment.intelligence_enricher.IntelligenceEnricher",
    "business_problem_agent.py": "backend.enrichment.intelligence_enricher.IntelligenceEnricher",
}

DEPRECATED_HEADER_TMPL = """\
# =============================================================================
# DEPRECATED — COMPATIBILITY ONLY
# This agent has been superseded by: {replacement}
# as part of the modular enrichment refactor (feature/modular-company-intelligence-refactor).
#
# STATUS: Removed from AgentOrchestrator execution path. Retained for:
#   - Regression comparison during migration safety period
#   - Import compatibility with any external scripts still using this class
#
# DO NOT extend or add new logic here. Use the replacement module above.
# This file will be removed after migration safety period ends.
# =============================================================================
"""

stamped = []
skipped = []

for fname, replacement in DEPRECATION_MAP.items():
    fpath = os.path.join(AGENTS_DIR, fname)
    if not os.path.exists(fpath):
        skipped.append(fname)
        continue

    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    # Idempotent — don't re-stamp if already done
    if "DEPRECATED — COMPATIBILITY ONLY" in content:
        skipped.append(f"{fname} (already stamped)")
        continue

    header = DEPRECATED_HEADER_TMPL.format(replacement=replacement)
    new_content = header + content

    with open(fpath, "w", encoding="utf-8") as f:
        f.write(new_content)

    stamped.append(fname)

print(f"✅ Stamped {len(stamped)} legacy agents:")
for f in stamped:
    print(f"   • {f}")

if skipped:
    print(f"\n⏭️  Skipped {len(skipped)}:")
    for f in skipped:
        print(f"   • {f}")
