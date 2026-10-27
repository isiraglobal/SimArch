"""SimArch AI Tool Extension & Agentic Integration Kit.

Enables AI tools (Claude Code, Cursor, Antigravity, LangChain, CrewAI, AutoGen)
to interact directly with SimArch organizations, persistent workflows, decision
intelligence, world simulation, and on-demand localhost control.
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from simarch.api.server_manager import dashboard_manager
from simarch.core.config import get_settings
from simarch.core.types import MemoryScope, TaskPriority, TaskStatus
from simarch.db.database import DatabaseManager
from simarch.decision.counterfactual import CounterfactualAnalyzer
from simarch.decision.graph import DecisionGraphEngine
from simarch.decision.intelligence import DecisionIntelligence
from simarch.decision.models import DecisionAlternative, DecisionRecord, EvaluationCriterion
from simarch.execution.engine import TaskEngine
from simarch.execution.models import Artifact, Deliverable, Task
from simarch.execution.review import ReviewEngine
from simarch.execution.scheduler import PersistentScheduler
from simarch.memory.retrieval import ContextAssembler
from simarch.memory.scoped_memory import ScopedMemoryEngine
from simarch.org.formation import WorkforceFormationPlanner
from simarch.simulation.engine import SimulationEngine
from simarch.simulation.models import SimulationConfig, WorldState
from simarch.simulation.scenarios import ScenarioAnalyzer


class SimArchAIExtension:
    """Universal AI agent extension for SimArch autonomous organizations and simulation."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.settings = get_settings()
        self.db_path = db_path or self.settings.get_db_path()
        self.db = DatabaseManager(self.db_path)

        self.formation = WorkforceFormationPlanner(self.db)
        self.task_engine = TaskEngine(self.db)
        self.scheduler = PersistentScheduler(self.db, self.task_engine)
        self.review_engine = ReviewEngine(self.db)
        self.decision_intel = DecisionIntelligence(self.db)
        self.decision_graph = DecisionGraphEngine(self.db)
        self.sim_engine = SimulationEngine(self.db)
        self.scenario_analyzer = ScenarioAnalyzer(self.db, self.sim_engine)
        self.memory_engine = ScopedMemoryEngine(self.db)
        self.context_assembler = ContextAssembler(self.db, self.memory_engine)

    # -------------------------------------------------------------------------
    # Core Operations Callable by AI Agents
    # -------------------------------------------------------------------------

    def form_organization(self, name: str, objective: str, scale: str = "auto") -> Dict[str, Any]:
        """Form an autonomous organization with roles, contracts, and authority."""
        org = self.formation.synthesize_organization(name, objective, scale)
        return {
            "org_id": org.id,
            "name": org.name,
            "mission": org.mission,
            "roles": [
                {
                    "id": r.id,
                    "title": r.title,
                    "role_type": r.role_type.value,
                    "reports_to": r.reports_to_id,
                    "decision_authority": r.decision_authority,
                    "tool_permissions": r.tool_permissions,
                    "budget_limit": r.budget_limit
                }
                for r in org.roles.values()
            ]
        }

    def get_organization(self, org_id: str) -> Dict[str, Any]:
        """Retrieve hierarchy and role contracts for an organization."""
        org = self.formation.load_organization(org_id)
        if not org:
            return {"error": f"Organization '{org_id}' not found"}
        return {
            "id": org.id,
            "name": org.name,
            "mission": org.mission,
            "roles": [r.model_dump() for r in org.roles.values()]
        }

    def create_project(self, org_id: str, name: str, objective: str, budget: float = 1000.0) -> Dict[str, Any]:
        """Initialize a strategic project initiative."""
        proj = self.task_engine.create_project(org_id, name, objective, budget)
        return proj.model_dump()

    def create_task(
        self,
        project_id: str,
        org_id: str,
        assigned_role_id: str,
        objective: str,
        acceptance_criteria: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        priority: str = "normal",
        budget: float = 100.0
    ) -> Dict[str, Any]:
        """Add an accountable task to the project DAG."""
        task = Task(
            project_id=project_id,
            org_id=org_id,
            assigned_role_id=assigned_role_id,
            objective=objective,
            acceptance_criteria=acceptance_criteria or [],
            dependencies=dependencies or [],
            priority=TaskPriority(priority),
            budget=budget
        )
        saved = self.task_engine.add_task(task)
        return saved.model_dump()

    def list_tasks(self, project_id: str) -> Dict[str, Any]:
        """List all tasks in a project DAG with current states and blockers."""
        tasks = self.task_engine.get_project_tasks(project_id)
        return {"tasks": [t.model_dump() for t in tasks]}

    def claim_task(self, worker_id: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Claim the next ready task using an atomic database lease."""
        task = self.scheduler.claim_next_ready_task(worker_id, project_id)
        if not task:
            return {"task": None, "message": "No eligible READY tasks available."}
        self.task_engine.transition_task(task.id, TaskStatus.RUNNING, actor_id=worker_id)
        return {"task": task.model_dump(), "message": f"Claimed and marked RUNNING by {worker_id}."}

    def submit_deliverable(
        self,
        task_id: str,
        summary: str,
        findings: Optional[Dict[str, Any]] = None,
        evidence: Optional[List[str]] = None,
        artifacts: Optional[List[str]] = None,
        blockers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Submit verifiable deliverable evidence for a task."""
        deliverable = Deliverable(
            summary=summary,
            findings=findings or {},
            evidence=evidence or [],
            artifacts=artifacts or [],
            blockers=blockers or []
        )
        task = self.task_engine.get_task(task_id)
        if not task:
            return {"error": f"Task '{task_id}' not found."}

        # Advance state to RUNNING if task was READY or ASSIGNED
        if task.status == TaskStatus.READY:
            self.task_engine.transition_task(task_id, TaskStatus.ASSIGNED, actor_id="worker")
            self.task_engine.transition_task(task_id, TaskStatus.RUNNING, actor_id="worker")
        elif task.status == TaskStatus.ASSIGNED:
            self.task_engine.transition_task(task_id, TaskStatus.RUNNING, actor_id="worker")

        self.task_engine.save_deliverable(task_id, deliverable)
        self.task_engine.transition_task(task_id, TaskStatus.REVIEW, actor_id="worker")
        return {"task_id": task_id, "status": "REVIEW", "deliverable": deliverable.model_dump()}

    def review_deliverable(
        self,
        task_id: str,
        reviewer_role_id: str,
        strict_criteria: bool = True
    ) -> Dict[str, Any]:
        """Perform independent audit on submitted deliverable."""
        task = self.task_engine.get_task(task_id)
        if not task or not task.deliverable:
            return {"error": f"Task '{task_id}' has no deliverable submitted for review."}

        verdict = self.review_engine.evaluate_deliverable(task, reviewer_role_id, task.deliverable, strict_criteria)
        if verdict.status.value == "approved":
            self.task_engine.transition_task(task_id, TaskStatus.COMPLETED, actor_id=reviewer_role_id)
        else:
            self.task_engine.transition_task(task_id, TaskStatus.RETRYING, actor_id=reviewer_role_id)

        return verdict.model_dump()

    def evaluate_decision(
        self,
        project_id: str,
        org_id: str,
        owner_role_id: str,
        objective: str,
        criteria: List[Dict[str, Any]],
        alternatives: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate multi-criteria decision alternatives with winning rationale and binary tree."""
        crit_objs = [EvaluationCriterion(**c) for c in criteria]
        alt_objs = [DecisionAlternative(**a) for a in alternatives]

        record = DecisionRecord(
            project_id=project_id,
            org_id=org_id,
            owner_role_id=owner_role_id,
            objective=objective,
            criteria=crit_objs,
            alternatives=alt_objs
        )

        evaluated = self.decision_intel.evaluate_and_select(record)
        binary_branch = self.decision_graph.get_binary_tree_view(evaluated)

        return {
            "decision_id": evaluated.id,
            "chosen_option": evaluated.chosen_option,
            "reasons_for_selection": evaluated.reasons_for_selection,
            "binary_comparison": binary_branch.model_dump() if binary_branch else None,
            "record": evaluated.model_dump()
        }

    def get_decision(self, decision_id: str) -> Dict[str, Any]:
        """Fetch evaluated decision record by ID."""
        record = self.decision_intel.get_decision(decision_id)
        if not record:
            return {"error": f"Decision '{decision_id}' not found"}
        branch = self.decision_graph.get_binary_tree_view(record)
        return {
            "decision": record.model_dump(),
            "binary_branch": branch.model_dump() if branch else None
        }

    def compare_counterfactual(self, decision_id: str, alternate_option_name: str) -> Dict[str, Any]:
        """Compare actual chosen option with a hypothetical counterfactual option."""
        record = self.decision_intel.get_decision(decision_id)
        if not record:
            return {"error": f"Decision '{decision_id}' not found"}
        comp = CounterfactualAnalyzer.compare_counterfactual(record, alternate_option_name)
        return comp.model_dump()

    def run_simulation(
        self,
        project_id: str,
        name: str = "Scenario Model",
        duration_days: float = 365.0,
        marketing_budget: float = 5000.0,
        random_seed: int = 42
    ) -> Dict[str, Any]:
        """Run discrete-event simulation with causal feedback loops."""
        cfg = SimulationConfig(
            name=name,
            duration_days=duration_days,
            marketing_budget_monthly=marketing_budget,
            random_seed=random_seed
        )
        return self.sim_engine.run_simulation(project_id, cfg)

    def run_monte_carlo(
        self,
        project_id: str,
        name: str = "Monte Carlo Projections",
        duration_days: float = 365.0,
        marketing_budget: float = 5000.0,
        iterations: int = 20
    ) -> Dict[str, Any]:
        """Run Monte Carlo batch simulation to calculate risk percentiles (p10, p50, p90)."""
        cfg = SimulationConfig(
            name=name,
            duration_days=duration_days,
            marketing_budget_monthly=marketing_budget
        )
        return self.scenario_analyzer.run_monte_carlo(project_id, cfg, iterations)

    def store_memory(
        self,
        org_id: str,
        scope: str,
        scope_id: str,
        key: str,
        content: str,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Store scoped organizational knowledge atom with contradiction checking."""
        entry = self.memory_engine.store_memory(
            org_id=org_id,
            scope=MemoryScope(scope),
            scope_id=scope_id,
            key=key,
            content=content,
            project_id=project_id,
            provenance={"author": "ai_agent", "source": "agent_extension"}
        )
        return entry.model_dump()

    def retrieve_context(
        self,
        org_id: str,
        project_id: str,
        query: str,
        role_id: str = "system",
        max_tokens: int = 1500
    ) -> str:
        """Assemble relevant memories within token budget for an objective."""
        return self.context_assembler.assemble_context(org_id, project_id, query, role_id, max_tokens)

    def toggle_localhost(
        self,
        enable: bool,
        port: int = 8400,
        host: str = "127.0.0.1"
    ) -> Dict[str, Any]:
        """Allow AI agent to dynamically decide whether to spin up or lock down the localhost dashboard.

        By default, localhost is locked and dormant. If the AI agent determines that human visual inspection
        is helpful, it can call toggle_localhost(enable=True). When finished, it can call toggle_localhost(enable=False).
        """
        if enable:
            return dashboard_manager.start(host=host, port=port)
        else:
            return dashboard_manager.stop()

    def get_localhost_status(self) -> Dict[str, Any]:
        """Check whether the localhost dashboard is running or locked."""
        return dashboard_manager.get_status()

    # -------------------------------------------------------------------------
    # Tool Schemas for AI Agents (OpenAI, Anthropic, JSON Schema)
    # -------------------------------------------------------------------------

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return full standard tool definitions for AI tool callers."""
        return [
            {
                "name": "simarch_form_organization",
                "description": "Synthesizes an autonomous AI organization with roles, contracts, authority, and tool permissions from an objective.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Organization name"},
                        "objective": {"type": "string", "description": "High level mission statement"},
                        "scale": {"type": "string", "enum": ["auto", "compact", "standard", "enterprise"], "default": "auto"}
                    },
                    "required": ["name", "objective"]
                }
            },
            {
                "name": "simarch_create_task",
                "description": "Creates an accountable work task within a project DAG with acceptance criteria and dependencies.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID"},
                        "org_id": {"type": "string", "description": "Organization ID"},
                        "assigned_role_id": {"type": "string", "description": "Role ID responsible for the task"},
                        "objective": {"type": "string", "description": "Detailed task objective"},
                        "acceptance_criteria": {"type": "array", "items": {"type": "string"}, "description": "Verifiable acceptance criteria"},
                        "dependencies": {"type": "array", "items": {"type": "string"}, "description": "Prerequisite task IDs"},
                        "priority": {"type": "string", "enum": ["low", "normal", "high", "critical"], "default": "normal"},
                        "budget": {"type": "number", "default": 100.0}
                    },
                    "required": ["project_id", "org_id", "assigned_role_id", "objective"]
                }
            },
            {
                "name": "simarch_submit_deliverable",
                "description": "Submits verified findings and evidence for a completed task to initiate independent review.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task ID"},
                        "summary": {"type": "string", "description": "Summary of work completed"},
                        "findings": {"type": "object", "description": "Structured findings dictionary"},
                        "evidence": {"type": "array", "items": {"type": "string"}, "description": "Concrete proofs and verification statements"}
                    },
                    "required": ["task_id", "summary"]
                }
            },
            {
                "name": "simarch_evaluate_decision",
                "description": "Scores multi-criteria decision alternatives, chooses the optimal option, and outputs winning rationale with a binary tree.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID"},
                        "org_id": {"type": "string", "description": "Organization ID"},
                        "owner_role_id": {"type": "string", "description": "Role ID making the decision"},
                        "objective": {"type": "string", "description": "Decision goal"},
                        "criteria": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "weight": {"type": "number"},
                                    "description": {"type": "string"}
                                },
                                "required": ["name", "weight", "description"]
                            }
                        },
                        "alternatives": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "estimated_cost": {"type": "number"},
                                    "expected_benefit": {"type": "number"},
                                    "risk_level": {"type": "string"},
                                    "scores": {"type": "object"}
                                },
                                "required": ["name", "description", "scores"]
                            }
                        }
                    },
                    "required": ["project_id", "org_id", "owner_role_id", "objective", "criteria", "alternatives"]
                }
            },
            {
                "name": "simarch_run_simulation",
                "description": "Runs a discrete-event business simulation over time (months/years) evaluating cash, revenue, CAC, churn, and runway.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID"},
                        "name": {"type": "string", "default": "Scenario Run"},
                        "duration_days": {"type": "number", "default": 365.0},
                        "marketing_budget": {"type": "number", "default": 5000.0},
                        "random_seed": {"type": "integer", "default": 42}
                    },
                    "required": ["project_id"]
                }
            },
            {
                "name": "simarch_toggle_localhost",
                "description": "Decide whether to unlock and start the local HTTP dashboard server or keep it locked and dormant. Call enable=true only when human visual inspection is needed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "enable": {"type": "boolean", "description": "True to start local dashboard on 127.0.0.1, False to stop and lock it"},
                        "port": {"type": "integer", "default": 8400, "description": "Loopback port"}
                    },
                    "required": ["enable"]
                }
            }
        ]

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch and execute tool call from an AI agent."""
        clean_name = tool_name.replace("simarch_", "")

        handlers: Dict[str, Callable[..., Any]] = {
            "form_organization": lambda a: self.form_organization(a["name"], a["objective"], a.get("scale", "auto")),
            "get_organization": lambda a: self.get_organization(a["org_id"]),
            "create_project": lambda a: self.create_project(a["org_id"], a["name"], a["objective"], a.get("budget", 1000.0)),
            "create_task": lambda a: self.create_task(
                a["project_id"], a["org_id"], a["assigned_role_id"], a["objective"],
                a.get("acceptance_criteria"), a.get("dependencies"), a.get("priority", "normal"), a.get("budget", 100.0)
            ),
            "list_tasks": lambda a: self.list_tasks(a["project_id"]),
            "claim_task": lambda a: self.claim_task(a["worker_id"], a.get("project_id")),
            "submit_deliverable": lambda a: self.submit_deliverable(
                a["task_id"], a["summary"], a.get("findings"), a.get("evidence"), a.get("artifacts"), a.get("blockers")
            ),
            "review_deliverable": lambda a: self.review_deliverable(
                a["task_id"], a["reviewer_role_id"], a.get("strict_criteria", True)
            ),
            "evaluate_decision": lambda a: self.evaluate_decision(
                a["project_id"], a["org_id"], a["owner_role_id"], a["objective"], a["criteria"], a["alternatives"]
            ),
            "get_decision": lambda a: self.get_decision(a["decision_id"]),
            "compare_counterfactual": lambda a: self.compare_counterfactual(a["decision_id"], a["alternate_option_name"]),
            "run_simulation": lambda a: self.run_simulation(
                a["project_id"], a.get("name", "Scenario Run"), a.get("duration_days", 365.0),
                a.get("marketing_budget", 5000.0), a.get("random_seed", 42)
            ),
            "run_monte_carlo": lambda a: self.run_monte_carlo(
                a["project_id"], a.get("name", "Monte Carlo Projections"), a.get("duration_days", 365.0),
                a.get("marketing_budget", 5000.0), a.get("iterations", 20)
            ),
            "store_memory": lambda a: self.store_memory(
                a["org_id"], a["scope"], a["scope_id"], a["key"], a["content"], a.get("project_id")
            ),
            "retrieve_context": lambda a: {"context": self.retrieve_context(
                a["org_id"], a["project_id"], a["query"], a.get("role_id", "system"), a.get("max_tokens", 1500)
            )},
            "toggle_localhost": lambda a: self.toggle_localhost(a["enable"], a.get("port", 8400)),
            "get_localhost_status": lambda a: self.get_localhost_status()
        }

        handler = handlers.get(clean_name)
        if not handler:
            return {"error": f"Unknown SimArch tool: '{tool_name}'"}

        try:
            return handler(arguments)
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
