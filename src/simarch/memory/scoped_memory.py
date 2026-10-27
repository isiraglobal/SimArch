"""SimArch scoped memory and context management engine."""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from simarch.core.exceptions import RolePermissionError
from simarch.core.types import MemoryScope, generate_id, utc_now_iso
from simarch.db.database import DatabaseManager


class MemoryEntry(BaseModel):
    """Scoped knowledge atom with provenance and contradiction tracking."""
    id: str = Field(default_factory=lambda: generate_id("mem"))
    org_id: str
    project_id: Optional[str] = None
    scope: MemoryScope
    scope_id: str
    key: str
    content: str
    provenance: Dict[str, Any] = Field(default_factory=dict)
    contradiction_flag: bool = False
    created_at: str = Field(default_factory=utc_now_iso)


class ScopedMemoryEngine:
    """Provides scoped, audited, and isolated persistent memory access."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def store_memory(
        self,
        org_id: str,
        scope: MemoryScope,
        scope_id: str,
        key: str,
        content: str,
        project_id: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None
    ) -> MemoryEntry:
        """Store a new memory item, checking for contradictions with existing keys."""
        existing = self.db.fetch_one(
            "SELECT * FROM memories WHERE org_id = ? AND scope = ? AND scope_id = ? AND key = ?",
            (org_id, scope.value, scope_id, key)
        )

        contradiction = False
        if existing:
            # Check if new content directly negates existing content
            old_content = existing["content"]
            if ("not " in content.lower() and content.lower().replace("not ", "") in old_content.lower()) or \
               ("not " in old_content.lower() and old_content.lower().replace("not ", "") in content.lower()):
                contradiction = True

        entry_id = generate_id("mem")
        entry = MemoryEntry(
            id=entry_id,
            org_id=org_id,
            project_id=project_id,
            scope=scope,
            scope_id=scope_id,
            key=key,
            content=content,
            provenance=provenance or {},
            contradiction_flag=contradiction
        )

        sql = """
        INSERT INTO memories (id, org_id, project_id, scope, scope_id, key, content, provenance_json, contradiction_flag, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.execute(sql, (
            entry.id, entry.org_id, entry.project_id, entry.scope.value, entry.scope_id,
            entry.key, entry.content, json.dumps(entry.provenance),
            1 if entry.contradiction_flag else 0, entry.created_at
        ))
        return entry

    def get_scoped_memories(
        self,
        org_id: str,
        scope: MemoryScope,
        scope_id: str
    ) -> List[MemoryEntry]:
        """Fetch all memory items within a specific scope and identifier."""
        rows = self.db.fetch_all(
            "SELECT * FROM memories WHERE org_id = ? AND scope = ? AND scope_id = ? ORDER BY created_at DESC",
            (org_id, scope.value, scope_id)
        )
        return [self._row_to_entry(r) for r in rows]

    def check_access(self, accessor_role_id: str, target_scope: MemoryScope, target_scope_id: str) -> bool:
        """Verify role has permission to access the requested memory scope."""
        # Task and employee memories are private unless accessor is assigned or an executive
        if target_scope in [MemoryScope.EMPLOYEE, MemoryScope.TASK]:
            if accessor_role_id != target_scope_id:
                # Check if executive
                role = self.db.fetch_one("SELECT role_type FROM roles WHERE id = ?", (accessor_role_id,))
                if not role or role["role_type"] not in ["executive", "auditor", "coordinator"]:
                    raise RolePermissionError(
                        f"Access denied: Role '{accessor_role_id}' cannot view private {target_scope.value} memory."
                    )
        return True

    def _row_to_entry(self, row: Dict[str, Any]) -> MemoryEntry:
        """Convert database row to MemoryEntry model."""
        return MemoryEntry(
            id=row["id"],
            org_id=row["org_id"],
            project_id=row.get("project_id"),
            scope=MemoryScope(row["scope"]),
            scope_id=row["scope_id"],
            key=row["key"],
            content=row["content"],
            provenance=json.loads(row["provenance_json"]) if row.get("provenance_json") else {},
            contradiction_flag=bool(row["contradiction_flag"]),
            created_at=row["created_at"]
        )
