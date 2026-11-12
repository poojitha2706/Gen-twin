from __future__ import annotations

import csv
import hashlib
import importlib
import json
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

import m2.rag as rag_module
from m2.chat import ChatAssistant
from m2.policy import decide
from m2.risk_model import ARTIFACT_VERSION, RiskModel

AI4I_SHA256 = "dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e"
AI4I_COLUMNS = {
    "UDI",
    "Product ID",
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
    "Machine failure",
    "TWF",
    "HDF",
    "PWF",
    "OSF",
    "RNF",
}


def _history_from_dataset_row(row: pd.Series, machine_id: str = "M05") -> Dict[str, Any]:
    return {
        "machine_id": machine_id,
        "type": str(row["Type"]),
        "air_temperature": float(row["Air temperature [K]"]),
        "process_temperature": float(row["Process temperature [K]"]),
        "rotational_speed": float(row["Rotational speed [rpm]"]),
        "torque": float(row["Torque [Nm]"]),
        "tool_wear": float(row["Tool wear [min]"]),
    }


def _inference_trace(model: RiskModel, history: Dict[str, Any]) -> Dict[str, Any]:
    normalized = model._history_to_row(history)
    frame = pd.DataFrame([normalized], columns=model.feature_columns)
    pipeline = model.pipeline
    raw_probabilities = pipeline.predict_proba(frame)[0]
    class_order = pipeline.classes_.tolist()
    positive_index = model._positive_class_index(len(raw_probabilities))
    transformed = pipeline.named_steps["preprocess"].transform(frame)
    if hasattr(transformed, "toarray"):
        transformed = transformed.toarray()
    transformed_values = [float(value) for value in transformed[0]]
    return {
        "input_features": normalized,
        "feature_order": list(frame.columns),
        "transformed_feature_names": pipeline.named_steps["preprocess"].get_feature_names_out().tolist(),
        "transformed_values": transformed_values,
        "class_order": class_order,
        "raw_class_probabilities": {
            str(label): float(probability)
            for label, probability in zip(class_order, raw_probabilities)
        },
        "raw_positive_probability": float(raw_probabilities[positive_index]),
        "calibration_temperature": float(model.temperature),
        "calibration_applied": bool(model.calibration_ready),
        "calibrated_probability": float(model.predict_proba(history)),
    }


def _representative_telemetry(model: RiskModel, dataset: pd.DataFrame) -> list[Dict[str, Any]]:
    holdout = dataset.loc[dataset["UDI"] >= 8001].reset_index(drop=True)
    histories = [_history_from_dataset_row(row) for _, row in holdout.iterrows()]
    rows = [model._history_to_row(history) for history in histories]
    frame = pd.DataFrame(rows, columns=model.feature_columns)
    raw_probabilities = model.pipeline.predict_proba(frame)
    positive_index = model._positive_class_index(raw_probabilities.shape[1])
    calibrated = model._apply_temperature(raw_probabilities[:, positive_index])

    normal_index = int(holdout.index[holdout["Machine failure"] == 0][0])
    failure_index = int(holdout.index[holdout["Machine failure"] == 1][0])
    borderline_index = int((abs(calibrated - 0.5)).argmin())
    cases = []
    for name, index in (
        ("normal", normal_index),
        ("borderline_nearest_to_0.5", borderline_index),
        ("failure_like", failure_index),
    ):
        label = int(holdout.iloc[index]["Machine failure"])
        trace = _inference_trace(model, histories[index])
        probability = trace["calibrated_probability"]
        cases.append({
            "case": name,
            "source": "AI4I ordered holdout, UDI 8001-10000",
            "udi": int(holdout.iloc[index]["UDI"]),
            "dataset_label": label,
            "input": histories[index],
            "trace": trace,
            "threshold": 0.5,
            "predicted_label_at_threshold": int(probability >= 0.5),
            "matches_dataset_label_at_threshold": int(probability >= 0.5) == label,
            "expected_behavior": (
                "Return a finite calibrated probability for this observed telemetry; "
                "the dataset label is a reference, not a guaranteed prediction."
            ),
        })
    return cases


def run_checks() -> Dict[str, Any]:
    dataset_path = ROOT / "data" / "ai4i_2020.csv"
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Required AI4I dataset is missing: {dataset_path}")

    dataset_bytes = dataset_path.read_bytes()
    dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()
    dataset = pd.read_csv(dataset_path)
    target_counts = {
        str(key): int(value)
        for key, value in dataset["Machine failure"].value_counts().sort_index().items()
    }
    if (
        dataset_hash != AI4I_SHA256
        or len(dataset) != 10000
        or set(dataset.columns) != AI4I_COLUMNS
        or not dataset["UDI"].is_unique
        or int(dataset["UDI"].min()) != 1
        or int(dataset["UDI"].max()) != 10000
        or target_counts != {"0": 9661, "1": 339}
    ):
        raise ValueError("AI4I dataset failed the known hash, schema, UDI, or target-distribution check.")

    model = RiskModel()
    try:
        model_summary = model.load_model()
    except FileNotFoundError:
        model_summary = model.train(force_retrain=True)
    if model_summary.get("dataset_source") != "csv:ai4i_2020.csv":
        raise RuntimeError(
            "The loaded risk artifact was not evaluated from data/ai4i_2020.csv; "
            "run `python scripts/run_m2_qa.py` to build a verified local artifact."
        )
    if model_summary.get("artifact_version", ARTIFACT_VERSION) != ARTIFACT_VERSION:
        raise RuntimeError("The loaded model artifact version does not match this M2 code.")

    history = _history_from_dataset_row(dataset.iloc[0])
    risk_trace = _inference_trace(model, history)
    risk_result = risk_trace["calibrated_probability"]
    if not 0.0 <= risk_result <= 1.0:
        raise AssertionError("Risk model returned a probability outside [0, 1].")

    try:
        model.predict_proba({"machine_id": "M05"})
    except ValueError as exc:
        invalid_telemetry = {"handled": True, "error": str(exc)}
    else:
        raise AssertionError("Missing required telemetry was not rejected.")

    policy_inputs = {
        "detector_conf": 1.0,
        "history_risk": 1.0,
        "retrieval_agreement": 1.0,
    }
    defect_decision = decide(**policy_inputs, event_type="defect")
    safety_decision = decide(**policy_inputs, event_type="ppe_violation")
    if defect_decision["decision"] != "auto_act" or defect_decision["human_review_required"]:
        raise AssertionError("Defect event threshold behavior did not match the policy.")
    if safety_decision["decision"] == "auto_act" or not safety_decision["human_review_required"]:
        raise AssertionError("Safety event did not require human review.")

    rag_module.chromadb = None
    rag_module.SentenceTransformer = None
    with tempfile.TemporaryDirectory(prefix="gentwin-m2-local-") as directory:
        data_dir = Path(directory)
        knowledge_base = rag_module.IncidentKnowledgeBase(
            data_dir=str(data_dir),
            persistent_dir=str(data_dir / "chroma"),
        )
        records = knowledge_base.build_incident_documents(
            count=48,
            output_path=str(data_dir / "synthetic_incidents.csv"),
            seed=42,
        )
        relevant = next(
            record
            for record in records
            if record["machine_id"] == "M05"
        )
        relevant["defect"] = "bearing wear"
        relevant["root_cause"] = "bearing wear"
        relevant["evidence"] = "M05 bearing wear recorded; root cause: bearing wear."
        foreign_org = {
            **relevant,
            "org_id": "org-other",
            "incident_id": "FOREIGN-ORG-1",
        }
        foreign_machine = {
            **relevant,
            "machine_id": "M06",
            "incident_id": "FOREIGN-MACHINE-1",
            "evidence": relevant["evidence"].replace("M05", "M06"),
        }
        with (data_dir / "synthetic_incidents.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=sorted(rag_module.REQUIRED_INCIDENT_FIELDS))
            writer.writeheader()
            writer.writerows([*records, foreign_org, foreign_machine])

        retrieved = knowledge_base.search(
            "bearing wear",
            org_id="demo-org",
            machine_id="M05",
            top_k=10,
        )
        retrieved_ids = {item["incident_id"] for item in retrieved}
        rag_isolated = bool(retrieved) and all(
            item["org_id"] == "demo-org" and item["machine_id"] == "M05"
            for item in retrieved
        )
        if "FOREIGN-ORG-1" in retrieved_ids or "FOREIGN-MACHINE-1" in retrieved_ids:
            raise AssertionError("RAG returned evidence outside the requested organization or machine.")

        explain_module = importlib.import_module("m2.explain")
        original_search = explain_module.search_similar_incidents
        original_risk = explain_module.risk
        explain_module.search_similar_incidents = knowledge_base.search
        explain_module.risk = lambda sample: {
            **original_risk(sample),
            "risk_score": float(risk_result),
        }
        try:
            event = {
                "event_id": "m2-local-check",
                "timestamp": "2026-10-25T00:00:00Z",
                "machine_id": "M05",
                "org_id": "demo-org",
                "event_type": "ppe_violation",
                "detector_confidence": 0.95,
                "summary": "bearing wear",
            }
            explanation = explain_module.explain(event, history)
        finally:
            explain_module.search_similar_incidents = original_search
            explain_module.risk = original_risk

        explanation_grounded = (
            explanation["observed_facts"]["machine_id"] == event["machine_id"]
            and explanation["probable_cause"] != "not found"
            and bool(explanation["evidence"])
            and explanation["probable_cause"]
            in {item["root_cause"] for item in explanation["evidence"]}
            and explanation["human_review_required"] is True
        )
        if not explanation_grounded:
            raise AssertionError("Explanation did not match the event scope and retrieved evidence.")

        chat_tools = {
            "get_machine_status": lambda org_id, machine_id: {
                "org_id": org_id,
                "machine_id": machine_id,
                "status": "fixture-only",
            },
            "get_machine_history": lambda org_id, machine_id: {
                **history,
                "org_id": org_id,
                "machine_id": machine_id,
            },
        }
        chat = ChatAssistant(tools=chat_tools, kb=knowledge_base)
        chat_status = chat.respond("Show machine status M05", org_id="demo-org")
        chat_risk = chat.respond("Explain risk for M05", org_id="demo-org")
        chat_offline_ok = (
            chat_status["answer"]["status"] == "fixture-only"
            and chat_risk["answer"]["org_id"] == "demo-org"
            and chat_risk["answer"]["machine_id"] == "M05"
            and 0 <= chat_risk["answer"]["risk_score"] <= 1
        )
        if not chat_offline_ok:
            raise AssertionError("Offline chat mock checks returned an invalid or unscoped response.")

    with tempfile.TemporaryDirectory(prefix="gentwin-m2-model-error-") as directory:
        missing_path = Path(directory) / "missing.pkl"
        try:
            RiskModel(model_path=str(missing_path)).load_model()
        except FileNotFoundError as exc:
            model_load_error = {"handled": True, "error_type": type(exc).__name__}
        else:
            raise AssertionError("A missing model artifact did not report FileNotFoundError.")

    return {
        "dataset": {
            "path": str(dataset_path),
            "sha256": dataset_hash,
            "rows": int(len(dataset)),
            "target_counts": target_counts,
        },
        "model": {
            "path": str(model.model_path),
            "artifact_version": ARTIFACT_VERSION,
            "dataset_source": model_summary["dataset_source"],
            "backend": model_summary.get("model_backend"),
            "risk_probability": float(risk_result),
            "inference_trace": risk_trace,
        },
        "checks": {
            "risk_probability_in_range": True,
            "invalid_telemetry": invalid_telemetry,
            "policy_fusion": {
                "inputs": policy_inputs,
                "defect_event": defect_decision,
                "safety_event": safety_decision,
                "separate_from_ml_probability": True,
                "physical_actions_executed": False,
            },
            "rag_org_machine_isolation": rag_isolated,
            "explanation_grounded_and_safety_reviewed": explanation_grounded,
            "offline_chat_mock": chat_offline_ok,
            "model_load_error": model_load_error,
            "physical_actions_executed": False,
        },
        "representative_telemetry": _representative_telemetry(model, dataset),
        "integration_scope": "M2 library only; temporary synthetic RAG records and explicitly mocked backend callbacks; no M1/M3/M4 services started.",
    }


def main() -> int:
    try:
        print(json.dumps(run_checks(), indent=2))
    except Exception as exc:
        print(json.dumps({
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }, indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
