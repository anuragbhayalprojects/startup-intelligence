-- Database Migration: Tracing & Observability Schema
-- Run this in your Supabase SQL Editor.

-- 1. Create main traces table
CREATE TABLE IF NOT EXISTS public.obs_traces (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  trace_id text UNIQUE NOT NULL,
  startup_name text,
  article_url text,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

-- 2. Create API calls trace table
CREATE TABLE IF NOT EXISTS public.obs_api_calls (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  trace_id text NOT NULL,
  route text NOT NULL,
  method text NOT NULL,
  payload jsonb DEFAULT '{}'::jsonb,
  response jsonb DEFAULT '{}'::jsonb,
  status_code integer,
  duration_ms numeric,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

-- 3. Create Agent executions table
CREATE TABLE IF NOT EXISTS public.obs_agent_executions (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  trace_id text NOT NULL,
  exec_id text NOT NULL,
  agent_name text NOT NULL,
  input_payload jsonb DEFAULT '{}'::jsonb,
  output_payload jsonb DEFAULT '{}'::jsonb,
  duration_ms numeric,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

-- 4. Create Prompt ledger table
CREATE TABLE IF NOT EXISTS public.obs_prompt_ledger (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  trace_id text NOT NULL,
  prompt_id text NOT NULL,
  agent_name text NOT NULL,
  prompt_template text NOT NULL,
  injected_context text NOT NULL,
  raw_response text NOT NULL,
  parsed_response jsonb DEFAULT '{}'::jsonb,
  duration_ms numeric,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

-- 5. Create DB mutations table
CREATE TABLE IF NOT EXISTS public.obs_db_mutations (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  trace_id text NOT NULL,
  txn_id text NOT NULL,
  table_name text NOT NULL,
  operation text NOT NULL,
  rows_affected integer,
  duration_ms numeric,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

-- 6. Create Graph mutations table
CREATE TABLE IF NOT EXISTS public.obs_graph_mutations (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  trace_id text NOT NULL,
  mutation_id text NOT NULL,
  operation text NOT NULL,
  details jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

-- 7. Create Frontend events table
CREATE TABLE IF NOT EXISTS public.obs_frontend_events (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  trace_id text NOT NULL,
  page text NOT NULL,
  component text NOT NULL,
  action text NOT NULL,
  payload jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

-- Add Indexes for performant search lookup in Trace Explorer
CREATE INDEX IF NOT EXISTS idx_obs_traces_trace_id ON public.obs_traces(trace_id);
CREATE INDEX IF NOT EXISTS idx_obs_api_calls_trace_id ON public.obs_api_calls(trace_id);
CREATE INDEX IF NOT EXISTS idx_obs_agent_executions_trace_id ON public.obs_agent_executions(trace_id);
CREATE INDEX IF NOT EXISTS idx_obs_prompt_ledger_trace_id ON public.obs_prompt_ledger(trace_id);
CREATE INDEX IF NOT EXISTS idx_obs_db_mutations_trace_id ON public.obs_db_mutations(trace_id);
CREATE INDEX IF NOT EXISTS idx_obs_graph_mutations_trace_id ON public.obs_graph_mutations(trace_id);
CREATE INDEX IF NOT EXISTS idx_obs_frontend_events_trace_id ON public.obs_frontend_events(trace_id);
