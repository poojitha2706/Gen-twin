from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_standalone_m2_runner_exercises_offline_contracts():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_m2_local.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    checks = report["checks"]
    assert report["model"]["dataset_source"] == "csv:ai4i_2020.csv"
    assert checks["risk_probability_in_range"] is True
    assert checks["invalid_telemetry"]["handled"] is True
    trace = report["model"]["inference_trace"]
    assert trace["feature_order"] == [
        "Machine_ID",
        "Type",
        "Air_temperature",
        "Process_temperature",
        "Rotational_speed",
        "Torque",
        "Tool_wear",
    ]
    assert trace["raw_positive_probability"] == trace["raw_class_probabilities"]["1"]
    assert trace["calibrated_probability"] == report["model"]["risk_probability"]
    assert len(report["representative_telemetry"]) == 3
    assert all(
        0 <= sample["trace"]["calibrated_probability"] <= 1
        and sample["trace"]["feature_order"] == trace["feature_order"]
        for sample in report["representative_telemetry"]
    )
    policy = checks["policy_fusion"]
    assert policy["inputs"] == {
        "detector_conf": 1.0,
        "history_risk": 1.0,
        "retrieval_agreement": 1.0,
    }
    assert policy["defect_event"]["decision"] == "auto_act"
    assert policy["safety_event"]["human_review_required"] is True
    assert policy["physical_actions_executed"] is False
    assert checks["rag_org_machine_isolation"] is True
    assert checks["explanation_grounded_and_safety_reviewed"] is True
    assert checks["offline_chat_mock"] is True
    assert checks["model_load_error"]["handled"] is True
    assert checks["physical_actions_executed"] is False
    assert "no M1/M3/M4 services started" in report["integration_scope"]
