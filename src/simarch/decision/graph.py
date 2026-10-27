"""SimArch decision graph and binary alternative representation."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from simarch.db.database import DatabaseManager
from simarch.decision.models import DecisionRecord


class DecisionGraphNode(BaseModel):
    """Node in the organizational decision graph."""
    id: str
    objective: str
    chosen_option: Optional[str] = None
    alternatives_count: int
    children: List[str] = Field(default_factory=list)


class BinaryAlternativeBranch(BaseModel):
    """Binary decision tree branch for direct comparative inspection."""
    decision_id: str
    objective: str
    selected_option: str
    selected_score: float
    rejected_option: str
    rejected_score: float
    key_trade_off: str
    flip_condition: str


class DecisionGraphEngine:
    """Constructs directed decision graphs and binary comparison trees."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def link_decisions(self, parent_id: str, child_id: str, relation_type: str = "depends_on") -> None:
        """Create a directed edge between two decisions."""
        self.db.execute("""
        INSERT OR IGNORE INTO decision_edges (parent_id, child_id, relation_type)
        VALUES (?, ?, ?)
        """, (parent_id, child_id, relation_type))

    def get_decision_graph(self, project_id: str) -> Dict[str, Any]:
        """Return full directed decision graph with nodes and edges."""
        dec_rows = self.db.fetch_all("SELECT * FROM decisions WHERE project_id = ?", (project_id,))
        nodes = []
        for r in dec_rows:
            nodes.append({
                "id": r["id"],
                "objective": r["objective"],
                "chosen_option": r["chosen_option"],
                "status": r["status"],
                "created_at": r["created_at"]
            })

        edges = self.db.fetch_all("""
        SELECT e.parent_id, e.child_id, e.relation_type
        FROM decision_edges e
        JOIN decisions d ON d.id = e.parent_id
        WHERE d.project_id = ?
        """, (project_id,))

        return {
            "project_id": project_id,
            "nodes": nodes,
            "edges": [dict(e) for e in edges]
        }

    def get_binary_tree_view(self, decision: DecisionRecord) -> Optional[BinaryAlternativeBranch]:
        """Render a binary branch when decision compares two primary alternatives."""
        if len(decision.alternatives) < 2:
            return None

        ranked = sorted(decision.alternatives, key=lambda a: a.weighted_total_score, reverse=True)
        selected = ranked[0]
        runner_up = ranked[1]

        trade_off_desc = (
            f"Selected '{selected.name}' with score {selected.weighted_total_score} "
            f"over '{runner_up.name}' with score {runner_up.weighted_total_score}."
        )

        flip = (
            f"If {runner_up.name}'s cost dropped by "
            f"${max(0.0, runner_up.estimated_cost - selected.estimated_cost):,.2f} "
            f"or risk decreased from {runner_up.risk_level} to low."
        )

        return BinaryAlternativeBranch(
            decision_id=decision.id,
            objective=decision.objective,
            selected_option=selected.name,
            selected_score=selected.weighted_total_score,
            rejected_option=runner_up.name,
            rejected_score=runner_up.weighted_total_score,
            key_trade_off=trade_off_desc,
            flip_condition=flip
        )
