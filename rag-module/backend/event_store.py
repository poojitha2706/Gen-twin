from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class EventRecord:
    event_id: str
    machine_id: str
    org_id: str
    event_type: str
    detector_confidence: float
    timestamp: str
    status: str = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)


class EventStore:
    def __init__(self):
        self._events: Dict[str, EventRecord] = {}
        self._org_events: Dict[str, List[str]] = defaultdict(list)

    def add_event(self, event: Dict[str, Any]) -> EventRecord:
        record = EventRecord(
            event_id=event["event_id"],
            machine_id=event["machine_id"],
            org_id=event["org_id"],
            event_type=event["event_type"],
            detector_confidence=float(event["detector_confidence"]),
            timestamp=event.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            metadata={k: v for k, v in event.items() if k not in {"event_id", "machine_id", "org_id", "event_type", "detector_confidence", "timestamp"}},
        )
        self._events[record.event_id] = record
        self._org_events[record.org_id].append(record.event_id)
        return record

    def get_events_for_org(self, org_id: str) -> List[EventRecord]:
        return [self._events[eid] for eid in self._org_events.get(org_id, [])]

    def get_recent_events(self, org_id: str, machine_id: str | None = None, limit: int = 10) -> List[EventRecord]:
        records = self.get_events_for_org(org_id)
        if machine_id:
            records = [r for r in records if r.machine_id == machine_id]
        return sorted(records, key=lambda r: r.timestamp, reverse=True)[:limit]
