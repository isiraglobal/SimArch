"""SimArch structured event logging and bus."""

from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field
import asyncio
from simarch.core.types import generate_id, utc_now_iso


class SystemEvent(BaseModel):
    """Structured event emitted across SimArch subsystems."""
    event_id: str = Field(default_factory=lambda: generate_id("evt"))
    event_type: str
    source_component: str
    organization_id: Optional[str] = None
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=utc_now_iso)


class EventBus:
    """In-memory asynchronous event bus with subscription callbacks."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[SystemEvent], Any]]] = {}
        self._history: List[SystemEvent] = []
        self._max_history = 1000

    def subscribe(self, event_type: str, callback: Callable[[SystemEvent], Any]) -> None:
        """Subscribe to a specific event type or '*' for all events."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def publish(self, event: SystemEvent) -> None:
        """Synchronously dispatch event to all registered subscribers."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # Dispatch specific
        for cb in self._subscribers.get(event.event_type, []):
            try:
                cb(event)
            except Exception:
                pass

        # Dispatch wildcard
        for cb in self._subscribers.get("*", []):
            try:
                cb(event)
            except Exception:
                pass

    def get_recent_events(self, limit: int = 50, project_id: Optional[str] = None) -> List[SystemEvent]:
        """Fetch recent events in reverse chronological order."""
        events = self._history
        if project_id:
            events = [e for e in events if e.project_id == project_id]
        return sorted(events[-limit:], key=lambda e: e.timestamp, reverse=True)


# Global default bus instance
default_event_bus = EventBus()
