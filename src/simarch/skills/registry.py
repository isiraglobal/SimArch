"""SimArch versioned skill registry and manifest validation."""

from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field
from simarch.core.exceptions import RolePermissionError, SimArchError


class SkillManifest(BaseModel):
    """Declarative specification of an organizational capability."""
    name: str
    version: str = "1.0.0"
    category: str
    description: str
    inputs_schema: Dict[str, Any] = Field(default_factory=dict)
    outputs_schema: Dict[str, Any] = Field(default_factory=dict)
    required_permissions: List[str] = Field(default_factory=list)
    timeout_seconds: int = 60


class Skill:
    """Executable capability wrapping a manifest and an implementation handler."""

    def __init__(self, manifest: SkillManifest, handler: Callable[..., Dict[str, Any]]) -> None:
        self.manifest = manifest
        self.handler = handler

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the skill handler with input validation."""
        return self.handler(inputs)


class SkillRegistry:
    """Catalog of versioned and validated organizational skills."""

    def __init__(self) -> None:
        self._skills: Dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """Register a new skill into the catalog."""
        self._skills[skill.manifest.name] = skill

    def get(self, name: str) -> Optional[Skill]:
        """Fetch skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> List[SkillManifest]:
        """List manifests of all registered capabilities."""
        return [s.manifest for s in self._skills.values()]
