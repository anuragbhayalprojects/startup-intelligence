"""
identity_resolution_agent.py
-----------------------------
Step 0b in the agent orchestrator. Runs AFTER IdentityDiscoveryAgent.

Responsibilities:
  1. Reads the resolved identity from state.identity (set by Step 0a)
  2. Validates minimum confidence threshold before persisting
  3. Upserts the identity into the startup_identity table via supabase_service
  4. Detects potential duplicate startups in the DB (fuzzy name + website matching)
  5. Logs resolution quality into the audit trail

This agent does NOT make LLM calls. All operations are deterministic.
"""

from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.utils.confidence_scorer import get_confidence_band


class IdentityResolutionAgent(BaseAgent):
    """Persists resolved identity to the DB registry and checks for duplicates."""

    # Minimum confidence required to write an identity record to the DB.
    # Below this threshold, the identity is logged as uncertain and skipped.
    MIN_CONFIDENCE_TO_PERSIST = 0.30

    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, f"[IdentityResolution] Starting for '{state.startup_name}'...")

        try:
            identity = state.identity
            startup_id = state.startup_id
            confidence = identity.get("identity_confidence", 0.0)

            # ----------------------------------------------------------------
            # 1. Confidence gating
            # ----------------------------------------------------------------
            band = get_confidence_band(confidence)
            if confidence < self.MIN_CONFIDENCE_TO_PERSIST:
                self.log_audit(
                    state,
                    f"[IdentityResolution] Confidence {confidence:.2f} below threshold "
                    f"({self.MIN_CONFIDENCE_TO_PERSIST}). Identity NOT persisted.",
                    metadata={"band": band["label"], "action": band["action"]}
                )
                state.identity["persisted"] = False
                state.identity["persistence_reason"] = f"Below minimum confidence {self.MIN_CONFIDENCE_TO_PERSIST}"
                return state

            # ----------------------------------------------------------------
            # 2. Duplicate detection
            # ----------------------------------------------------------------
            potential_duplicate = None
            if startup_id:
                potential_duplicate = self._check_for_duplicate(
                    startup_id=startup_id,
                    startup_name=state.startup_name,
                    website=identity.get("website", ""),
                )

            if potential_duplicate:
                self.log_audit(
                    state,
                    f"[IdentityResolution] Potential duplicate detected: "
                    f"startup_id={potential_duplicate.get('startup_id')}, "
                    f"name='{potential_duplicate.get('startup_name')}'. Skipping persistence.",
                    metadata={"duplicate": potential_duplicate, "error": False}
                )
                state.identity["potential_duplicate_id"] = potential_duplicate.get("startup_id")
                state.identity["persisted"] = False
                state.identity["persistence_reason"] = "Potential duplicate detected"
                return state

            # ----------------------------------------------------------------
            # 3. Persist to startup_identity table
            # ----------------------------------------------------------------
            if not startup_id:
                self.log_audit(
                    state,
                    "[IdentityResolution] No startup_id in state — cannot persist identity.",
                    metadata={"error": True}
                )
                state.identity["persisted"] = False
                return state

            from backend.services.supabase_service import upsert_identity_record
            from datetime import datetime, timezone

            identity_payload = {
                "startup_name": state.startup_name,
                "brand_name": identity.get("brand_name", state.startup_name).strip().lower(),
                "website": identity.get("website", ""),
                "linkedin_company_url": identity.get("linkedin_company_url", ""),
                "primary_founder_name": identity.get("primary_founder_name", ""),
                "primary_founder_linkedin": identity.get("primary_founder_linkedin", ""),
                "primary_founder_title": identity.get("primary_founder_title", "Founder"),
                "leadership": identity.get("leadership", []),
                "headquarters": identity.get("headquarters", ""),
                "founded_year": identity.get("founded_year"),
                "founded_year_confidence": state.startup_features.founded_year_confidence or 0.0,
                "identity_confidence": confidence,
                "source": identity.get("identity_source", "search"),
                "evidence_count": identity.get("evidence_count", 0),
                "last_verified": datetime.now(timezone.utc).isoformat(),
                "verification_notes": f"Resolved by IdentityResolutionAgent. Band: {band['label']}.",
            }

            result = upsert_identity_record(startup_id, identity_payload)

            if result:
                state.identity["persisted"] = True
                state.identity["persistence_reason"] = f"Confidence {confidence:.2f} ≥ {self.MIN_CONFIDENCE_TO_PERSIST} threshold"
                self.log_audit(
                    state,
                    f"[IdentityResolution] Identity persisted for startup_id={startup_id}. "
                    f"Band: {band['label']}, Confidence: {confidence:.2f}",
                    metadata={
                        "startup_id": startup_id,
                        "confidence": confidence,
                        "band": band["label"],
                        "source": identity.get("identity_source"),
                        "evidence_count": identity.get("evidence_count"),
                    }
                )
            else:
                state.identity["persisted"] = False
                state.identity["persistence_reason"] = "Upsert returned no result (possible DB error)"
                self.log_audit(
                    state,
                    f"[IdentityResolution] Upsert returned no data for startup_id={startup_id}.",
                    metadata={"error": False}
                )

        except Exception as e:
            state.errors.append(f"IdentityResolutionAgent failed: {str(e)}")
            self.log_audit(
                state,
                f"[IdentityResolution] Unexpected error: {str(e)}",
                metadata={"error": True}
            )

        return state

    def _check_for_duplicate(
        self,
        startup_id: int,
        startup_name: str,
        website: str,
    ) -> dict | None:
        """
        Checks the startup_identity table for a matching record with:
          - A different startup_id (not self-match)
          - Same website OR highly similar name

        Returns the conflicting record or None if no duplicate is found.
        """
        try:
            from backend.services.supabase_service import supabase

            # Website exact match check (most reliable dedup signal)
            if website:
                res = supabase.table("startup_identity").select("startup_id, startup_name, website").eq("website", website).execute()
                if res.data:
                    for rec in res.data:
                        if rec.get("startup_id") != startup_id:
                            return rec

            # Name exact match (normalized)
            normalized_name = startup_name.strip().lower()
            res2 = supabase.table("startup_identity").select("startup_id, startup_name").ilike("brand_name", normalized_name).execute()
            if res2.data:
                for rec in res2.data:
                    if rec.get("startup_id") != startup_id:
                        return rec

        except Exception as e:
            print(f"⚠️ [IdentityResolution] Duplicate check failed: {e}")

        return None
