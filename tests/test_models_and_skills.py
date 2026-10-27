"""Tests for Models, Router, Skills, Resource Limits, and Self-Learning (Items 13 & 14)."""

import pytest
from simarch.core.exceptions import RolePermissionError, SecurityViolationError
from simarch.core.types import RoleType
from simarch.db.database import DatabaseManager
from simarch.learning.improvement import ControlledImprovementEngine
from simarch.models.providers import DeterministicLocalProvider, ExternalAPIProvider
from simarch.models.router import ModelRouter
from simarch.org.models import RoleContract
from simarch.org.permissions import PermissionEnforcer
from simarch.skills.library import build_default_skill_registry


def test_model_router_deterministic_fallback():
    """Verify router cleanly falls back to zero-cost deterministic provider when no API key configured."""
    router = ModelRouter()
    provider = router.route_for_task(task_priority="normal", complexity="routine")
    assert isinstance(provider, DeterministicLocalProvider)

    resp = provider.generate("Decompose the objective into tasks.")
    assert resp.model_name == "deterministic-local"
    assert resp.cost_usd == 0.0
    assert resp.parsed_json is not None
    assert "tasks" in resp.parsed_json


def test_external_api_provider_graceful_fallback(monkeypatch):
    """Verify ExternalAPIProvider falls back gracefully when environment variable is unset."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = ExternalAPIProvider("openai")
    resp = provider.generate("Plan project architecture")
    assert "fallback" in resp.model_name.lower() or "deterministic" in resp.model_name.lower()
    assert resp.content is not None


def test_role_budget_limit_enforcement():
    """Verify role budget limits strictly reject excessive resource allocations."""
    role = RoleContract(
        org_id="org1",
        title="Junior Analyst",
        role_type=RoleType.SPECIALIST,
        mission="Analyze",
        budget_limit=500.0
    )

    # Within budget
    PermissionEnforcer.verify_budget(role, 450.0)

    # Exceeds budget
    with pytest.raises(RolePermissionError, match="exceeds role 'Junior Analyst' limit"):
        PermissionEnforcer.verify_budget(role, 550.0)


def test_skills_library_execution():
    """Verify built-in skills can be discovered and executed with valid output."""
    registry = build_default_skill_registry()
    skill = registry.get("software_engineering")
    assert skill is not None

    result = skill.execute({"feature": "Authentication Gateway", "language": "python"})
    assert result["status"] == "success"
    assert result["syntax_valid"] is True
    assert "authentication_gateway.py" in result["artifacts_generated"]


def test_controlled_self_improvement_security_guard(temp_db: DatabaseManager):
    """Verify self-improvement loop strictly forbids modifying permissions or security controls."""
    engine = ControlledImprovementEngine(temp_db)
    temp_db.execute("INSERT INTO organizations (id, name, mission, created_at, updated_at) VALUES ('org1', 'O1', 'M1', '', '')")

    # Attempt unauthorized modification
    with pytest.raises(SecurityViolationError, match="cannot modify security, auth, or permission bounds"):
        engine.propose_change(
            org_id="org1",
            category="permissions",
            proposal={"bypass": True, "grant_all": True},
            baseline_metrics={"quality": 0.8}
        )
