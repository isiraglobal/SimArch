"""Tests for SimArch AI Tool Extension, MCP Server, and Localhost Locking."""

import asyncio
from pathlib import Path
import pytest
from simarch.api.server_manager import dashboard_manager
from simarch.extension.toolkit import SimArchAIExtension
from simarch.mcp.server import MCPServer


def test_ai_extension_lifecycle(tmp_path: Path):
    """Verify AI Extension exposes all core organizational and simulation capabilities."""
    db_file = tmp_path / "test_ext.db"
    ext = SimArchAIExtension(db_file)

    # 1. Form Organization
    org_res = ext.form_organization("Apex Systems", "Build autonomous agent platforms", scale="compact")
    assert "org_id" in org_res
    assert len(org_res["roles"]) >= 3
    org_id = org_res["org_id"]
    lead_role_id = org_res["roles"][1]["id"]
    auditor_role_id = org_res["roles"][-1]["id"]

    # 2. Create Project & Task
    proj = ext.create_project(org_id, "Sprint 1", "Release v0.1")
    task = ext.create_task(
        proj["id"], org_id, lead_role_id,
        "Implement verification engine",
        acceptance_criteria=["Zero circular dependencies", "Contracts documented"]
    )
    assert task["id"].startswith("task_")

    # 3. Submit Deliverable & Independent Review
    del_res = ext.submit_deliverable(
        task["id"],
        "Finished engine",
        findings={"modules": 4},
        evidence=["Zero circular dependencies verified", "Contracts documented"]
    )
    assert del_res["status"] == "REVIEW"

    rev_res = ext.review_deliverable(task["id"], auditor_role_id)
    assert rev_res["status"] == "approved"

    # 4. Decision Intelligence
    dec_res = ext.evaluate_decision(
        proj["id"], org_id, lead_role_id,
        "Choose runtime backend",
        criteria=[{"name": "Simplicity", "weight": 1.0, "description": "Ease of ops"}],
        alternatives=[
            {"name": "SQLite", "description": "Local", "estimated_cost": 0, "scores": {"Simplicity": 10.0}},
            {"name": "Postgres", "description": "Cloud", "estimated_cost": 500, "scores": {"Simplicity": 6.0}}
        ]
    )
    assert dec_res["chosen_option"] == "SQLite"
    assert dec_res["binary_comparison"] is not None

    # 5. Discrete Event Simulation
    sim_res = ext.run_simulation(proj["id"], "Test Run", duration_days=90.0, marketing_budget=4000.0)
    assert sim_res["outcomes"]["final_customers"] > 0


def test_localhost_locking_and_ai_decision(tmp_path: Path):
    """Verify localhost starts locked/dormant and can be unlocked/locked on demand by AI agent."""
    db_file = tmp_path / "test_lock.db"
    ext = SimArchAIExtension(db_file)

    # Initially dormant
    initial_status = ext.get_localhost_status()
    assert initial_status["active"] is False
    assert initial_status["locked"] is True

    # AI agent decides to unlock dashboard
    start_res = ext.toggle_localhost(enable=True, port=8419)
    assert start_res["status"] in ["started", "already_running"]
    assert "8419" in start_res["url"]

    # Verify active status
    active_status = ext.get_localhost_status()
    assert active_status["active"] is True
    assert active_status["locked"] is False

    # AI agent decides human inspection is finished, locks localhost
    stop_res = ext.toggle_localhost(enable=False)
    assert stop_res["status"] == "stopped"

    # Verify locked again
    final_status = ext.get_localhost_status()
    assert final_status["active"] is False
    assert final_status["locked"] is True


@pytest.mark.asyncio
async def test_mcp_server_protocol(tmp_path: Path):
    """Verify Model Context Protocol (MCP) JSON-RPC handler."""
    server = MCPServer()
    server.extension = SimArchAIExtension(tmp_path / "test_mcp.db")

    # 1. Initialize
    init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    init_res = await server.handle_request(init_req)
    assert init_res["result"]["serverInfo"]["name"] == "simarch-ai-extension"
    assert "tools" in init_res["result"]["capabilities"]

    # 2. Tools List
    tools_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    tools_res = await server.handle_request(tools_req)
    tool_names = [t["name"] for t in tools_res["result"]["tools"]]
    assert "simarch_form_organization" in tool_names
    assert "simarch_toggle_localhost" in tool_names
    assert "simarch_evaluate_decision" in tool_names

    # 3. Tools Call
    call_req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "simarch_form_organization",
            "arguments": {
                "name": "MCP Corp",
                "objective": "Autonomous multi-agent research"
            }
        }
    }
    call_res = await server.handle_request(call_req)
    assert call_res["result"]["isError"] is False
    content_text = call_res["result"]["content"][0]["text"]
    assert "MCP Corp" in content_text

    # 4. Resources List
    res_list_req = {"jsonrpc": "2.0", "id": 4, "method": "resources/list"}
    res_list_res = await server.handle_request(res_list_req)
    assert len(res_list_res["result"]["resources"]) >= 3
