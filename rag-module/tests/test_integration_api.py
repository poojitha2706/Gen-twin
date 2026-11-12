from fastapi.testclient import TestClient
from importlib import import_module

backend_app = import_module("backend.app")


client = TestClient(backend_app.app)

VALID_HISTORY = {
    "machine_id": "M05",
    "type": "Thermal Damage",
    "air_temperature": 88,
    "process_temperature": 95,
    "rotational_speed": 1800,
    "torque": 52,
    "tool_wear": 0.7,
}

VALID_RISK = {
    "risk_score": 0.42,
    "risk_level": "medium",
    "model": "test-model",
    "dataset_source": "test-fixture",
    "calibration_status": "temperature_scaled_on_validation",
    "temperature": 1.0,
    "explanation": {"status": "not_available", "summary": []},
    "summary": "Test response",
}

VALID_EXPLANATION = {
    "probable_cause": "not found",
    "cause_confidence": None,
    "machine_history_risk": 0.42,
    "shap_summary": {"status": "not_available", "summary": []},
    "similar_incident_ids": [],
    "retrieval_agreement": 0.0,
    "retrieval_relevance": 0.0,
    "fusion_decision_score": 0.33,
    "decision": "escalate",
    "human_review_required": True,
    "observed_facts": {},
    "predictions": {},
    "hypotheses": {},
    "human_readable_explanation": "No similar incidents were retrieved.",
    "limitations": "Evidence is insufficient.",
    "evidence": [],
}


def test_risk_endpoint_maps_valid_inference(monkeypatch):
    monkeypatch.setattr(backend_app, "risk", lambda history: VALID_RISK)

    response = client.post("/risk", json={"machine_history": VALID_HISTORY})

    assert response.status_code == 200
    assert response.json() == VALID_RISK


def test_risk_endpoint_rejects_invalid_telemetry():
    response = client.post("/risk", json={"machine_history": {"machine_id": "M05"}})

    assert response.status_code == 422


def test_risk_endpoint_reports_invalid_model_output_as_unavailable(monkeypatch):
    invalid_response = {**VALID_RISK, "risk_score": 1.5}
    monkeypatch.setattr(backend_app, "risk", lambda history: invalid_response)

    response = client.post("/risk", json={"machine_history": VALID_HISTORY})

    assert response.status_code == 503
    assert response.json()["detail"] == "M2 inference is unavailable or returned an invalid response."


def test_risk_endpoint_reports_model_loading_failure(monkeypatch):
    def fail(_history):
        raise OSError("private model path")

    monkeypatch.setattr(backend_app, "risk", fail)

    response = client.post("/risk", json={"machine_history": VALID_HISTORY})

    assert response.status_code == 503
    assert "private model path" not in response.text


def test_explanation_endpoint_maps_valid_response(monkeypatch):
    monkeypatch.setattr(backend_app, "explain", lambda event, history: VALID_EXPLANATION)
    event = {
        "event_id": "evt-test",
        "timestamp": "2026-01-01T00:00:00Z",
        "machine_id": "M05",
        "org_id": "test-org",
        "event_type": "defect",
        "detector_confidence": 0.84,
    }

    response = client.post(
        "/explain",
        json={"event": event, "machine_history": VALID_HISTORY},
    )

    assert response.status_code == 200
    assert response.json() == VALID_EXPLANATION


def test_explanation_endpoint_rejects_invalid_event(monkeypatch):
    def invalid(_event, _history):
        raise ValueError("event must contain a valid timestamp")

    monkeypatch.setattr(backend_app, "explain", invalid)

    response = client.post(
        "/explain",
        json={"event": {}, "machine_history": VALID_HISTORY},
    )

    assert response.status_code == 422


def test_m2_cors_allows_the_local_frontend_origin():
    response = client.options(
        "/risk",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
