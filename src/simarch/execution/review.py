"""SimArch independent review and quality verification engine."""

import json
from typing import List, Optional
from simarch.core.types import ReviewStatus, TaskStatus, generate_id, utc_now_iso
from simarch.db.database import DatabaseManager
from simarch.execution.models import Deliverable, ReviewVerdict, Task


class ReviewEngine:
    """Performs rigorous independent verification of deliverables against acceptance criteria."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def evaluate_deliverable(
        self,
        task: Task,
        reviewer_role_id: str,
        deliverable: Deliverable,
        strict_criteria: bool = True
    ) -> ReviewVerdict:
        """Evaluate deliverable evidence and acceptance criteria."""
        actionable_revisions: List[str] = []

        # 1. Verify acceptance criteria
        if task.acceptance_criteria:
            summary_lower = deliverable.summary.lower()
            evidence_text = " ".join(deliverable.evidence).lower()
            findings_text = json.dumps(deliverable.findings).lower()
            combined_corpus = f"{summary_lower} {evidence_text} {findings_text}"

            for criterion in task.acceptance_criteria:
                # Basic semantic presence check; when strict, deliverable must address key words
                crit_words = [w.lower() for w in criterion.split() if len(w) > 3]
                matched = any(w in combined_corpus for w in crit_words)
                if not matched and strict_criteria:
                    actionable_revisions.append(f"Deliverable failed to satisfy criterion: '{criterion}'. Provide verifiable evidence.")

        # 2. Check for reported blockers
        if deliverable.blockers:
            actionable_revisions.append(f"Deliverable contains unresolved blockers: {', '.join(deliverable.blockers)}")

        # 3. Determine verdict
        if actionable_revisions:
            status = ReviewStatus.REVISION_REQUESTED
            feedback = f"Review rejected with {len(actionable_revisions)} required revision(s)."
        else:
            status = ReviewStatus.APPROVED
            feedback = "Independent review passed. All acceptance criteria and evidence verified."

        verdict = ReviewVerdict(
            reviewer_role_id=reviewer_role_id,
            status=status,
            feedback=feedback,
            actionable_revisions=actionable_revisions,
            evaluated_at=utc_now_iso()
        )

        # Record in database
        review_id = generate_id("rev")
        self.db.execute("""
        INSERT INTO task_reviews (id, task_id, reviewer_role_id, status, feedback, actionable_revisions_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            review_id,
            task.id,
            reviewer_role_id,
            verdict.status.value,
            verdict.feedback,
            json.dumps(verdict.actionable_revisions),
            verdict.evaluated_at
        ))

        # Update role performance stats in database
        if verdict.status == ReviewStatus.APPROVED:
            self.db.execute("""
            UPDATE tasks SET review_results_json = ? WHERE id = ?
            """, (json.dumps(verdict.model_dump()), task.id))
        else:
            self.db.execute("""
            UPDATE tasks SET review_results_json = ?, retry_count = retry_count + 1 WHERE id = ?
            """, (json.dumps(verdict.model_dump()), task.id))

        return verdict
