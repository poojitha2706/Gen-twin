from __future__ import annotations

import os
import pickle
from typing import Any, Dict, List, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.event_store import EventStore
from m2.chat import ChatAssistant
from m2.explain import explain
from m2.policy import decide
from m2.risk_model import RiskModel, risk

app = FastAPI(title="GenTwin Vision Backend")
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "M4_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class RiskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    machine_history: Dict[str, Any]


class RiskResponse(BaseModel):
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: Literal["low", "medium", "high"]
    model: str
    dataset_source: str
    calibration_status: Literal["temperature_scaled_on_validation", "uncalibrated"]
    temperature: float = Field(gt=0.0)
    explanation: Dict[str, Any]
    summary: str


class ExplainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event: Dict[str, Any]
    machine_history: Dict[str, Any]


class ExplainResponse(BaseModel):
    probable_cause: str
    cause_confidence: float | None
    machine_history_risk: float = Field(ge=0.0, le=1.0)
    shap_summary: Dict[str, Any]
    similar_incident_ids: List[str]
    retrieval_agreement: float = Field(ge=0.0, le=1.0)
    retrieval_relevance: float = Field(ge=0.0, le=1.0)
    fusion_decision_score: float = Field(ge=0.0, le=1.0)
    decision: str
    human_review_required: bool
    observed_facts: Dict[str, Any]
    predictions: Dict[str, Any]
    hypotheses: Dict[str, Any]
    human_readable_explanation: str
    limitations: str
    evidence: List[Dict[str, Any]]


store = EventStore()
chat = ChatAssistant()


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "GenTwin Vision"}


@app.post("/risk", response_model=RiskResponse)
def risk_prediction(payload: RiskRequest):
    try:
        RiskModel()._history_to_row(payload.machine_history)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        result = risk(payload.machine_history)
        return RiskResponse.model_validate(result)
    except (OSError, RuntimeError, ValueError, TypeError, pickle.UnpicklingError, ValidationError) as exc:
        raise HTTPException(status_code=503, detail="M2 inference is unavailable or returned an invalid response.") from exc


@app.post("/explain", response_model=ExplainResponse)
def event_explanation(payload: ExplainRequest):
    try:
        result = explain(payload.event, payload.machine_history)
        return ExplainResponse.model_validate(result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (OSError, RuntimeError, TypeError, pickle.UnpicklingError, ValidationError) as exc:
        raise HTTPException(status_code=503, detail="M2 explanation is unavailable or returned an invalid response.") from exc


@app.post("/events")
def create_event(payload: Dict[str, Any]):
    try:
        event = dict(payload)
        if "event_id" not in event:
            event["event_id"] = f"evt-{len(store._events) + 1}"
        record = store.add_event(event)
        return {"status": "accepted", "event": {"event_id": record.event_id, "org_id": record.org_id, "machine_id": record.machine_id}}
    except Exception as exc:  # pragma: no cover - defensive validation path
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/events")
def list_events(org_id: str = Query(...), machine_id: str | None = None):
    return {
        "org_id": org_id,
        "events": [
            {
                "event_id": r.event_id,
                "machine_id": r.machine_id,
                "event_type": r.event_type,
                "detector_confidence": r.detector_confidence,
                "timestamp": r.timestamp,
                "status": r.status,
            }
            for r in store.get_recent_events(org_id, machine_id=machine_id)
        ],
    }


@app.post("/chat")
def chat_endpoint(payload: Dict[str, Any]):
    org_id = payload.get("org_id")
    if not org_id:
        raise HTTPException(status_code=401, detail="org_id must be provided from authenticated backend context")
    user_message = payload.get("message", "")
    return chat.respond(message=user_message, org_id=org_id)


@app.get("/ws/{org_id}")
def ws_stub(org_id: str):
    return {"status": "websocket-ready", "org_id": org_id, "message": "WebSocket route registered for this organisation"}


@app.get("/decision")
def decision_preview(detector_conf: float = 0.8, history_risk: float = 0.7, retrieval_agreement: float = 0.6, event_type: str = "defect"):
    return decide(detector_conf, history_risk, retrieval_agreement, event_type)
