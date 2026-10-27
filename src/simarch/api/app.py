"""SimArch FastAPI application and REST service."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from simarch.core.config import get_settings
from simarch.core.events import default_event_bus
from simarch.core.types import RoleType, TaskPriority, TaskStatus
from simarch.db.database import DatabaseManager
from simarch.decision.counterfactual import CounterfactualAnalyzer
from simarch.decision.graph import DecisionGraphEngine
from simarch.decision.intelligence import DecisionIntelligence
from simarch.decision.models import DecisionAlternative, DecisionRecord, EvaluationCriterion
from simarch.execution.engine import TaskEngine
from simarch.execution.models import Task
from simarch.execution.scheduler import PersistentScheduler
from simarch.learning.adaptation import AdaptationEngine
from simarch.org.formation import WorkforceFormationPlanner
from simarch.simulation.engine import SimulationEngine
from simarch.simulation.models import SimulationConfig, WorldState

# Instantiate core application
app = FastAPI(
    title="SimArch API",
    description="Simulation Architecture - Autonomous AI Organizations & Persistent Workforce",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize subsystems
settings = get_settings()
db = DatabaseManager(settings.get_db_path())
task_engine = TaskEngine(db)
scheduler = PersistentScheduler(db, task_engine)
decision_intel = DecisionIntelligence(db)
decision_graph = DecisionGraphEngine(db)
sim_engine = SimulationEngine(db)
formation_planner = WorkforceFormationPlanner(db)
adaptation_engine = AdaptationEngine(db)

# Mount static and templates
UI_DIR = Path(__file__).parent.parent / "ui"
STATIC_DIR = UI_DIR / "static"
TEMPLATES_DIR = UI_DIR / "templates"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard() -> str:
    """Serve the single-page operational dashboard."""
    template_path = TEMPLATES_DIR / "index.html"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return "<h1>SimArch Dashboard</h1><p>Template not found.</p>"


@app.get("/api/overview")
async def get_overview() -> Dict[str, Any]:
    """Return consolidated operational metrics for the overview dashboard."""
    org_count = db.fetch_one("SELECT COUNT(*) as c FROM organizations")["c"]
    proj_count = db.fetch_one("SELECT COUNT(*) as c FROM projects")["c"]
    completed_tasks = db.fetch_one("SELECT COUNT(*) as c FROM tasks WHERE status = 'COMPLETED'")["c"]
    pending_tasks = db.fetch_one("SELECT COUNT(*) as c FROM tasks WHERE status NOT IN ('COMPLETED', 'FAILED', 'CANCELLED')")["c"]
    dec_count = db.fetch_one("SELECT COUNT(*) as c FROM decisions")["c"]

    recent_projects = db.fetch_all("SELECT * FROM projects ORDER BY created_at DESC LIMIT 5")
    recent_events = [e.model_dump() for e in default_event_bus.get_recent_events(limit=10)]

    return {
        "org_count": org_count,
        "project_count": proj_count,
        "tasks_completed": completed_tasks,
        "tasks_pending": pending_tasks,
        "decision_count": dec_count,
        "projects": recent_projects,
        "events": recent_events
    }


class OrgCreateRequest(BaseModel):
    name: str
    objective: str
    scale: str = "auto"


@app.post("/api/orgs")
async def create_organization(req: OrgCreateRequest) -> Dict[str, Any]:
    """Dynamically form and persist an organization based on an objective."""
    org = formation_planner.synthesize_organization(req.name, req.objective, req.scale)
    return {"status": "created", "organization": org.model_dump()}


@app.get("/api/roles")
async def list_roles() -> Dict[str, Any]:
    """List all corporate role contracts across organizations."""
    roles = db.fetch_all("SELECT * FROM roles ORDER BY created_at ASC")
    import json
    return {
        "roles": [
            {
                "id": r["id"],
                "org_id": r["org_id"],
                "title": r["title"],
                "role_type": r["role_type"],
                "reports_to_id": r["reports_to_id"],
                "mission": r["mission"],
                "decision_authority": json.loads(r["decision_authority_json"]),
                "tool_permissions": json.loads(r["tool_permissions_json"]),
                "budget_limit": r["budget_limit"]
            }
            for r in roles
        ]
    }


@app.get("/api/tasks")
async def list_tasks(project_id: Optional[str] = None) -> Dict[str, Any]:
    """List tasks, optionally filtered by project ID."""
    if project_id:
        tasks = task_engine.get_project_tasks(project_id)
    else:
        rows = db.fetch_all("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 50")
        tasks = [task_engine._row_to_task(r) for r in rows]

    return {"tasks": [t.model_dump() for t in tasks]}


class SimulationRunRequest(BaseModel):
    name: str = "Autonomous SaaS Model"
    duration_days: float = 365.0
    marketing_budget: float = 5000.0
    random_seed: int = 42


@app.post("/api/simulations/run")
async def run_simulation_endpoint(req: SimulationRunRequest) -> Dict[str, Any]:
    """Run discrete-event simulation scenario."""
    default_proj = db.fetch_one("SELECT id FROM projects LIMIT 1")
    if default_proj:
        proj_id = default_proj["id"]
    else:
        # Create default org and project to satisfy foreign key constraint
        default_org = db.fetch_one("SELECT id FROM organizations LIMIT 1")
        if not default_org:
            org = formation_planner.synthesize_organization("Simulation Lab", "World Simulation Sandbox", scale="compact")
            org_id = org.id
        else:
            org_id = default_org["id"]
        new_proj = task_engine.create_project(org_id, "Simulation Study", "Simulate strategic operational outcomes")
        proj_id = new_proj.id

    cfg = SimulationConfig(
        name=req.name,
        duration_days=req.duration_days,
        marketing_budget_monthly=req.marketing_budget,
        random_seed=req.random_seed
    )
    result = sim_engine.run_simulation(proj_id, cfg)
    return result


@app.get("/api/decisions")
async def list_decisions(project_id: Optional[str] = None) -> Dict[str, Any]:
    """List evaluated decisions."""
    if project_id:
        decs = decision_intel.get_project_decisions(project_id)
    else:
        rows = db.fetch_all("SELECT * FROM decisions ORDER BY created_at DESC LIMIT 50")
        decs = [decision_intel._row_to_record(r) for r in rows]

    return {"decisions": [d.model_dump() for d in decs]}


@app.get("/api/decisions/{decision_id}/binary-tree")
async def get_decision_binary_tree(decision_id: str) -> Dict[str, Any]:
    """Get binary alternative comparison branch for a decision."""
    dec = decision_intel.get_decision(decision_id)
    if not dec:
        raise HTTPException(status_code=404, detail="Decision not found")

    branch = decision_graph.get_binary_tree_view(dec)
    return {"branch": branch.model_dump() if branch else None}


@app.get("/api/decisions/{decision_id}/counterfactual")
async def get_decision_counterfactual(decision_id: str, alternate_name: str) -> Dict[str, Any]:
    """Evaluate counterfactual delta for a decision."""
    dec = decision_intel.get_decision(decision_id)
    if not dec:
        raise HTTPException(status_code=404, detail="Decision not found")

    comp = CounterfactualAnalyzer.compare_counterfactual(dec, alternate_name)
    return {"counterfactual": comp.model_dump()}


@app.get("/api/audit-log")
async def get_audit_log(limit: int = 50) -> Dict[str, Any]:
    """Fetch immutable audit records."""
    rows = db.fetch_all("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,))
    return {"audit_log": rows}
