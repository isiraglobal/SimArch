"""SimArch core exceptions."""

class SimArchError(Exception):
    """Base exception for all SimArch errors."""
    pass


class ConfigurationError(SimArchError):
    """Raised when configuration is invalid or missing."""
    pass


class DatabaseError(SimArchError):
    """Raised when a database operation fails."""
    pass


class OrganizationError(SimArchError):
    """Raised when organization creation or validation fails."""
    pass


class RolePermissionError(SimArchError):
    """Raised when a role attempts an unauthorized action or privilege escalation."""
    pass


class TaskExecutionError(SimArchError):
    """Raised when task scheduling or execution encounters a fatal error."""
    pass


class DependencyCycleError(TaskExecutionError):
    """Raised when task dependencies contain a circular reference."""
    pass


class LeaseExpiredError(TaskExecutionError):
    """Raised when a worker lease has expired or been preempted."""
    pass


class ReviewRejectedError(TaskExecutionError):
    """Raised when a deliverable fails independent review."""
    pass


class DecisionError(SimArchError):
    """Raised when a decision record or graph operation is invalid."""
    pass


class SimulationError(SimArchError):
    """Raised when a simulation scenario or step fails."""
    pass


class ModelProviderError(SimArchError):
    """Raised when an external model provider fails or is unconfigured."""
    pass


class WorkspaceError(SimArchError):
    """Raised when temporary workspace allocation or cleanup fails."""
    pass


class SecurityViolationError(SimArchError):
    """Raised on security violation (path traversal, unauthorized role elevation, etc.)."""
    pass
