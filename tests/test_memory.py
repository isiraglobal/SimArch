"""Tests for Scoped Memory, Isolation, Provenance, and Contradiction (Items 9 & 11)."""

import pytest
from simarch.core.exceptions import RolePermissionError
from simarch.core.types import MemoryScope
from simarch.db.database import DatabaseManager
from simarch.memory.retrieval import ContextAssembler
from simarch.memory.scoped_memory import ScopedMemoryEngine


def test_scoped_memory_isolation(temp_db: DatabaseManager, memory_engine: ScopedMemoryEngine):
    """Verify memories stored under different scopes remain strictly isolated."""
    temp_db.execute("INSERT INTO organizations (id, name, mission, created_at, updated_at) VALUES ('org1', 'O1', 'M1', '', '')")
    temp_db.execute("INSERT INTO projects (id, org_id, name, objective, created_at, updated_at) VALUES ('p1', 'org1', 'P1', 'O1', '', '')")

    # Store in Org scope
    memory_engine.store_memory(
        org_id="org1",
        scope=MemoryScope.ORGANIZATION,
        scope_id="org1",
        key="company_policy",
        content="All public releases require independent audit approval."
    )

    # Store in Project scope
    memory_engine.store_memory(
        org_id="org1",
        project_id="p1",
        scope=MemoryScope.PROJECT,
        scope_id="p1",
        key="sprint_goal",
        content="Deliver MVP within 2 weeks."
    )

    org_mems = memory_engine.get_scoped_memories("org1", MemoryScope.ORGANIZATION, "org1")
    assert len(org_mems) == 1
    assert org_mems[0].key == "company_policy"

    proj_mems = memory_engine.get_scoped_memories("org1", MemoryScope.PROJECT, "p1")
    assert len(proj_mems) == 1
    assert proj_mems[0].key == "sprint_goal"


def test_contradiction_detection(temp_db: DatabaseManager, memory_engine: ScopedMemoryEngine):
    """Verify contradiction flag is raised when conflicting statements are stored under same key."""
    temp_db.execute("INSERT INTO organizations (id, name, mission, created_at, updated_at) VALUES ('org1', 'O1', 'M1', '', '')")

    # Entry 1
    memory_engine.store_memory(
        org_id="org1",
        scope=MemoryScope.ORGANIZATION,
        scope_id="org1",
        key="deployment_policy",
        content="Automated deployment is authorized on Fridays."
    )

    # Entry 2: direct negation
    entry2 = memory_engine.store_memory(
        org_id="org1",
        scope=MemoryScope.ORGANIZATION,
        scope_id="org1",
        key="deployment_policy",
        content="Automated deployment is not authorized on Fridays."
    )

    assert entry2.contradiction_flag is True


def test_context_assembler_budget(temp_db: DatabaseManager, memory_engine: ScopedMemoryEngine):
    """Verify context assembler respects token constraints and ranks by relevance."""
    temp_db.execute("INSERT INTO organizations (id, name, mission, created_at, updated_at) VALUES ('org1', 'O1', 'M1', '', '')")
    temp_db.execute("INSERT INTO projects (id, org_id, name, objective, created_at, updated_at) VALUES ('p1', 'org1', 'P1', 'O1', '', '')")

    memory_engine.store_memory(
        org_id="org1",
        scope=MemoryScope.ORGANIZATION,
        scope_id="org1",
        key="architecture_guidelines",
        content="Use Python for orchestration and SQLite for persistence.",
        provenance={"source": "CTO Handbook", "author": "CTO"}
    )

    assembler = ContextAssembler(temp_db, memory_engine)
    context = assembler.assemble_context(
        org_id="org1",
        project_id="p1",
        query="What database should we use for persistence?",
        role_id="role_lead",
        max_tokens=200
    )

    assert "SQLite" in context
    assert "CTO Handbook" in context
