from __future__ import annotations

import math
import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

try:
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.base import clone
    from sklearn.dummy import DummyClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        accuracy_score,
        average_precision_score,
        confusion_matrix,
        f1_score,
        precision_recall_curve,
        precision_score,
        recall_score,
        roc_auc_score,
    )
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
except Exception:  # pragma: no cover
    ColumnTransformer = None
    SimpleImputer = None
    accuracy_score = None
    average_precision_score = None
    confusion_matrix = None
    f1_score = None
    precision_score = None
    recall_score = None
    roc_auc_score = None
    precision_recall_curve = None
    clone = None
    DummyClassifier = None
    LogisticRegression = None
    train_test_split = None
    Pipeline = None
    OneHotEncoder = None
    StandardScaler = None
    HistGradientBoostingClassifier = None
    RandomForestClassifier = None

try:
    import xgboost as xgb
except Exception:  # pragma: no cover
    xgb = None

try:
    import lightgbm as lgb
except Exception:  # pragma: no cover
    lgb = None

try:
    import shap
except Exception:  # pragma: no cover
    shap = None


DEFAULT_FEATURES: List[str] = [
    "Machine_ID",
    "Type",
    "Air_temperature",
    "Process_temperature",
    "Rotational_speed",
    "Torque",
    "Tool_wear",
]
ARTIFACT_VERSION = 3
NUMERIC_FEATURES = [
    "Air_temperature",
    "Process_temperature",
    "Rotational_speed",
    "Torque",
    "Tool_wear",
]


class RiskModel:
    def __init__(self, model_path: Optional[str] = None, temperature: float = 1.0):
        data_dir = Path(__file__).resolve().parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = Path(model_path) if model_path else data_dir / "risk_model_v3.pkl"
        self.pipeline = None
        self.feature_columns: List[str] = list(DEFAULT_FEATURES)
        self._train_summary: Dict[str, Any] = {}
        self.temperature = float(temperature)
        if not math.isfinite(self.temperature) or self.temperature <= 0:
            raise ValueError("Calibration temperature must be positive and finite.")
        self.calibration_ready = False
        self.dataset_source = "not_loaded"
        self.split_strategy = "stratified_random"

    def _canonicalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {
            "machine_id": "Machine_ID",
            "machine": "Machine_ID",
            "type": "Type",
            "defect_type": "Type",
            "air_temperature": "Air_temperature",
            "process_temperature": "Process_temperature",
            "rotational_speed": "Rotational_speed",
            "torque": "Torque",
            "tool_wear": "Tool_wear",
            "failure": "Failure",
            "label": "Failure",
            "Machine failure": "Failure",
            "Air temperature [K]": "Air_temperature",
            "Process temperature [K]": "Process_temperature",
            "Rotational speed [rpm]": "Rotational_speed",
            "Torque [Nm]": "Torque",
            "Tool wear [min]": "Tool_wear",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        if "Type" not in df.columns and "type" in df.columns:
            df.rename(columns={"type": "Type"}, inplace=True)
        if "Machine_ID" not in df.columns and "machine_id" in df.columns:
            df.rename(columns={"machine_id": "Machine_ID"}, inplace=True)
        return df

    def _synth_ai4i(self) -> pd.DataFrame:
        rng = np.random.default_rng(42)
        rows: List[Dict[str, Any]] = []
        defect_types = ["No Defect", "Wear", "Overstrain", "Thermal Damage", "Voltage", "Tool Wear"]
        for i in range(1400):
            temp = 30 + rng.normal(0, 8)
            rotation = 1400 + rng.normal(0, 250)
            torque = 40 + rng.normal(0, 10)
            tool_wear = rng.uniform(0, 1.0)
            defect = defect_types[i % len(defect_types)]
            machine = f"M{i % 12 + 1:02d}"
            risk_signal = (
                0.12
                + max(temp - 80, 0.0) / 120.0
                + max(rotation - 1700, 0.0) / 4000.0
                + max(tool_wear - 0.7, 0.0) * 0.4
                + max(torque - 65.0, 0.0) / 300.0
            )
            if defect in {"Thermal Damage", "Tool Wear"}:
                risk_signal += 0.25
            failure_probability = min(0.98, max(0.05, risk_signal))
            label = int(rng.random() < failure_probability)
            rows.append(
                {
                    "Machine_ID": machine,
                    "Type": defect,
                    "Air_temperature": float(temp),
                    "Process_temperature": float(temp + 8 + rng.normal(0, 2)),
                    "Rotational_speed": float(rotation),
                    "Torque": float(torque),
                    "Tool_wear": float(tool_wear),
                    "Failure": int(label),
                }
            )
        return pd.DataFrame(rows)

    def _load_dataset(self) -> pd.DataFrame:
        candidates = [
            Path(__file__).resolve().parent.parent / "data" / "ai4i_2020.csv",
            Path(__file__).resolve().parent.parent / "data" / "ai4i.csv",
            Path.cwd() / "data" / "ai4i_2020.csv",
        ]
        for candidate in candidates:
            if candidate.exists():
                df = pd.read_csv(candidate)
                self.dataset_source = f"csv:{candidate.name}"
                return self._canonicalize_columns(df)
        self.dataset_source = "synthetic_fallback"
        return self._synth_ai4i()

    def _build_pipeline(self) -> Pipeline:
        if Pipeline is None or ColumnTransformer is None:
            raise RuntimeError("scikit-learn is required to train the risk model.")

        numeric_cols = [
            "Air_temperature",
            "Process_temperature",
            "Rotational_speed",
            "Torque",
            "Tool_wear",
        ]
        categorical_cols = ["Machine_ID", "Type"]

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), numeric_cols),
                ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols),
            ],
            remainder="drop",
        )

        if xgb is not None:
            model = xgb.XGBClassifier(
                objective="binary:logistic",
                eval_metric="logloss",
                n_estimators=200,
                max_depth=4,
                learning_rate=0.08,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=42,
            )
        elif lgb is not None:
            model = lgb.LGBMClassifier(
                objective="binary",
                metric="binary_logloss",
                n_estimators=200,
                learning_rate=0.08,
                random_state=42,
            )
        elif RandomForestClassifier is not None:
            model = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced")
        else:
            model = HistGradientBoostingClassifier(random_state=42)

        pipeline = Pipeline([("preprocess", preprocessor), ("model", model)])
        self.feature_columns = list(DEFAULT_FEATURES)
        return pipeline

    def _prepare_dataset(self) -> pd.DataFrame:
        df = self._load_dataset().copy()
        df = self._canonicalize_columns(df)
        target_candidates = ["Failure", "failure", "label"]
        target_name = next((name for name in target_candidates if name in df.columns), None)
        if target_name is None:
            raise ValueError("No target column was found in the dataset; expected 'Failure' or 'label'.")
        df = df.rename(columns={target_name: "Failure"})

        required_features = set(NUMERIC_FEATURES + ["Type"])
        missing_features = sorted(required_features - set(df.columns))
        if missing_features:
            raise ValueError(f"Dataset is missing required feature columns: {missing_features}")

        if df.empty:
            raise ValueError("Training dataset is empty.")
        if "UDI" in df.columns:
            order = pd.to_numeric(df["UDI"], errors="coerce")
            if order.isna().any() or not np.isfinite(order.to_numpy(dtype=float)).all() or order.duplicated().any():
                raise ValueError("Dataset UDI values must be finite, unique, and numeric for ordered splitting.")
            df = df.assign(_udi_order=order).sort_values("_udi_order", kind="stable")
            self.split_strategy = "chronological_udi"
        else:
            self.split_strategy = "stratified_random"
        if "Machine_ID" not in df.columns:
            df["Machine_ID"] = "M00"

        for col in NUMERIC_FEATURES:
            numeric_values = pd.to_numeric(df[col], errors="coerce")
            invalid = numeric_values.isna() & df[col].notna()
            if invalid.any():
                raise ValueError(f"Dataset feature '{col}' contains non-numeric values.")
            finite_values = numeric_values.dropna().to_numpy(dtype=float)
            if not np.isfinite(finite_values).all():
                raise ValueError(f"Dataset feature '{col}' contains infinite values.")
            if numeric_values.isna().all():
                raise ValueError(f"Dataset feature '{col}' contains no usable values.")
            df[col] = numeric_values

        df["Machine_ID"] = df["Machine_ID"].astype(str)
        if df["Type"].isna().any() or df["Type"].astype(str).str.strip().eq("").any():
            raise ValueError("Dataset feature 'Type' contains missing or empty values.")
        df["Type"] = df["Type"].astype(str)
        labels = pd.to_numeric(df["Failure"], errors="coerce")
        if labels.isna().any() or not labels.isin([0, 1]).all():
            raise ValueError("Target 'Failure' must contain only binary 0/1 labels.")
        df["Failure"] = labels.astype(int)
        if df["Failure"].nunique() < 2:
            raise ValueError("Target 'Failure' must contain both positive and negative classes.")
        counts = df["Failure"].value_counts()
        if counts.min() < 10:
            raise ValueError("Training requires at least ten examples from each target class.")
        return df[["Machine_ID", "Type", "Air_temperature", "Process_temperature", "Rotational_speed", "Torque", "Tool_wear", "Failure"]]

    def _history_to_row(self, machine_history: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(machine_history, dict):
            raise ValueError("machine_history must be a dictionary of feature values.")

        aliases = {
            "Machine_ID": ("machine_id", "Machine_ID"),
            "Type": ("type", "Type"),
            "Air_temperature": ("air_temperature", "Air_temperature"),
            "Process_temperature": ("process_temperature", "Process_temperature"),
            "Rotational_speed": ("rotational_speed", "Rotational_speed"),
            "Torque": ("torque", "Torque"),
            "Tool_wear": ("tool_wear", "Tool_wear"),
        }
        recognized_keys = {
            "machine_id",
            "Machine_ID",
            "type",
            "Type",
            "air_temperature",
            "Air_temperature",
            "process_temperature",
            "Process_temperature",
            "rotational_speed",
            "Rotational_speed",
            "torque",
            "Torque",
            "tool_wear",
            "Tool_wear",
        }
        if not isinstance(machine_history, dict) or not set(machine_history).intersection(recognized_keys):
            raise ValueError("machine_history must contain known machine telemetry fields.")

        normalized: Dict[str, Any] = {}
        missing = []
        for feature, keys in aliases.items():
            value = next((machine_history[key] for key in keys if key in machine_history), None)
            if value is None:
                if feature in {"Machine_ID", "Type"}:
                    normalized[feature] = "M00" if feature == "Machine_ID" else "No Defect"
                    continue
                missing.append(feature)
                continue
            if feature in NUMERIC_FEATURES:
                if isinstance(value, bool):
                    raise ValueError(f"Telemetry feature '{feature}' must be numeric, not boolean.")
                try:
                    numeric = float(value)
                except (TypeError, ValueError, OverflowError) as exc:
                    raise ValueError(f"Telemetry feature '{feature}' must be numeric.") from exc
                if not math.isfinite(numeric):
                    raise ValueError(f"Telemetry feature '{feature}' must be finite.")
                if abs(numeric) > 1_000_000:
                    raise ValueError(f"Telemetry feature '{feature}' exceeds the supported magnitude.")
                normalized[feature] = numeric
            else:
                if not isinstance(value, str):
                    raise ValueError(f"Telemetry feature '{feature}' must be a string.")
                if not str(value).strip():
                    raise ValueError(f"Telemetry feature '{feature}' cannot be empty.")
                normalized[feature] = str(value).strip()
        if missing:
            raise ValueError(f"machine_history is missing required telemetry features: {missing}")
        return {key: normalized[key] for key in DEFAULT_FEATURES}

    def train(self, force_retrain: bool = False) -> Dict[str, Any]:
        if self.pipeline is not None and not force_retrain and self.model_path.exists():
            self.load_model()
            return self._train_summary

        df = self._prepare_dataset()
        X = df[DEFAULT_FEATURES]
        y = df["Failure"]

        if self.split_strategy == "chronological_udi":
            train_end = int(len(df) * 0.6)
            validation_end = int(len(df) * 0.8)
            X_train, X_val, X_test = X.iloc[:train_end], X.iloc[train_end:validation_end], X.iloc[validation_end:]
            y_train, y_val, y_test = y.iloc[:train_end], y.iloc[train_end:validation_end], y.iloc[validation_end:]
            if any(labels.nunique() < 2 for labels in (y_train, y_val, y_test)):
                raise ValueError("Ordered train, validation, and test partitions must each contain both target classes.")
        else:
            X_train, X_temp, y_train, y_temp = train_test_split(
                X,
                y,
                test_size=0.4,
                random_state=42,
                stratify=y,
            )
            X_val, X_test, y_val, y_test = train_test_split(
                X_temp,
                y_temp,
                test_size=0.5,
                random_state=42,
                stratify=y_temp,
            )

        self.pipeline = self._build_pipeline()
        self.pipeline.fit(X_train, y_train)

        val_probs = self.pipeline.predict_proba(X_val)[:, 1]
        self.temperature = self._fit_temperature_scaling(val_probs, y_val)
        self.calibration_ready = True

        raw_test_probs = self.pipeline.predict_proba(X_test)[:, 1]
        raw_val_probs = self.pipeline.predict_proba(X_val)[:, 1]
        test_probs = self.pipeline.predict_proba(X_test)[:, 1]
        test_probs = self._apply_temperature(test_probs)
        test_preds = (test_probs >= 0.5).astype(int)
        validation_calibrated = self._apply_temperature(raw_val_probs)
        selected_threshold = self._select_f1_threshold(y_val.to_numpy(), validation_calibrated)
        threshold_values = (0.1, 0.2, 0.3, 0.5, selected_threshold)
        threshold_results = {
            str(round(float(threshold), 6)): self._classification_metrics(
                y_test.to_numpy(), test_probs, float(threshold)
            )
            for threshold in threshold_values
        }
        baselines = self._evaluate_baselines(X_train, y_train, X_val, y_val, X_test, y_test, selected_threshold)

        self._train_summary = {
            "dataset_rows": int(len(df)),
            "dataset_source": self.dataset_source,
            "split_strategy": self.split_strategy,
            "model_backend": type(self.pipeline.named_steps["model"]).__name__,
            "target_class_counts": {str(k): int(v) for k, v in y.value_counts().sort_index().items()},
            "split_class_counts": {
                "train": {str(k): int(v) for k, v in y_train.value_counts().sort_index().items()},
                "validation": {str(k): int(v) for k, v in y_val.value_counts().sort_index().items()},
                "test": {str(k): int(v) for k, v in y_test.value_counts().sort_index().items()},
            },
            "training_seed": 42,
            "train_rows": int(len(X_train)),
            "validation_rows": int(len(X_val)),
            "test_rows": int(len(X_test)),
            "precision": float(precision_score(y_test, test_preds, zero_division=0)),
            "recall": float(recall_score(y_test, test_preds, zero_division=0)),
            "f1": float(f1_score(y_test, test_preds, zero_division=0)),
            "accuracy": float(accuracy_score(y_test, test_preds)),
            "roc_auc": float(roc_auc_score(y_test, test_probs)) if len(np.unique(y_test)) > 1 else None,
            "precision_recall_auc": float(average_precision_score(y_test, test_probs)) if len(np.unique(y_test)) > 1 else None,
            "precision_recall_auc_method": "average_precision_non_interpolated",
            "confusion_matrix": confusion_matrix(y_test, test_preds).tolist(),
            "temperature": float(self.temperature),
            "ece_before": self._expected_calibration_error(raw_test_probs, y_test.to_numpy()),
            "ece_after": self._expected_calibration_error(test_probs, y_test.to_numpy()),
            "brier_before": float(np.mean((raw_test_probs - y_test.to_numpy()) ** 2)),
            "brier_after": float(np.mean((test_probs - y_test.to_numpy()) ** 2)),
            "threshold_selection": {
                "method": "maximum validation F1 after validation-fitted temperature scaling",
                "threshold": float(selected_threshold),
            },
            "threshold_results": threshold_results,
            "baselines": baselines,
        }
        self.save_model()
        return self._train_summary

    @staticmethod
    def _classification_metrics(labels: np.ndarray, probabilities: np.ndarray, threshold: float) -> Dict[str, Any]:
        predictions = (np.asarray(probabilities, dtype=float) >= threshold).astype(int)
        labels = np.asarray(labels, dtype=int)
        return {
            "threshold": float(threshold),
            "precision": float(precision_score(labels, predictions, zero_division=0)),
            "recall": float(recall_score(labels, predictions, zero_division=0)),
            "f1": float(f1_score(labels, predictions, zero_division=0)),
            "confusion_matrix": confusion_matrix(labels, predictions).tolist(),
        }

    @staticmethod
    def _select_f1_threshold(labels: np.ndarray, probabilities: np.ndarray) -> float:
        precisions, recalls, thresholds = precision_recall_curve(labels, probabilities)
        if len(thresholds) == 0:
            return 0.5
        f1_values = 2 * precisions[:-1] * recalls[:-1] / np.maximum(precisions[:-1] + recalls[:-1], 1e-12)
        best = np.flatnonzero(f1_values == np.max(f1_values))
        return float(thresholds[int(best[-1])])

    def _evaluate_baselines(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        selected_threshold: float,
    ) -> Dict[str, Any]:
        if clone is None or DummyClassifier is None or LogisticRegression is None:
            return {"status": "unavailable", "reason": "scikit-learn baseline dependencies are unavailable"}

        preprocess = self.pipeline.named_steps["preprocess"]
        estimators = {
            "dummy_prior": DummyClassifier(strategy="prior"),
            "logistic_regression_balanced": LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42),
        }
        reports = {}
        for name, estimator in estimators.items():
            if name == "dummy_prior":
                baseline = Pipeline([("model", estimator)])
            else:
                baseline_preprocess = clone(preprocess)
                baseline_preprocess.set_params(
                    num=Pipeline([
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ])
                )
                baseline = Pipeline([("preprocess", baseline_preprocess), ("model", estimator)])
            baseline.fit(X_train, y_train)
            validation_probs = baseline.predict_proba(X_val)[:, 1]
            baseline_threshold = self._select_f1_threshold(y_val.to_numpy(), validation_probs)
            test_probs = baseline.predict_proba(X_test)[:, 1]
            predictions = (test_probs >= 0.5).astype(int)
            reports[name] = {
                "threshold_selection": {
                    "method": "maximum validation F1; test labels not used",
                    "threshold": float(baseline_threshold),
                },
                "precision": float(precision_score(y_test, predictions, zero_division=0)),
                "recall": float(recall_score(y_test, predictions, zero_division=0)),
                "f1": float(f1_score(y_test, predictions, zero_division=0)),
                "accuracy": float(accuracy_score(y_test, predictions)),
                "roc_auc": float(roc_auc_score(y_test, test_probs)) if len(np.unique(y_test)) > 1 else None,
                "precision_recall_auc": float(average_precision_score(y_test, test_probs)) if len(np.unique(y_test)) > 1 else None,
                "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
                "ece": self._expected_calibration_error(test_probs, y_test.to_numpy()),
                "brier": float(np.mean((test_probs - y_test.to_numpy()) ** 2)),
                "threshold_results": {
                    str(round(threshold, 6)): self._classification_metrics(y_test.to_numpy(), test_probs, threshold)
                    for threshold in (0.1, 0.2, 0.3, 0.5, baseline_threshold, selected_threshold)
                },
            }
        return reports

    def _fit_temperature_scaling(self, probs: np.ndarray, labels: pd.Series) -> float:
        if any(isinstance(value, (bool, np.bool_)) for value in np.asarray(probs, dtype=object).flat):
            raise ValueError("Calibration probabilities cannot be boolean.")
        raw_labels = np.asarray(labels)
        if not np.isin(raw_labels, [0, 1]).all():
            raise ValueError("Calibration labels must contain only binary 0/1 values.")
        try:
            probs = np.asarray(probs, dtype=float)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Calibration probabilities must be finite numeric values.") from exc
        labels = raw_labels.astype(int)
        if probs.ndim != 1 or len(probs) == 0 or len(probs) != len(labels):
            raise ValueError("Calibration probabilities and labels must be non-empty one-dimensional arrays of equal length.")
        if (
            not np.isfinite(probs).all()
            or np.any((probs < 0) | (probs > 1))
            or not np.isin(labels, [0, 1]).all()
        ):
            raise ValueError("Calibration data contains invalid probabilities or labels.")
        if np.unique(labels).size < 2:
            raise ValueError("Temperature scaling requires both classes in validation labels.")
        probs = np.clip(probs, 1e-9, 1.0 - 1e-9)
        logits = np.log(probs / (1.0 - probs))
        best_temperature = 1.0
        best_loss = float("inf")
        for temp in np.arange(0.5, 5.1, 0.1):
            scaled = 1.0 / (1.0 + np.exp(-logits / temp))
            clipped = np.clip(scaled, 1e-9, 1.0 - 1e-9)
            loss = -np.mean(labels * np.log(clipped) + (1 - labels) * np.log(1 - clipped))
            if loss < best_loss:
                best_loss = float(loss)
                best_temperature = float(temp)
        return best_temperature

    def _apply_temperature(self, probs: np.ndarray) -> np.ndarray:
        if not math.isfinite(self.temperature) or self.temperature <= 0:
            raise ValueError("Calibration temperature must be positive and finite.")
        if any(isinstance(value, (bool, np.bool_)) for value in np.asarray(probs, dtype=object).flat):
            raise ValueError("Probabilities cannot be boolean.")
        try:
            probs = np.asarray(probs, dtype=float)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Probabilities must be finite numeric values.") from exc
        if not np.isfinite(probs).all() or np.any((probs < 0) | (probs > 1)):
            raise ValueError("Probabilities must be finite values in [0, 1].")
        probs = np.clip(probs, 1e-9, 1.0 - 1e-9)
        logits = np.log(probs / (1.0 - probs))
        scaled = 1.0 / (1.0 + np.exp(-logits / max(self.temperature, 1e-6)))
        return np.clip(scaled, 1e-9, 1.0 - 1e-9)

    def save_model(self) -> str:
        if self.pipeline is None:
            raise ValueError("Cannot save a model before training or loading one.")
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "artifact_version": ARTIFACT_VERSION,
            "pipeline": self.pipeline,
            "temperature": self.temperature,
            "feature_columns": self.feature_columns,
            "train_summary": self._train_summary,
        }
        temporary_path = self.model_path.with_name(f".{self.model_path.name}.tmp")
        try:
            with temporary_path.open("wb") as handle:
                pickle.dump(payload, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.model_path)
        except Exception:
            if temporary_path.exists():
                temporary_path.unlink()
            raise
        return str(self.model_path)

    def load_model(self) -> Dict[str, Any]:
        if not self.model_path.exists():
            raise FileNotFoundError(f"No trained model file exists at {self.model_path}.")
        with self.model_path.open("rb") as handle:
            payload = pickle.load(handle)
        if not isinstance(payload, dict) or payload.get("artifact_version") != ARTIFACT_VERSION:
            raise ValueError("Unsupported or corrupt risk-model artifact version.")
        pipeline = payload.get("pipeline")
        if not hasattr(pipeline, "predict_proba"):
            raise ValueError("Risk-model artifact does not contain a compatible probability pipeline.")
        pipeline_features = getattr(pipeline, "feature_names_in_", None)
        named_steps = getattr(pipeline, "named_steps", {})
        preprocessor = named_steps.get("preprocess") if hasattr(named_steps, "get") else None
        preprocessor_features = getattr(preprocessor, "feature_names_in_", None)
        if not np.array_equal(pipeline_features, DEFAULT_FEATURES) or not np.array_equal(
            preprocessor_features, DEFAULT_FEATURES
        ):
            raise ValueError("Risk-model artifact contains an incompatible feature schema or ordering.")
        self._positive_class_index(2, pipeline)
        try:
            temperature = float(payload["temperature"])
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Risk-model artifact contains an invalid calibration temperature.") from exc
        if not math.isfinite(temperature) or temperature <= 0:
            raise ValueError("Risk-model artifact contains an invalid calibration temperature.")
        feature_columns = payload.get("feature_columns")
        summary = payload.get("train_summary")
        if feature_columns != DEFAULT_FEATURES or not isinstance(summary, dict):
            raise ValueError("Risk-model artifact contains invalid feature metadata or training summary.")
        self.pipeline = pipeline
        self.temperature = temperature
        self.feature_columns = list(feature_columns)
        self._train_summary = summary
        self.calibration_ready = bool(self._train_summary)
        return self._train_summary

    def _positive_class_index(self, probability_count: int, pipeline: Any = None) -> int:
        model_pipeline = self.pipeline if pipeline is None else pipeline
        classes = np.asarray(getattr(model_pipeline, "classes_", []))
        if (
            classes.ndim != 1
            or len(classes) != probability_count
            or classes.dtype.kind not in "iuf"
            or not np.array_equal(np.sort(classes), np.asarray([0, 1]))
        ):
            raise ValueError("Risk-model pipeline has an incompatible binary class mapping.")
        return int(np.flatnonzero(classes == 1)[0])

    def predict_proba(self, machine_history: Dict[str, Any]) -> float:
        if not isinstance(machine_history, dict):
            raise ValueError("machine_history must be a dictionary of numeric monitoring values.")
        row = self._history_to_row(machine_history)

        if self.pipeline is None:
            if self.model_path.exists():
                self.load_model()
            else:
                self.train()

        frame = pd.DataFrame([row], columns=DEFAULT_FEATURES)
        probabilities = np.asarray(self.pipeline.predict_proba(frame), dtype=float)
        if (
            probabilities.ndim != 2
            or probabilities.shape[0] != 1
            or probabilities.shape[1] < 2
            or not np.isfinite(probabilities).all()
            or np.any((probabilities < 0) | (probabilities > 1))
            or not np.allclose(probabilities.sum(axis=1), 1.0, rtol=1e-6, atol=1e-8)
        ):
            raise ValueError("Risk-model pipeline returned invalid class probabilities.")
        positive_index = self._positive_class_index(probabilities.shape[1])
        positive_probabilities = probabilities[:, positive_index]
        adjusted = self._apply_temperature(positive_probabilities) if self.calibration_ready else positive_probabilities
        return float(np.clip(adjusted[0], 0.0, 1.0))

    def shap_values(self, machine_history: Dict[str, Any]) -> Dict[str, Any]:
        if shap is None:
            return {"status": "not_available", "reason": "shap dependency is not installed", "summary": []}

        if self.pipeline is None:
            if self.model_path.exists():
                self.load_model()
            else:
                self.train()

        try:
            row = pd.DataFrame([self._history_to_row(machine_history)], columns=DEFAULT_FEATURES)
            preprocessor = self.pipeline.named_steps["preprocess"]
            transformed = preprocessor.transform(row)
            model = self.pipeline.named_steps["model"]
            explainer = shap.Explainer(model, transformed)
            values = explainer(transformed)
            arr = values.values if hasattr(values, "values") else np.asarray(values)
            arr = np.asarray(arr)
            feature_names = preprocessor.get_feature_names_out()
            feature_count = len(feature_names)
            if arr.ndim == 3:
                if arr.shape[0] != 1:
                    raise ValueError("Expected SHAP output for one prediction row.")
                row_values = arr[0]
                if row_values.shape[0] == feature_count:
                    arr = row_values[:, 1] if row_values.shape[1] >= 2 else row_values[:, 0]
                elif row_values.shape[1] == feature_count:
                    arr = row_values[1] if row_values.shape[0] >= 2 else row_values[0]
                else:
                    raise ValueError("Unexpected SHAP feature and output axes.")
            elif arr.ndim == 2:
                if arr.shape == (1, feature_count):
                    arr = arr[0]
                elif arr.shape == (feature_count, 1):
                    arr = arr[:, 0]
                elif arr.shape[0] == feature_count and arr.shape[1] >= 2:
                    arr = arr[:, 1]
                elif arr.shape[1] == feature_count and arr.shape[0] >= 2:
                    arr = arr[1]
            if arr.ndim != 1 or len(arr) != feature_count or not np.isfinite(arr).all():
                raise ValueError("Unexpected SHAP array shape for summary generation.")
        except Exception as exc:
            return {
                "status": "fallback",
                "reason": f"SHAP summary generation failed: {type(exc).__name__}: {exc}",
                "summary": [],
            }

        summary = []
        for i, feature in enumerate(feature_names):
            value = float(np.abs(arr[i]))
            summary.append({"feature": feature, "importance": value})
        summary = sorted(summary, key=lambda item: item["importance"], reverse=True)[:5]
        return {"status": "ok", "summary": summary}

    def evaluate_calibration(self, X_val: pd.DataFrame, y_val: pd.Series) -> Dict[str, Any]:
        if self.pipeline is None:
            raise ValueError("A trained model is required before calibration evaluation.")
        if len(X_val) == 0 or len(X_val) != len(y_val):
            raise ValueError("Calibration evaluation requires non-empty features and matching labels.")
        raw_labels = np.asarray(y_val)
        if not np.isin(raw_labels, [0, 1]).all():
            raise ValueError("Calibration evaluation labels must be binary.")
        labels = raw_labels.astype(int)
        if np.unique(labels).size < 2:
            raise ValueError("Calibration evaluation requires binary labels containing both classes.")
        raw_probs = self.pipeline.predict_proba(X_val)[:, 1]
        raw_prob = np.clip(np.asarray(raw_probs, dtype=float), 1e-9, 1.0 - 1e-9)
        before = self._expected_calibration_error(raw_prob, labels)
        calibrated = self._apply_temperature(raw_prob)
        after = self._expected_calibration_error(calibrated, labels)
        return {
            "ece_before": float(before),
            "ece_after": float(after),
            "improvement": float(before - after),
            "temperature": float(self.temperature),
            "brier_before": float(np.mean((raw_prob - labels) ** 2)),
            "brier_after": float(np.mean((calibrated - labels) ** 2)),
        }

    @staticmethod
    def _expected_calibration_error(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
        if any(isinstance(value, (bool, np.bool_)) for value in np.asarray(probs, dtype=object).flat):
            raise ValueError("ECE probabilities cannot be boolean.")
        try:
            probs = np.asarray(probs, dtype=float)
            labels = np.asarray(labels, dtype=float)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("ECE inputs must contain finite numeric values.") from exc
        if probs.ndim != 1 or labels.ndim != 1 or len(probs) == 0 or len(probs) != len(labels):
            raise ValueError("ECE requires non-empty one-dimensional probabilities and labels of equal length.")
        if not np.isfinite(probs).all() or np.any((probs < 0) | (probs > 1)):
            raise ValueError("ECE probabilities must be finite values in [0, 1].")
        if not np.isin(labels, [0, 1]).all() or n_bins <= 0:
            raise ValueError("ECE labels must be binary and n_bins must be positive.")
        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
        ece = 0.0
        for idx in range(n_bins):
            lower = bin_edges[idx]
            upper = bin_edges[idx + 1]
            mask = (probs >= lower) & (probs < upper if idx < n_bins - 1 else probs <= upper)
            if not np.any(mask):
                continue
            avg_conf = float(probs[mask].mean())
            avg_acc = float(labels[mask].mean())
            ece += float(mask.mean()) * abs(avg_conf - avg_acc)
        return float(ece)


def risk(machine_history: Dict[str, Any]) -> Dict[str, Any]:
    global _DEFAULT_MODEL
    if _DEFAULT_MODEL is None:
        _DEFAULT_MODEL = RiskModel()
        if _DEFAULT_MODEL.model_path.exists():
            _DEFAULT_MODEL.load_model()
        else:
            _DEFAULT_MODEL.train()
    model = _DEFAULT_MODEL
    score = model.predict_proba(machine_history)
    explanation = model.shap_values(machine_history)
    risk_level = "high" if score >= 0.7 else "medium" if score >= 0.4 else "low"
    return {
        "risk_score": float(np.clip(score, 0.0, 1.0)),
        "risk_level": risk_level,
        "model": model._train_summary.get("model_backend", "loaded pipeline"),
        "dataset_source": model._train_summary.get("dataset_source", model.dataset_source),
        "calibration_status": "temperature_scaled_on_validation" if model.calibration_ready else "uncalibrated",
        "temperature": float(model.temperature),
        "explanation": explanation,
        "summary": "Failure risk estimated from machinery telemetry and maintenance context.",
    }


_DEFAULT_MODEL: Optional[RiskModel] = None
