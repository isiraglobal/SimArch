"""SimArch controlled self-improvement loop."""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from simarch.core.exceptions import SecurityViolationError
from simarch.core.types import generate_id, utc_now_iso
from simarch.db.database import DatabaseManager


class ImprovementProposal(BaseModel):
    """Structured proposal for optimizing a workflow, prompt, or role parameter."""
    id: str = Field(default_factory=lambda: generate_id("imp"))
    org_id: str
    category: str  # workflow, prompt_template, role_specification, routing_rule
    proposal: Dict[str, Any]
    baseline_metrics: Dict[str, float]
    evaluated_metrics: Dict[str, float] = Field(default_factory=dict)
    status: str = "PROPOSED"  # PROPOSED, EVALUATING, APPROVED, DEPLOYED, REJECTED, ROLLED_BACK
    version: int = 1
    created_at: str = Field(default_factory=utc_now_iso)
    deployed_at: Optional[str] = None


class ControlledImprovementEngine:
    """Manages the OBSERVE -> PROPOSE -> EVALUATE -> APPROVE -> VERSION -> DEPLOY -> MONITOR -> ROLLBACK lifecycle."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def propose_change(
        self,
        org_id: str,
        category: str,
        proposal: Dict[str, Any],
        baseline_metrics: Dict[str, float]
    ) -> ImprovementProposal:
        """Create a new improvement proposal, guarding against unauthorized security modifications."""
        # Security invariant: self-improvement cannot alter permissions, auth, or core policies
        forbidden_keys = ["permissions", "security", "auth", "bypass", "drop", "admin_override"]
        prop_str = json.dumps(proposal).lower()
        if any(k in prop_str for k in forbidden_keys):
            raise SecurityViolationError("Self-improvement proposal cannot modify security, auth, or permission bounds.")

        item = ImprovementProposal(
            org_id=org_id,
            category=category,
            proposal=proposal,
            baseline_metrics=baseline_metrics,
            status="PROPOSED"
        )

        sql = """
        INSERT INTO learning_proposals (id, org_id, category, proposal_json, baseline_metrics_json, evaluated_metrics_json, status, version, created_at, deployed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.execute(sql, (
            item.id, item.org_id, item.category, json.dumps(item.proposal),
            json.dumps(item.baseline_metrics), json.dumps(item.evaluated_metrics),
            item.status, item.version, item.created_at, item.deployed_at
        ))
        return item

    def evaluate_proposal(self, proposal_id: str, simulated_metrics: Dict[str, float]) -> ImprovementProposal:
        """Evaluate proposal against baseline. If metrics improve, approve for deployment."""
        row = self.db.fetch_one("SELECT * FROM learning_proposals WHERE id = ?", (proposal_id,))
        if not row:
            raise ValueError(f"Proposal '{proposal_id}' not found.")

        baseline = json.loads(row["baseline_metrics_json"])
        # Check if key metric (e.g. latency, quality) improved
        improved = True
        if "quality" in simulated_metrics and "quality" in baseline:
            if simulated_metrics["quality"] < baseline["quality"]:
                improved = False
        if "latency" in simulated_metrics and "latency" in baseline:
            if simulated_metrics["latency"] > baseline["latency"]:
                improved = False

        status = "APPROVED" if improved else "REJECTED"
        self.db.execute("""
        UPDATE learning_proposals
        SET evaluated_metrics_json = ?, status = ?
        WHERE id = ?
        """, (json.dumps(simulated_metrics), status, proposal_id))

        return self.get_proposal(proposal_id)

    def deploy_proposal(self, proposal_id: str) -> ImprovementProposal:
        """Deploy an approved improvement proposal."""
        row = self.db.fetch_one("SELECT * FROM learning_proposals WHERE id = ?", (proposal_id,))
        if not row or row["status"] != "APPROVED":
            raise ValueError("Only APPROVED proposals can be deployed.")

        now_str = utc_now_iso()
        self.db.execute("""
        UPDATE learning_proposals
        SET status = 'DEPLOYED', deployed_at = ?, version = version + 1
        WHERE id = ?
        """, (now_str, proposal_id))

        self.db.log_audit("proposal", proposal_id, "improvement_engine", "deploy_proposal")
        return self.get_proposal(proposal_id)

    def rollback_proposal(self, proposal_id: str) -> ImprovementProposal:
        """Roll back a deployed proposal to the previous baseline version."""
        self.db.execute("""
        UPDATE learning_proposals
        SET status = 'ROLLED_BACK'
        WHERE id = ? AND status = 'DEPLOYED'
        """, (proposal_id,))

        self.db.log_audit("proposal", proposal_id, "improvement_engine", "rollback_proposal")
        return self.get_proposal(proposal_id)

    def get_proposal(self, proposal_id: str) -> Optional[ImprovementProposal]:
        """Fetch proposal by ID."""
        row = self.db.fetch_one("SELECT * FROM learning_proposals WHERE id = ?", (proposal_id,))
        if not row:
            return None
        return ImprovementProposal(
            id=row["id"],
            org_id=row["org_id"],
            category=row["category"],
            proposal=json.loads(row["proposal_json"]),
            baseline_metrics=json.loads(row["baseline_metrics_json"]),
            evaluated_metrics=json.loads(row["evaluated_metrics_json"]),
            status=row["status"],
            version=row["version"],
            created_at=row["created_at"],
            deployed_at=row["deployed_at"]
        )
