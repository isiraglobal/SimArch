"""SimArch first_organization end-to-end reproducible demonstration."""

import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from simarch.core.types import DecisionStatus, ReviewStatus, TaskPriority, TaskStatus
from simarch.db.database import DatabaseManager
from simarch.decision.counterfactual import CounterfactualAnalyzer
from simarch.decision.graph import DecisionGraphEngine
from simarch.decision.intelligence import DecisionIntelligence
from simarch.decision.models import DecisionAlternative, DecisionRecord, EvaluationCriterion
from simarch.execution.engine import TaskEngine
from simarch.execution.models import Artifact, Deliverable, Task
from simarch.execution.review import ReviewEngine
from simarch.execution.scheduler import PersistentScheduler
from simarch.org.formation import WorkforceFormationPlanner
from simarch.simulation.engine import SimulationEngine
from simarch.simulation.models import SimulationConfig

console = Console()


def run_first_organization_smoke_test(db_path: Path) -> dict:
    """Execute complete end-to-end organizational lifecycle with real execution and recovery."""
    console.print("\n[bold cyan]════════════════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]       SIMARCH END-TO-END DEMONSTRATION: FIRST ORGANIZATION         [/bold cyan]")
    console.print("[bold cyan]════════════════════════════════════════════════════════════════════[/bold cyan]\n")

    db = DatabaseManager(db_path)
    task_engine = TaskEngine(db)
    scheduler = PersistentScheduler(db, task_engine)
    formation = WorkforceFormationPlanner(db)
    decision_intel = DecisionIntelligence(db)
    decision_graph = DecisionGraphEngine(db)
    review_engine = ReviewEngine(db)
    sim_engine = SimulationEngine(db)

    # 1. Accept clear business objective
    objective = "Research autonomous AI architecture and implement an evidence-backed verification engine."
    console.print(f"[bold]Step 1: Business Objective:[/bold]\n  [italic]{objective}[/italic]\n")

    # 2 & 3. Construct proportionate organization
    org = formation.synthesize_organization(name="Nexus Research Labs", objective=objective, scale="compact")
    console.print(f"[bold green]Step 2: Organization Formed:[/bold green] {org.name} ({org.id})")
    for r in org.roles.values():
        console.print(f"  • [bold]{r.title}[/bold] ({r.role_type.value}) - Authority: {r.decision_authority}")

    coordinator = org.get_role_by_title("Project Coordinator") or list(org.roles.values())[0]
    engineer = org.get_role_by_title("Lead Software Engineer") or list(org.roles.values())[1]
    auditor = org.get_role_by_title("Quality & Verification Auditor") or list(org.roles.values())[-1]

    # 4. Create Project and Task Dependency Graph
    proj = task_engine.create_project(org.id, "SimArch Genesis", objective, budget=5000.0)
    console.print(f"\n[bold green]Step 3: Strategic Project Initialized:[/bold green] {proj.name} ({proj.id})")

    # Task 1: Research & Architectural Spec
    task_1 = Task(
        project_id=proj.id,
        org_id=org.id,
        assigned_role_id=engineer.id,
        objective="Design architectural specification and modular component contracts.",
        acceptance_criteria=["Document contracts", "Ensure zero circular dependencies"],
        priority=TaskPriority.HIGH,
        budget=1200.0
    )
    task_engine.add_task(task_1)

    # Task 2: Core Verification Implementation (depends on Task 1)
    task_2 = Task(
        project_id=proj.id,
        org_id=org.id,
        assigned_role_id=engineer.id,
        objective="Implement verification state machine and independent review protocol.",
        acceptance_criteria=["Pass unit tests", "Produce concrete deliverable findings"],
        dependencies=[task_1.id],
        priority=TaskPriority.CRITICAL,
        budget=2000.0
    )
    task_engine.add_task(task_2)

    console.print(f"  • Task 1 created: {task_1.objective} ([green]{task_1.status.value}[/green])")
    console.print(f"  • Task 2 created: {task_2.objective} ([yellow]{task_2.status.value}[/yellow] - waiting for Task 1)")

    # 5. Execute bounded work for Task 1
    worker_id = "worker_node_alpha"
    claimed_1 = scheduler.claim_next_ready_task(worker_id, proj.id)
    assert claimed_1 is not None and claimed_1.id == task_1.id
    task_engine.transition_task(task_1.id, TaskStatus.RUNNING, actor_id=worker_id)

    # Produce real deliverable and artifact
    d1 = Deliverable(
        summary="Completed specification defining modular contracts for Task, Memory, and Decision engines.",
        findings={"modules": ["org", "execution", "decision", "simulation"], "acyclic": True},
        evidence=["Document contracts verified", "Ensure zero circular dependencies validated in test suite"],
        artifacts=["arch_spec.md"]
    )
    task_engine.save_deliverable(task_1.id, d1)
    task_engine.add_artifact(Artifact(
        task_id=task_1.id,
        project_id=proj.id,
        name="arch_spec.md",
        artifact_type="document",
        content_text="# SimArch Architectural Specification\nModular Monolith with WAL SQLite"
    ))

    # 6. Independent Review of Task 1 Deliverable
    task_engine.transition_task(task_1.id, TaskStatus.REVIEW, actor_id=worker_id)
    verdict_1 = review_engine.evaluate_deliverable(task_1, auditor.id, d1)
    assert verdict_1.status == ReviewStatus.APPROVED
    task_engine.transition_task(task_1.id, TaskStatus.COMPLETED, actor_id=auditor.id)
    scheduler.release_lease(task_1.id, worker_id)

    console.print(f"\n[bold green]Step 4: Task 1 Delivered & Audited:[/bold green] [bold]APPROVED[/bold] by {auditor.title}")

    # Check that Task 2 was automatically unblocked by DAG engine!
    t2_refreshed = task_engine.get_task(task_2.id)
    assert t2_refreshed.status == TaskStatus.READY
    console.print(f"  • Task 2 status automatically promoted: [bold green]{t2_refreshed.status.value}[/bold green]")

    # 7 & 8. Decision Intelligence: Create Decision with Alternatives & Criteria
    dec = DecisionRecord(
        project_id=proj.id,
        org_id=org.id,
        owner_role_id=coordinator.id,
        objective="Select primary runtime persistence engine for digital workforce state.",
        criteria=[
            EvaluationCriterion(name="Operational Simplicity", weight=0.4, description="Zero external cluster setup required"),
            EvaluationCriterion(name="Performance & ACID Guarantees", weight=0.35, description="High throughput concurrency & WAL support"),
            EvaluationCriterion(name="Deployment Footprint", weight=0.25, description="Minimal memory and binary footprint")
        ],
        alternatives=[
            DecisionAlternative(
                name="SQLite with WAL & Thread-Safe Leases",
                description="Zero external dependencies, local-first file database with full ACID transactions.",
                estimated_cost=0.0,
                expected_benefit=9500.0,
                risk_level="low",
                scores={"Operational Simplicity": 9.5, "Performance & ACID Guarantees": 8.8, "Deployment Footprint": 9.8}
            ),
            DecisionAlternative(
                name="Distributed Multi-Node Cluster",
                description="High complexity distributed storage cluster requiring separate operational maintenance.",
                estimated_cost=15000.0,
                expected_benefit=7000.0,
                risk_level="high",
                scores={"Operational Simplicity": 3.0, "Performance & ACID Guarantees": 9.2, "Deployment Footprint": 2.5}
            )
        ]
    )
    evaluated_dec = decision_intel.evaluate_and_select(dec)
    branch = decision_graph.get_binary_tree_view(evaluated_dec)

    console.print(f"\n[bold green]Step 5: Decision Intelligence Evaluated:[/bold green]")
    console.print(f"  • Decision: {evaluated_dec.objective}")
    console.print(f"  • Selected Winner: [bold green]{evaluated_dec.chosen_option}[/bold green]")
    console.print(f"  • Rationale: {evaluated_dec.reasons_for_selection}")
    if branch:
        console.print(f"  • Binary Comparison vs Runner-up: {branch.rejected_option}")
        console.print(f"  • Flip Condition: {branch.flip_condition}")

    # Counterfactual evaluation
    cf = CounterfactualAnalyzer.compare_counterfactual(evaluated_dec, "Distributed Multi-Node Cluster")
    console.print(f"  • Counterfactual Cost Delta: {cf.variance_analysis['cost_difference']}")

    # 9. Discrete Event Simulation Run
    sim_cfg = SimulationConfig(name="Genesis 12-Month Projections", duration_days=365.0, marketing_budget_monthly=4500.0)
    sim_res = sim_engine.run_simulation(proj.id, sim_cfg)
    console.print(f"\n[bold green]Step 6: Discrete-Event Simulation Executed:[/bold green]")
    console.print(f"  • Simulated 365 Days: Final Cash = ${sim_res['outcomes']['final_cash']:,.2f}, Customers = {sim_res['outcomes']['final_customers']}")

    # 10. Crash & Restart Recovery Check
    console.print(f"\n[bold green]Step 7: Verifying Process Restart & Persistent Recovery:[/bold green]")
    # Simulate fresh process opening the database anew
    fresh_db = DatabaseManager(db_path)
    fresh_task_engine = TaskEngine(fresh_db)
    recovered_proj = fresh_task_engine.get_project(proj.id)
    recovered_tasks = fresh_task_engine.get_project_tasks(proj.id)

    assert recovered_proj is not None
    assert len(recovered_tasks) == 2
    assert recovered_tasks[0].status == TaskStatus.COMPLETED
    assert recovered_tasks[1].status == TaskStatus.READY

    console.print(f"  • Successfully recovered Project: {recovered_proj.name} ({recovered_proj.status})")
    console.print(f"  • Task 1 recovered in terminal state: {recovered_tasks[0].status.value}")
    console.print(f"  • Task 2 recovered in ready state: {recovered_tasks[1].status.value}")
    console.print(f"\n[bold green]✓ FIRST ORGANIZATION SMOKE TEST PASSED COMPREHENSIVELY.[/bold green]\n")

    return {
        "status": "PASSED",
        "org_id": org.id,
        "project_id": proj.id,
        "decision_id": evaluated_dec.id,
        "tasks_verified": len(recovered_tasks)
    }
