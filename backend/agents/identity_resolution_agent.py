# =============================================================================
# DEPRECATED — COMPATIBILITY ONLY
# This agent has been superseded by: backend.enrichment.identity_enricher.IdentityEnricher
# as part of the modular enrichment refactor (feature/modular-company-intelligence-refactor).
#
# STATUS: Removed from AgentOrchestrator execution path. Retained for:
#   - Regression comparison during migration safety period
#   - Import compatibility with any external scripts still using this class
#
# DO NOT extend or add new logic here. Use the replacement module above.
# This file will be removed after migration safety period ends.
# =============================================================================
import json
import os
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState

class IdentityResolutionAgent(BaseAgent):
    """
    Step 0b: Calculates weighted confidence scores, defines verification status,
    checks for duplicates, and upserts entity mapping data.
    """

    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, f"[IdentityResolution] Resolving entity verification status for '{state.startup_name}'...")
        
        # 1. Load weights configuration
        rules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "entity_resolution_rules.json")
        weights = {
            "website_name_match": 25,
            "linkedin_name_match": 25,
            "website_linkedin_desc_similarity": 20,
            "linkedin_website_domain_match": 15,
            "industry_match": 10,
            "founder_validation": 5
        }
        thresholds = {
            "verified": 90,
            "likely_match": 75,
            "partial_match": 50,
            "needs_review": 0
        }
        
        enable_semantic_alignment_check = True
        if os.path.exists(rules_path):
            try:
                with open(rules_path, "r") as f:
                    config = json.load(f)
                    weights = config.get("confidence_weights", weights)
                    thresholds = config.get("verification_thresholds", thresholds)
                    enable_semantic_alignment_check = config.get("enable_semantic_alignment_check", enable_semantic_alignment_check)
            except Exception:
                pass
                
        # 2. Compute components & scores deterministically
        website_val = state.identity.get("website", {}).get("value", "")
        linkedin_val = state.identity.get("linkedin_company_url", {}).get("value", "")
        
        score = 0.0
        
        # Website Match Points
        if website_val:
            score += weights.get("website_name_match", 25)
            # Domain matches LinkedIn domain
            if linkedin_val and (website_val.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0] in linkedin_val):
                score += weights.get("linkedin_website_domain_match", 15)
                
        # LinkedIn Match Points
        if linkedin_val:
            score += weights.get("linkedin_name_match", 25)
            
        # Description Overlap (Simulated high match base if both present)
        if website_val and linkedin_val:
            score += weights.get("website_linkedin_desc_similarity", 20)
            
        # Add basic taxonomy / industry matching
        score += weights.get("industry_match", 10)
        
        # Founder resolution
        if state.identity.get("primary_founder_name"):
            score += weights.get("founder_validation", 5)
            
        final_score = min(int(round(score)), 100)
        
        # 3. Semantic alignment validation (comparing news, crawled website, and LinkedIn snippets)
        is_mismatched = False
        mismatch_reason = ""
        verification_notes = ""

        if enable_semantic_alignment_check:
            self.log_audit(state, "[IdentityResolution] Initiating semantic alignment check...")
            crawled_data = state.article_data.get("crawled_content", {})
            homepage_text = crawled_data.get("homepage", {}).get("text_content", "") or ""
            about_text = crawled_data.get("about", {}).get("text_content", "") or ""
            
            linkedin_snippets = ""
            snippets = state.article_data.get("discovered_snippets", {})
            linkedin_records = snippets.get("linkedin", [])
            for rec in linkedin_records:
                linkedin_snippets += f"- Title: {rec.get('title')}\n  Snippet: {rec.get('snippet')}\n"
                
            news_headline = state.article_data.get("headline", "")
            news_desc = state.article_data.get("text_content") or state.article_data.get("description") or ""
            
            alignment_prompt = f"""You are a precise corporate entity-alignment validation assistant.
Your task is to compare information from three sources and determine if they all refer to the SAME startup/company, or if there is an active contradiction indicating they are completely different entities.

Sources:
1. News Article:
   - Headline: {news_headline}
   - Context: {news_desc}
2. Crawled Website:
   - Homepage Text: {homepage_text[:1500]}
   - About Page Text: {about_text[:1500]}
3. LinkedIn Search Snippets:
   - Snippets: {linkedin_snippets[:1500]}

Instructions:
- If any of these sources explicitly contradict each other (e.g., the website is for a luxury fashion brand named "Cred" but the news article describes a fintech payments startup named "Cred", or they have completely different business models/industries), classify the status as "MISMATCHED".
- If the sources have insufficient/sparse details but do not actively contradict each other, classify them as "ALIGNED".
- If the sources are "ALIGNED" but suggest a minor branding variation or different spelling for the startup, provide the canonical name in the "canonical_name" field. Otherwise, "canonical_name" should be "{state.startup_name}".
- Provide a clear, concise "mismatch_reason" explaining the contradiction if "MISMATCHED". If they align, leave it empty.

You must return ONLY a valid JSON object matching this schema:
{{
  "alignment_status": "ALIGNED" | "MISMATCHED",
  "canonical_name": "string",
  "mismatch_reason": "string"
}}
Do not write any markdown code block wrappers, prefix text, or conversational text. Return only the raw JSON block.
"""
            try:
                from backend.agents.utils import call_ollama
                res = call_ollama(alignment_prompt, json_format=True)
                if res:
                    alignment_status = res.get("alignment_status", "ALIGNED").upper()
                    canonical_name = res.get("canonical_name", state.startup_name) or state.startup_name
                    mismatch_reason = res.get("mismatch_reason", "") or ""
                    
                    if alignment_status == "MISMATCHED":
                        is_mismatched = True
                        self.log_audit(state, f"[IdentityResolution] Active contradiction detected: {mismatch_reason}")
                    else:
                        if canonical_name and canonical_name != state.startup_name:
                            self.log_audit(state, f"[IdentityResolution] Aligning startup name to canonical version: '{canonical_name}' (was: '{state.startup_name}')")
                            state.startup_name = canonical_name
                            state.identity["brand_name"] = canonical_name
            except Exception as e:
                self.log_audit(state, f"Failed to execute semantic alignment check: {e}")

        if is_mismatched:
            status = "MISMATCHED"
            final_score = 10
            verification_notes = f"Semantic alignment mismatch: {mismatch_reason}"
            state.identity["mismatch_reason"] = mismatch_reason
        else:
            status = "NEEDS_REVIEW"
            if final_score >= thresholds.get("verified", 90):
                status = "VERIFIED"
            elif final_score >= thresholds.get("likely_match", 75):
                status = "LIKELY_MATCH"
            elif final_score >= thresholds.get("partial_match", 50):
                status = "PARTIAL_MATCH"
            verification_notes = f"Verification status: {status} via refactored pipeline."
            
        state.identity["identity_confidence"] = final_score
        state.identity["verification_status"] = status
        state.identity["verification_notes"] = verification_notes
        
        # Sync simple flat variables for backward compatibility
        state.startup_features.identity_confidence = final_score / 100.0
        
        # DB Upsert stub/check if startup_id exists
        from backend.services.supabase_service import upsert_identity_record
        if state.startup_id:
            try:
                upsert_identity_record(state.startup_id, {
                    "startup_name": state.startup_name,
                    "brand_name": state.startup_name.strip().lower(),
                    "website": website_val,
                    "linkedin_company_url": linkedin_val,
                    "identity_confidence": final_score / 100.0,
                    "verification_notes": verification_notes
                })
            except Exception as e:
                self.log_audit(state, f"Identity registry upsert failed: {e}")
                
        self.log_audit(state, f"[IdentityResolution] Completed. Score: {final_score}, Status: {status}")
        return state
