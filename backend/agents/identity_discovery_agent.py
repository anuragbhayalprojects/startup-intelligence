"""
identity_discovery_agent.py
---------------------------
Step 0a in the agent orchestrator.

Discovers the authoritative identity attributes of a startup using the
registry-first waterfall strategy:
  1. startup_identity table (DB registry)
  2. CANONICAL_OVERLOADS / taxonomy_mapper
  3. website_resolver (known domains → AI-extracted → inferred)
  4. linkedin_resolver (known slugs → search)
  5. leadership_resolver (known founders → analysis_json → search)

Writes the resolved identity into state.identity and updates
state.startup_features with the canonical fields.

Does NOT make AI/LLM calls — all resolution is deterministic.
"""

import re
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.utils.website_resolver import resolve_website
from backend.utils.linkedin_resolver import resolve_linkedin_company_url
from backend.utils.leadership_resolver import resolve_founders


class IdentityDiscoveryAgent(BaseAgent):
    """Resolves startup identity attributes without LLM inference."""

    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, f"[IdentityDiscovery] Starting for '{state.startup_name}'...")

        try:
            startup_id = state.startup_id
            name = state.startup_name
            existing_website = state.article_data.get("enriched_raw", {}).get("resolved_website", "")
            analysis_json = state.article_data.get("analysis_json", {})

            # ----------------------------------------------------------------
            # 1. Resolve website
            # ----------------------------------------------------------------
            website = resolve_website(
                brand_name=name,
                extracted_website=existing_website or analysis_json.get("startup_website", ""),
                startup_id=startup_id,
                skip_registry=False,
            )

            # ----------------------------------------------------------------
            # 2. Resolve LinkedIn company URL
            # ----------------------------------------------------------------
            linkedin_url = resolve_linkedin_company_url(
                brand_name=name,
                startup_id=startup_id,
                skip_registry=False,
            )

            # ----------------------------------------------------------------
            # 3. Resolve founders/leadership
            # ----------------------------------------------------------------
            leadership = resolve_founders(
                brand_name=name,
                analysis_json=analysis_json,
                startup_id=startup_id,
                skip_registry=False,
            )
            primary_founder = leadership[0] if leadership else {}

            # ----------------------------------------------------------------
            # 3.5 Discover Legal Name from website About/Terms/Privacy
            # ----------------------------------------------------------------
            legal_name = ""
            if website and "example.com" not in website:
                try:
                    import requests
                    from bs4 import BeautifulSoup
                    
                    # Normalize URL
                    web_url = website if website.startswith("http") else "https://" + website
                    paths = ["", "/about", "/terms", "/privacy", "/about-us", "/terms-of-use", "/privacy-policy"]
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                    legal_pattern = re.compile(r'\b([A-Z][a-zA-Z\s,]{3,50}?\s+(?:Pvt\.?\s*Ltd\.?|Private\s+Limited|Inc\.?|LLC))\b')
                    
                    for path in paths:
                        url = web_url.rstrip("/") + path
                        try:
                            # Short timeout to keep pipeline responsive
                            response = requests.get(url, headers=headers, timeout=2.5, allow_redirects=True)
                            if response.status_code == 200:
                                soup = BeautifulSoup(response.text, "html.parser")
                                # Remove scripts/styles
                                for element in soup(["script", "style"]):
                                    element.decompose()
                                page_text = soup.get_text()
                                
                                match = legal_pattern.search(page_text)
                                if match:
                                    extracted = match.group(1).strip()
                                    extracted = re.sub(r'\s+', ' ', extracted)
                                    if len(extracted.split()) <= 6:
                                        legal_name = extracted
                                        break
                        except Exception:
                            continue
                except Exception as le:
                    self.log_audit(state, f"[IdentityDiscovery] Legal name resolution error: {le}")

            # ----------------------------------------------------------------
            # 4. Compute confidence and source
            # ----------------------------------------------------------------
            evidence = 0
            source_parts = []

            if website:
                evidence += 1
                source_parts.append("website")
            if linkedin_url:
                evidence += 1
                source_parts.append("linkedin")
            if primary_founder.get("name"):
                evidence += 1
                source_parts.append("founder")
            if leadership:
                evidence += 1
                source_parts.append("leadership")

            # Determine the best source label
            identity_source = "search"
            try:
                from backend.services.supabase_service import get_identity_record
                if startup_id and get_identity_record(startup_id):
                    identity_source = "identity_registry"
                    evidence = max(evidence, 3)
            except Exception:
                pass

            if not identity_source or identity_source == "search":
                from backend.utils.website_resolver import KNOWN_DOMAINS
                name_lower = name.lower()
                if any(k in name_lower for k in KNOWN_DOMAINS):
                    identity_source = "known_domain_registry"
                else:
                    try:
                        from backend.utils.taxonomy_mapper import CANONICAL_OVERLOADS
                        if any(k in name_lower for k in CANONICAL_OVERLOADS):
                            identity_source = "canonical_overloads"
                            evidence = max(evidence, 2)
                    except Exception:
                        pass

            # Base confidence from evidence count
            from backend.utils.confidence_scorer import compute_identity_confidence
            confidence = compute_identity_confidence(
                evidence_count=evidence,
                source=identity_source,
                has_website=bool(website),
                has_linkedin=bool(linkedin_url),
                has_founder=bool(primary_founder.get("name")),
            )

            # Get founded year if available
            founded_year = None
            try:
                founded_year = int(analysis_json.get("founded_year")) if analysis_json.get("founded_year") else None
            except Exception:
                pass

            # ----------------------------------------------------------------
            # 5. Write to state.identity
            # ----------------------------------------------------------------
            state.identity.update({
                "resolved": bool(website or linkedin_url or primary_founder.get("name")),
                "brand_name": name,
                "legal_name": legal_name,
                "website": website or "",
                "linkedin_company_url": linkedin_url or "",
                "founders": leadership,
                "established_year": founded_year,
                "confidence": confidence,
                "source": identity_source,
                
                # Keep these for backward compat and UI
                "primary_founder_name": primary_founder.get("name", ""),
                "primary_founder_linkedin": primary_founder.get("linkedin_url", ""),
                "primary_founder_title": primary_founder.get("role", "Founder"),
                "leadership": leadership,
                "headquarters": state.startup_features.headquarters or "",
                "identity_confidence": confidence,
                "identity_source": identity_source,
                "evidence_count": evidence,
            })

            # ----------------------------------------------------------------
            # 6. Sync startup_features with resolved identity
            # ----------------------------------------------------------------
            if primary_founder.get("name") and state.startup_features.founder_name in ("Unknown", "", None):
                state.startup_features.founder_name = primary_founder.get("name", "Unknown")
            if primary_founder.get("linkedin_url") and not state.startup_features.founder_linkedin_url:
                state.startup_features.founder_linkedin_url = primary_founder.get("linkedin_url", "")
            if linkedin_url and not state.startup_features.linkedin_company_url:
                state.startup_features.linkedin_company_url = linkedin_url
            if leadership:
                state.startup_features.leadership = leadership
            state.startup_features.identity_confidence = confidence
            state.startup_features.identity_source = identity_source

            self.log_audit(
                state,
                f"[IdentityDiscovery] Resolved identity for '{name}'. "
                f"website={bool(website)}, linkedin={bool(linkedin_url)}, "
                f"founder={bool(primary_founder.get('name'))}, confidence={confidence:.2f}, source={identity_source}",
                metadata={
                    "confidence": confidence,
                    "source": identity_source,
                    "evidence_count": evidence,
                    "has_website": bool(website),
                    "has_linkedin": bool(linkedin_url),
                    "has_founder": bool(primary_founder.get("name")),
                }
            )

        except Exception as e:
            state.errors.append(f"IdentityDiscoveryAgent failed: {str(e)}")
            self.log_audit(state, f"[IdentityDiscovery] Failed: {str(e)}", metadata={"error": True})

        return state
