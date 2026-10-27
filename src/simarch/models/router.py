"""SimArch complexity-based model router and fallback manager."""

import os
from typing import Optional
from simarch.models.providers import BaseModelProvider, DeterministicLocalProvider, ExternalAPIProvider
from simarch.models.registry import ModelDescriptor, ModelRegistry


class ModelRouter:
    """Intelligently routes inference workloads based on complexity, budget, and provider health."""

    def __init__(self, registry: Optional[ModelRegistry] = None) -> None:
        self.registry = registry or ModelRegistry()
        self.local_provider = DeterministicLocalProvider()
        self._sync_provider_availability()

    def _sync_provider_availability(self) -> None:
        """Enable hosted model descriptors if corresponding API credentials exist in environment."""
        if os.getenv("OPENAI_API_KEY"):
            m = self.registry.get("gpt-4o")
            if m:
                m.is_available = True
        if os.getenv("ANTHROPIC_API_KEY"):
            m = self.registry.get("claude-3-5-sonnet")
            if m:
                m.is_available = True

    def route_for_task(self, task_priority: str, complexity: str = "standard") -> BaseModelProvider:
        """Select the optimal model provider according to task requirements."""
        if complexity == "heavy" or task_priority == "critical":
            # Prefer high-capacity model if key available
            if os.getenv("ANTHROPIC_API_KEY"):
                return ExternalAPIProvider("anthropic", fallback_provider=self.local_provider)
            if os.getenv("OPENAI_API_KEY"):
                return ExternalAPIProvider("openai", fallback_provider=self.local_provider)

        # Default to fast, reliable zero-cost local provider
        return self.local_provider
