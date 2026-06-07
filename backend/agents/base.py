from datetime import datetime
from backend.models.startup_state import StartupState

class BaseAgent:
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
        # Avoid direct mutation that breaks copy/pydantic strict flows:
        # Appending to the existing list is allowed under 'never mutate unrelated sections'.
        state.audit_trail.append(log_entry)
        return state
