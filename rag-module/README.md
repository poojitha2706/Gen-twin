# GenTwin Vision — M2 Intelligence

This workspace contains the M2 intelligence module and local integration contracts. The workspace does not contain the team's production M1, M3, or M4 code; this documentation does not claim those systems have been integrated or tested.

## M2 capabilities

- Machine-history failure-risk model with input validation, model artifact versioning, validation-set temperature scaling, ordered UDI holdouts for AI4I, and test-set metrics.
- Deterministic synthetic fallback training data, clearly identified in every training report. It is not the AI4I 2020 dataset and its metrics must not be presented as AI4I results.
- Incident record generation and retrieval with organisation/machine filters. ChromaDB + Sentence Transformers are optional; the offline fallback uses TF-IDF.
- Explainability separates observed event fields, model predictions, and evidence-backed cause hypotheses. Retrieval similarity is a ranking score, not a calibrated probability.
- The decision fusion score is a heuristic, not a calibrated probability. Safety events always require human review; any automatic action remains simulated.
- Read-only chat routing requires trusted backend context and injected data tools. When a backend tool is unavailable, the assistant returns `not found` rather than inventing machine states, events, documents, or telemetry.

## Installation

Install core requirements for offline tests and local fallback operation:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Install optional enhanced retrieval/explanation/model backends only when wanted:

```powershell
python -m pip install -r requirements-optional.txt
```

Optional packages can download large ML models; the standard QA suite does not require model downloads or API credentials.

## Dataset and model

The workspace contains `data/ai4i_2020.csv`, retrieved from the [UCI Machine Learning Repository AI4I 2020 dataset](https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset). QA checks the exact 10,000-row schema, UDI sequence, and target distribution (9,661 no-failure / 339 failure) before reporting real-data metrics. SHA-256: `dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e`.

When no AI4I file is present, `RiskModel` uses a fixed-seed synthetic dataset and includes `dataset_source: synthetic_fallback` in its training report. Synthetic fallback results are useful for code-path checks only. AI4I's failure target is rare (3.39%); accuracy is not sufficient by itself, so QA also reports PR-AUC, class counts, calibration, baselines, confusion matrices, and threshold curves.

For AI4I, rows are sorted by unique UDI and split in order into 60% training, 20% validation, and 20% test. Preprocessing and model fitting use only the training partition; temperature scaling and F1-threshold selection use only validation; reported evaluation uses the held-out test partition. The chronological split avoids random mixing of observations from the dataset's generated sequence, but UDI is not a timestamp and this single benchmark split is not evidence of production performance. Without UDI, the fallback path uses stratified random splits.

The default training report compares the risk model with a prior-only dummy and a class-balanced logistic-regression baseline trained on the same training partition. Test threshold results include fixed cutoffs and the F1-maximizing validation cutoff; the latter is not selected from test outcomes. Thresholds are evaluation diagnostics, not recommendations for production automatic actions.

Risk model artifacts use Python pickle serialization. Only load artifacts created by a trusted local training process; do not load files received from untrusted sources. The evaluation/split update advances the artifact version and uses `data/risk_model_v3.pkl`; older synthetic-fallback artifacts remain untouched and are not loaded by the default path.

## Synthetic incident knowledge base

Generate 300 clearly labeled synthetic records:

```powershell
python scripts/generate_incidents.py --output data/synthetic_incidents.csv --count 300 --seed 42
```

The generator uses a fixed default seed. Generated examples are synthetic and are not real factory records.

## M2 QA and outputs

Run the standalone offline M2 functional smoke-check (no M1/M3/M4 process or API credentials required):

```powershell
python scripts/run_m2_local.py
```

This loads the local v3 risk model (training it from AI4I if the artifact is absent) and verifies the dataset hash/schema. Its JSON includes sanitized feature/preprocessing and raw-to-calibrated probability traces, representative normal/borderline/failure-like AI4I holdout examples, and a separately labelled policy-fusion check. It also uses a temporary synthetic RAG fixture and clearly identified in-process mock callbacks for backend-only chat data. It does not start a network server or perform equipment actions. It fails with a clear message if the verified AI4I dataset or a compatible AI4I-trained artifact is unavailable.

Telemetry units must match the AI4I training data: air/process temperature in kelvin, rotational speed in rpm, torque in Nm, and tool wear in minutes. AI4I does not contain machine IDs, so training fills `Machine_ID` with `M00`; the standalone fixture uses `M05`, which the encoder treats as an unknown category. This dataset therefore provides no learned machine-specific signal.

Run the complete offline M2 suite and generate the distinct-scenario inventory, machine-readable results, coverage report, readable summary, and source ZIP:

```powershell
python scripts/run_m2_qa.py
```

QA outputs are written under `qa/`; the source bundle is `artifacts/GenTwin_M2_QA_Source.zip`. The scenario catalog includes a 1,331-case independent grid over the fusion inputs, in addition to validation, persistence, calibration, RAG, explainability, chat, safety, and isolation cases.
The defect ledger is `qa/m2_defect_fixes.md` with traceable failure inputs, results and regressions in `qa/m2_defect_fixes.json`.

To run tests without generating reports:

```powershell
python -m pytest -q tests
```

The inventory and test results distinguish scenarios defined, executed, passed, failed, skipped, and blocked. Coverage is reported only when the installed pytest-cov plugin produces it.

## Public M2 contracts

- `risk(machine_history) -> dict`
- `decide(detector_conf, history_risk, retrieval_agreement, event_type) -> dict`
- `explain(event, machine_history) -> dict`

`ChatAssistant` accepts trusted tool callbacks for backend status, event, trend, document, and history data. Supply `org_id` from authenticated backend context; never trust an LLM or client-supplied organisation identity.

## Local HTTP integration

The existing FastAPI application can be run locally from this module:

```powershell
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8001
```

In addition to `/health`, `/events`, `/chat`, and the policy preview routes, the application exposes:

- `POST /risk` with `{"machine_history": {...}}` to run the existing calibrated M2 risk model. The response includes `risk_score`, `risk_level`, model/backend and training-dataset metadata, calibration state, and the actual optional explanation result.
- `POST /explain` with `{"event": {...}, "machine_history": {...}}` to call the existing grounded explanation operation. The event must contain the validated event contract and the machine history must match the event scope.

Invalid telemetry and event contracts return HTTP 422. Model loading, inference, and invalid model outputs return HTTP 503 without exposing model paths or request contents. Browser origins are restricted by `M4_ALLOWED_ORIGINS`; the local default is `http://localhost:5173,http://127.0.0.1:5173`.

These routes do not add authentication. Keep them bound to loopback for local development; do not expose them to a network or treat client-provided organization IDs as authenticated identity. M4 only calls `/risk`; it does not connect to the unscoped chat or similar-incident search paths.

## Current limitations

- Live Groq/Gemini generation and API fault handling are not implemented or tested.
- ChromaDB persistence, SentenceTransformer model downloads, authenticated backend calls, and M1/M3/M4 integration are not exercised by the offline QA run; optional services are mocked or absent.
- Document extraction/ingestion (PDF/TXT/DOCX) must be connected to the actual backend upload pipeline; chat document search currently requires an injected, organisation-scoped backend tool.
- Production authentication, persistent backend database integration, WebSocket delivery, and frontend behavior are outside this M2-only work and were not tested.

## Authorship
This module was written by Raviteja. It was imported into the shared repository by Poojitha.
