"""SimArch persistent job scheduler, worker lease manager, and crash recovery."""

import datetime
from typing import List, Optional
from simarch.core.exceptions import LeaseExpiredError, TaskExecutionError
from simarch.core.types import TaskStatus, generate_id, utc_now, utc_now_iso
from simarch.db.database import DatabaseManager
from simarch.execution.engine import TaskEngine
from simarch.execution.models import Task


class PersistentScheduler:
    """Manages worker leases, persistent state recovery, and execution scheduling."""

    def __init__(self, db: DatabaseManager, task_engine: TaskEngine, lease_duration_seconds: int = 30) -> None:
        self.db = db
        self.task_engine = task_engine
        self.lease_duration_seconds = lease_duration_seconds

    def claim_next_ready_task(self, worker_id: str, project_id: Optional[str] = None) -> Optional[Task]:
        """Atomically claim the next eligible READY task using database leases."""
        now_str = utc_now_iso()
        lease_expiry = (utc_now() + datetime.timedelta(seconds=self.lease_duration_seconds)).isoformat()

        # Find eligible task
        query = "SELECT id FROM tasks WHERE status = 'READY'"
        params = []
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        query += " ORDER BY CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'normal' THEN 3 ELSE 4 END, created_at ASC LIMIT 1"

        candidate = self.db.fetch_one(query, params)
        if not candidate:
            return None

        task_id = candidate["id"]
        # Atomic lease claim
        with self.db.transaction() as cur:
            cur.execute("""
            UPDATE tasks
            SET status = 'ASSIGNED',
                lease_worker_id = ?,
                lease_expires_at = ?,
                heartbeat_at = ?,
                updated_at = ?
            WHERE id = ? AND status = 'READY'
            """, (worker_id, lease_expiry, now_str, now_str, task_id))

            if cur.rowcount == 0:
                return None  # Race condition: claimed by another worker

        return self.task_engine.get_task(task_id)

    def heartbeat(self, task_id: str, worker_id: str) -> None:
        """Extend lease for an actively running worker."""
        now = utc_now()
        now_str = now.isoformat()
        lease_expiry = (now + datetime.timedelta(seconds=self.lease_duration_seconds)).isoformat()

        with self.db.transaction() as cur:
            cur.execute("""
            UPDATE tasks
            SET lease_expires_at = ?,
                heartbeat_at = ?,
                updated_at = ?
            WHERE id = ? AND lease_worker_id = ? AND status IN ('ASSIGNED', 'RUNNING')
            """, (lease_expiry, now_str, now_str, task_id, worker_id))

            if cur.rowcount == 0:
                raise LeaseExpiredError(f"Worker '{worker_id}' lost lease on task '{task_id}'. Preempted or expired.")

    def release_lease(self, task_id: str, worker_id: str) -> None:
        """Release worker lease upon task completion, failure, or handoff."""
        now_str = utc_now_iso()
        self.db.execute("""
        UPDATE tasks
        SET lease_worker_id = NULL,
            lease_expires_at = NULL,
            updated_at = ?
        WHERE id = ? AND lease_worker_id = ?
        """, (now_str, task_id, worker_id))

    def recover_crashed_tasks(self) -> int:
        """Scan for abandoned leases, recover tasks, and re-enqueue or fail according to retry policies."""
        now_str = utc_now_iso()
        stale_rows = self.db.fetch_all("""
        SELECT * FROM tasks
        WHERE status IN ('ASSIGNED', 'RUNNING')
          AND lease_expires_at IS NOT NULL
          AND lease_expires_at < ?
        """, (now_str,))

        recovered_count = 0
        for row in stale_rows:
            task_id = row["id"]
            retries = row["retry_count"]
            if retries < 3:
                # Reset to READY for retry
                self.db.execute("""
                UPDATE tasks
                SET status = 'READY',
                    retry_count = retry_count + 1,
                    lease_worker_id = NULL,
                    lease_expires_at = NULL,
                    updated_at = ?
                WHERE id = ?
                """, (now_str, task_id))
                self.db.log_audit("task", task_id, "scheduler_recovery", "reclaimed_stale_lease",
                                  {"status": row["status"]}, {"status": "READY", "retry_count": retries + 1})
            else:
                # Max retries exceeded
                self.db.execute("""
                UPDATE tasks
                SET status = 'FAILED',
                    lease_worker_id = NULL,
                    lease_expires_at = NULL,
                    updated_at = ?
                WHERE id = ?
                """, (now_str, task_id))
                self.db.log_audit("task", task_id, "scheduler_recovery", "fail_stale_lease_exhausted",
                                  {"status": row["status"]}, {"status": "FAILED"})
            recovered_count += 1

        return recovered_count

    def pause_project(self, project_id: str) -> None:
        """Pause ongoing execution for a project."""
        now_str = utc_now_iso()
        self.db.execute("UPDATE projects SET status = 'PAUSED', updated_at = ? WHERE id = ?", (now_str, project_id))
        self.db.log_audit("project", project_id, "scheduler", "pause_project")

    def resume_project(self, project_id: str) -> None:
        """Resume execution for a paused project."""
        now_str = utc_now_iso()
        self.db.execute("UPDATE projects SET status = 'ACTIVE', updated_at = ? WHERE id = ?", (now_str, project_id))
        self.db.log_audit("project", project_id, "scheduler", "resume_project")

    def cancel_project(self, project_id: str) -> None:
        """Cancel project and all unfinished child tasks."""
        now_str = utc_now_iso()
        self.db.execute("UPDATE projects SET status = 'CANCELLED', updated_at = ? WHERE id = ?", (now_str, project_id))
        self.db.execute("""
        UPDATE tasks
        SET status = 'CANCELLED', updated_at = ?
        WHERE project_id = ? AND status NOT IN ('COMPLETED', 'FAILED')
        """, (now_str, project_id))
        self.db.log_audit("project", project_id, "scheduler", "cancel_project")
