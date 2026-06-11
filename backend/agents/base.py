import time
from datetime import datetime
from backend.models.startup_state import StartupState
from backend.utils.tracing import (
    set_exec_id,
    reset_exec_id,
    generate_uuid,
    log_agent_execution
)

class BaseAgent:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if 'run' in cls.__dict__:
            original_run = cls.run
            
            def wrapped_run(self, state: StartupState, *args, **kwargs) -> StartupState:
                agent_name = cls.__name__
                exec_id = generate_uuid()
                token = set_exec_id(exec_id)
                start_time = time.perf_counter()
                
                # Safely extract input metadata
                input_payload = {
                    "startup_name": getattr(state, "startup_name", None),
                    "website": getattr(state, "website", None),
                    "source_url": getattr(state, "source_url", None)
                }
                
                try:
                    result = original_run(self, state, *args, **kwargs)
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    
                    output_payload = {
                        "status": "success",
                        "audit_trail_len": len(getattr(result, "audit_trail", []))
                    }
                    # Include some high level outputs if relevant
                    for attr in ["brand_name", "legal_name", "relevance_score", "status", "priority_band"]:
                        if hasattr(result, attr):
                            output_payload[attr] = getattr(result, attr)
                            
                    log_agent_execution(
                        exec_id=exec_id,
                        agent_name=agent_name,
                        input_payload=input_payload,
                        output_payload=output_payload,
                        duration_ms=duration_ms
                    )
                    return result
                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    log_agent_execution(
                        exec_id=exec_id,
                        agent_name=agent_name,
                        input_payload=input_payload,
                        output_payload={"status": "error", "error": str(e)},
                        duration_ms=duration_ms
                    )
                    raise e
                finally:
                    reset_exec_id(token)
            
            cls.run = wrapped_run

    def run(self, state: StartupState) -> StartupState:
        raise NotImplementedError("Each agent must implement its own run method.")

    def log_audit(self, state: StartupState, message: str, metadata: dict = None) -> StartupState:
        """Appends a timestamped audit record to the state's audit trail."""
        agent_name = self.__class__.__name__
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "agent": agent_name,
            "message": message,
            "metadata": metadata or {}
        }
        state.audit_trail.append(log_entry)
        return state

