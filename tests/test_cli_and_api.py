"""Tests for Importability, CLI, REST API, and End-to-End Execution (Items 1, 16, 17, 20)."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner
import simarch
from simarch.api.app import app
from simarch.cli import app as cli_app
from simarch.execution.smoke_test import run_first_organization_smoke_test


def test_package_importability():
    """Verify package import and version metadata."""
    assert simarch.__version__ == "0.1.0"


def test_cli_version_and_init(tmp_path: Path):
    """Verify CLI basic initialization and version commands."""
    runner = CliRunner()

    v_res = runner.invoke(cli_app, ["version"])
    assert v_res.exit_code == 0
    assert "0.1.0" in v_res.output

    init_res = runner.invoke(cli_app, ["init", "--path", str(tmp_path)])
    assert init_res.exit_code == 0
    assert "SimArch Workspace Initialized" in init_res.output


def test_cli_org_and_project_lifecycle(tmp_path: Path, monkeypatch):
    """Verify CLI organization creation and project status inspection."""
    monkeypatch.setenv("SIMARCH_HOME", str(tmp_path))
    runner = CliRunner()

    org_res = runner.invoke(cli_app, ["org", "create", "--name", "CLI Ventures", "--objective", "Develop AI"])
    assert org_res.exit_code == 0
    assert "Organization Formed" in org_res.output

    list_res = runner.invoke(cli_app, ["org", "list"])
    assert list_res.exit_code == 0
    assert "CLI Ventures" in list_res.output


def test_api_endpoints():
    """Verify FastAPI endpoints serve real data and simulation results."""
    client = TestClient(app)

    # 1. Root dashboard HTML
    root_res = client.get("/")
    assert root_res.status_code == 200
    assert "SimArch" in root_res.text

    # 2. Overview metrics
    ov_res = client.get("/api/overview")
    assert ov_res.status_code == 200
    data = ov_res.json()
    assert "org_count" in data
    assert "tasks_completed" in data

    # 3. Create Org via API
    create_res = client.post("/api/orgs", json={
        "name": "API Enterprise",
        "objective": "Build automated intelligence pipelines",
        "scale": "compact"
    })
    assert create_res.status_code == 200
    org_data = create_res.json()
    assert org_data["status"] == "created"
    assert org_data["organization"]["name"] == "API Enterprise"

    # 4. Run Simulation via API
    sim_res = client.post("/api/simulations/run", json={
        "name": "Test Simulation Run",
        "duration_days": 180,
        "marketing_budget": 5000,
        "random_seed": 42
    })
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert "outcomes" in sim_data
    assert sim_data["outcomes"]["final_customers"] > 0


def test_complete_end_to_end_smoke_test(tmp_path: Path):
    """Verify complete end-to-end first_organization workflow runs and passes in clean environment."""
    test_db = tmp_path / "e2e_first_org.db"
    results = run_first_organization_smoke_test(test_db)
    assert results["status"] == "PASSED"
    assert results["tasks_verified"] == 2
    assert results["org_id"].startswith("org_")
    assert results["project_id"].startswith("proj_")
