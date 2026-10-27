"""SimArch task execution DAG and workflow engine."""

import json
from typing import Any, Dict, List, Optional, Set
from simarch.core.events import SystemEvent, default_event_bus
from simarch.core.exceptions import DependencyCycleError, TaskExecutionError
from simarch.core.types import (
    ReviewStatus,
    TaskPriority,
    TaskStatus,
    generate_id,
    utc_now_iso,
)
from simarch.db.database import DatabaseManager
from simarch.execution.models import Artifact, Deliverable, Project, ReviewVerdict, Task


class TaskEngine:
    """Manages the lifecycle, DAG dependencies, and status state machine for all tasks."""

    VALID_TRANSITIONS = {
        TaskStatus.PROPOSED: {TaskStatus.READY, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
        TaskStatus.BLOCKED: {TaskStatus.READY, TaskStatus.CANCELLED},
        TaskStatus.READY: {TaskStatus.ASSIGNED, TaskStatus.CANCELLED},
        TaskStatus.ASSIGNED: {TaskStatus.RUNNING, TaskStatus.READY, TaskStatus.CANCELLED},
        TaskStatus.RUNNING: {TaskStatus.REVIEW, TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.RETRYING, TaskStatus.CANCELLED},
        TaskStatus.REVIEW: {TaskStatus.COMPLETED, TaskStatus.RETRYING, TaskStatus.FAILED, TaskStatus.CANCELLED},
        TaskStatus.RETRYING: {TaskStatus.READY, TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED},
        TaskStatus.COMPLETED: set(),  # Terminal state
        TaskStatus.FAILED: {TaskStatus.RETRYING, TaskStatus.READY},
        TaskStatus.CANCELLED: set(),  # Terminal state
    }

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def create_project(self, org_id: str, name: str, objective: str, budget: float = 1000.0) -> Project:
        """Create a new strategic initiative project."""
        proj = Project(org_id=org_id, name=name, objective=objective, budget=budget)
        sql = """
        INSERT INTO projects (id, org_id, name, objective, status, budget, spent, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.execute(sql, (
            proj.id, proj.org_id, proj.name, proj.objective,
            proj.status, proj.budget, proj.spent, proj.created_at, proj.updated_at
        ))
        default_event_bus.publish(SystemEvent(
            event_type="project_created",
            source_component="TaskEngine",
            organization_id=org_id,
            project_id=proj.id,
            payload={"name": name, "objective": objective}
        ))
        return proj

    def get_project(self, project_id: str) -> Optional[Project]:
        """Fetch project by ID."""
        row = self.db.fetch_one("SELECT * FROM projects WHERE id = ?", (project_id,))
        if not row:
            return None
        return Project(**row)

    def add_task(self, task: Task) -> Task:
        """Add a task, validate DAG acyclicity, and set initial status based on dependencies."""
        # Check DAG acyclicity before insertion
        existing_tasks = self.get_project_tasks(task.project_id)
        self._detect_cycle(task, existing_tasks)

        # Check if all dependencies are already completed
        if task.dependencies:
            all_done = self._are_dependencies_met(task.dependencies)
            task.status = TaskStatus.READY if all_done else TaskStatus.BLOCKED
        else:
            task.status = TaskStatus.READY

        sql = """
        INSERT INTO tasks (
            id, project_id, org_id, assigned_role_id, owner_id, objective,
            inputs_json, acceptance_criteria_json, dependencies_json,
            priority, budget, status, deliverable_json, review_results_json,
            retry_count, lease_worker_id, lease_expires_at, heartbeat_at,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.execute(sql, (
            task.id, task.project_id, task.org_id, task.assigned_role_id, task.owner_id,
            task.objective, json.dumps(task.inputs), json.dumps(task.acceptance_criteria),
            json.dumps(task.dependencies), task.priority.value, task.budget,
            task.status.value,
            json.dumps(task.deliverable.model_dump()) if task.deliverable else None,
            json.dumps(task.review_results.model_dump()) if task.review_results else None,
            task.retry_count, task.lease_worker_id, task.lease_expires_at,
            task.heartbeat_at, task.created_at, task.updated_at
        ))

        default_event_bus.publish(SystemEvent(
            event_type="task_created",
            source_component="TaskEngine",
            organization_id=task.org_id,
            project_id=task.project_id,
            task_id=task.id,
            payload={"objective": task.objective, "status": task.status.value}
        ))
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Fetch and hydrate task by ID."""
        row = self.db.fetch_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if not row:
            return None
        return self._row_to_task(row)

    def get_project_tasks(self, project_id: str) -> List[Task]:
        """Fetch all tasks for a project ordered by creation time."""
        rows = self.db.fetch_all("SELECT * FROM tasks WHERE project_id = ? ORDER BY created_at ASC", (project_id,))
        return [self._row_to_task(r) for r in rows]

    def transition_task(self, task_id: str, new_status: TaskStatus, actor_id: str = "engine") -> Task:
        """Safely transition a task to a new state if valid in the state machine."""
        task = self.get_task(task_id)
        if not task:
            raise TaskExecutionError(f"Task with id '{task_id}' not found.")

        current_status = task.status
        allowed = self.VALID_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise TaskExecutionError(
                f"Invalid task transition from {current_status.value} to {new_status.value}. "
                f"Allowed target states: {[s.value for s in allowed]}"
            )

        before_state = task.model_dump()
        task.status = new_status
        task.updated_at = utc_now_iso()

        self.db.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
            (new_status.value, task.updated_at, task.id)
        )
        self.db.log_audit("task", task.id, actor_id, f"transition_{new_status.value.lower()}", before_state, task.model_dump())

        default_event_bus.publish(SystemEvent(
            event_type=f"task_{new_status.value.lower()}",
            source_component="TaskEngine",
            organization_id=task.org_id,
            project_id=task.project_id,
            task_id=task.id,
            payload={"old_status": current_status.value, "new_status": new_status.value}
        ))

        # If task reached COMPLETED, unblock downstream tasks in the DAG
        if new_status == TaskStatus.COMPLETED:
            self._unblock_downstream_tasks(task.project_id)

        return task

    def save_deliverable(self, task_id: str, deliverable: Deliverable) -> Task:
        """Attach verified deliverable and findings to task."""
        task = self.get_task(task_id)
        if not task:
            raise TaskExecutionError(f"Task '{task_id}' not found.")

        task.deliverable = deliverable
        task.updated_at = utc_now_iso()
        self.db.execute(
            "UPDATE tasks SET deliverable_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(deliverable.model_dump()), task.updated_at, task.id)
        )
        return task

    def add_artifact(self, artifact: Artifact) -> Artifact:
        """Record a concrete output artifact associated with a task/project."""
        sql = """
        INSERT INTO artifacts (id, task_id, project_id, name, artifact_type, storage_path, content_text, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.execute(sql, (
            artifact.id, artifact.task_id, artifact.project_id, artifact.name,
            artifact.artifact_type, artifact.storage_path, artifact.content_text,
            json.dumps(artifact.metadata), artifact.created_at
        ))
        return artifact

    def get_project_artifacts(self, project_id: str) -> List[Artifact]:
        """Fetch all artifacts produced in a project."""
        rows = self.db.fetch_all("SELECT * FROM artifacts WHERE project_id = ? ORDER BY created_at ASC", (project_id,))
        return [
            Artifact(
                id=r["id"],
                task_id=r["task_id"],
                project_id=r["project_id"],
                name=r["name"],
                artifact_type=r["artifact_type"],
                storage_path=r["storage_path"],
                content_text=r["content_text"],
                metadata=json.loads(r["metadata_json"]),
                created_at=r["created_at"]
            )
            for r in rows
        ]

    def _unblock_downstream_tasks(self, project_id: str) -> None:
        """Scan BLOCKED tasks in the project and promote to READY if all dependencies completed."""
        blocked_rows = self.db.fetch_all(
            "SELECT * FROM tasks WHERE project_id = ? AND status = ?",
            (project_id, TaskStatus.BLOCKED.value)
        )
        for r in blocked_rows:
            deps = json.loads(r["dependencies_json"])
            if self._are_dependencies_met(deps):
                self.transition_task(r["id"], TaskStatus.READY, actor_id="dag_resolver")

    def _are_dependencies_met(self, dep_task_ids: List[str]) -> bool:
        """Check if all prerequisite tasks are in COMPLETED status."""
        for dep_id in dep_task_ids:
            row = self.db.fetch_one("SELECT status FROM tasks WHERE id = ?", (dep_id,))
            if not row or row["status"] != TaskStatus.COMPLETED.value:
                return False
        return True

    def _detect_cycle(self, new_task: Task, existing_tasks: List[Task]) -> None:
        """Construct graph and ensure no circular dependency exists."""
        graph: Dict[str, List[str]] = {t.id: t.dependencies for t in existing_tasks}
        graph[new_task.id] = new_task.dependencies

        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                if dfs(node):
                    raise DependencyCycleError(
                        f"Circular dependency detected involving task '{new_task.id}' and dependencies {new_task.dependencies}"
                    )

    def _row_to_task(self, row: Dict[str, Any]) -> Task:
        """Convert database row to Task model."""
        deliverable = None
        if row.get("deliverable_json"):
            deliverable = Deliverable(**json.loads(row["deliverable_json"]))

        review_results = None
        if row.get("review_results_json"):
            review_results = ReviewVerdict(**json.loads(row["review_results_json"]))

        return Task(
            id=row["id"],
            project_id=row["project_id"],
            org_id=row["org_id"],
            assigned_role_id=row["assigned_role_id"],
            owner_id=row["owner_id"],
            objective=row["objective"],
            inputs=json.loads(row["inputs_json"]) if row.get("inputs_json") else {},
            acceptance_criteria=json.loads(row["acceptance_criteria_json"]) if row.get("acceptance_criteria_json") else [],
            dependencies=json.loads(row["dependencies_json"]) if row.get("dependencies_json") else [],
            priority=TaskPriority(row["priority"]),
            budget=row["budget"],
            status=TaskStatus(row["status"]),
            deliverable=deliverable,
            review_results=review_results,
            retry_count=row["retry_count"],
            lease_worker_id=row.get("lease_worker_id"),
            lease_expires_at=row.get("lease_expires_at"),
            heartbeat_at=row.get("heartbeat_at"),
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
