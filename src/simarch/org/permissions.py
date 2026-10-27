"""SimArch role permission enforcement engine."""

from typing import List, Optional
from simarch.core.exceptions import RolePermissionError, SecurityViolationError
from simarch.org.models import RoleContract


class PermissionEnforcer:
    """Enforces role authority, tool permissions, and delegation constraints."""

    @staticmethod
    def verify_tool_access(role: RoleContract, tool_name: str) -> None:
        """Verify if role has explicit permission to execute a tool.
        Wildcard '*' grants general tools, but sensitive tools must still be allowed.
        """
        # Forbidden tools that no role can execute implicitly
        if tool_name in ["grant_role_privilege", "modify_system_policy", "drop_tables"]:
            raise SecurityViolationError(f"Tool '{tool_name}' is permanently restricted by system policy.")

        if "*" in role.tool_permissions or tool_name in role.tool_permissions:
            return

        raise RolePermissionError(
            f"Role '{role.title}' ({role.id}) does not have permission to execute tool '{tool_name}'. "
            f"Granted permissions: {role.tool_permissions}"
        )

    @staticmethod
    def verify_decision_authority(role: RoleContract, decision_scope: str) -> None:
        """Verify role has authority to finalize a strategic or operational decision."""
        if "*" in role.decision_authority or decision_scope in role.decision_authority:
            return

        raise RolePermissionError(
            f"Role '{role.title}' ({role.id}) lacks decision authority for '{decision_scope}'. "
            f"Authorized decisions: {role.decision_authority}"
        )

    @staticmethod
    def verify_delegation(delegator: RoleContract, delegatee: RoleContract, current_depth: int) -> None:
        """Ensure delegation does not exceed bounds or assign work to unauthorized roles."""
        if current_depth >= delegator.max_delegation_depth:
            raise RolePermissionError(
                f"Delegation depth {current_depth} exceeds role '{delegator.title}' limit of {delegator.max_delegation_depth}."
            )

        # Ensure delegator is allowed to delegate to this role title or type
        if delegator.delegation_permissions and "*" not in delegator.delegation_permissions:
            if delegatee.title not in delegator.delegation_permissions and delegatee.role_type.value not in delegator.delegation_permissions:
                raise RolePermissionError(
                    f"Role '{delegator.title}' cannot delegate to '{delegatee.title}'. Allowed targets: {delegator.delegation_permissions}"
                )

    @staticmethod
    def verify_budget(role: RoleContract, requested_amount: float) -> None:
        """Ensure task resource allocation does not violate role budget limit."""
        if requested_amount > role.budget_limit:
            raise RolePermissionError(
                f"Requested budget ${requested_amount:.2f} exceeds role '{role.title}' limit of ${role.budget_limit:.2f}."
            )
