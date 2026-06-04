// frontend/src/lib/taxonomy.ts

export interface Industry {
  name: string;
  sectors: Record<string, string[]>;
}

export const TAXONOMY = {
  industries: [
    {
      name: "Financial Services",
      sectors: {
        "FinTech": [
          "Digital Banking",
          "Neobanking",
          "Lending",
          "Consumer Lending",
          "MSME Lending",
          "Mortgage Tech",
          "WealthTech",
          "InvestmentTech",
          "Stock Broking",
          "Payments",
          "UPI Infrastructure",
          "Cross-border Payments",
          "Embedded Finance",
          "RegTech",
          "TreasuryTech",
          "TaxTech",
          "Credit Infrastructure",
          "Collections",
          "Fraud Detection"
        ],
        "InsurTech": [
          "Digital Insurance",
          "Embedded Insurance",
          "Claims Automation",
          "Insurance Distribution",
          "Insurance Infrastructure",
          "Risk Analytics"
        ],
        "Capital Markets Tech": [
          "Trading Infrastructure",
          "Market Data",
          "Investment Platforms",
          "Wealth Infrastructure",
          "Alternative Investments"
        ]
      }
    },
    {
      name: "Artificial Intelligence",
      sectors: {
        "Generative AI": [
          "Text Generation",
          "Image Generation",
          "Video Generation",
          "Multimodal AI"
        ],
        "Agentic AI": [
          "Customer Service Agents",
          "Sales Agents",
          "Coding Agents",
          "Workflow Agents",
          "Knowledge Agents"
        ],
        "AI Infrastructure": [
          "LLM Platforms",
          "Vector Databases",
          "Model Hosting",
          "AI Observability",
          "AI Security"
        ],
        "AI Applications": [
          "AI Healthcare",
          "AI FinTech",
          "AI HRTech",
          "AI LegalTech",
          "AI SalesTech",
          "AI MarketingTech"
        ]
      }
    },
    {
      name: "Enterprise Software",
      sectors: {
        "SaaS": [
          "CRM",
          "ERP",
          "Accounting",
          "Billing",
          "Procurement",
          "Compliance",
          "Workflow Automation",
          "Project Management"
        ],
        "Productivity": [
          "Collaboration",
          "Team Communication",
          "Knowledge Management",
          "Documentation"
        ],
        "Future of Work": [
          "Workforce Productivity",
          "Remote Work",
          "Gig Economy",
          "Freelance Platforms"
        ]
      }
    },
    {
      name: "Cybersecurity",
      sectors: {
        "Cybersecurity": [
          "Identity Security",
          "Endpoint Security",
          "Cloud Security",
          "Application Security",
          "Threat Intelligence",
          "Fraud Prevention",
          "Governance Risk Compliance",
          "Data Security",
          "Network Security",
          "Zero Trust"
        ]
      }
    },
    {
      name: "Healthcare & Life Sciences",
      sectors: {
        "HealthTech": [
          "Telemedicine",
          "Diagnostics",
          "Hospital Management",
          "Healthcare SaaS",
          "Mental Health",
          "Women's Health",
          "Wellness",
          "Healthcare AI"
        ],
        "MedTech": [
          "Medical Devices",
          "Remote Monitoring",
          "Digital Therapeutics"
        ],
        "Biotechnology": [
          "Genomics",
          "Drug Discovery",
          "Synthetic Biology",
          "Bioinformatics"
        ]
      }
    },
    {
      name: "Commerce & Retail",
      sectors: {
        "E-commerce": [
          "Marketplaces",
          "B2B Commerce",
          "Social Commerce",
          "Quick Commerce",
          "Cross-border Commerce"
        ],
        "RetailTech": [
          "POS",
          "Inventory Management",
          "Retail Analytics",
          "Loyalty Platforms"
        ],
        "D2C Brands": [
          "Fashion",
          "Beauty",
          "Personal Care",
          "Home & Living",
          "Pet Care"
        ]
      }
    },
    {
      name: "Transportation & Logistics",
      sectors: {
        "LogisticsTech": [
          "FreightTech",
          "WarehouseTech",
          "Supply Chain Visibility",
          "Fleet Management"
        ],
        "Mobility": [
          "EV Platforms",
          "EV Charging",
          "Shared Mobility",
          "Connected Vehicles"
        ]
      }
    }
  ] as Industry[],
  business_models: [
    "B2B",
    "B2C",
    "B2B2C",
    "D2C",
    "Marketplace",
    "SaaS",
    "Subscription",
    "Transaction-Based",
    "Usage-Based",
    "Advertising",
    "Enterprise License"
  ],
  stages: [
    "Seed",
    "Series A",
    "Series B",
    "Series C",
    "Series D",
    "Growth",
    "Public",
    "Unknown"
  ]
};
