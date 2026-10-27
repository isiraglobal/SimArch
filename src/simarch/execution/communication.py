"""SimArch structured cross-department communication engine."""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from simarch.core.exceptions import RolePermissionError
from simarch.core.types import generate_id, utc_now_iso
from simarch.db.database import DatabaseManager


class Message(BaseModel):
    """Structured message exchanged between organizational roles."""
    id: str = Field(default_factory=lambda: generate_id("msg"))
    project_id: str
    task_id: Optional[str] = None
    sender_role_id: str
    recipient_role_id: str
    message_type: str  # inquiry, response, escalation, consultation, handoff
    content: str
    artifacts: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class CommunicationEngine:
    """Manages inter-role collaboration while enforcing recursion and rate boundaries."""

    def __init__(self, db: DatabaseManager, max_history_per_task: int = 50) -> None:
        self.db = db
        self.max_history_per_task = max_history_per_task

    def send_message(self, message: Message) -> Message:
        """Deliver and record a structured message between roles."""
        if message.task_id:
            # Check depth to prevent infinite circular dialogue
            count_row = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM messages WHERE task_id = ?",
                (message.task_id,)
            )
            count = count_row["count"] if count_row else 0
            if count >= self.max_history_per_task:
                raise RolePermissionError(
                    f"Communication thread limit reached for task '{message.task_id}' ({count} messages). "
                    "Forced escalation required to prevent runaway discussion."
                )

        sql = """
        INSERT INTO messages (id, project_id, task_id, sender_role_id, recipient_role_id, message_type, content, artifacts_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.execute(sql, (
            message.id,
            message.project_id,
            message.task_id,
            message.sender_role_id,
            message.recipient_role_id,
            message.message_type,
            message.content,
            json.dumps(message.artifacts),
            message.created_at
        ))
        return message

    def get_task_messages(self, task_id: str) -> List[Message]:
        """Fetch all messages associated with a specific task."""
        rows = self.db.fetch_all(
            "SELECT * FROM messages WHERE task_id = ? ORDER BY created_at ASC",
            (task_id,)
        )
        return [
            Message(
                id=r["id"],
                project_id=r["project_id"],
                task_id=r["task_id"],
                sender_role_id=r["sender_role_id"],
                recipient_role_id=r["recipient_role_id"],
                message_type=r["message_type"],
                content=r["content"],
                artifacts=json.loads(r["artifacts_json"]),
                created_at=r["created_at"]
            )
            for r in rows
        ]
