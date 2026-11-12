from __future__ import annotations

import math
from typing import Any, Dict

from .contracts import validate_event
from .policy import decide
from .rag import search_similar_incidents
from .risk_model import risk


def _coerce_score(value: Any, default: float = 0.0) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    if not math.isfinite(numeric):
        return default
    return max(0.0, min(1.0, numeric))


def explain(event: Dict[str, Any], machine_history: Dict[str, Any]) -> Dict[str, Any]:
    validated_event = validate_event(event)
    if not isinstance(machine_history, dict):
        raise ValueError("machine_history must be a dictionary")

    event = dict(event)
    machine_history = dict(machine_history)
    machine_id = validated_event.machine_id
    org_id = validated_event.org_id
    history_machine = machine_history.get("machine_id", machine_history.get("Machine_ID"))
    if not isinstance(history_machine, str) or history_machine.strip().upper() != machine_id.strip().upper():
        raise ValueError("machine_history must match the event machine_id.")
    history_org = machine_history.get("org_id")
    if history_org is not None and str(history_org).strip() != org_id:
        raise ValueError("machine_history org_id must match the event org_id.")
    detector_conf = validated_event.detector_confidence
    risk_summary = risk(machine_history)
    history_risk = _coerce_score(risk_summary["risk_score"])
    query = event.get("summary") or event.get("event_type") or "machine defect"
    raw_retrieval = search_similar_incidents(
        query=query,
        org_id=str(org_id),
        machine_id=str(machine_id) if machine_id != "unknown" else None,
        top_k=3,
    )
    retrieval = []
    if isinstance(raw_retrieval, list):
        for item in raw_retrieval:
            if not isinstance(item, dict):
                continue
            evidence = item.get("evidence")
            cause = item.get("root_cause")
            incident_id = item.get("incident_id")
            if (
                str(item.get("org_id", "")) != str(org_id)
                or str(item.get("machine_id", "")).strip().upper() != str(machine_id).strip().upper()
                or not isinstance(evidence, str)
                or not evidence.strip()
                or not isinstance(cause, str)
                or not cause.strip()
                or cause.casefold() not in evidence.casefold()
                or not incident_id
                or isinstance(item.get("score"), bool)
            ):
                continue
            try:
                score = float(item["score"])
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
            if not math.isfinite(score) or score < -1.0 or score > 1.0:
                continue
            retrieval.append({**item, "score": score})
    retrieval = [item for item in retrieval if item["score"] >= 0.2]
    raw_relevance = max((float(item.get("score", 0.0)) for item in retrieval), default=0.0)
    agreement = max(0.0, min(1.0, (raw_relevance - 0.2) / 0.8))
    decision = decide(detector_conf, history_risk, agreement, event.get("event_type", "defect"))

    probable_cause = retrieval[0].get("root_cause") if retrieval else "not found"
    cause_confidence = None
    response = {
        "probable_cause": probable_cause,
        "cause_confidence": cause_confidence,
        "machine_history_risk": history_risk,
        "shap_summary": risk_summary.get("explanation", {"status": "not_available", "summary": []}),
        "similar_incident_ids": [item["incident_id"] for item in retrieval],
        "retrieval_agreement": float(agreement),
        "retrieval_relevance": float(raw_relevance),
        "fusion_decision_score": float(decision["score"]),
        "decision": decision["decision"],
        "human_review_required": decision["human_review_required"],
        "observed_facts": {
            "event_id": validated_event.event_id,
            "machine_id": machine_id,
            "event_type": validated_event.event_type,
            "detector_confidence": detector_conf,
            "timestamp": validated_event.timestamp,
        },
        "predictions": {
            "machine_history_risk": history_risk,
            "decision": decision["decision"],
        },
        "hypotheses": {
            "probable_cause": probable_cause,
            "cause_confidence": None,
        },
        "human_readable_explanation": (
            f"Machine {machine_id} is assigned a {decision['decision']} decision based on detector confidence "
            f"({detector_conf:.2f}), historical risk ({history_risk:.2f}), and retrieval agreement ({agreement:.2f})."
        ),
        "limitations": "Observed evidence is distinguished from model hypotheses; missing or weak retrieval is reported conservatively.",
        "evidence": retrieval,
    }

    if not retrieval:
        response["limitations"] = "No relevant incidents were retrieved; the explanation remains conservative and evidence is insufficient."
        response["probable_cause"] = "not found"
        response["human_readable_explanation"] = (
            f"Machine {machine_id} has insufficient evidence for a causal explanation; the action decision was kept conservative."
        )
    else:
        response["limitations"] += " Cause confidence is not estimated; similarity scores are ranking signals, not probabilities."
    return response
