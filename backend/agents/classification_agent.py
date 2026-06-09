import os
import json
from backend.agents.base import BaseAgent
from backend.models.startup_state import StartupState
from backend.agents.utils import call_ollama, get_rag_context

TAXONOMY_PATH = "backend/config/startup_taxonomy.json"

class ClassificationAgent(BaseAgent):
    def run(self, state: StartupState) -> StartupState:
        self.log_audit(state, "Starting Classification process...")
        
        try:
            # 1. Load taxonomy JSON
            taxonomy_str = "{}"
            if os.path.exists(TAXONOMY_PATH):
                with open(TAXONOMY_PATH, "r") as f:
                    taxonomy_str = f.read()
                    
            # 2. Get RAG context for sector classifications
            rag_context = get_rag_context(state.startup_name, category_filter="Knowledge", top_k=2)
            
            prompt = f"""You are a precise startup classification engine.
Your task is to classify the startup '{state.startup_name}' using standard corporate sector mappings.

Start by reviewing the ICICI Group Master Taxonomy JSON:
{taxonomy_str}

Use the RAG Reference Context:
{rag_context}

Startup Description / Article details:
Headline: {state.article_data.get('headline', '')}
Summary: {state.article_data.get('description', '')}

Based on these details, classify this company under exactly one Industry, one primary Sector, and one Subsector from the Taxonomy.
Identify all applicable business models (e.g. B2B, SaaS, B2C, Marketplace, Transaction-Based) and relevant tags.

Return ONLY a valid JSON object matching the schema below. Do not add markdown wrappers (no ```json code blocks), notes, or explanations.

JSON Schema:
{{
  "industry": "Financial Services",
  "sector": "FinTech",
  "subsector": "Lending",
  "business_models": ["B2B", "SaaS"],
  "tags": ["retail-lending", "credit-scoring"]
}}
"""
            classification = call_ollama(prompt, json_format=True)
            
            # 3. Populate state features
            state.startup_features.industry = classification.get("industry") or "Financial Services"
            state.startup_features.sector = classification.get("sector") or "Unknown"
            state.startup_features.subsector = classification.get("subsector") or "Unknown"
            state.startup_features.business_models = classification.get("business_models") or []
            state.startup_features.tags = classification.get("tags") or []
            
            # Store full classification under state metadata or logs
            self.log_audit(
                state, 
                f"Classified '{state.startup_name}' under Industry: '{state.startup_features.industry}', Sector: '{state.startup_features.sector}', Subsector: '{state.startup_features.subsector}'",
                metadata={
                    "classification": classification
                }
            )

        except Exception as e:
            state.errors.append(f"ClassificationAgent failed: {str(e)}")
            self.log_audit(state, f"ClassificationAgent failed: {str(e)}", metadata={"error": True})

        return state
