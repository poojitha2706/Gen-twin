from __future__ import annotations

import math
from typing import Any, Dict

from .contracts import DecisionResult

SAFETY_EVENTS = {"ppe_violation", "stopped_machine", "fire", "thermal_event", "safety", "collision", "gas_leak"}
THRESHOLDS = {"auto_act": 0.90, "alert": 0.60, "escalate": 0.60}


def _coerce_probability(value: Any, default: float = 0.0) -> tuple[float, bool]:
    if value is None:
        return float(default), False
    if isinstance(value, bool):
        return float(default), False
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return float(default), False
    if not math.isfinite(numeric):
        return float(default), False
    if numeric < 0.0 or numeric > 1.0:
        return float(default), False
    return float(numeric), True


def decide(detector_conf: float, history_risk: float, retrieval_agreement: float, event_type: str) -> Dict[str, Any]:
    """Fusion policy matching the GenTwin Vision thresholds.

    Score >=0.90 => auto_act
    Score >=0.60 and <0.90 => alert
    Score <0.60 => escalate
    Safety events always require human notification regardless of score.
    """
    if event_type is None or str(event_type).strip() == "":
        raise ValueError("event_type cannot be empty")

    detector_conf, detector_valid = _coerce_probability(detector_conf)
    history_risk, history_valid = _coerce_probability(history_risk)
    retrieval_agreement, retrieval_valid = _coerce_probability(retrieval_agreement)
    invalid_inputs = [
        name
        for name, valid in (
            ("detector_conf", detector_valid),
            ("history_risk", history_valid),
            ("retrieval_agreement", retrieval_valid),
        )
        if not valid
    ]
    normalized_event = str(event_type).strip().lower()

    if normalized_event in SAFETY_EVENTS:
        score = 0.45 * detector_conf + 0.35 * history_risk + 0.20 * retrieval_agreement
        decision = "alert" if score >= THRESHOLDS["alert"] else "escalate"
        return DecisionResult(
            score=float(score),
            decision=decision,
            human_review_required=True,
            threshold=dict(THRESHOLDS),
            notes="Safety event: human review required regardless of the raw score.",
            details={
                "event_type": normalized_event,
                "detector_confidence": detector_conf,
                "history_risk": history_risk,
                "retrieval_agreement": retrieval_agreement,
                "invalid_inputs": invalid_inputs,
            },
        ).__dict__

    score = 0.45 * detector_conf + 0.35 * history_risk + 0.20 * retrieval_agreement
    if score >= THRESHOLDS["auto_act"]:
        decision = "auto_act"
    elif score >= THRESHOLDS["alert"]:
        decision = "alert"
    else:
        decision = "escalate"

    return DecisionResult(
        score=float(score),
        decision=decision,
        human_review_required=(decision in {"alert", "escalate"}),
        threshold=dict(THRESHOLDS),
        notes="Heuristic fusion uses detector confidence, historical risk, and evidence agreement; the score is not a calibrated probability.",
        details={
            "event_type": normalized_event,
            "detector_confidence": detector_conf,
            "history_risk": history_risk,
            "retrieval_agreement": retrieval_agreement,
            "invalid_inputs": invalid_inputs,
        },
    ).__dict__
