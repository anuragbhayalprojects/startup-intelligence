from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List, Union

class AIRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    task: str = "enrichment_products"
    json_format: bool = True
    num_ctx: int = 4096
    temperature: float = 0.0
    agent_name: str = "AIRouter"
    required_schema_keys: Optional[Union[List[str], Dict[str, Any]]] = None

class AIResponse(BaseModel):
    content: Any  # Can be parsed dict/list or raw string response
    provider: str
    model: str
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    latency_ms: float = 0.0
    usage: Dict[str, Any] = Field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})

    def to_legacy_dict(self) -> Dict[str, Any]:
        """
        Embeds the exact nested _routing metadata block to keep legacy obs_prompt_ledger
        and frontend observability functioning.
        """
        routing_meta = {
            "provider": self.provider,
            "model": self.model,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "latency_ms": self.latency_ms,
            "usage": self.usage
        }
        
        if isinstance(self.content, dict):
            res = dict(self.content)
        elif isinstance(self.content, list):
            res = {"list_content": self.content}
        else:
            res = {"response_text": str(self.content)}

        res["_routing"] = routing_meta
        return res
