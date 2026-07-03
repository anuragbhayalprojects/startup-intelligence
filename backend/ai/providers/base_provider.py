from abc import ABC, abstractmethod
from typing import Any
from backend.ai.types import AIRequest, AIResponse

class BaseProvider(ABC):
    @abstractmethod
    async def generate(self, request: AIRequest) -> AIResponse:
        """
        Executes a completion request asynchronously and returns an AIResponse.
        """
        pass
