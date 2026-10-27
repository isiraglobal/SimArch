"""Tests for Execution Engine, Review, Messaging, and Scheduler (Items 4, 5, 6, 7, 8)."""

import pytest
from simarch.core.exceptions import DependencyCycleError, LeaseExpiredError, TaskExecutionError
from simarch.core.types import ReviewStatus, TaskPriority, TaskStatus
from simarch.db.database import DatabaseManager
from simarch.execution.communication import CommunicationEngine, Message
from simarch.execution.engine import TaskEngine
from simarch.execution.models import Deliverable, Task
from simarch.execution.review import ReviewEngine
from simarch.execution.scheduler import PersistentScheduler


def test_task_dag_acyclicity(temp_db: DatabaseManager, task_engine: TaskEngine):
    """Verify circular task dependencies are detected and rejected."""
    # Create valid setup
    temp_db.execute("INSERT INTO organizations (id, name, mission, created_at, updated_at) VALUES ('org1', 'O1', 'M1', '', '')")
    temp_db.execute("INSERT INTO roles (id, org_id, title, role_type, mission, created_at) VALUES ('r1', 'org1', 'Lead', 'specialist', 'M', '')")
    proj = task_engine.create_project("org1", "P1", "Obj1")

    t1 = Task(id="task_A", project_id=proj.id, org_id="org1", assigned_role_id="r1", objective="A")
    task_engine.add_task(t1)

    t2 = Task(id="task_B", project_id=proj.id, org_id="org1", assigned_role_id="r1", objective="B", dependencies=["task_A"])
    task_engine.add_task(t2)

    # Creating cycle: task_C depends on B, and A depends on C
    t3 = Task(id="task_C", project_id=proj.id, org_id="org1", assigned_role_id="r1", objective="C", dependencies=["task_B"])
    task_engine.add_task(t3)

    # Now attempt to add task that loops back
    t_cycle = Task(id="task_D", project_id=proj.id, org_id="org1", assigned_role_id="r1", objective="D", dependencies=["task_C"])
    # If task A had dependency on D:
    with pytest.raises(DependencyCycleError):
        # Manually verify cycle check
        task_engine._detect_cycle(Task(id="task_A", project_id=proj.id, org_id="org1", assigned_role_id="r1", objective="A", dependencies=["task_C"]), [t1, t2, t3])


def test_task_dependency_unblocking(temp_db: DatabaseManager, task_engine: TaskEngine):
    """Verify downstream tasks remain BLOCKED until all dependencies reach COMPLETED."""
    temp_db.execute("INSERT INTO organizations (id, name, mission, created_at, updated_at) VALUES ('org1', 'O1', 'M1', '', '')")
    temp_db.execute("INSERT INTO roles (id, org_id, title, role_type, mission, created_at) VALUES ('r1', 'org1', 'Lead', 'specialist', 'M', '')")
    proj = task_engine.create_project("org1", "P1", "Obj1")

    t1 = Task(id="t1", project_id=proj.id, org_id="org1", assigned_role_id="r1", objective="Task 1")
    task_engine.add_task(t1)

    t2 = Task(id="t2", project_id=proj.id, org_id="org1", assigned_role_id="r1", objective="Task 2", dependencies=["t1"])
    task_engine.add_task(t2)

    assert t1.status == TaskStatus.READY
    assert t2.status == TaskStatus.BLOCKED

    # Complete t1
    task_engine.transition_task(t1.id, TaskStatus.ASSIGNED)
    task_engine.transition_task(t1.id, TaskStatus.RUNNING)
    task_engine.transition_task(t1.id, TaskStatus.COMPLETED)

    # t2 should now be promoted to READY
    t2_updated = task_engine.get_task(t2.id)
    assert t2_updated.status == TaskStatus.READY


def test_independent_review_and_revision(temp_db: DatabaseManager, task_engine: TaskEngine, review_engine: ReviewEngine):
    """Verify review engine rejects deliverables missing required acceptance criteria."""
    temp_db.execute("INSERT INTO organizations (id, name, mission, created_at, updated_at) VALUES ('org1', 'O1', 'M1', '', '')")
    temp_db.execute("INSERT INTO roles (id, org_id, title, role_type, mission, created_at) VALUES ('r1', 'org1', 'Lead', 'specialist', 'M', '')")
    temp_db.execute("INSERT INTO roles (id, org_id, title, role_type, mission, created_at) VALUES ('r_auditor', 'org1', 'Auditor', 'auditor', 'M', '')")
    proj = task_engine.create_project("org1", "P1", "Obj1")

    task = Task(
        project_id=proj.id,
        org_id="org1",
        assigned_role_id="r1",
        objective="Implement security protocol",
        acceptance_criteria=["Zero vulnerabilities", "Run static analysis"]
    )
    task_engine.add_task(task)

    # Incomplete deliverable (missing criteria)
    bad_deliverable = Deliverable(
        summary="Done with some code.",
        evidence=["wrote basic files"]
    )
    verdict = review_engine.evaluate_deliverable(task, "r_auditor", bad_deliverable, strict_criteria=True)
    assert verdict.status == ReviewStatus.REVISION_REQUESTED
    assert len(verdict.actionable_revisions) > 0

    # Satisfying deliverable
    good_deliverable = Deliverable(
        summary="Completed security protocol. Passed static analysis with zero vulnerabilities found.",
        evidence=["Zero vulnerabilities verified in scan report", "Run static analysis passed"]
    )
    good_verdict = review_engine.evaluate_deliverable(task, "r_auditor", good_deliverable, strict_criteria=True)
    assert good_verdict.status == ReviewStatus.APPROVED


def test_persistent_lease_and_crash_recovery(temp_db: DatabaseManager, task_engine: TaskEngine, scheduler: PersistentScheduler):
    """Verify worker leases expire and stale tasks are recovered back to READY."""
    temp_db.execute("INSERT INTO organizations (id, name, mission, created_at, updated_at) VALUES ('org1', 'O1', 'M1', '', '')")
    temp_db.execute("INSERT INTO roles (id, org_id, title, role_type, mission, created_at) VALUES ('r1', 'org1', 'Lead', 'specialist', 'M', '')")
    proj = task_engine.create_project("org1", "P1", "Obj1")

    task = Task(project_id=proj.id, org_id="org1", assigned_role_id="r1", objective="Long calculation")
    task_engine.add_task(task)

    # Worker 1 claims task
    claimed = scheduler.claim_next_ready_task("worker_crash_victim", proj.id)
    assert claimed is not None
    assert claimed.id == task.id

    # Simulate crash: set lease_expires_at into the past
    temp_db.execute("UPDATE tasks SET lease_expires_at = '2000-01-01T00:00:00' WHERE id = ?", (task.id,))

    # Run crash recovery
    recovered_count = scheduler.recover_crashed_tasks()
    assert recovered_count == 1

    refreshed = task_engine.get_task(task.id)
    assert refreshed.status == TaskStatus.READY
    assert refreshed.retry_count == 1
    assert refreshed.lease_worker_id is None


def test_cross_functional_messaging(temp_db: DatabaseManager, comms_engine: CommunicationEngine):
    """Verify structured inter-role messaging."""
    temp_db.execute("INSERT INTO organizations (id, name, mission, created_at, updated_at) VALUES ('org1', 'O1', 'M1', '', '')")
    temp_db.execute("INSERT INTO roles (id, org_id, title, role_type, mission, created_at) VALUES ('r1', 'org1', 'CEO', 'executive', 'M', '')")
    temp_db.execute("INSERT INTO roles (id, org_id, title, role_type, mission, created_at) VALUES ('r2', 'org1', 'CTO', 'executive', 'M', '')")
    temp_db.execute("INSERT INTO projects (id, org_id, name, objective, created_at, updated_at) VALUES ('p1', 'org1', 'P', 'O', '', '')")

    msg = Message(
        project_id="p1",
        sender_role_id="r1",
        recipient_role_id="r2",
        message_type="inquiry",
        content="Please provide the technical specifications for Phase 1."
    )
    comms_engine.send_message(msg)

    # Fetch
    stored = temp_db.fetch_one("SELECT * FROM messages WHERE id = ?", (msg.id,))
    assert stored is not None
    assert stored["content"] == msg.content
