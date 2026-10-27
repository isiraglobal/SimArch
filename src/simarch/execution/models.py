"""SimArch task execution and deliverable models."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from simarch.core.types import (
    ReviewStatus,
    TaskPriority,
    TaskStatus,
    generate_id,
    utc_now_iso,
)


class Deliverable(BaseModel):
    """Structured output returned by an accountable worker."""
    summary: str
    findings: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[str] = Field(default_factory=list)
    artifacts: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    is_complete: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReviewVerdict(BaseModel):
    """Independent evaluation of a deliverable against acceptance criteria."""
    reviewer_role_id: str
    status: ReviewStatus
    feedback: str
    actionable_revisions: List[str] = Field(default_factory=list)
    evaluated_at: str = Field(default_factory=utc_now_iso)


class Task(BaseModel):
    """Accountable work unit with strict state, dependencies, and audit trail."""
    id: str = Field(default_factory=lambda: generate_id("task"))
    project_id: str
    org_id: str
    assigned_role_id: str
    owner_id: str = "system"
    objective: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    acceptance_criteria: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    priority: TaskPriority = TaskPriority.NORMAL
    budget: float = 100.0
    status: TaskStatus = TaskStatus.PROPOSED
    deliverable: Optional[Deliverable] = None
    review_results: Optional[ReviewVerdict] = None
    retry_count: int = 0
    max_retries: int = 3
    lease_worker_id: Optional[str] = None
    lease_expires_at: Optional[str] = None
    heartbeat_at: Optional[str] = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class Project(BaseModel):
    """Long-running strategic initiative comprising interconnected tasks."""
    id: str = Field(default_factory=lambda: generate_id("proj"))
    org_id: str
    name: str
    objective: str
    status: str = "ACTIVE"  # ACTIVE, PAUSED, COMPLETED, CANCELLED
    budget: float = 1000.0
    spent: float = 0.0
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class Artifact(BaseModel):
    """Durable file or evidence deliverable created during task execution."""
    id: str = Field(default_factory=lambda: generate_id("art"))
    task_id: Optional[str] = None
    project_id: str
    name: str
    artifact_type: str  # code, report, dataset, diagram, config
    storage_path: Optional[str] = None
    content_text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
