"""Pytest configuration and shared test fixtures for SimArch."""

import tempfile
from pathlib import Path
import pytest
from simarch.core.types import RoleType
from simarch.db.database import DatabaseManager
from simarch.decision.graph import DecisionGraphEngine
from simarch.decision.intelligence import DecisionIntelligence
from simarch.execution.communication import CommunicationEngine
from simarch.execution.engine import TaskEngine
from simarch.execution.review import ReviewEngine
from simarch.execution.scheduler import PersistentScheduler
from simarch.memory.retrieval import ContextAssembler
from simarch.memory.scoped_memory import ScopedMemoryEngine
from simarch.org.formation import WorkforceFormationPlanner
from simarch.simulation.engine import SimulationEngine
from simarch.workspace.manager import WorkspaceManager


@pytest.fixture
def temp_db(tmp_path: Path) -> DatabaseManager:
    """Provide an isolated temporary SQLite database for each test."""
    db_file = tmp_path / "test_simarch.db"
    return DatabaseManager(db_file)


@pytest.fixture
def task_engine(temp_db: DatabaseManager) -> TaskEngine:
    return TaskEngine(temp_db)


@pytest.fixture
def scheduler(temp_db: DatabaseManager, task_engine: TaskEngine) -> PersistentScheduler:
    return PersistentScheduler(temp_db, task_engine, lease_duration_seconds=5)


@pytest.fixture
def formation_planner(temp_db: DatabaseManager) -> WorkforceFormationPlanner:
    return WorkforceFormationPlanner(temp_db)


@pytest.fixture
def decision_intel(temp_db: DatabaseManager) -> DecisionIntelligence:
    return DecisionIntelligence(temp_db)


@pytest.fixture
def decision_graph(temp_db: DatabaseManager) -> DecisionGraphEngine:
    return DecisionGraphEngine(temp_db)


@pytest.fixture
def review_engine(temp_db: DatabaseManager) -> ReviewEngine:
    return ReviewEngine(temp_db)


@pytest.fixture
def sim_engine(temp_db: DatabaseManager) -> SimulationEngine:
    return SimulationEngine(temp_db)


@pytest.fixture
def memory_engine(temp_db: DatabaseManager) -> ScopedMemoryEngine:
    return ScopedMemoryEngine(temp_db)


@pytest.fixture
def comms_engine(temp_db: DatabaseManager) -> CommunicationEngine:
    return CommunicationEngine(temp_db)


@pytest.fixture
def workspace_manager(tmp_path: Path, temp_db: DatabaseManager) -> WorkspaceManager:
    ws_dir = tmp_path / "workspaces"
    return WorkspaceManager(ws_dir, temp_db, default_ttl_hours=1)
