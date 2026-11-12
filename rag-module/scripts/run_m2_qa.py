from __future__ import annotations

import hashlib
import importlib
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
QA_DIR = ROOT / "qa"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from m2_scenario_catalog import POLICY_CASE_BY_ID  # noqa: E402


TEST_EXPECTATIONS = {
    "test_policy_invalid_evidence_fails_closed": ("fusion", "Invalid probability input contributes zero and is identified."),
    "test_every_safety_event_requires_human_review": ("safety", "Safety event never returns auto_act and always requires human review."),
    "test_policy_exact_threshold_and_adjacent_inputs": ("fusion", "Threshold and adjacent representable values follow the specified tiers."),
    "test_policy_rejects_empty_event_type": ("fusion", "Missing or blank event types are rejected."),
    "test_risk_rejects_each_missing_required_telemetry_field": ("risk_validation", "Missing required telemetry raises ValueError."),
    "test_risk_rejects_malformed_numeric_telemetry": ("risk_validation", "Malformed, missing, non-finite, or boolean telemetry raises ValueError."),
    "test_risk_rejects_extreme_telemetry_magnitudes": ("risk_validation", "Unsupported telemetry magnitude raises ValueError."),
    "test_training_report_labels_synthetic_fallback_and_imbalance": ("risk_evaluation", "Training report identifies provenance, model and class counts."),
    "test_udi_dataset_uses_ordered_holdouts_and_validation_only_threshold_selection": ("risk_evaluation", "UDI data uses ordered holdouts and selects thresholds using validation data only."),
    "test_udi_split_rejects_non_unique_order_values": ("risk_validation", "Duplicate UDI ordering data is rejected instead of silently randomized."),
    "test_ordered_split_rejects_a_partition_missing_one_class": ("risk_validation", "Ordered evaluation fails when a required partition lacks one target class."),
    "test_model_artifact_rejects_invalid_calibration_metadata": ("persistence", "Malformed or unsafe calibration metadata in serialized artifacts is rejected."),
    "test_model_serialization_failure_cleans_temporary_artifact": ("persistence", "Failed model serialization leaves no partial temporary artifact."),
    "test_temperature_scaling_rejects_boolean_probabilities_and_fractional_labels": ("calibration", "Calibration rejects boolean probabilities and non-binary labels."),
    "test_temperature_application_rejects_boolean_probability_input": ("calibration", "Probability calibration does not coerce booleans into numeric values."),
    "test_shap_binary_output_shape_is_converted_to_feature_summary": ("explainability", "Supported SHAP output axis layouts normalize to the same feature summary."),
    "test_shap_malformed_feature_axis_returns_explicit_fallback": ("explainability", "Malformed SHAP shapes return an explicit fallback, not fabricated feature scores."),
    "test_training_input_rejects_missing_target": ("risk_validation", "Missing target column raises ValueError."),
    "test_training_rejects_malformed_datasets": ("risk_validation", "Malformed or undersized training data raises ValueError."),
    "test_training_model_persistence_and_reload": ("persistence", "Trusted model artifact reload reproduces inference."),
    "test_corrupt_model_artifact_reports_error": ("persistence", "Corrupt artifact is rejected with an explicit deserialization error."),
    "test_incompatible_model_artifact_version_rejected": ("persistence", "Unsupported artifact version is rejected."),
    "test_invalid_calibration_temperature_rejected": ("calibration", "Invalid temperature is rejected."),
    "test_temperature_scaling_rejects_invalid_validation": ("calibration", "Invalid validation probabilities or labels are rejected."),
    "test_temperature_scaling_is_reproducible": ("calibration", "Repeated temperature fitting on same data returns the same temperature."),
    "test_ece_known_reference_values": ("calibration", "ECE matches independently calculated reference values."),
    "test_ece_rejects_invalid_inputs": ("calibration", "Invalid ECE inputs raise ValueError."),
    "test_shap_returns_documented_optional_shape": ("explainability", "Missing SHAP dependency returns a documented unavailable result."),
    "test_shap_dependency_failure_is_explicit": ("explainability", "SHAP runtime error returns an explicit safe fallback."),
    "test_incident_generator_is_reproducible_and_unique": ("rag_generation", "Seeded synthetic incidents are reproducible, unique and labelled."),
    "test_incident_generator_rejects_nonpositive_count": ("rag_generation", "Nonpositive record count raises ValueError."),
    "test_incident_record_validation_rejects_bad_fields": ("rag_validation", "Malformed incident records are rejected."),
    "test_incident_ingestion_deduplicates_and_search_cites_actual_records": ("rag_retrieval", "Retrieval returns stored IDs, evidence and ordered uncalibrated relevance."),
    "test_local_ingestion_is_searchable_without_csv_persistence": ("rag_storage", "Offline ingestion is searchable before CSV persistence."),
    "test_legacy_persistent_collection_duplicate_ingestion_is_idempotent": ("rag_persistence", "Legacy persistent collections ignore already stored IDs on repeated ingestion."),
    "test_incident_search_applies_org_and_machine_filters": ("isolation", "Retrieval is restricted to requested org and machine."),
    "test_incident_search_empty_and_irrelevant_queries": ("rag_retrieval", "Empty, irrelevant or unknown-org queries return no evidence."),
    "test_incident_search_top_k_boundaries": ("rag_retrieval", "Top-k limits result count including zero."),
    "test_incident_search_rejects_invalid_top_k": ("rag_validation", "Invalid top-k values are rejected."),
    "test_incident_search_rejects_non_string_machine_scope": ("rag_validation", "Invalid machine scope types fail explicitly."),
    "test_incident_csv_empty_and_corrupt_inputs": ("rag_storage", "Empty and malformed CSV files fail explicitly."),
    "test_persistent_retrieval_uses_chroma_query_filters": ("rag_persistence", "Chroma query applies org/machine filters and maps stored evidence."),
    "test_explanation_separates_observed_prediction_and_hypothesis": ("explainability", "Explanation separates observed facts, predictions and evidence-backed hypotheses."),
    "test_explanation_does_not_claim_cause_without_retrieved_evidence": ("explainability", "No retrieval evidence yields not-found cause and no confidence."),
    "test_explanation_discards_unscoped_or_unsupported_retrieval_hypotheses": ("isolation", "Explanations reject cross-scope or evidence-unsupported retrieval causes."),
    "test_explanation_rejects_mismatched_machine_or_org_context": ("isolation", "Explanations reject telemetry that does not match the event scope."),
    "test_explanation_retrieval_rejects_malformed_scores_and_records": ("explainability", "Malformed retrieval scores and citation records cannot support explanations."),
    "test_explanation_returns_not_found_for_non_list_retrieval": ("explainability", "Unexpected retrieval response types yield a conservative not-found cause."),
    "test_explanation_risk_score_coercion_is_finite_and_bounded": ("risk_validation", "Explanation score coercion rejects invalid probabilities and clamps finite values."),
    "test_explanation_rejects_non_dict_machine_history": ("risk_validation", "Explanation requires dictionary telemetry."),
    "test_policy_overflowing_integer_fails_closed": ("fusion", "Unrepresentably large integer probabilities fail closed."),
    "test_event_contract_rejects_boolean_and_unrepresentable_confidence": ("contracts", "Event confidence rejects booleans and unrepresentable numeric input."),
    "test_event_contract_rejects_non_dict_and_incomplete_events": ("contracts", "Non-dictionary and incomplete events are rejected."),
    "test_training_reuses_a_valid_existing_artifact": ("persistence", "Training reuses a valid existing model artifact without retraining."),
    "test_prediction_rejects_invalid_pipeline_probabilities": ("risk_validation", "Inference rejects malformed, non-finite, and out-of-range model probabilities."),
    "test_prediction_allows_missing_optional_machine_and_type_categories": ("risk_validation", "Optional machine and type telemetry retains documented defaults."),
    "test_invalid_telemetry_is_rejected_before_model_training": ("risk_validation", "Malformed telemetry is rejected before costly model loading or training."),
    "test_default_model_path_uses_new_artifact_version": ("persistence", "Default inference no longer loads the old synthetic-fallback artifact."),
    "test_incident_csv_duplicate_ids_remain_organization_scoped": ("isolation", "CSV deduplication preserves equal incident IDs in distinct organizations."),
    "test_incident_search_fails_closed_without_any_similarity_backend": ("rag_retrieval", "Search returns no evidence when no similarity backend is available."),
    "test_chat_scope_verifier_rejects_missing_or_mismatched_scope": ("isolation", "The common chat scope verifier rejects missing and mismatched fields."),
    "test_chat_returns_not_found_for_null_and_malformed_tool_results": ("chat_grounding", "Null and malformed tool outputs cannot become user-facing evidence."),
    "test_chat_documents_reject_entries_without_document_ids": ("chat_citations", "Document evidence without a citation identifier is rejected."),
    "test_standalone_m2_runner_exercises_offline_contracts": ("standalone", "The M2-only runner validates the real model/dataset plus isolated RAG, explanation, policy, and mocked chat without other services."),
    "test_chat_rejects_invalid_scope_and_non_list_tool_results": ("chat_validation", "Invalid machine identifiers and non-list service results fail closed."),
    "test_event_contract_rejects_malformed_fields": ("contracts", "Malformed shared events are rejected."),
    "test_chat_requires_live_data_provider_and_never_invents_status": ("chat_grounding", "Missing backend tool returns not found, never invented machine data."),
    "test_chat_routes_machine_status_and_rejects_cross_org_response": ("isolation", "Cross-organization status data is rejected."),
    "test_chat_routes_events_and_cites_only_scoped_event_ids": ("chat_citations", "Chat cites only events from authenticated org and machine."),
    "test_chat_documents_are_marked_untrusted_and_cited": ("prompt_injection", "Document excerpts are cited and explicitly marked untrusted."),
    "test_chat_injection_and_secret_requests_do_not_invoke_tools": ("prompt_injection", "Secret/injection request does not invoke a data tool."),
    "test_chat_returns_safe_tool_failure_without_leaking_exception": ("fault_injection", "Tool errors return safe result without exception details or secrets."),
    "test_chat_malformed_or_contextless_requests_fail_closed": ("chat_validation", "Malformed or contextless requests return not found."),
    "test_chat_routes_history_trend_only_to_real_provider": ("chat_grounding", "History trend is returned only from the provided backend tool."),
    "test_chat_risk_requires_scoped_history_and_never_fabricates_it": ("chat_grounding", "Risk explanation requires scoped backend history."),
    "test_chat_retrieval_citations_must_match_org": ("isolation", "Foreign-org incident evidence and citation are rejected."),
}


class ResultPlugin:
    def __init__(self):
        self.collected = []
        self.results: Dict[str, Dict[str, Any]] = {}

    def pytest_collection_finish(self, session):
        self.collected = [item.nodeid for item in session.items]

    def pytest_runtest_logreport(self, report):
        if report.when == "call" or (report.when == "setup" and report.failed):
            self.results[report.nodeid] = {
                "outcome": report.outcome,
                "duration_seconds": round(float(report.duration), 6),
                "failure": str(report.longrepr) if report.failed else None,
            }
        elif report.when == "setup" and report.skipped:
            self.results[report.nodeid] = {
                "outcome": "skipped",
                "duration_seconds": round(float(report.duration), 6),
                "failure": str(report.longrepr),
            }


def scenario_inventory(nodeids):
    inventory = []
    for nodeid in nodeids:
        function = nodeid.split("::")[-1].split("[", 1)[0]
        parameter = re.search(r"\[(M2-POLICY-GRID-\d+)\]", nodeid)
        if parameter:
            case = POLICY_CASE_BY_ID[parameter.group(1)]
            inventory.append({
                "scenario_id": case["id"],
                "category": "fusion_grid",
                "requirements": [case["requirement"]],
                "inputs": {
                    "detector_conf": case["detector_conf"],
                    "history_risk": case["history_risk"],
                    "retrieval_agreement": case["retrieval_agreement"],
                },
                "expected_behavior": {
                    "score": case["expected_score"],
                    "decision": case["expected_decision"],
                },
                "pytest_nodeid": nodeid,
            })
            continue

        category, expected = TEST_EXPECTATIONS.get(
            function,
            ("regression", f"All assertions in {function} pass for this scenario."),
        )
        stable = hashlib.sha256(nodeid.encode("utf-8")).hexdigest()[:12]
        inventory.append({
            "scenario_id": f"M2-CASE-{stable}",
            "category": category,
            "requirements": [function.upper()],
            "inputs": {"pytest_nodeid": nodeid},
            "expected_behavior": expected,
            "pytest_nodeid": nodeid,
        })
    return inventory


def calibration_and_training_example():
    from m2.risk_model import RiskModel

    with tempfile.TemporaryDirectory(prefix="gentwin-m2-eval-") as directory:
        model = RiskModel(model_path=str(Path(directory) / "risk_model.pkl"))
        summary = model.train(force_retrain=True)
        dataset_path = ROOT / "data" / "ai4i_2020.csv"
        if summary.get("dataset_source") == "csv:ai4i_2020.csv" and dataset_path.exists():
            dataset = pd.read_csv(dataset_path)
            expected_columns = {
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
            target_counts = {
                str(key): int(value)
                for key, value in dataset["Machine failure"].value_counts().sort_index().items()
            }
            schema_valid = set(dataset.columns) == expected_columns
            order_valid = (
                dataset["UDI"].is_unique
                and int(dataset["UDI"].min()) == 1
                and int(dataset["UDI"].max()) == 10000
            )
            target_valid = target_counts == {"0": 9661, "1": 339}
            if len(dataset) != 10000 or not schema_valid or not order_valid or not target_valid:
                raise ValueError("The local AI4I CSV does not match the validated UCI dataset schema, ordering, or target counts.")
            summary["dataset_validation"] = {
                "status": "validated",
                "source": "UCI Machine Learning Repository, dataset 601",
                "source_url": "https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset",
                "sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
                "rows": int(len(dataset)),
                "columns": list(dataset.columns),
                "schema_matches_expected": schema_valid,
                "udi_unique": bool(dataset["UDI"].is_unique),
                "udi_min": int(dataset["UDI"].min()),
                "udi_max": int(dataset["UDI"].max()),
                "target_counts": target_counts,
            }
        else:
            summary["dataset_validation"] = {
                "status": "unavailable",
                "reason": "No verified UCI AI4I 2020 CSV was loaded; fallback metrics are synthetic only.",
            }
        return summary


def rag_example():
    rag = importlib.import_module("m2.rag")
    rag.SentenceTransformer = None
    rag.chromadb = None
    with tempfile.TemporaryDirectory(prefix="gentwin-m2-rag-") as directory:
        kb = rag.IncidentKnowledgeBase(data_dir=directory, persistent_dir=str(Path(directory) / "chroma"))
        records = kb.build_incident_documents(300, str(Path(directory) / "synthetic_incidents.csv"), seed=42)
        hits = kb.search("bearing wear vibration", org_id="demo-org", top_k=5)
        saved_ids = {record["incident_id"] for record in records}
        return {
            "generated_records": len(records),
            "hits": hits,
            "citations_verified": all(hit["incident_id"] in saved_ids for hit in hits),
        }


def main():
    QA_DIR.mkdir(parents=True, exist_ok=True)
    inventory_path = QA_DIR / "m2_test_inventory.json"
    results_path = QA_DIR / "m2_test_results.json"
    summary_path = QA_DIR / "m2_test_summary.md"
    coverage_path = QA_DIR / "coverage.json"

    plugin = ResultPlugin()
    args = [
        "-q",
        str(ROOT / "tests" / "test_m2_core.py"),
        str(ROOT / "tests" / "test_m2_exhaustive.py"),
        str(ROOT / "tests" / "test_m2_local_runner.py"),
        "--cov=m2",
        "--cov-branch",
        f"--cov-report=json:{coverage_path}",
        "--cov-report=term-missing",
    ]
    started = time.monotonic()
    pytest_exit = pytest.main(args, plugins=[plugin])
    elapsed = round(time.monotonic() - started, 3)
    standalone_started = time.monotonic()
    standalone = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    standalone_elapsed = round(time.monotonic() - standalone_started, 3)
    standalone_counts = {
        outcome: int(count)
        for count, outcome in re.findall(r"(\d+)\s+(passed|failed|skipped|error)", standalone.stdout)
    }
    inventory = scenario_inventory(plugin.collected)
    inventory_ids = [item["scenario_id"] for item in inventory]
    if len(set(inventory_ids)) != len(inventory_ids):
        raise RuntimeError("QA inventory contains duplicate scenario IDs.")

    for item in inventory:
        item["outcome"] = plugin.results.get(item["pytest_nodeid"], {}).get("outcome", "not_executed")
        item["duration_seconds"] = plugin.results.get(item["pytest_nodeid"], {}).get("duration_seconds")
        item["failure"] = plugin.results.get(item["pytest_nodeid"], {}).get("failure")
    inventory_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    outcomes = [plugin.results.get(nodeid, {}).get("outcome", "not_executed") for nodeid in plugin.collected]
    passed = outcomes.count("passed")
    failed = outcomes.count("failed")
    skipped = outcomes.count("skipped")
    blocked = outcomes.count("not_executed")
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": "python scripts/run_m2_qa.py",
        "pytest_exit_code": int(pytest_exit),
        "duration_seconds": elapsed,
        "standalone_test_run": {
            "command": "python -m pytest -q tests",
            "exit_code": int(standalone.returncode),
            "duration_seconds": standalone_elapsed,
            "counts": standalone_counts,
            "output": standalone.stdout.strip(),
        },
        "scenarios_defined": len(inventory),
        "distinct_scenario_ids": len(set(inventory_ids)),
        "scenarios_executed": len(plugin.results),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "blocked_or_not_executed": blocked,
        "failures": [
            {"scenario_id": item["scenario_id"], "failure": item["failure"]}
            for item in inventory
            if item["outcome"] == "failed"
        ],
    }

    try:
        report["training_evaluation"] = calibration_and_training_example()
    except Exception as exc:
        report["training_evaluation"] = {
            "status": "blocked",
            "reason": f"{type(exc).__name__}: {exc}",
        }
    try:
        rag_result = rag_example()
        report["rag_example"] = {
            "generated_records": rag_result["generated_records"],
            "hit_count": len(rag_result["hits"]),
            "cited_ids": [hit["incident_id"] for hit in rag_result["hits"]],
            "citations_verified_against_store": rag_result["citations_verified"],
            "score_kind": (
                rag_result["hits"][0]["score_kind"] if rag_result["hits"] else None
            ),
        }
    except Exception as exc:
        report["rag_example"] = {"status": "blocked", "reason": f"{type(exc).__name__}: {exc}"}

    from m2.policy import decide

    report["policy_examples"] = {
        label: decide(*values, "defect")
        for label, values in {
            "auto_act": (1.0, 1.0, 1.0),
            "alert": (0.8, 0.7, 0.6),
            "escalate": (0.2, 0.3, 0.2),
        }.items()
    }
    report["safety_example"] = decide(1.0, 1.0, 1.0, "ppe_violation")
    if coverage_path.exists():
        report["coverage_file"] = "coverage.json"
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        report["coverage"] = coverage.get("totals", {})
    results_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    training = report["training_evaluation"]
    coverage_totals = report.get("coverage", {})
    dataset_validation = training.get("dataset_validation", {})
    baselines = training.get("baselines", {})
    thresholds = training.get("threshold_results", {})
    threshold_table = "\n".join(
        f"| {details['threshold']:.6f} | {details['precision']:.4f} | {details['recall']:.4f} | "
        f"{details['f1']:.4f} | {details['confusion_matrix']} |"
        for details in thresholds.values()
    )
    baseline_table = "\n".join(
        f"| {name} | {details['precision']:.4f} | {details['recall']:.4f} | {details['f1']:.4f} | "
        f"{details['roc_auc']!s} | {details['precision_recall_auc']!s} | {details['confusion_matrix']} |"
        for name, details in baselines.items()
    )
    coverage_statement_rate = coverage_totals.get("percent_statements_covered", coverage_totals.get("percent_covered"))
    summary_path.write_text(
        "# GenTwin Vision M2 QA Results\n\n"
        f"- Generated (UTC): {report['generated_at_utc']}\n"
        f"- Full QA command: `python scripts/run_m2_qa.py` (final exit "
        f"{int(bool(pytest_exit or standalone.returncode or report.get('training_evaluation', {}).get('status') == 'blocked'))}; "
        f"pytest {pytest_exit}; {elapsed}s)\n"
        f"- Independent documented test command: `python -m pytest -q tests` "
        f"(exit {standalone.returncode}; {standalone_elapsed}s; {standalone.stdout.strip()})\n"
        f"- Scenarios defined/unique/executed: {report['scenarios_defined']}/{report['distinct_scenario_ids']}/"
        f"{report['scenarios_executed']}; passed {passed}, failed {failed}, skipped {skipped}, blocked {blocked}\n"
        f"- Dataset source: `{training.get('dataset_source', training.get('status', 'unknown'))}`; "
        f"validation `{dataset_validation.get('status', 'not reported')}`\n"
        f"- Split: `{training.get('split_strategy', 'unavailable')}`; rows train/validation/test: "
        f"{training.get('train_rows')}/{training.get('validation_rows')}/{training.get('test_rows')}\n"
        f"- Class counts overall: `{training.get('target_class_counts')}`; by split: `{training.get('split_class_counts')}`\n"
        f"- Model test metrics at threshold 0.5: precision `{training.get('precision')}`, recall `{training.get('recall')}`, "
        f"F1 `{training.get('f1')}`, ROC-AUC `{training.get('roc_auc')}`, PR-AUC `{training.get('precision_recall_auc')}`, "
        f"confusion matrix `[ [TN, FP], [FN, TP] ]` `{training.get('confusion_matrix')}`\n"
        f"- Calibration: temperature `{training.get('temperature')}`, ECE `{training.get('ece_before')}` → "
        f"`{training.get('ece_after')}`, Brier `{training.get('brier_before')}` → `{training.get('brier_after')}`\n"
        f"- Validation-only threshold selection: `{training.get('threshold_selection')}`\n\n"
        "## Test-set threshold results\n\n"
        "| Threshold | Precision | Recall | F1 | Confusion matrix [ [TN, FP], [FN, TP] ] |\n"
        "|---:|---:|---:|---:|---|\n"
        f"{threshold_table}\n\n"
        "## Baselines (test set; threshold 0.5)\n\n"
        "| Baseline | Precision | Recall | F1 | ROC-AUC | PR-AUC | Confusion matrix |\n"
        "|---|---:|---:|---:|---:|---:|---|\n"
        f"{baseline_table}\n\n"
        "## Data, coverage, and scope\n\n"
        f"- Dataset check: `{dataset_validation}`\n"
        f"- Statement coverage: `{coverage_totals.get('covered_lines')}/{coverage_totals.get('num_statements')}` "
        f"({coverage_statement_rate}%); branch coverage: `{coverage_totals.get('covered_branches')}/"
        f"{coverage_totals.get('num_branches')}` ({coverage_totals.get('percent_branches_covered')}%).\n"
        f"- RAG citations were checked against the stored records: "
        f"`{report['rag_example'].get('citations_verified_against_store', False)}`. Similarity is a ranking signal, not a probability.\n"
        "- Offline tests use local fixtures and mocked optional services. No live authentication, M1/M3/M4 integration, "
        "ChromaDB deployment, embedding download, or external API integration was exercised.\n"
        "- This is a single ordered holdout evaluation on AI4I's UDI sequence. UDI is ordering, not a documented timestamp; "
        "the benchmark is synthetic/simulated manufacturing data and is not production validation.\n",
        encoding="utf-8",
    )

    report["source_package"] = "artifacts/GenTwin_M2_QA_Source.zip"
    evaluation_blocked = report.get("training_evaluation", {}).get("status") == "blocked"
    report["exit_code"] = int(bool(pytest_exit or standalone.returncode or evaluation_blocked))
    results_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    package = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "package_m2.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    report["source_package"] = package.stdout.strip() or report["source_package"]
    report["package_error"] = package.stderr.strip() if package.returncode else None
    report["exit_code"] = int(bool(pytest_exit or standalone.returncode or package.returncode or evaluation_blocked))
    results_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary = summary_path.read_text(encoding="utf-8")
    summary = summary.replace(
        f"(final exit {int(bool(pytest_exit or standalone.returncode or evaluation_blocked))}; pytest {pytest_exit}; {elapsed}s)",
        f"(final exit {report['exit_code']}; pytest {pytest_exit}; {elapsed}s)",
    )
    summary_path.write_text(summary, encoding="utf-8")

    print(json.dumps({
        "scenarios_defined": report["scenarios_defined"],
        "distinct_scenario_ids": report["distinct_scenario_ids"],
        "scenarios_executed": report["scenarios_executed"],
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "blocked_or_not_executed": blocked,
        "results": str(results_path),
        "inventory": str(inventory_path),
        "summary": str(summary_path),
        "source_package": report.get("source_package"),
    }, indent=2))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
