import os
import re
import json
import requests
import traceback

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = "nomic-embed-text"

def build_configs():
    print("🛠️ Creating directories...")
    os.makedirs("backend/config", exist_ok=True)
    os.makedirs("backend/knowledge/vector_index", exist_ok=True)

    # 1. Generate startup_taxonomy.json from docs/startup_sector_mappings.json
    taxonomy_src = "docs/startup_sector_mappings.json"
    taxonomy_dest = "backend/config/startup_taxonomy.json"
    if os.path.exists(taxonomy_src):
        with open(taxonomy_src, "r") as sf:
            tax_data = json.load(sf)
        with open(taxonomy_dest, "w") as df:
            json.dump(tax_data, df, indent=2)
        print(f"✅ Generated {taxonomy_dest}")
    else:
        # Fallback empty structure if source not found
        with open(taxonomy_dest, "w") as df:
            json.dump({"industries": [], "business_models": [], "industry_relevance": []}, df, indent=2)
        print(f"⚠️ Source taxonomy not found. Generated empty {taxonomy_dest}")

    # 2. Generate business_problems.json
    business_problems = {
      "problems": [
        # ICICI Bank
        {
          "problem_id": "Acquisition_Cost",
          "problem_name": "Rising acquisition costs",
          "entity": "ICICI Bank",
          "business_team": "Retail Banking",
          "keywords": ["acquisition", "onboarding cost", "customer conversion", "CAC"],
          "priority": "High",
          "startup_categories": ["Digital Banking", "Neobanking", "RegTech", "Document AI"]
        },
        {
          "problem_id": "Digital_Onboarding_Friction",
          "problem_name": "Digital onboarding friction",
          "entity": "ICICI Bank",
          "business_team": "Retail Banking",
          "keywords": ["onboarding", "KYC", "e-KYC", "friction", "drop-off"],
          "priority": "High",
          "startup_categories": ["RegTech", "Document AI", "Identity Security"]
        },
        {
          "problem_id": "Credit_Risk_Assessment",
          "problem_name": "Credit risk assessment",
          "entity": "ICICI Bank",
          "business_team": "Lending",
          "keywords": ["credit risk", "risk assessment", "underwriting", "credit score", "scoring"],
          "priority": "High",
          "startup_categories": ["Lending", "Alternative Data", "Data Analytics"]
        },
        {
          "problem_id": "Lending_Fraud",
          "problem_name": "Fraudulent lending applications",
          "entity": "ICICI Bank",
          "business_team": "Lending",
          "keywords": ["fraud", "identity theft", "fake docs", "impersonation"],
          "priority": "High",
          "startup_categories": ["Fraud Detection", "Cybersecurity", "RegTech"]
        },
        {
          "problem_id": "Collection_Inefficiency",
          "problem_name": "Collection inefficiencies",
          "entity": "ICICI Bank",
          "business_team": "Lending",
          "keywords": ["collections", "delinquency", "recovery", "dunning", "repayment"],
          "priority": "Medium",
          "startup_categories": ["Collections", "Agentic AI", "Data Analytics"]
        },
        {
          "problem_id": "Payment_Reconciliation",
          "problem_name": "Payment reconciliation",
          "entity": "ICICI Bank",
          "business_team": "Payments",
          "keywords": ["reconciliation", "settlement", "payment flow", "ledger"],
          "priority": "Medium",
          "startup_categories": ["Payments", "UPI Infrastructure", "TaxTech"]
        },
        {
          "problem_id": "Information_Security",
          "problem_name": "Cyber threats and Data leakage",
          "entity": "ICICI Bank",
          "business_team": "Information Security",
          "keywords": ["cybersecurity", "threat detection", "data leak", "malware", "phishing", "zero trust"],
          "priority": "High",
          "startup_categories": ["Cybersecurity", "AI Infrastructure"]
        },
        # ICICI Lombard
        {
          "problem_id": "Claims_Fraud",
          "problem_name": "Claims leakage and fraud",
          "entity": "ICICI Lombard",
          "business_team": "Claims",
          "keywords": ["claims fraud", "insurance leak", "fake claims", "fraudulent claims"],
          "priority": "High",
          "startup_categories": ["Claims Automation", "Fraud Detection", "Risk Analytics"]
        },
        {
          "problem_id": "Claims_Processing_Speed",
          "problem_name": "Slow claims processing and customer dissatisfaction",
          "entity": "ICICI Lombard",
          "business_team": "Claims",
          "keywords": ["claims processing", "payout", "settle claim", "customer satisfaction"],
          "priority": "High",
          "startup_categories": ["Claims Automation", "Document AI", "Generative AI"]
        },
        {
          "problem_id": "Underwriting_Accuracy",
          "problem_name": "Risk assessment accuracy and pricing optimization",
          "entity": "ICICI Lombard",
          "business_team": "Underwriting",
          "keywords": ["underwriting", "pricing", "risk model", "actuarial", "loss ratio"],
          "priority": "High",
          "startup_categories": ["Risk Analytics", "Data Analytics", "Alternative Data"]
        },
        {
          "problem_id": "Lombard_Distribution",
          "problem_name": "Customer acquisition and agent productivity",
          "entity": "ICICI Lombard",
          "business_team": "Distribution",
          "keywords": ["agent productivity", "acquisition", "distribution", "leads"],
          "priority": "Medium",
          "startup_categories": ["Insurance Distribution", "Agentic AI"]
        },
        # ICICI Securities
        {
          "problem_id": "Investor_Acquisition_Securities",
          "problem_name": "Low investor participation and high CAC",
          "entity": "ICICI Securities",
          "business_team": "Investor Acquisition",
          "keywords": ["investor acquisition", "trading conversion", "brokerage onboarding"],
          "priority": "High",
          "startup_categories": ["Stock Broking", "WealthTech", "Investment Platforms"]
        },
        {
          "problem_id": "Advisory_Scalability",
          "problem_name": "Limited advisor scalability and generic recommendations",
          "entity": "ICICI Securities",
          "business_team": "Wealth Advisory",
          "keywords": ["personalized advisory", "portfolio management", "wealth advisor", "robo advisory"],
          "priority": "High",
          "startup_categories": ["WealthTech", "Generative AI", "Capital Markets Tech"]
        },
        {
          "problem_id": "User_Dormancy",
          "problem_name": "Dormant users and low trading activity",
          "entity": "ICICI Securities",
          "business_team": "Investor Engagement",
          "keywords": ["dormancy", "trading activity", "retention", "user engagement"],
          "priority": "Medium",
          "startup_categories": ["Investment Platforms", "Agentic AI", "Financial Wellness"]
        },
        # ICICI Home Finance
        {
          "problem_id": "Mortgage_Acquisition",
          "problem_name": "Lead generation and customer conversion for home loans",
          "entity": "ICICI Home Finance",
          "business_team": "Mortgage Acquisition",
          "keywords": ["mortgage", "home loan", "lead generation", "loan funnel"],
          "priority": "High",
          "startup_categories": ["Mortgage Tech", "PropTech", "Lending"]
        },
        {
          "problem_id": "HFC_Underwriting",
          "problem_name": "Credit assessment quality and underwriting delays",
          "entity": "ICICI Home Finance",
          "business_team": "Credit Assessment",
          "keywords": ["property valuation", "credit quality", "underwriting delay", "loan processing"],
          "priority": "High",
          "startup_categories": ["Mortgage Tech", "Alternative Data", "Document AI"]
        },
        # ICICI Prudential Life
        {
          "problem_id": "Life_Distribution",
          "problem_name": "Agent productivity and conversion rates",
          "entity": "ICICI Prudential Life",
          "business_team": "Distribution",
          "keywords": ["agent productivity", "policy sale", "lead conversion", "bancassurance"],
          "priority": "High",
          "startup_categories": ["Insurance Distribution", "Agentic AI", "Generative AI"]
        },
        {
          "problem_id": "Policy_Lapse_Persistency",
          "problem_name": "Policy lapses and customer disengagement",
          "entity": "ICICI Prudential Life",
          "business_team": "Persistency",
          "keywords": ["policy lapse", "persistency", "renewal", "retention"],
          "priority": "High",
          "startup_categories": ["Risk Analytics", "Data Analytics", "Agentic AI"]
        },
        # ICICI Prudential AMC
        {
          "problem_id": "AMC_Investor_Acquisition",
          "problem_name": "Limited new investors and digital acquisition challenges",
          "entity": "ICICI Prudential AMC",
          "business_team": "Investor Acquisition",
          "keywords": ["mutual fund onboarding", "SIP growth", "AUM", "digital acquisition"],
          "priority": "High",
          "startup_categories": ["WealthTech", "Investment Platforms", "RegTech"]
        },
        {
          "problem_id": "SIP_Discontinuation",
          "problem_name": "SIP discontinuation and investor inactivity",
          "entity": "ICICI Prudential AMC",
          "business_team": "Investor Retention",
          "keywords": ["SIP lapse", "investor churn", "mutual fund redemption"],
          "priority": "High",
          "startup_categories": ["Data Analytics", "Agentic AI", "Financial Wellness"]
        }
      ]
    }
    with open("backend/config/business_problems.json", "w") as f:
        json.dump(business_problems, f, indent=2)
    print("✅ Generated backend/config/business_problems.json")

    # 3. Generate opportunity_matrix.json
    opportunity_matrix = {
      "GenAI Copilots": {"Bank": 10, "Lombard": 8, "Securities": 8, "HFC": 7, "Pru Life": 8, "AMC": 7},
      "Cybersecurity": {"Bank": 10, "Lombard": 10, "Securities": 10, "HFC": 9, "Pru Life": 10, "AMC": 9},
      "Fraud Detection": {"Bank": 10, "Lombard": 9, "Securities": 8, "HFC": 8, "Pru Life": 7, "AMC": 6},
      "Claims Automation": {"Bank": 2, "Lombard": 10, "Securities": 1, "HFC": 1, "Pru Life": 8, "AMC": 1},
      "WealthTech": {"Bank": 5, "Lombard": 2, "Securities": 10, "HFC": 1, "Pru Life": 7, "AMC": 10},
      "RetirementTech": {"Bank": 2, "Lombard": 1, "Securities": 6, "HFC": 1, "Pru Life": 10, "AMC": 9},
      "MortgageTech": {"Bank": 4, "Lombard": 1, "Securities": 1, "HFC": 10, "Pru Life": 1, "AMC": 1},
      "PropTech": {"Bank": 3, "Lombard": 2, "Securities": 1, "HFC": 10, "Pru Life": 1, "AMC": 1},
      "LendingTech": {"Bank": 10, "Lombard": 2, "Securities": 2, "HFC": 8, "Pru Life": 1, "AMC": 1},
      "RegTech": {"Bank": 10, "Lombard": 10, "Securities": 9, "HFC": 8, "Pru Life": 9, "AMC": 8},
      "Data Analytics": {"Bank": 9, "Lombard": 9, "Securities": 8, "HFC": 8, "Pru Life": 8, "AMC": 8},
      "Document AI": {"Bank": 9, "Lombard": 9, "Securities": 8, "HFC": 8, "Pru Life": 8, "AMC": 7},
      "HealthTech": {"Bank": 3, "Lombard": 9, "Securities": 1, "HFC": 1, "Pru Life": 8, "AMC": 1},
      "Embedded Insurance": {"Bank": 2, "Lombard": 10, "Securities": 1, "HFC": 1, "Pru Life": 9, "AMC": 1},
      "Financial Wellness": {"Bank": 6, "Lombard": 2, "Securities": 8, "HFC": 2, "Pru Life": 9, "AMC": 8},
      "MSME SaaS": {"Bank": 9, "Lombard": 3, "Securities": 1, "HFC": 2, "Pru Life": 1, "AMC": 1},
      "TradeTech": {"Bank": 9, "Lombard": 1, "Securities": 3, "HFC": 1, "Pru Life": 1, "AMC": 1},
      "Alternative Data": {"Bank": 8, "Lombard": 8, "Securities": 8, "HFC": 8, "Pru Life": 7, "AMC": 6},
      "Decision Intelligence": {"Bank": 9, "Lombard": 9, "Securities": 8, "HFC": 7, "Pru Life": 8, "AMC": 7},
      "Climate Risk": {"Bank": 6, "Lombard": 9, "Securities": 2, "HFC": 4, "Pru Life": 2, "AMC": 3}
    }
    with open("backend/config/opportunity_matrix.json", "w") as f:
        json.dump(opportunity_matrix, f, indent=2)
    print("✅ Generated backend/config/opportunity_matrix.json")

    # 4. Generate strategic_fit.json
    strategic_fit = {
      "weights": {
        "business_problem_relevance": 25,
        "entity_alignment": 15,
        "business_team_alignment": 10,
        "deployability": 15,
        "market_validation": 10,
        "innovation_differentiation": 5,
        "scalability": 5,
        "strategic_investment_potential": 5,
        "ecosystem_influence": 5
      },
      "bands": [
        {"min": 0, "max": 30, "label": "Low Strategic Fit", "action": "Ignore"},
        {"min": 31, "max": 50, "label": "Moderate Strategic Fit", "action": "Monitor"},
        {"min": 51, "max": 70, "label": "Good Strategic Fit", "action": "Founder Meeting"},
        {"min": 71, "max": 85, "label": "High Strategic Fit", "action": "Business Introduction"},
        {"min": 86, "max": 95, "label": "Very High Strategic Fit", "action": "POC"},
        {"min": 96, "max": 100, "label": "Exceptional Strategic Fit", "action": "Strategic Investment Review"}
      ]
    }
    with open("backend/config/strategic_fit.json", "w") as f:
        json.dump(strategic_fit, f, indent=2)
    print("✅ Generated backend/config/strategic_fit.json")

    # 5. Generate relevance_scoring.json
    relevance_scoring = {
      "weights": {
        "strategic_relevance": 40,
        "deployability": 20,
        "traction": 15,
        "growth_signals": 10,
        "team_quality": 10,
        "funding_signals": 5
      }
    }
    with open("backend/config/relevance_scoring.json", "w") as f:
        json.dump(relevance_scoring, f, indent=2)
    print("✅ Generated backend/config/relevance_scoring.json")

    # 6. Generate startup_signal_framework.json
    startup_signal_framework = {
      "positive_signals": {
        "enterprise_customer_wins": 10,
        "revenue_growth": 10,
        "product_adoption": 9,
        "strategic_partnerships": 9,
        "geographic_expansion": 8,
        "leadership_hiring": 7,
        "funding_round": 6,
        "accelerator_participation": 5,
        "patent_activity": 5,
        "awards_recognition": 3
      },
      "negative_signals": {
        "leadership_exits": -5,
        "layoffs": -6,
        "regulatory_issues": -9,
        "product_failure": -8,
        "major_customer_loss": -8,
        "data_breach": -10
      },
      "bands": [
        {"min": -100, "max": 20, "label": "Weak Momentum"},
        {"min": 21, "max": 40, "label": "Moderate Momentum"},
        {"min": 41, "max": 60, "label": "Strong Momentum"},
        {"min": 61, "max": 200, "label": "Exceptional Momentum"}
      ]
    }
    with open("backend/config/startup_signal_framework.json", "w") as f:
        json.dump(startup_signal_framework, f, indent=2)
    print("✅ Generated backend/config/startup_signal_framework.json")

    # 7. Generate action_framework.json
    action_framework = {
      "decision_matrix": [
        {"strategic_fit": "Low", "deployability": "Low", "action": "Ignore"},
        {"strategic_fit": "Medium", "deployability": "Low", "action": "Monitor"},
        {"strategic_fit": "Medium", "deployability": "Medium", "action": "Founder Meeting"},
        {"strategic_fit": "High", "deployability": "Medium", "action": "Business Introduction"},
        {"strategic_fit": "High", "deployability": "High", "action": "POC"},
        {"strategic_fit": "Very High", "deployability": "High", "action": "Strategic Investment Review"},
        {"strategic_fit": "Exceptional", "deployability": "High", "action": "Strategic Investment Review"}
      ]
    }
    with open("backend/config/action_framework.json", "w") as f:
        json.dump(action_framework, f, indent=2)
    print("✅ Generated backend/config/action_framework.json")

    # 8. Generate scoring_weights.json
    scoring_weights = {
      "relevance_weight": 0.40,
      "strategic_fit_weight": 0.35,
      "signal_weight": 0.25
    }
    with open("backend/config/scoring_weights.json", "w") as f:
        json.dump(scoring_weights, f, indent=2)
    print("✅ Generated backend/config/scoring_weights.json")

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def chunk_document(filepath, category):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"⚠️ Failed to read {filepath}: {e}")
        return []

    # Clean the content slightly, keeping sections
    lines = content.split("\n")
    sections = []
    current_section = []
    current_header = "Introduction"

    for line in lines:
        if line.startswith("#"):
            if current_section:
                sections.append((current_header, "\n".join(current_section)))
                current_section = []
            current_header = line.strip("# ")
        current_section.append(line)

    if current_section:
        sections.append((current_header, "\n".join(current_section)))

    chunks = []
    chunk_size = 1000
    overlap = 150

    for header, sect_content in sections:
        sect_content = clean_text(sect_content)
        if len(sect_content) <= chunk_size:
            chunks.append({
                "header": header,
                "content": sect_content,
                "filepath": filepath,
                "category": category
            })
        else:
            # Sliding window chunking
            start = 0
            while start < len(sect_content):
                end = start + chunk_size
                # If we are near the end, take the remaining slice
                if end >= len(sect_content):
                    chunk_text = sect_content[start:]
                    start = len(sect_content)
                else:
                    # Look for spaces to cut cleanly
                    cut = sect_content.rfind(" ", start, end)
                    if cut != -1 and cut > start + chunk_size // 2:
                        chunk_text = sect_content[start:cut]
                        start = cut - overlap
                    else:
                        chunk_text = sect_content[start:end]
                        start = end - overlap
                
                if len(chunk_text.strip()) > 50:
                    chunks.append({
                        "header": header,
                        "content": chunk_text.strip(),
                        "filepath": filepath,
                        "category": category
                    })
    return chunks

def build_vector_index():
    print("📝 Indexing documentation files recursively...")
    doc_dirs = {
        "docs/context": "Context",
        "docs/ethos": "Ethos",
        "docs/knowledge": "Knowledge",
        "docs/scoring": "Scoring",
        "docs/architecture": "Architecture"
    }

    all_chunks = []
    for directory, category in doc_dirs.items():
        if not os.path.exists(directory):
            print(f"⚠️ Directory {directory} does not exist. Skipping.")
            continue
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".md"):
                    filepath = os.path.join(root, file)
                    print(f"   Parsing {filepath} ({category})")
                    all_chunks.extend(chunk_document(filepath, category))

    print(f"📊 Created {len(all_chunks)} chunks. Generating embeddings...")

    vector_db = []
    failed_count = 0

    for idx, chunk in enumerate(all_chunks):
        try:
            print(f"   [{idx + 1}/{len(all_chunks)}] Embedding chunk from: {os.path.basename(chunk['filepath'])}")
            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": chunk["content"]
                },
                timeout=15.0
            )
            resp.raise_for_status()
            embedding = resp.json().get("embedding")
            if embedding:
                vector_db.append({
                    "id": idx,
                    "category": chunk["category"],
                    "filepath": chunk["filepath"],
                    "header": chunk["header"],
                    "content": chunk["content"],
                    "embedding": embedding
                })
            else:
                print(f"   ⚠️ No embedding returned for chunk {idx}")
                failed_count += 1
        except Exception as e:
            print(f"   ⚠️ Failed to get embedding for chunk {idx}: {e}")
            failed_count += 1

    if vector_db:
        index_path = "backend/knowledge/vector_index/rag_embeddings.json"
        with open(index_path, "w") as f:
            json.dump(vector_db, f)
        print(f"🏆 RAG Vector Index successfully compiled with {len(vector_db)} vectors saved to {index_path}!")
    else:
        print("❌ FAILED to compile any embeddings.")

    if failed_count > 0:
        print(f"⚠️ Warning: {failed_count} chunks failed to embed.")

if __name__ == "__main__":
    try:
        build_configs()
        build_vector_index()
    except Exception as e:
        print(f"💥 Compilation failed with fatal error: {e}")
        traceback.print_exc()
