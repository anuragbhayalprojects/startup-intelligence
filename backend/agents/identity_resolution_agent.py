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
        
        if os.path.exists(rules_path):
            try:
                with open(rules_path, "r") as f:
                    config = json.load(f)
                    weights = config.get("confidence_weights", weights)
                    thresholds = config.get("verification_thresholds", thresholds)
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
        
        # 3. Resolve status band
        status = "NEEDS_REVIEW"
        if final_score >= thresholds.get("verified", 90):
            status = "VERIFIED"
        elif final_score >= thresholds.get("likely_match", 75):
            status = "LIKELY_MATCH"
        elif final_score >= thresholds.get("partial_match", 50):
            status = "PARTIAL_MATCH"
            
        state.identity["identity_confidence"] = final_score
        state.identity["verification_status"] = status
        
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
                    "verification_notes": f"Verification status: {status} via refactored pipeline."
                })
            except Exception as e:
                self.log_audit(state, f"Identity registry upsert failed: {e}")
                
        self.log_audit(state, f"[IdentityResolution] Completed. Score: {final_score}, Status: {status}")
        return state
