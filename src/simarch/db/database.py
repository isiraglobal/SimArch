"""SimArch database connection manager and transaction engine."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union
from simarch.core.exceptions import DatabaseError
from simarch.core.types import generate_id, utc_now_iso
from simarch.db.schema import CREATE_TABLES_SQL


class DatabaseManager:
    """Manages SQLite operations with WAL mode, transactions, and row dict conversion."""

    def __init__(self, db_path: Union[str, Path]) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create and configure a new SQLite connection."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            check_same_thread=False,
            isolation_level=None  # Managed transactions
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def _init_db(self) -> None:
        """Execute schema initialization script."""
        with self.get_connection() as conn:
            conn.executescript(CREATE_TABLES_SQL)

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager yielding an active connection."""
        conn = self._get_connection()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for an atomic database transaction."""
        conn = self._get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE;")
            cursor = conn.cursor()
            yield cursor
            conn.execute("COMMIT;")
        except Exception as e:
            conn.execute("ROLLBACK;")
            raise DatabaseError(f"Transaction failed and rolled back: {e}") from e
        finally:
            conn.close()

    def execute(self, sql: str, params: Union[Tuple[Any, ...], List[Any], Dict[str, Any]] = ()) -> sqlite3.Cursor:
        """Execute a single statement inside an auto-commit or immediate transaction."""
        with self.get_connection() as conn:
            return conn.execute(sql, params)

    def fetch_one(self, sql: str, params: Union[Tuple[Any, ...], List[Any]] = ()) -> Optional[Dict[str, Any]]:
        """Fetch a single record as a dictionary."""
        with self.get_connection() as conn:
            cur = conn.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def fetch_all(self, sql: str, params: Union[Tuple[Any, ...], List[Any]] = ()) -> List[Dict[str, Any]]:
        """Fetch all records matching query as dictionaries."""
        with self.get_connection() as conn:
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def log_audit(self, entity_type: str, entity_id: str, actor_id: str, action: str,
                  before_state: Optional[Dict[str, Any]] = None,
                  after_state: Optional[Dict[str, Any]] = None) -> str:
        """Record an immutable audit log entry."""
        audit_id = generate_id("aud")
        sql = """
        INSERT INTO audit_log (id, entity_type, entity_id, actor_id, action, before_state_json, after_state_json, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.execute(sql, (
            audit_id,
            entity_type,
            entity_id,
            actor_id,
            action,
            json.dumps(before_state or {}),
            json.dumps(after_state or {}),
            utc_now_iso()
        ))
        return audit_id
