"""SimArch core domain types and enumerations."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import datetime
import uuid


def generate_id(prefix: str = "") -> str:
    """Generate a prefixed unique identifier."""
    raw = uuid.uuid4().hex[:12]
    return f"{prefix}_{raw}" if prefix else raw


def utc_now() -> datetime.datetime:
    """Return current UTC timestamp with timezone."""
    return datetime.datetime.now(datetime.timezone.utc)


def utc_now_iso() -> str:
    """Return current UTC timestamp formatted as ISO string."""
    return utc_now().isoformat()


class RoleType(str, Enum):
    """Executive, management, and operational role categories."""
    EXECUTIVE = "executive"      # CEO, CTO, CFO, COO, etc.
    DIRECTOR = "director"        # Head of Engineering, Product, Research
    MANAGER = "manager"          # Team Lead, Project Manager
    SPECIALIST = "specialist"    # Engineer, Analyst, Researcher, Marketer
    AUDITOR = "auditor"          # Independent reviewer, QA, Compliance
    COORDINATOR = "coordinator"  # Cross-functional workflow runner


class TaskStatus(str, Enum):
    """Rigorous task execution state machine states."""
    PROPOSED = "PROPOSED"
    READY = "READY"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    REVIEW = "REVIEW"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RETRYING = "RETRYING"


class TaskPriority(str, Enum):
    """Execution priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewStatus(str, Enum):
    """Independent review verdict."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class DecisionStatus(str, Enum):
    """Decision intelligence life cycle."""
    PROPOSED = "proposed"
    EVALUATING = "evaluating"
    SELECTED = "selected"
    RECONSIDERED = "reconsidered"
    OVERRULED = "overruled"


class MemoryScope(str, Enum):
    """Scoped memory isolation boundaries."""
    ORGANIZATION = "organization"
    DEPARTMENT = "department"
    PROJECT = "project"
    EMPLOYEE = "employee"
    TASK = "task"
    DECISION = "decision"
    EVIDENCE = "evidence"


class WorkspaceLifecycle(str, Enum):
    """Workspace state transitions."""
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    CHECKPOINTED = "CHECKPOINTED"
    CLEANUP_ELIGIBLE = "CLEANUP_ELIGIBLE"
    DELETED = "DELETED"
