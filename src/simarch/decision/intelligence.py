"""SimArch decision evaluation and rationale intelligence."""

import json
from typing import Any, Dict, List, Optional
from simarch.core.types import DecisionStatus, generate_id, utc_now_iso
from simarch.db.database import DatabaseManager
from simarch.decision.models import DecisionAlternative, DecisionRecord, EvaluationCriterion


class DecisionIntelligence:
    """Evaluates multi-criteria alternatives, selects the optimal choice, and records the rationale."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def evaluate_and_select(self, record: DecisionRecord) -> DecisionRecord:
        """Score alternatives using criteria weights, determine the winning option, and explain why."""
        if not record.alternatives:
            raise ValueError("Cannot evaluate a decision without at least two alternatives.")

        total_weight = sum(c.weight for c in record.criteria) or 1.0

        for alt in record.alternatives:
            weighted_sum = 0.0
            for crit in record.criteria:
                score = alt.scores.get(crit.name, 5.0)
                weighted_sum += score * crit.weight
            alt.weighted_total_score = round(weighted_sum / total_weight, 2)

        # Sort alternatives by weighted score descending
        ranked = sorted(record.alternatives, key=lambda a: a.weighted_total_score, reverse=True)
        winner = ranked[0]
        record.chosen_option = winner.name
        record.status = DecisionStatus.SELECTED

        # Record why rejected alternatives lost
        for alt in ranked[1:]:
            diff = round(winner.weighted_total_score - alt.weighted_total_score, 2)
            alt.rejected_reason = (
                f"Scored {alt.weighted_total_score:.2f} vs winner's {winner.weighted_total_score:.2f} (-{diff} pts). "
                f"Higher risk ({alt.risk_level}) or inferior criteria performance."
            )

        # Formulate grounded rationale
        record.reasons_for_selection = (
            f"Alternative '{winner.name}' achieved the highest weighted utility score ({winner.weighted_total_score:.2f}/10.0). "
            f"Expected benefit: ${winner.expected_benefit:,.2f} at estimated cost: ${winner.estimated_cost:,.2f} with {winner.risk_level} risk."
        )

        record.updated_at = utc_now_iso()
        self.save_decision(record)
        return record

    def save_decision(self, record: DecisionRecord) -> None:
        """Persist decision record to database."""
        sql = """
        INSERT OR REPLACE INTO decisions (
            id, project_id, org_id, owner_role_id, objective, chosen_option,
            alternatives_json, criteria_json, trade_offs_json, risks_json,
            evidence_json, status, reconsideration_conditions, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.execute(sql, (
            record.id, record.project_id, record.org_id, record.owner_role_id,
            record.objective, record.chosen_option,
            json.dumps([a.model_dump() for a in record.alternatives]),
            json.dumps([c.model_dump() for c in record.criteria]),
            json.dumps(record.trade_offs),
            json.dumps(record.risks),
            json.dumps(record.evidence),
            record.status.value,
            record.reconsideration_conditions,
            record.created_at,
            record.updated_at
        ))

    def get_decision(self, decision_id: str) -> Optional[DecisionRecord]:
        """Fetch decision record by ID."""
        row = self.db.fetch_one("SELECT * FROM decisions WHERE id = ?", (decision_id,))
        if not row:
            return None
        return self._row_to_record(row)

    def get_project_decisions(self, project_id: str) -> List[DecisionRecord]:
        """Fetch all decisions belonging to a project."""
        rows = self.db.fetch_all("SELECT * FROM decisions WHERE project_id = ? ORDER BY created_at ASC", (project_id,))
        return [self._row_to_record(r) for r in rows]

    def _row_to_record(self, row: Dict[str, Any]) -> DecisionRecord:
        """Convert database row to DecisionRecord model."""
        alts = [DecisionAlternative(**a) for a in json.loads(row["alternatives_json"])]
        crits = [EvaluationCriterion(**c) for c in json.loads(row["criteria_json"])]
        return DecisionRecord(
            id=row["id"],
            project_id=row["project_id"],
            org_id=row["org_id"],
            owner_role_id=row["owner_role_id"],
            objective=row["objective"],
            chosen_option=row["chosen_option"],
            alternatives=alts,
            criteria=crits,
            trade_offs=json.loads(row["trade_offs_json"]),
            risks=json.loads(row["risks_json"]),
            evidence=json.loads(row["evidence_json"]),
            status=DecisionStatus(row["status"]),
            reconsideration_conditions=row["reconsideration_conditions"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
