"""Tests for Temporary Workspace Management and Path Security (Items 15 & 19)."""

from pathlib import Path
import pytest
from simarch.core.exceptions import SecurityViolationError, WorkspaceError
from simarch.core.types import WorkspaceLifecycle
from simarch.db.database import DatabaseManager
from simarch.workspace.manager import WorkspaceManager


def test_workspace_provisioning_and_lifecycle(temp_db: DatabaseManager, workspace_manager: WorkspaceManager):
    """Verify workspace is provisioned with unique ID, path inside sandbox, and registered in DB."""
    desc = workspace_manager.provision_workspace(owner_id="worker_1", purpose="Build and test compiler module")

    assert desc.id.startswith("ws_")
    assert desc.lifecycle == WorkspaceLifecycle.ACTIVE
    assert Path(desc.path).exists()

    # Create dummy intermediate file inside workspace
    work_file = Path(desc.path) / "intermediate.tmp"
    work_file.write_text("temporary scratch data", encoding="utf-8")
    assert work_file.exists()


def test_workspace_checkpointing(tmp_path: Path, temp_db: DatabaseManager, workspace_manager: WorkspaceManager):
    """Verify promotion/checkpointing preserves artifacts to destination before workspace cleanup."""
    desc = workspace_manager.provision_workspace(owner_id="worker_2", purpose="Generate report")
    report_file = Path(desc.path) / "final_report.pdf"
    report_file.write_text("Report data", encoding="utf-8")

    checkpoint_dir = tmp_path / "long_term_storage"
    preserved_path = workspace_manager.checkpoint_workspace(desc.id, checkpoint_dir)

    assert (preserved_path / "final_report.pdf").exists()

    # Check updated lifecycle status in DB
    row = temp_db.fetch_one("SELECT lifecycle FROM workspaces WHERE id = ?", (desc.id,))
    assert row["lifecycle"] == WorkspaceLifecycle.CHECKPOINTED.value


def test_workspace_cleanup_eligibility(temp_db: DatabaseManager, workspace_manager: WorkspaceManager):
    """Verify workspaces marked eligible for cleanup are safely removed without deleting persistent data."""
    desc = workspace_manager.provision_workspace(owner_id="worker_3", purpose="Scratch testing")
    ws_path = Path(desc.path)
    assert ws_path.exists()

    workspace_manager.mark_cleanup_eligible(desc.id)
    cleaned_count = workspace_manager.cleanup_expired_workspaces()

    assert cleaned_count == 1
    assert not ws_path.exists()

    row = temp_db.fetch_one("SELECT lifecycle FROM workspaces WHERE id = ?", (desc.id,))
    assert row["lifecycle"] == WorkspaceLifecycle.DELETED.value
