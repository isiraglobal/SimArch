"""Tests for Organization Engine and Role Contracts (Items 2 & 3)."""

import pytest
from simarch.core.exceptions import RolePermissionError, SecurityViolationError
from simarch.core.types import RoleType
from simarch.db.database import DatabaseManager
from simarch.org.formation import WorkforceFormationPlanner
from simarch.org.models import RoleContract
from simarch.org.permissions import PermissionEnforcer


def test_organization_creation_and_persistence(temp_db: DatabaseManager, formation_planner: WorkforceFormationPlanner):
    """Verify dynamic workforce formation synthesizes appropriate roles and persists to DB."""
    org = formation_planner.synthesize_organization(
        name="Acme Autonomous Corp",
        objective="Build and operate an automated market intelligence pipeline.",
        scale="standard"
    )

    assert org.id.startswith("org_")
    assert org.name == "Acme Autonomous Corp"
    assert len(org.roles) >= 4

    # Verify reloading from DB
    loaded = formation_planner.load_organization(org.id)
    assert loaded is not None
    assert loaded.id == org.id
    assert loaded.name == org.name
    assert len(loaded.roles) == len(org.roles)


def test_permission_enforcement_allowed_tool():
    """Verify role with permission can access authorized tools."""
    contract = RoleContract(
        org_id="org_1",
        title="Software Engineer",
        role_type=RoleType.SPECIALIST,
        mission="Code",
        tool_permissions=["write_code", "run_tests"]
    )
    # Should not raise
    PermissionEnforcer.verify_tool_access(contract, "write_code")
    PermissionEnforcer.verify_tool_access(contract, "run_tests")


def test_permission_enforcement_denied_tool():
    """Verify role without permission is strictly denied."""
    contract = RoleContract(
        org_id="org_1",
        title="Research Analyst",
        role_type=RoleType.SPECIALIST,
        mission="Research",
        tool_permissions=["web_search", "document_read"]
    )
    with pytest.raises(RolePermissionError, match="does not have permission"):
        PermissionEnforcer.verify_tool_access(contract, "git_push_production")


def test_security_violation_guard():
    """Verify permanent security controls prevent any role from executing prohibited tools."""
    contract = RoleContract(
        org_id="org_1",
        title="Chief Executive Officer",
        role_type=RoleType.EXECUTIVE,
        mission="Lead",
        tool_permissions=["*"]  # Even with wildcard!
    )
    with pytest.raises(SecurityViolationError, match="permanently restricted"):
        PermissionEnforcer.verify_tool_access(contract, "grant_role_privilege")


def test_decision_authority_enforcement():
    """Verify decision authority checks prevent unauthorized decisions."""
    specialist = RoleContract(
        org_id="org_1",
        title="Junior Analyst",
        role_type=RoleType.SPECIALIST,
        mission="Analyze",
        decision_authority=["task_execution"]
    )
    with pytest.raises(RolePermissionError, match="lacks decision authority"):
        PermissionEnforcer.verify_decision_authority(specialist, "strategic_merger")


def test_delegation_limits_and_depth():
    """Verify delegation depth is bounded to prevent runaway recursion."""
    manager = RoleContract(
        org_id="org_1",
        title="Manager",
        role_type=RoleType.MANAGER,
        mission="Manage",
        max_delegation_depth=2,
        delegation_permissions=["Specialist"]
    )
    subordinate = RoleContract(
        org_id="org_1",
        title="Specialist",
        role_type=RoleType.SPECIALIST,
        mission="Execute"
    )

    # Within limit
    PermissionEnforcer.verify_delegation(manager, subordinate, current_depth=1)

    # Exceeds depth limit
    with pytest.raises(RolePermissionError, match="exceeds role 'Manager' limit"):
        PermissionEnforcer.verify_delegation(manager, subordinate, current_depth=2)
