"""SimArch decision intelligence models."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from simarch.core.types import DecisionStatus, generate_id, utc_now_iso


class DecisionAlternative(BaseModel):
    """A distinct course of action evaluated during decision making."""
    id: str = Field(default_factory=lambda: generate_id("alt"))
    name: str
    description: str
    estimated_cost: float = 0.0
    expected_benefit: float = 0.0
    risk_level: str = "medium"  # low, medium, high, critical
    scores: Dict[str, float] = Field(default_factory=dict)  # criterion_name -> score (0-10)
    weighted_total_score: float = 0.0
    rejected_reason: Optional[str] = None


class EvaluationCriterion(BaseModel):
    """Weighted standard used to rank decision alternatives."""
    name: str
    weight: float = 1.0  # Normalized relative weight
    description: str


class DecisionRecord(BaseModel):
    """Comprehensive, auditable, and inspectable record of a material organizational decision."""
    id: str = Field(default_factory=lambda: generate_id("dec"))
    project_id: str
    org_id: str
    owner_role_id: str
    objective: str
    alternatives: List[DecisionAlternative] = Field(default_factory=list)
    criteria: List[EvaluationCriterion] = Field(default_factory=list)
    trade_offs: Dict[str, Any] = Field(default_factory=dict)
    risks: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    chosen_option: Optional[str] = None
    reasons_for_selection: Optional[str] = None
    status: DecisionStatus = DecisionStatus.PROPOSED
    expected_outcomes: Dict[str, Any] = Field(default_factory=dict)
    actual_outcomes: Dict[str, Any] = Field(default_factory=dict)
    reconsideration_conditions: Optional[str] = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
