"""SimArch self-learning, staffing adaptation, and trend awareness."""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from simarch.core.types import generate_id, utc_now_iso
from simarch.db.database import DatabaseManager


class StaffingRecommendation(BaseModel):
    """Recommendation for staffing optimization based on empirical performance."""
    role_id: str
    role_title: str
    quality_score: float
    pass_rate_pct: float
    recommended_action: str  # promote, retain, reassign, adjust_budget


class TrendSignal(BaseModel):
    """External operational or industry signal influencing strategic planning."""
    id: str = Field(default_factory=lambda: generate_id("trend"))
    org_id: str
    topic: str
    summary: str
    source: str
    confidence: float
    expiration_date: str
    created_at: str = Field(default_factory=utc_now_iso)


class AdaptationEngine:
    """Implements company adaptation, staffing evaluation, and market trend tracking."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def evaluate_role_staffing(self, org_id: str) -> List[StaffingRecommendation]:
        """Empirically evaluate all roles in an organization using review and task history."""
        roles = self.db.fetch_all("SELECT * FROM roles WHERE org_id = ?", (org_id,))
        recommendations = []

        for r in roles:
            role_id = r["id"]
            # Fetch completed and failed tasks
            task_counts = self.db.fetch_all("""
            SELECT status, COUNT(*) as count FROM tasks WHERE assigned_role_id = ? GROUP BY status
            """, (role_id,))
            counts = {row["status"]: row["count"] for row in task_counts}

            completed = counts.get("COMPLETED", 0)
            failed = counts.get("FAILED", 0)
            total = completed + failed

            # Fetch review verdicts
            reviews = self.db.fetch_all("""
            SELECT tr.status, COUNT(*) as count
            FROM task_reviews tr
            JOIN tasks t ON t.id = tr.task_id
            WHERE t.assigned_role_id = ?
            GROUP BY tr.status
            """, (role_id,))
            rev_counts = {row["status"]: row["count"] for row in reviews}

            approved = rev_counts.get("approved", 0)
            rejected = rev_counts.get("rejected", 0) + rev_counts.get("revision_requested", 0)
            total_revs = approved + rejected

            pass_rate = (approved / total_revs * 100.0) if total_revs > 0 else 100.0
            quality = round(pass_rate / 100.0, 2)

            action = "retain"
            if total >= 3 and pass_rate >= 90.0:
                action = "promote"
            elif total >= 3 and pass_rate < 60.0:
                action = "adjust_supervision"

            recommendations.append(StaffingRecommendation(
                role_id=role_id,
                role_title=r["title"],
                quality_score=quality,
                pass_rate_pct=round(pass_rate, 1),
                recommended_action=action
            ))

        return recommendations

    def record_trend_signal(self, org_id: str, topic: str, summary: str, source: str, confidence: float = 0.85, expires_days: int = 90) -> TrendSignal:
        """Capture verifiable trend signal with provenance and expiration."""
        import datetime
        from simarch.core.types import utc_now
        expiry = (utc_now() + datetime.timedelta(days=expires_days)).isoformat()
        trend = TrendSignal(
            org_id=org_id,
            topic=topic,
            summary=summary,
            source=source,
            confidence=confidence,
            expiration_date=expiry
        )
        return trend
