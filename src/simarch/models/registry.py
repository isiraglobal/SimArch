"""SimArch model registry and capabilities inventory."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ModelDescriptor(BaseModel):
    """Specification of an AI model's profile, cost, and operational limits."""
    name: str
    provider: str  # local, openai, anthropic, gemini
    context_window: int = 8192
    cost_per_1k_input_usd: float = 0.0
    cost_per_1k_output_usd: float = 0.0
    latency_tier: str = "fast"  # fast, standard, heavy
    capabilities: List[str] = Field(default_factory=list)  # planning, coding, analysis, routine
    tool_calling: bool = True
    is_available: bool = True


class ModelRegistry:
    """Maintains catalog of available foundation and local models."""

    def __init__(self) -> None:
        self._models: Dict[str, ModelDescriptor] = {}
        self._register_default_models()

    def _register_default_models(self) -> None:
        """Register built-in local and hosted model profiles."""
        self.register(ModelDescriptor(
            name="deterministic-local",
            provider="local",
            context_window=32768,
            cost_per_1k_input_usd=0.0,
            cost_per_1k_output_usd=0.0,
            latency_tier="fast",
            capabilities=["planning", "coding", "analysis", "routine", "evaluation"],
            tool_calling=True,
            is_available=True
        ))

        self.register(ModelDescriptor(
            name="gpt-4o",
            provider="openai",
            context_window=128000,
            cost_per_1k_input_usd=0.005,
            cost_per_1k_output_usd=0.015,
            latency_tier="standard",
            capabilities=["planning", "coding", "analysis", "heavy_reasoning"],
            tool_calling=True,
            is_available=False  # Auto-enabled if OPENAI_API_KEY present
        ))

        self.register(ModelDescriptor(
            name="claude-3-5-sonnet",
            provider="anthropic",
            context_window=200000,
            cost_per_1k_input_usd=0.003,
            cost_per_1k_output_usd=0.015,
            latency_tier="standard",
            capabilities=["planning", "coding", "analysis", "heavy_reasoning"],
            tool_calling=True,
            is_available=False  # Auto-enabled if ANTHROPIC_API_KEY present
        ))

    def register(self, descriptor: ModelDescriptor) -> None:
        """Add or update model descriptor in registry."""
        self._models[descriptor.name] = descriptor

    def get(self, name: str) -> Optional[ModelDescriptor]:
        """Fetch model descriptor by name."""
        return self._models.get(name)

    def list_available(self) -> List[ModelDescriptor]:
        """Return all models marked available."""
        return [m for m in self._models.values() if m.is_available]
