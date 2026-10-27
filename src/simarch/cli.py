"""SimArch Command-Line Interface (CLI)."""

import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from simarch import __version__
from simarch.core.config import get_settings
from simarch.core.types import DecisionStatus, TaskPriority, TaskStatus
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
from simarch.simulation.models import SimulationConfig, WorldState

app = typer.Typer(
    name="simarch",
    help="SimArch: Simulation Architecture for Autonomous AI Organizations & Digital Workforce",
    add_completion=False
)
console = Console()


def _get_services():
    settings = get_settings()
    db = DatabaseManager(settings.get_db_path())
    task_engine = TaskEngine(db)
    scheduler = PersistentScheduler(db, task_engine)
    formation = WorkforceFormationPlanner(db)
    decision_intel = DecisionIntelligence(db)
    decision_graph = DecisionGraphEngine(db)
    sim_engine = SimulationEngine(db)
    review_engine = ReviewEngine(db)
    return db, task_engine, scheduler, formation, decision_intel, decision_graph, sim_engine, review_engine


@app.command()
def version():
    """Display current SimArch release version."""
    console.print(f"[bold cyan]SimArch[/bold cyan] version [bold green]{__version__}[/bold green]")


@app.command()
def init(
    path: Optional[Path] = typer.Option(None, help="Custom directory path for SimArch data storage.")
):
    """Initialize local SimArch workspace, SQLite WAL database, and directories."""
    settings = get_settings()
    if path:
        settings.home_dir = path
    db_path = settings.get_db_path()
    ws_dir = settings.get_workspace_dir()

    db = DatabaseManager(db_path)
    console.print(Panel(
        f"[bold green]SimArch Workspace Initialized[/bold green]\n"
        f"Database: [cyan]{db_path}[/cyan]\n"
        f"Workspaces: [cyan]{ws_dir}[/cyan]\n"
        f"Storage Mode: [bold]SQLite WAL Mode with Foreign Keys[/bold]",
        title="SimArch System Initialization"
    ))


# Org Subcommands
org_app = typer.Typer(help="Manage autonomous organizations and dynamic role contracts.")
app.add_typer(org_app, name="org")


@org_app.command("create")
def org_create(
    name: str = typer.Option(..., "--name", "-n", help="Name of the organization."),
    objective: str = typer.Option(..., "--objective", "-o", help="Mission statement or objective."),
    scale: str = typer.Option("auto", "--scale", "-s", help="Organization scale: auto, compact, standard, enterprise.")
):
    """Form a new organization and generate proportionate role contracts."""
    db, _, _, formation, _, _, _, _ = _get_services()
    org = formation.synthesize_organization(name, objective, scale)

    table = Table(title=f"Organization Formed: {org.name} ({org.id})")
    table.add_column("Role Title", style="cyan", no_wrap=True)
    table.add_column("Tier", style="magenta")
    table.add_column("Reports To", style="dim")
    table.add_column("Decision Authority", style="green")
    table.add_column("Tool Permissions", style="yellow")
    table.add_column("Budget Limit", justify="right")

    for r in org.roles.values():
        table.add_row(
            r.title,
            r.role_type.value,
            r.reports_to_id or "Root",
            ", ".join(r.decision_authority[:2]),
            ", ".join(r.tool_permissions[:3]),
            f"${r.budget_limit:,.2f}"
        )

    console.print(table)


@org_app.command("list")
def org_list():
    """List all persisted organizations."""
    db, _, _, _, _, _, _, _ = _get_services()
    orgs = db.fetch_all("SELECT * FROM organizations ORDER BY created_at DESC")

    table = Table(title="Persisted Organizations")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold cyan")
    table.add_column("Mission", style="white")
    table.add_column("Created", style="dim")

    for o in orgs:
        table.add_row(o["id"], o["name"], o["mission"], o["created_at"])

    console.print(table)


# Project Subcommands
proj_app = typer.Typer(help="Manage strategic initiatives and tasks.")
app.add_typer(proj_app, name="project")


@proj_app.command("start")
def project_start(
    org_id: str = typer.Option(..., "--org", help="Organization ID."),
    name: str = typer.Option(..., "--name", "-n", help="Project name."),
    objective: str = typer.Option(..., "--objective", "-o", help="Project objective."),
    budget: float = typer.Option(1000.0, "--budget", "-b", help="Resource budget.")
):
    """Initialize a new strategic project."""
    _, task_engine, _, _, _, _, _, _ = _get_services()
    proj = task_engine.create_project(org_id, name, objective, budget)
    console.print(f"[bold green]Project started successfully:[/bold green] ID [bold cyan]{proj.id}[/bold cyan]")


@proj_app.command("status")
def project_status(project_id: str = typer.Argument(..., help="Project ID.")):
    """Inspect project progress, tasks, and deliverables."""
    _, task_engine, _, _, _, _, _, _ = _get_services()
    proj = task_engine.get_project(project_id)
    if not proj:
        console.print(f"[red]Project '{project_id}' not found.[/red]")
        raise typer.Exit(code=1)

    tasks = task_engine.get_project_tasks(project_id)
    console.print(Panel(
        f"Name: [bold]{proj.name}[/bold]\n"
        f"Objective: {proj.objective}\n"
        f"Status: [bold cyan]{proj.status}[/bold cyan] | Budget: ${proj.budget:,.2f} (Spent: ${proj.spent:,.2f})",
        title=f"Project Status: {proj.id}"
    ))

    table = Table(title="Project Tasks")
    table.add_column("ID", style="dim")
    table.add_column("Objective", style="white")
    table.add_column("Role", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Retries", justify="right")

    for t in tasks:
        color = "green" if t.status == TaskStatus.COMPLETED else "yellow" if t.status == TaskStatus.RUNNING else "white"
        table.add_row(t.id, t.objective, t.assigned_role_id, f"[{color}]{t.status.value}[/{color}]", str(t.retry_count))

    console.print(table)


@proj_app.command("pause")
def project_pause(project_id: str = typer.Argument(..., help="Project ID.")):
    """Pause ongoing execution of a project."""
    _, _, scheduler, _, _, _, _, _ = _get_services()
    scheduler.pause_project(project_id)
    console.print(f"[bold yellow]Project '{project_id}' paused.[/bold yellow]")


@proj_app.command("resume")
def project_resume(project_id: str = typer.Argument(..., help="Project ID.")):
    """Resume execution of a paused project."""
    _, _, scheduler, _, _, _, _, _ = _get_services()
    scheduler.resume_project(project_id)
    console.print(f"[bold green]Project '{project_id}' resumed.[/bold green]")


# Decision Subcommands
dec_app = typer.Typer(help="Manage decision intelligence records and graphs.")
app.add_typer(dec_app, name="decision")


@dec_app.command("inspect")
def decision_inspect(decision_id: str = typer.Argument(..., help="Decision ID.")):
    """Inspect full audit record and winning rationale for a decision."""
    _, _, _, _, decision_intel, decision_graph, _, _ = _get_services()
    dec = decision_intel.get_decision(decision_id)
    if not dec:
        console.print(f"[red]Decision '{decision_id}' not found.[/red]")
        raise typer.Exit(code=1)

    console.print(Panel(
        f"Objective: [bold]{dec.objective}[/bold]\n"
        f"Winner: [bold green]{dec.chosen_option}[/bold green]\n"
        f"Status: {dec.status.value}\n\n"
        f"[bold]Winning Rationale:[/bold]\n{dec.reasons_for_selection}",
        title=f"Decision Intelligence Record: {dec.id}"
    ))

    # Binary tree view
    branch = decision_graph.get_binary_tree_view(dec)
    if branch:
        console.print(Panel(
            f"Selected: [bold green]{branch.selected_option}[/bold green] (Score: {branch.selected_score:.2f})\n"
            f"Runner-up: [red]{branch.rejected_option}[/red] (Score: {branch.rejected_score:.2f})\n\n"
            f"Trade-off: {branch.key_trade_off}\n"
            f"Flip Condition: [italic]{branch.flip_condition}[/italic]",
            title="Binary Decision Tree View"
        ))


# Simulation Subcommand
sim_app = typer.Typer(help="Run discrete-event simulations and scenario comparisons.")
app.add_typer(sim_app, name="sim")


@sim_app.command("run")
def sim_run(
    project_id: str = typer.Option("proj_sim", "--project", help="Associated project ID."),
    name: str = typer.Option("SaaS Business Model", "--name", "-n", help="Simulation name."),
    duration: float = typer.Option(365.0, "--duration", "-d", help="Simulated duration in days."),
    marketing: float = typer.Option(5000.0, "--marketing", "-m", help="Monthly marketing budget.")
):
    """Execute a discrete-event simulation."""
    _, _, _, _, _, _, sim_engine, _ = _get_services()
    cfg = SimulationConfig(name=name, duration_days=duration, marketing_budget_monthly=marketing)
    res = sim_engine.run_simulation(project_id, cfg)
    out = res["outcomes"]

    console.print(Panel(
        f"Simulated Days: [bold]{res['config']['duration_days']}[/bold]\n"
        f"Ending Cash: [bold green]${out['final_cash']:,.2f}[/bold green]\n"
        f"Monthly Revenue: [bold cyan]${out['final_monthly_revenue']:,.2f}[/bold cyan]\n"
        f"Customers: [bold]{out['final_customers']}[/bold]\n"
        f"Product Readiness: [bold]{out['final_product_readiness']}%[/bold]\n"
        f"Financial Survival: [bold]{'SURVIVED / SOLVENT' if out['survived'] else 'INSOLVENT'}[/bold]",
        title=f"Simulation Complete: {name}"
    ))


# First Organization Smoke Test
@app.command("smoke-test")
def smoke_test():
    """Run the complete end-to-end reproducible first_organization smoke test."""
    from simarch.execution.smoke_test import run_first_organization_smoke_test
    db_path = get_settings().get_db_path()
    run_first_organization_smoke_test(db_path)


# Serve Subcommand
@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host."),
    port: int = typer.Option(8400, "--port", "-p", help="Bind port.")
):
    """Launch the SimArch operational dashboard and REST API service."""
    import uvicorn
    console.print(f"[bold green]Starting SimArch Operational Dashboard[/bold green] on [cyan]http://{host}:{port}[/cyan]")
    uvicorn.run("simarch.api.app:app", host=host, port=port, log_level="info")


# MCP Server Subcommand for AI Tools
@app.command("mcp")
def mcp():
    """Launch the Model Context Protocol (MCP) stdio server for direct AI tool integration."""
    from simarch.mcp.server import main as mcp_main
    mcp_main()


# AI Extension Configuration Helper
@app.command("extension-config")
def extension_config():
    """Print ready-to-use configuration snippets to hardwire SimArch as an extension in AI tools."""
    claude_mcp = {
        "mcpServers": {
            "simarch": {
                "command": "simarch-mcp",
                "args": []
            }
        }
    }

    cursor_mcp = {
        "mcpServers": {
            "simarch": {
                "command": "simarch",
                "args": ["mcp"]
            }
        }
    }

    console.print(Panel(
        f"[bold cyan]Hardwire SimArch as an AI Extension[/bold cyan]\n\n"
        f"[bold]1. For Claude Code / Claude Desktop ([code]claude_desktop_config.json[/code]):[/bold]\n"
        f"[green]{json.dumps(claude_mcp, indent=2)}[/green]\n\n"
        f"[bold]2. For Cursor / Antigravity ([code].cursor/mcp.json[/code] or [code].mcp.json[/code]):[/bold]\n"
        f"[green]{json.dumps(cursor_mcp, indent=2)}[/green]\n\n"
        f"[bold]3. Localhost Locking Policy:[/bold]\n"
        f"By default, localhost is [bold red]LOCKED & DORMANT[/bold red] with zero listening ports.\n"
        f"The AI agent can invoke [cyan]simarch_toggle_localhost(enable=True)[/cyan] only when human visual inspection is needed.",
        title="SimArch AI Extension Setup"
    ))


# Dashboard Locking & Localhost Controller Subcommand
dash_app = typer.Typer(help="Control and inspect the on-demand localhost dashboard server.")
app.add_typer(dash_app, name="dashboard")


@dash_app.command("status")
def dash_status():
    """Check whether the localhost dashboard is active or locked."""
    from simarch.api.server_manager import dashboard_manager
    status = dashboard_manager.get_status()
    if status["active"]:
        console.print(f"[bold green]Dashboard is ACTIVE[/bold green] at [cyan]{status['url']}[/cyan]")
    else:
        console.print("[bold yellow]Localhost is LOCKED & DORMANT[/bold yellow] (no ports listening).")


@dash_app.command("start")
def dash_start(
    port: int = typer.Option(8400, "--port", "-p", help="Port to bind to on loopback.")
):
    """Unlock and start the localhost dashboard server."""
    from simarch.api.server_manager import dashboard_manager
    res = dashboard_manager.start(host="127.0.0.1", port=port)
    console.print(f"[bold green]{res['message']}[/bold green]")


@dash_app.command("stop")
def dash_stop():
    """Stop the dashboard server and lock localhost."""
    from simarch.api.server_manager import dashboard_manager
    res = dashboard_manager.stop()
    console.print(f"[bold yellow]{res['message']}[/bold yellow]")


if __name__ == "__main__":
    app()
