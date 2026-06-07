import os
import json
import logging
from typing import Dict, Any, List

class ScoringService:
    @staticmethod
    def calculate_priority_score(
        relevance_score: int, 
        strategic_fit_score: int, 
        deployability_score: int, 
        signal_score: int
    ) -> int:
        """
        Calculates the final overall priority score using the formula:
        priority_score = relevance_score * 0.40 + strategic_fit_score * 0.30 + deployability_score * 0.20 + signal_score * 0.10
        """
        # Relevance Gate Check (if relevance is < 50, priority is capped/bypassed)
        if relevance_score < 50:
            return relevance_score
            
        priority = (relevance_score * 0.40) + (strategic_fit_score * 0.30) + (deployability_score * 0.20) + (signal_score * 0.10)
        return int(round(priority))

    @staticmethod
    def calculate_recommendation_score(priority_score: int, confidence_score: int) -> int:
        """
        Calculates the final recommendation score using the formula:
        recommendation_score = priority_score * 0.70 + confidence_score * 0.30
        """
        rec_score = (priority_score * 0.70) + (confidence_score * 0.30)
        return int(round(rec_score))

    @staticmethod
    def map_priority_band(priority_score: int) -> str:
        """
        Maps a priority score to an operational urgency band:
        90-100 -> Critical
        80-89 -> High
        65-79 -> Medium
        50-64 -> Low
        0-49 -> Ignore
        """
        if priority_score >= 90:
            return "Critical"
        elif priority_score >= 80:
            return "High"
        elif priority_score >= 65:
            return "Medium"
        elif priority_score >= 50:
            return "Low"
        else:
            return "Ignore"

    @staticmethod
    def calculate_confidence_score(state: Any) -> int:
        """
        Calculates the confidence score (0-100) based on data completeness,
        business problem match strength, source reliability, and classification certainty.
        """
        features = state.startup_features
        article = state.article_data
        
        # 1. Data Completeness (40 Points)
        has_website = bool(features.headquarters and features.headquarters != "Unknown") or bool(article.get("enriched_raw", {}).get("resolved_website"))
        has_founder = bool(features.founder_name and features.founder_name != "Unknown")
        has_linkedin = bool(features.founder_linkedin_url)
        has_description = bool(article.get("description") and len(article.get("description")) > 10)
        has_taxonomy = bool(features.sector and features.sector != "Unknown") and bool(features.subsector and features.subsector != "Unknown")
        has_funding = bool(features.startup_stage and features.startup_stage != "Unknown")
        
        completeness_fields = [has_website, has_founder, has_linkedin, has_description, has_taxonomy, has_funding]
        completed_count = sum(1 for f in completeness_fields if f)
        
        completeness_map = {
            6: 40,
            5: 34,
            4: 27,
            3: 20,
            2: 13,
            1: 7,
            0: 0
        }
        data_completeness_score = completeness_map.get(completed_count, 0)

        # 2. Business Problem Match Strength (30 Points)
        prob_count = len(features.business_problems)
        if prob_count == 0:
            business_problem_match_score = 0
        elif prob_count == 1:
            business_problem_match_score = 10
        elif prob_count == 2:
            business_problem_match_score = 20
        else:
            business_problem_match_score = 30

        # 3. Source Reliability (20 Points)
        website_url = article.get("enriched_raw", {}).get("resolved_website", "")
        website_verified = bool(website_url and "example.com" not in website_url)
        founder_linkedin = features.founder_linkedin_url
        linkedin_verified = bool(founder_linkedin and "linkedin.com" in founder_linkedin)
        source = article.get("source", "")
        trusted_news_found = bool(source and source != "Unknown")

        source_reliability_score = 0
        if website_verified:
            source_reliability_score += 8
        if linkedin_verified:
            source_reliability_score += 6
        if trusted_news_found:
            source_reliability_score += 6

        # 4. Classification Certainty (10 Points)
        # Check classification metadata inside audit_trail
        class_certainty = 10  # Default to max certainty if not explicitly defined
        for entry in state.audit_trail:
            if "classification" in entry.get("metadata", {}):
                meta = entry["metadata"]["classification"]
                if isinstance(meta, dict) and "confidence" in meta:
                    confidence_val = meta["confidence"]
                    try:
                        confidence_val = int(confidence_val)
                        if confidence_val >= 90:
                            class_certainty = 10
                        elif confidence_val >= 80:
                            class_certainty = 8
                        elif confidence_val >= 70:
                            class_certainty = 6
                        elif confidence_val >= 60:
                            class_certainty = 4
                        else:
                            class_certainty = 2
                    except Exception:
                        pass
                break

        confidence_score = (
            data_completeness_score +
            business_problem_match_score +
            source_reliability_score +
            class_certainty
        )
        return max(0, min(100, confidence_score))

    @staticmethod
    def calculate_assignment_score(priority_score: int) -> int:
        """
        Initializes the assignment score to priority_score.
        """
        return priority_score

    @staticmethod
    def map_assignment_band(assignment_score: int) -> str:
        """
        Maps the assignment score to an assignment band:
        90-100 -> Immediate Action
        75-89 -> High Priority
        60-74 -> Medium Priority
        40-59 -> Low Priority
        Below 40 -> Watchlist
        """
        if assignment_score >= 90:
            return "Immediate Action"
        elif assignment_score >= 75:
            return "High Priority"
        elif assignment_score >= 60:
            return "Medium Priority"
        elif assignment_score >= 40:
            return "Low Priority"
        else:
            return "Watchlist"
