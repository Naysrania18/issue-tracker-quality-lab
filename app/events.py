"""Tiny in-process event queue plus a consumer that writes notifications."""
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventType(str, Enum):
    ISSUE_CREATED = "IssueCreated"
    STATE_CHANGED = "StateChanged"
    TEST_RUN_COMPLETED = "TestRunCompleted"


@dataclass
class Event:
    type: EventType
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # Per-issue counter used to spot out-of-order delivery of StateChanged events.
    sequence: int = 0


class EventBus:
    def __init__(self) -> None:
        self._queue: deque[Event] = deque()
        self.published: list[Event] = []
        self._sequences: dict[int, int] = {}

    def next_sequence(self, issue_id: int) -> int:
        self._sequences[issue_id] = self._sequences.get(issue_id, 0) + 1
        return self._sequences[issue_id]

    def publish(self, event: Event) -> None:
        self.published.append(event)
        self._queue.append(event)

    def pending(self) -> list[Event]:
        return list(self._queue)

    def pop_all(self) -> list[Event]:
        events = list(self._queue)
        self._queue.clear()
        return events


class NotificationConsumer:
    """Turns events into rows in the notifications table."""

    def __init__(self, conn) -> None:
        self.conn = conn
        self._last_sequence: dict[int, int] = {}

    def handle(self, event: Event) -> bool:
        """Return True if a notification was written."""
        if event.type == EventType.STATE_CHANGED:
            issue_id = event.payload["issue_id"]
            # Out-of-order protection: ignore events older than one already handled.
            if event.sequence < self._last_sequence.get(issue_id, 0):
                return False
            self._last_sequence[issue_id] = event.sequence
        message = self._format(event)
        # PLANTED-DEFECT-4: no check of event.event_id, so a re-delivered event
        # produces a second notification.
        self.conn.execute(
            "INSERT INTO notifications (event_id, event_type, message, created_at) VALUES (?,?,?,?)",
            (event.event_id, event.type.value, message, datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()
        return True

    def drain(self, bus: EventBus) -> int:
        return sum(1 for e in bus.pop_all() if self.handle(e))

    @staticmethod
    def _format(event: Event) -> str:
        p = event.payload
        if event.type == EventType.ISSUE_CREATED:
            return f"Issue #{p['issue_id']} created: {p['title']}"
        if event.type == EventType.STATE_CHANGED:
            return f"Issue #{p['issue_id']} moved {p['old']} -> {p['new']}"
        return f"Test run #{p['run_id']} completed with status {p['status']}"
