CREATE TABLE startups (
    id BIGSERIAL PRIMARY KEY,
    startup_name TEXT UNIQUE NOT NULL,
    website TEXT,
    linkedin_url TEXT,
    city TEXT,
    state TEXT,
    country TEXT DEFAULT 'India',
    industry TEXT,
    sector TEXT,
    subsector TEXT,
    business_models JSONB,
    industry_relevance JSONB,
    tags JSONB,
    funding_stage TEXT,
    founded_year INT,
    description TEXT,
    source TEXT,
    source_url TEXT,
    dedup_hash TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE startup_analysis (
    id BIGSERIAL PRIMARY KEY,
    startup_id BIGINT REFERENCES startups(id),

    ai_summary TEXT,

    bfsi_relevance_score INT,
    enterprise_readiness_score INT,
    strategic_fit_score INT,
    integration_feasibility_score INT,
    priority_score INT,

    icici_primary_entity TEXT,

    use_cases JSONB,
    co_creation_opportunities JSONB,

    analysis_json JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE startup_assignments (
    id BIGSERIAL PRIMARY KEY,

    startup_id BIGINT REFERENCES startups(id),

    assigned_to TEXT,
    icici_entity TEXT,

    assignment_status TEXT DEFAULT 'pending',

    notes TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE startup_activity_logs (
    id BIGSERIAL PRIMARY KEY,

    startup_id BIGINT REFERENCES startups(id),

    activity_type TEXT,
    activity_notes TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);