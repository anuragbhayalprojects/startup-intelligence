import random
import string
import time
import logging
from datetime import datetime
from contextvars import ContextVar

# Setup logging
logger = logging.getLogger("startup_intelligence.tracing")

# Context variables to hold current execution state across threads/tasks
_trace_id_var = ContextVar("trace_id", default=None)
_exec_id_var = ContextVar("exec_id", default=None)

def generate_trace_id() -> str:
    """Generates a trace ID in the format TRACE_YYYYMMDD_XXXXXX."""
    date_str = datetime.now().strftime("%Y%m%d")
    random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"TRACE_{date_str}_{random_str}"

def generate_uuid() -> str:
    """Generates a random hex ID for operations."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=16))

def get_trace_id() -> str | None:
    """Gets the active Trace ID from context."""
    return _trace_id_var.get()

def set_trace_id(trace_id: str):
    """Sets the active Trace ID in context."""
    return _trace_id_var.set(trace_id)

def reset_trace_id(token):
    """Resets the Trace ID in context using the token."""
    _trace_id_var.reset(token)

def get_exec_id() -> str | None:
    """Gets the active Agent Execution ID from context."""
    return _exec_id_var.get()

def set_exec_id(exec_id: str):
    """Sets the active Agent Execution ID in context."""
    return _exec_id_var.set(exec_id)

def reset_exec_id(token):
    """Resets the Agent Execution ID in context using the token."""
    _exec_id_var.reset(token)


# Database logger helper wrapper
def _safe_supabase_insert(table_name: str, payload: dict):
    """Safely attempts to insert a record into Supabase, logging errors instead of raising."""
    trace_id = get_trace_id()
    if not trace_id:
        trace_id = generate_trace_id()
        set_trace_id(trace_id)
        # Create a root trace record in Supabase so foreign keys in other tables are satisfied
        try:
            from backend.services.supabase_service import supabase
            supabase.table("obs_traces").insert({
                "trace_id": trace_id,
                "startup_name": "NewsIngestion",
                "article_url": "Sync Feed"
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to automatically create root trace record: {e}")
        
    payload["trace_id"] = trace_id
    
    try:
        from backend.services.supabase_service import supabase
        res = supabase.table(table_name).insert(payload).execute()
        return res
    except Exception as e:
        logger.warning(f"Observability tracing insert failed for '{table_name}' (possibly migration not applied yet): {e}")
        return None


def log_trace(startup_name: str = None, article_url: str = None):
    """Creates the root trace entry in obs_traces if it does not exist."""
    trace_id = get_trace_id()
    if not trace_id:
        return
        
    try:
        from backend.services.supabase_service import supabase
        # Check if already exists
        res = supabase.table("obs_traces").select("id").eq("trace_id", trace_id).execute()
        if not res.data:
            supabase.table("obs_traces").insert({
                "trace_id": trace_id,
                "startup_name": startup_name,
                "article_url": article_url
            }).execute()
    except Exception as e:
        logger.warning(f"Failed to create root trace record: {e}")


def log_api_call(route: str, method: str, payload: dict, response: dict, status_code: int, duration_ms: float):
    """Logs an API request metadata and latency."""
    _safe_supabase_insert("obs_api_calls", {
        "route": route,
        "method": method,
        "payload": payload or {},
        "response": response or {},
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2)
    })


def log_agent_execution(exec_id: str, agent_name: str, input_payload: dict, output_payload: dict, duration_ms: float):
    """Logs an agent lifecycle run execution."""
    _safe_supabase_insert("obs_agent_executions", {
        "exec_id": exec_id,
        "agent_name": agent_name,
        "input_payload": input_payload or {},
        "output_payload": output_payload or {},
        "duration_ms": round(duration_ms, 2)
    })


def log_prompt_ledger(prompt_id: str, agent_name: str, prompt_template: str, injected_context: str, raw_response: str, parsed_response: dict, duration_ms: float):
    """Logs exact prompts sent to the LLM and their parsed responses."""
    _safe_supabase_insert("obs_prompt_ledger", {
        "prompt_id": prompt_id,
        "agent_name": agent_name,
        "prompt_template": prompt_template or "",
        "injected_context": injected_context or "",
        "raw_response": raw_response or "",
        "parsed_response": parsed_response or {},
        "duration_ms": round(duration_ms, 2)
    })


def log_db_mutation(txn_id: str, table_name: str, operation: str, rows_affected: int, duration_ms: float):
    """Logs SELECT, INSERT, UPDATE, DELETE query performance on Supabase database."""
    _safe_supabase_insert("obs_db_mutations", {
        "txn_id": txn_id,
        "table_name": table_name,
        "operation": operation,
        "rows_affected": rows_affected,
        "duration_ms": round(duration_ms, 2)
    })


def log_graph_mutation(mutation_id: str, operation: str, details: dict):
    """Logs knowledge graph mutation events."""
    _safe_supabase_insert("obs_graph_mutations", {
        "mutation_id": mutation_id,
        "operation": operation,
        "details": details or {}
    })


def log_frontend_event(page: str, component: str, action: str, payload: dict):
    """Logs frontend events passed from the UI."""
    _safe_supabase_insert("obs_frontend_events", {
        "page": page,
        "component": component,
        "action": action,
        "payload": payload or {}
    })


def wrap_supabase_client(client):
    """Wraps postgrest client object to intercept database call execute() methods for query telemetry."""
    original_table = client.table
    
    def wrapped_table(table_name: str, *args, **kwargs):
        builder = original_table(table_name, *args, **kwargs)
        # Avoid tracing insert queries to the observability tables themselves to prevent infinite recursion
        if table_name.startswith("obs_"):
            return builder
            
        # We wrap select, insert, update, delete methods on the builder
        def wrap_method(method_name):
            original_method = getattr(builder, method_name)
            
            def wrapped_method(*m_args, **m_kwargs):
                sub_builder = original_method(*m_args, **m_kwargs)
                # Now sub_builder is the query builder (like SelectRequestBuilder) which has .execute()
                if not hasattr(sub_builder, "execute"):
                    return sub_builder
                    
                original_execute = sub_builder.execute
                
                def wrapped_execute(*e_args, **e_kwargs):
                    import time
                    from backend.utils.tracing import generate_uuid, log_db_mutation
                    
                    operation = method_name.upper()
                    txn_id = "TXN_" + generate_uuid()
                    start_time = time.perf_counter()
                    
                    try:
                        res = original_execute(*e_args, **e_kwargs)
                        duration_ms = (time.perf_counter() - start_time) * 1000.0
                        rows_affected = 0
                        if res and hasattr(res, "data") and res.data:
                            rows_affected = len(res.data) if isinstance(res.data, list) else 1
                            
                        log_db_mutation(
                            txn_id=txn_id,
                            table_name=table_name,
                            operation=operation,
                            rows_affected=rows_affected,
                            duration_ms=duration_ms
                        )
                        return res
                    except Exception as ex:
                        duration_ms = (time.perf_counter() - start_time) * 1000.0
                        log_db_mutation(
                            txn_id=txn_id,
                            table_name=table_name,
                            operation=f"{operation}_ERROR",
                            rows_affected=0,
                            duration_ms=duration_ms
                        )
                        raise ex
                
                sub_builder.execute = wrapped_execute
                return sub_builder
                
            setattr(builder, method_name, wrapped_method)
            
        for method in ("select", "insert", "update", "delete"):
            if hasattr(builder, method):
                wrap_method(method)
                
        return builder
        
    client.table = wrapped_table
    return client
