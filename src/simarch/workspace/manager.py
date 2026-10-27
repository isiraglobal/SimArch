"""SimArch temporary workspace manager and lifecycle engine."""

import datetime
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from simarch.core.exceptions import SecurityViolationError, WorkspaceError
from simarch.core.types import WorkspaceLifecycle, generate_id, utc_now, utc_now_iso
from simarch.db.database import DatabaseManager


class WorkspaceDescriptor(BaseModel):
    """Manifest describing an isolated execution workspace and its bounds."""
    id: str = Field(default_factory=lambda: generate_id("ws"))
    owner_id: str
    purpose: str
    path: str
    lifecycle: WorkspaceLifecycle = WorkspaceLifecycle.CREATED
    expires_at: str
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class WorkspaceManager:
    """Safely provisions, isolates, checkpoints, and purges task workspaces."""

    def __init__(self, root_dir: Path, db: DatabaseManager, default_ttl_hours: int = 24) -> None:
        self.root_dir = root_dir.resolve()
        self.db = db
        self.default_ttl_hours = default_ttl_hours
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def provision_workspace(self, owner_id: str, purpose: str, ttl_hours: Optional[int] = None) -> WorkspaceDescriptor:
        """Create a dedicated, sandboxed workspace directory."""
        ws_id = generate_id("ws")
        ws_path = (self.root_dir / ws_id).resolve()

        # Path traversal guard
        if not str(ws_path).startswith(str(self.root_dir)):
            raise SecurityViolationError("Workspace path resolves outside the configured root sandbox.")

        ws_path.mkdir(parents=True, exist_ok=True)

        hours = ttl_hours or self.default_ttl_hours
        expires_at = (utc_now() + datetime.timedelta(hours=hours)).isoformat()

        desc = WorkspaceDescriptor(
            id=ws_id,
            owner_id=owner_id,
            purpose=purpose,
            path=str(ws_path),
            lifecycle=WorkspaceLifecycle.ACTIVE,
            expires_at=expires_at
        )

        sql = """
        INSERT INTO workspaces (id, owner_id, purpose, path, lifecycle, expires_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.execute(sql, (
            desc.id, desc.owner_id, desc.purpose, desc.path,
            desc.lifecycle.value, desc.expires_at, desc.created_at, desc.updated_at
        ))
        return desc

    def checkpoint_workspace(self, ws_id: str, destination_dir: Path) -> Path:
        """Promote and checkpoint workspace contents to persistent storage before cleanup."""
        row = self.db.fetch_one("SELECT * FROM workspaces WHERE id = ?", (ws_id,))
        if not row:
            raise WorkspaceError(f"Workspace '{ws_id}' not found.")

        src_path = Path(row["path"]).resolve()
        dest = destination_dir.resolve()
        dest.mkdir(parents=True, exist_ok=True)

        if not src_path.exists():
            raise WorkspaceError(f"Source workspace path does not exist: {src_path}")

        # Copy non-disposable files
        shutil.copytree(src_path, dest / ws_id, dirs_exist_ok=True)

        now_str = utc_now_iso()
        self.db.execute("""
        UPDATE workspaces SET lifecycle = ?, updated_at = ? WHERE id = ?
        """, (WorkspaceLifecycle.CHECKPOINTED.value, now_str, ws_id))

        return dest / ws_id

    def mark_cleanup_eligible(self, ws_id: str) -> None:
        """Mark workspace as safe for garbage collection."""
        now_str = utc_now_iso()
        self.db.execute("""
        UPDATE workspaces SET lifecycle = ?, updated_at = ? WHERE id = ?
        """, (WorkspaceLifecycle.CLEANUP_ELIGIBLE.value, now_str, ws_id))

    def cleanup_expired_workspaces(self) -> int:
        """Safely delete workspaces whose TTL has expired and are eligible for removal."""
        now_str = utc_now_iso()
        rows = self.db.fetch_all("""
        SELECT * FROM workspaces
        WHERE (lifecycle = 'CLEANUP_ELIGIBLE' OR expires_at < ?)
          AND lifecycle != 'DELETED'
        """, (now_str,))

        cleaned = 0
        for r in rows:
            target_path = Path(r["path"]).resolve()
            # Double check path isolation
            if str(target_path).startswith(str(self.root_dir)) and target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)

            self.db.execute("""
            UPDATE workspaces SET lifecycle = 'DELETED', updated_at = ? WHERE id = ?
            """, (now_str, r["id"]))
            cleaned += 1

        return cleaned
