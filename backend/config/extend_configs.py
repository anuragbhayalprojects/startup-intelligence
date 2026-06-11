import json
import os

def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved {path}")

def get_taxonomy_structure():
    tax = load_json("backend/config/startup_taxonomy.json")
    print(f"[extend_configs] Loaded taxonomy from backend/config/startup_taxonomy.json")
    
    # Map sectors/subsectors to their parent industries
    sector_to_industry = {}
    subsector_to_sector = {}
    
    all_sectors = []
    all_subsectors = []
    
    for ind in tax.get("industries", []):
        ind_name = ind["name"]
        for sect_name, subs in ind.get("sectors", {}).items():
            sector_to_industry[sect_name] = ind_name
            all_sectors.append(sect_name)
            for sub in subs:
                subsector_to_sector[sub] = sect_name
                all_subsectors.append(sub)
                
    print(f"[extend_configs] Extracted {len(all_sectors)} sectors and {len(all_subsectors)} subsectors")
    return tax, sector_to_industry, subsector_to_sector, all_sectors, all_subsectors

def extend_opportunity_matrix():
    tax, sector_to_industry, subsector_to_sector, all_sectors, all_subsectors = get_taxonomy_structure()
    
    matrix = load_json("backend/config/opportunity_matrix.json")
    
    # We want to map ALL sectors and subsectors to opportunity matrix keys
    # Let's define default scoring generator based on sector/industry
    def get_scores_for_category(cat_name):
        # Resolve to sector and industry
        sect = cat_name
        if cat_name in subsector_to_sector:
            sect = subsector_to_sector[cat_name]
        
        ind = sector_to_industry.get(sect, "Other")
        
        # Default scores
        scores = {"Bank": 3, "Lombard": 2, "Securities": 2, "HFC": 2, "Pru Life": 2, "AMC": 2}
        
        if ind == "Financial Services":
            if sect == "FinTech":
                if "Lending" in cat_name or cat_name in ["Lending", "Consumer Lending", "MSME Lending", "Credit Infrastructure", "Collections"]:
                    scores = {"Bank": 10, "Lombard": 2, "Securities": 2, "HFC": 8, "Pru Life": 1, "AMC": 1}
                elif "Payment" in cat_name or cat_name in ["Payments", "UPI Infrastructure", "Cross-border Payments", "Embedded Finance"]:
                    scores = {"Bank": 10, "Lombard": 4, "Securities": 4, "HFC": 3, "Pru Life": 3, "AMC": 3}
                elif "Wealth" in cat_name or "Investment" in cat_name or cat_name in ["WealthTech", "InvestmentTech", "Stock Broking", "TreasuryTech", "TaxTech"]:
                    scores = {"Bank": 6, "Lombard": 2, "Securities": 10, "HFC": 1, "Pru Life": 7, "AMC": 10}
                elif cat_name in ["RegTech", "Fraud Detection"]:
                    scores = {"Bank": 10, "Lombard": 10, "Securities": 9, "HFC": 8, "Pru Life": 9, "AMC": 8}
                else:
                    scores = {"Bank": 8, "Lombard": 5, "Securities": 6, "HFC": 5, "Pru Life": 5, "AMC": 6}
            elif sect == "InsurTech":
                scores = {"Bank": 3, "Lombard": 10, "Securities": 1, "HFC": 1, "Pru Life": 9, "AMC": 1}
            elif sect == "Capital Markets Tech":
                scores = {"Bank": 4, "Lombard": 2, "Securities": 10, "HFC": 1, "Pru Life": 5, "AMC": 9}
        elif ind == "Artificial Intelligence":
            scores = {"Bank": 10, "Lombard": 8, "Securities": 8, "HFC": 7, "Pru Life": 8, "AMC": 7}
        elif ind == "Cybersecurity":
            scores = {"Bank": 10, "Lombard": 10, "Securities": 10, "HFC": 9, "Pru Life": 10, "AMC": 9}
        elif ind == "Healthcare & Life Sciences":
            scores = {"Bank": 3, "Lombard": 9, "Securities": 1, "HFC": 1, "Pru Life": 8, "AMC": 1}
        elif ind == "Real Estate & Construction":
            scores = {"Bank": 3, "Lombard": 2, "Securities": 1, "HFC": 10, "Pru Life": 1, "AMC": 1}
        elif ind == "Enterprise Software":
            scores = {"Bank": 9, "Lombard": 6, "Securities": 6, "HFC": 5, "Pru Life": 6, "AMC": 5}
        elif ind == "Energy & Sustainability":
            scores = {"Bank": 6, "Lombard": 9, "Securities": 2, "HFC": 4, "Pru Life": 2, "AMC": 3}
        elif ind == "Transportation & Logistics":
            if sect == "Mobility":
                scores = {"Bank": 8, "Lombard": 8, "Securities": 2, "HFC": 3, "Pru Life": 2, "AMC": 2}
            else:
                scores = {"Bank": 7, "Lombard": 5, "Securities": 2, "HFC": 2, "Pru Life": 2, "AMC": 2}
        elif ind == "Commerce & Retail":
            scores = {"Bank": 6, "Lombard": 3, "Securities": 2, "HFC": 2, "Pru Life": 2, "AMC": 2}
        elif ind == "Agriculture & Food":
            if "Finance" in cat_name or cat_name == "Agri Finance":
                scores = {"Bank": 9, "Lombard": 7, "Securities": 1, "HFC": 2, "Pru Life": 1, "AMC": 1}
            else:
                scores = {"Bank": 5, "Lombard": 8, "Securities": 1, "HFC": 1, "Pru Life": 2, "AMC": 1}
        return scores

    # Add all sectors and subsectors to opportunity matrix if not already present
    for cat in all_sectors + all_subsectors:
        if cat not in matrix:
            matrix[cat] = get_scores_for_category(cat)
            
    # Also add standard industry names
    for ind in tax.get("industries", []):
        ind_name = ind["name"]
        if ind_name not in matrix:
            # Generate generic score for industry
            scores = {"Bank": 5, "Lombard": 5, "Securities": 5, "HFC": 5, "Pru Life": 5, "AMC": 5}
            matrix[ind_name] = scores
            
    save_json("backend/config/opportunity_matrix.json", matrix)

def extend_business_problems():
    tax, sector_to_industry, subsector_to_sector, all_sectors, all_subsectors = get_taxonomy_structure()
    
    problems_data = load_json("backend/config/business_problems.json")
    problems = problems_data.get("problems", [])
    
    # Let's map categories to problems based on keyword association and logical rules
    category_to_problems = {prob["problem_id"]: set(prob.get("startup_categories", [])) for prob in problems}
    
    # We want to map ALL sectors and subsectors
    for cat in all_sectors + all_subsectors:
        cat_lower = cat.lower()
        sect = cat
        if cat in subsector_to_sector:
            sect = subsector_to_sector[cat]
        ind = sector_to_industry.get(sect, "")
        
        # 1. Map to Information_Security
        if ind == "Cybersecurity" or "security" in cat_lower or "prevention" in cat_lower:
            category_to_problems["Information_Security"].add(cat)
            
        # 2. Map to Acquisition_Cost
        if (ind in ["Commerce & Retail", "Consumer Internet", "Education"] or 
            sect in ["SaaS", "Productivity", "Future of Work", "Creator Economy", "Social Platforms", "Gaming", "TravelTech", "E-commerce", "RetailTech", "D2C Brands", "EdTech"] or
            "marketing" in cat_lower or "sales" in cat_lower or "ad" in cat_lower or "crm" in cat_lower):
            category_to_problems["Acquisition_Cost"].add(cat)
            
        # 3. Map to Digital_Onboarding_Friction
        if ("onboarding" in cat_lower or "kyc" in cat_lower or "identity" in cat_lower or 
            cat in ["RegTech", "Document AI", "Identity Security", "Authentication", "Zero Trust", "MSME SaaS"]):
            category_to_problems["Digital_Onboarding_Friction"].add(cat)
            
        # 4. Map to Credit_Risk_Assessment
        if (cat in ["Lending", "Alternative Data", "Data Analytics", "Credit Scoring", "Risk Management", "Open Banking", "Consumer Lending", "MSME Lending", "Credit Infrastructure", "TreasuryTech"] or
            ind == "Energy & Sustainability" or "climate" in cat_lower or "esg" in cat_lower or
            cat in ["Agritech", "Precision Agriculture", "Farm Management", "Agri Finance", "Farm Inputs"]):
            category_to_problems["Credit_Risk_Assessment"].add(cat)
            
        # 5. Map to Lending_Fraud
        if (cat in ["Fraud Detection", "Cybersecurity", "RegTech", "Risk Tech", "Identity Security", "Fraud Prevention", "Compliance"]):
            category_to_problems["Lending_Fraud"].add(cat)
            
        # 6. Map to Collection_Inefficiency
        if (cat in ["Collections", "Agentic AI", "Data Analytics", "Debt Recovery", "Customer Engagement", "LendingTech", "MSME Lending", "MSME SaaS", "ERP"]):
            category_to_problems["Collection_Inefficiency"].add(cat)
            
        # 7. Map to Payment_Reconciliation
        if (cat in ["Payments", "UPI Infrastructure", "TaxTech", "Accounting", "ERP", "Billing", "B2B SaaS", "Treasury Management", "Cross-border Payments", "Embedded Finance"]):
            category_to_problems["Payment_Reconciliation"].add(cat)
            
        # 8. Map to Claims_Fraud
        if (ind == "Healthcare & Life Sciences" or sect == "InsurTech" or 
            cat in ["Claims Automation", "Fraud Detection", "Risk Analytics", "Fraud Prevention", "Computer Vision", "Drones", "Commercial Drones", "Drone Analytics"]):
            category_to_problems["Claims_Fraud"].add(cat)
            
        # 9. Map to Claims_Processing_Speed
        if (cat in ["Claims Automation", "Document AI", "Generative AI", "Workflow Automation", "Text Generation", "Multimodal AI", "InsurTech"]):
            category_to_problems["Claims_Processing_Speed"].add(cat)
            
        # 10. Map to Underwriting_Accuracy
        if (sect in ["InsurTech", "Mobility", "LogisticsTech"] or
            cat in ["Risk Analytics", "Data Analytics", "Alternative Data", "Actuarial Tech", "IoT", "Industrial IoT", "Smart Cities", "Connected Devices", "Connected Vehicles", "EV Platforms", "EV Charging", "Shared Mobility", "Fleet Management", "Supply Chain Visibility", "FreightTech", "WarehouseTech"]):
            category_to_problems["Underwriting_Accuracy"].add(cat)
            
        # 11. Map to Lombard_Distribution
        if (sect in ["InsurTech", "Generative AI", "Agentic AI"] or 
            cat in ["Insurance Distribution", "SalesTech", "CRM", "MarTech", "Agentic AI", "Sales Agents", "Customer Service Agents", "Influencer Platforms", "Creator Tools"]):
            category_to_problems["Lombard_Distribution"].add(cat)
            
        # 12. Map to Investor_Acquisition_Securities
        if (cat in ["Stock Broking", "WealthTech", "Investment Platforms", "AdTech", "MarTech", "Alternative Investments", "Wealth Infrastructure"]):
            category_to_problems["Investor_Acquisition_Securities"].add(cat)
            
        # 13. Map to Advisory_Scalability
        if (cat in ["WealthTech", "Generative AI", "Capital Markets Tech", "Robo-Advisory", "Wealth Management", "Investment Platforms", "Text Generation", "Multimodal AI", "Knowledge Agents"]):
            category_to_problems["Advisory_Scalability"].add(cat)
            
        # 14. Map to User_Dormancy
        if (cat in ["Investment Platforms", "Agentic AI", "Financial Wellness", "WealthTech", "Customer Engagement", "Gamification", "MarTech"]):
            category_to_problems["User_Dormancy"].add(cat)
            
        # 15. Map to Mortgage_Acquisition
        if (cat in ["Mortgage Tech", "PropTech", "Lending", "Lead Generation", "Real Estate Tech", "Property Marketplace", "Brokerage Tech", "Rental Platforms"]):
            category_to_problems["Mortgage_Acquisition"].add(cat)
            
        # 16. Map to HFC_Underwriting
        if (cat in ["Mortgage Tech", "Alternative Data", "Document AI", "Real Estate Tech", "PropTech", "Property Management", "Smart Buildings", "Facility Management", "Construction Automation", "ConstructionTech"]):
            category_to_problems["HFC_Underwriting"].add(cat)
            
        # 17. Map to Life_Distribution
        if (sect in ["InsurTech", "Generative AI", "Agentic AI"] or 
            cat in ["Insurance Distribution", "SalesTech", "CRM", "MarTech", "Sales Agents", "Customer Service Agents"]):
            category_to_problems["Life_Distribution"].add(cat)
            
        # 18. Map to Policy_Lapse_Persistency
        if (cat in ["Risk Analytics", "Data Analytics", "Agentic AI", "Customer Retention", "CRM", "Customer Engagement", "InsurTech"]):
            category_to_problems["Policy_Lapse_Persistency"].add(cat)
            
        # 19. Map to AMC_Investor_Acquisition
        if (cat in ["WealthTech", "Investment Platforms", "RegTech", "Mutual Funds", "Asset Management", "MarTech", "Wealth Infrastructure"]):
            category_to_problems["AMC_Investor_Acquisition"].add(cat)
            
        # 20. Map to SIP_Discontinuation
        if (cat in ["Data Analytics", "Agentic AI", "Financial Wellness", "WealthTech", "Customer Retention", "Behavioral Tech"]):
            category_to_problems["SIP_Discontinuation"].add(cat)

        # Let's ensure DeepTech / Hardware categories map somewhere generic as well (e.g. Underwriting_Accuracy or HFC_Underwriting)
        if ind == "DeepTech" or sect in ["SpaceTech", "Robotics", "Quantum Computing", "Semiconductor", "Drones"]:
            category_to_problems["Underwriting_Accuracy"].add(cat)
            category_to_problems["Information_Security"].add(cat)

    # Fallback/Catch-all to ensure 100% of categories are mapped to at least one business problem
    for cat in all_sectors + all_subsectors:
        cat_lower = cat.lower()
        sect = cat
        if cat in subsector_to_sector:
            sect = subsector_to_sector[cat]
        ind = sector_to_industry.get(sect, "")
        
        # Check if this category is mapped to at least one problem
        mapped_count = sum(1 for prob_id, cats in category_to_problems.items() if cat in cats)
        if mapped_count == 0:
            # Determine appropriate generic business problem
            if ind in ["Financial Services", "Artificial Intelligence", "Enterprise Software", "Cybersecurity"]:
                category_to_problems["Information_Security"].add(cat)
                category_to_problems["Acquisition_Cost"].add(cat)
            elif ind in ["Healthcare & Life Sciences", "Energy & Sustainability", "Transportation & Logistics", "Manufacturing & Industrial", "DeepTech"]:
                category_to_problems["Underwriting_Accuracy"].add(cat)
                category_to_problems["Credit_Risk_Assessment"].add(cat)
            elif ind in ["Commerce & Retail", "Consumer Internet", "Education", "Agriculture & Food", "Government & Defense", "Telecom & Connectivity"]:
                category_to_problems["Acquisition_Cost"].add(cat)
                category_to_problems["Payment_Reconciliation"].add(cat)
            else:
                category_to_problems["Acquisition_Cost"].add(cat)

    # Re-apply updated lists to problems object
    for prob in problems:
        prob_id = prob["problem_id"]
        prob["startup_categories"] = sorted(list(category_to_problems[prob_id]))
        
    save_json("backend/config/business_problems.json", problems_data)

if __name__ == "__main__":
    extend_opportunity_matrix()
    extend_business_problems()
