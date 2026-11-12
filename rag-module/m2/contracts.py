from __future__ import annotations

from dataclasses import dataclass, field
import datetime as dt
import math
from typing import Any, Dict, List, Optional


@dataclass
class EventSchema:
    event_id: str
    timestamp: str
    machine_id: str
    org_id: str
    event_type: str
    detector_confidence: float
    evidence_paths: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionResult:
    score: float
    decision: str
    human_review_required: bool
    threshold: Dict[str, float]
    notes: str
    details: Dict[str, Any] = field(default_factory=dict)


def validate_event(event: Dict[str, Any]) -> EventSchema:
    if not isinstance(event, dict):
        raise ValueError("event must be a dictionary.")
    required = {"event_id", "timestamp", "machine_id", "org_id", "event_type", "detector_confidence"}
    missing = sorted(required - set(event.keys()))
    if missing:
        raise ValueError(f"Missing required event fields: {missing}")
    text_fields = ("event_id", "timestamp", "machine_id", "org_id", "event_type")
    empty = [name for name in text_fields if not str(event[name]).strip()]
    if empty:
        raise ValueError(f"Event fields cannot be empty: {empty}")
    try:
        parsed_timestamp = dt.datetime.fromisoformat(str(event["timestamp"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be a valid ISO 8601 date-time.") from exc
    if "T" not in str(event["timestamp"]):
        raise ValueError("timestamp must include a date and time.")
    if isinstance(event["detector_confidence"], bool):
        raise ValueError("detector_confidence must be a finite number in [0, 1].")
    try:
        confidence = float(event["detector_confidence"])
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("detector_confidence must be a finite number in [0, 1].") from exc
    if not math.isfinite(confidence) or confidence < 0 or confidence > 1:
        raise ValueError("detector_confidence must be a finite number in [0, 1].")
    evidence_paths = event.get("evidence_paths", [])
    if not isinstance(evidence_paths, list) or not all(isinstance(path, str) for path in evidence_paths):
        raise ValueError("evidence_paths must be a list of strings.")
    return EventSchema(
        event_id=str(event["event_id"]),
        timestamp=parsed_timestamp.isoformat(),
        machine_id=str(event["machine_id"]),
        org_id=str(event["org_id"]),
        event_type=str(event["event_type"]),
        detector_confidence=confidence,
        evidence_paths=list(evidence_paths),
        extra={k: v for k, v in event.items() if k not in required and k != "evidence_paths"},
    )
