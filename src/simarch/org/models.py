"""SimArch organization models and role contracts."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from simarch.core.types import RoleType, generate_id, utc_now_iso


class RoleContract(BaseModel):
    """Enforceable contract defining a corporate role, its authority, and bounds."""
    id: str = Field(default_factory=lambda: generate_id("role"))
    org_id: str
    title: str
    role_type: RoleType
    reports_to_id: Optional[str] = None
    mission: str
    responsibilities: List[str] = Field(default_factory=list)
    decision_authority: List[str] = Field(default_factory=list)
    tool_permissions: List[str] = Field(default_factory=list)
    information_access: List[str] = Field(default_factory=list)
    budget_limit: float = 1000.0
    required_outputs: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)
    delegation_permissions: List[str] = Field(default_factory=list)
    max_delegation_depth: int = 3
    escalation_conditions: List[str] = Field(default_factory=list)
    review_required: bool = True
    performance_history: Dict[str, Any] = Field(default_factory=lambda: {
        "tasks_completed": 0,
        "tasks_failed": 0,
        "reviews_passed": 0,
        "reviews_rejected": 0,
        "quality_score": 1.0
    })
    created_at: str = Field(default_factory=utc_now_iso)


class Department(BaseModel):
    """Functional department within an organization."""
    id: str = Field(default_factory=lambda: generate_id("dept"))
    name: str
    head_role_id: Optional[str] = None
    roles: List[str] = Field(default_factory=list)


class Organization(BaseModel):
    """Autonomous AI organization with hierarchical and cross-functional structure."""
    id: str = Field(default_factory=lambda: generate_id("org"))
    name: str
    mission: str
    governance_model: str = "standard"  # e.g., 'executive_board', 'flat_collaborative', 'standard'
    departments: List[Department] = Field(default_factory=list)
    roles: Dict[str, RoleContract] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def get_role_by_title(self, title: str) -> Optional[RoleContract]:
        """Find a role contract by its title."""
        for role in self.roles.values():
            if role.title.lower() == title.lower():
                return role
        return None

    def get_direct_reports(self, role_id: str) -> List[RoleContract]:
        """Return all roles reporting directly to the specified role."""
        return [r for r in self.roles.values() if r.reports_to_id == role_id]
