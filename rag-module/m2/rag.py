from __future__ import annotations

import csv
import datetime as dt
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

try:
    import chromadb
except Exception:  # pragma: no cover
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:  # pragma: no cover
    TfidfVectorizer = None
    cosine_similarity = None


REQUIRED_INCIDENT_FIELDS = {
    "incident_id",
    "timestamp",
    "machine_id",
    "defect",
    "temperature_c",
    "vibration_mm_s",
    "shift",
    "root_cause",
    "resolution",
    "org_id",
    "synthetic",
    "source",
    "evidence",
}
MIN_RELEVANCE = 0.05


class IncidentKnowledgeBase:
    def __init__(self, persistent_dir: Optional[str] = None, data_dir: Optional[str] = None):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.data_dir = Path(data_dir) if data_dir else self.base_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        configured_persistent_dir = os.getenv("CHROMA_PERSIST_DIRECTORY")
        self.persistent_dir = Path(persistent_dir or configured_persistent_dir) if (persistent_dir or configured_persistent_dir) else self.data_dir / "chroma"
        self.model_name = os.getenv("MODEL_NAME", "all-MiniLM-L6-v2")
        self.model = None
        self.collection = None
        self._ready = False
        self._model_attempted = False
        self.embedding_error = None
        self.vector_store_error = None
        self._embedding_cache = {}
        self._ingested_records: Dict[tuple[str, str], Dict[str, Any]] = {}
        self._load_collection()

    def _load_model(self):
        if self._model_attempted:
            return
        self._model_attempted = True
        if SentenceTransformer is None:
            self.embedding_error = "sentence-transformers dependency is not installed"
            return
        try:
            self.model = SentenceTransformer(self.model_name)
        except Exception as exc:  # pragma: no cover
            self.model = None
            self.embedding_error = f"{type(exc).__name__}: {exc}"

    def _load_collection(self):
        if chromadb is None:
            self.vector_store_error = "chromadb dependency is not installed"
            return
        try:
            client = chromadb.PersistentClient(path=str(self.persistent_dir))
            self.collection = client.get_or_create_collection(name="synthetic_incidents")
            self._ready = True
        except Exception as exc:  # pragma: no cover
            self.collection = None
            self.vector_store_error = f"{type(exc).__name__}: {exc}"

    @staticmethod
    def _coerce_record(record: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(record, dict):
            raise ValueError("Each incident record must be a dictionary.")
        missing = sorted(REQUIRED_INCIDENT_FIELDS - set(record.keys()))
        if missing:
            raise ValueError(f"Missing incident fields: {missing}")
        normalized = dict(record)
        normalized["incident_id"] = str(record["incident_id"]).strip()
        normalized["machine_id"] = str(record["machine_id"]).strip().upper()
        normalized["org_id"] = str(record["org_id"]).strip()
        normalized["defect"] = str(record["defect"]).strip().lower()
        for name in ("incident_id", "machine_id", "org_id", "defect", "root_cause", "resolution", "source", "evidence", "shift"):
            if not str(normalized.get(name, "")).strip():
                raise ValueError(f"Incident field '{name}' cannot be empty.")
        try:
            timestamp = dt.datetime.fromisoformat(str(record["timestamp"]).replace("Z", "+00:00"))
            if "T" not in str(record["timestamp"]):
                raise ValueError("Incident timestamp must include a time.")
            if isinstance(record["temperature_c"], bool) or isinstance(record["vibration_mm_s"], bool):
                raise ValueError("Incident measurements cannot be boolean.")
            temperature = float(record["temperature_c"])
            vibration = float(record["vibration_mm_s"])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Incident timestamp and measurements must be valid.") from exc
        if not math.isfinite(temperature) or not math.isfinite(vibration):
            raise ValueError("Incident measurements must be finite.")
        synthetic = record["synthetic"]
        if isinstance(synthetic, str):
            if synthetic.strip().lower() not in {"true", "false"}:
                raise ValueError("Incident 'synthetic' field must be boolean.")
            synthetic = synthetic.strip().lower() == "true"
        if not isinstance(synthetic, bool):
            raise ValueError("Incident 'synthetic' field must be boolean.")
        normalized["timestamp"] = timestamp.isoformat()
        normalized["synthetic"] = synthetic
        normalized["temperature_c"] = temperature
        normalized["vibration_mm_s"] = vibration
        return normalized

    def build_incident_documents(
        self,
        count: int = 300,
        output_path: Optional[str] = None,
        seed: int = 42,
    ) -> List[Dict[str, Any]]:
        if count <= 0:
            raise ValueError("Incident count must be positive.")
        rng = np.random.default_rng(seed)
        machines = [f"M{n:02d}" for n in range(1, 13)]
        defects = ["overheating", "vibration", "misalignment", "bearing wear", "electrical fault", "cooling failure", "sensor drift", "blocked filter"]
        shifts = ["A", "B", "C"]
        root_causes = {
            "overheating": ["cooling loop fouled", "ambient heat surge", "insufficient lubrication"],
            "vibration": ["bearing wear", "rotor imbalance", "loose mounting"],
            "misalignment": ["coupling misalignment", "chassis shift", "belt tension drift"],
            "bearing wear": ["lack of scheduled maintenance", "contamination ingress", "incorrect preload"],
            "electrical fault": ["loose terminal", "voltage instability", "control board issue"],
            "cooling failure": ["fan degradation", "pump cavitation", "blocked filter"],
            "sensor drift": ["calibration drift", "thermal drift", "signal degradation"],
            "blocked filter": ["dust accumulation", "poor housekeeping", "filter missed during change"],
        }
        records: List[Dict[str, Any]] = []
        for i in range(1, count + 1):
            defect = defects[i % len(defects)]
            machine = machines[i % len(machines)]
            temp = 68 + rng.normal(0, 12)
            vibration = 0.6 + rng.normal(0, 0.7)
            shift = shifts[i % len(shifts)]
            root = root_causes[defect][i % len(root_causes[defect])]
            resolution = f"Replace worn component and inspect {root}; confirm thermal and vibration return to baseline."
            record = {
                "incident_id": f"SYN-{i:04d}",
                "timestamp": f"2024-01-{(i % 28) + 1:02d}T{(i * 3) % 24:02d}:00:00Z",
                "machine_id": machine,
                "defect": defect,
                "temperature_c": round(float(temp), 2),
                "vibration_mm_s": round(float(vibration), 2),
                "shift": shift,
                "root_cause": root,
                "resolution": resolution,
                "org_id": "demo-org",
                "synthetic": True,
                "source": "synthetic_incident_generator",
                "evidence": f"{machine} {defect} during shift {shift}; temperature {temp:.1f}C, vibration {vibration:.2f} mm/s; likely root cause: {root}.",
            }
            records.append(self._coerce_record(record))

        output = Path(output_path) if output_path else self.data_dir / "synthetic_incidents.csv"
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=sorted(REQUIRED_INCIDENT_FIELDS))
            writer.writeheader()
            writer.writerows(records)
        return records

    def load_csv(self, csv_path: Optional[str] = None) -> List[Dict[str, Any]]:
        path = Path(csv_path) if csv_path else self.data_dir / "synthetic_incidents.csv"
        if not path.exists():
            return self.build_incident_documents(output_path=str(path))
        df = pd.read_csv(path)
        records = []
        seen_ids = set()
        for row_number, raw in enumerate(df.to_dict(orient="records"), start=2):
            try:
                normalized = self._coerce_record(raw)
            except ValueError as exc:
                raise ValueError(f"Invalid incident record at CSV row {row_number}: {exc}") from exc
            record_key = (normalized["org_id"], normalized["incident_id"])
            if record_key not in seen_ids:
                records.append(normalized)
                seen_ids.add(record_key)
        return records

    def ingest(self, records: Optional[List[Dict[str, Any]]] = None):
        if records is None:
            records = self.load_csv()
        if self.collection is not None and not self._model_attempted:
            self._load_model()
        seen = set()
        deduplicated = []
        for record in records:
            item = self._coerce_record(record)
            record_key = (item["org_id"], item["incident_id"])
            if record_key in seen:
                continue
            seen.add(record_key)
            deduplicated.append(item)
        if self.collection is not None and self.model is not None:
            ids = [f"{record['org_id']}:{record['incident_id']}" for record in deduplicated]
            docs = [record.get("evidence", "") for record in deduplicated]
            embeddings = self.model.encode(docs).tolist()
            metadatas = [
                {
                    "org_id": record["org_id"],
                    "machine_id": record["machine_id"],
                    "defect": record["defect"],
                    "root_cause": record["root_cause"],
                    "synthetic": record["synthetic"],
                    "incident_id": record["incident_id"],
                }
                for record in deduplicated
            ]
            if hasattr(self.collection, "upsert"):
                self.collection.upsert(ids=ids, embeddings=embeddings, documents=docs, metadatas=metadatas)
            else:
                existing = set()
                if hasattr(self.collection, "get"):
                    stored = self.collection.get(ids=ids)
                    if not isinstance(stored, dict) or not isinstance(stored.get("ids"), list):
                        raise RuntimeError("Persistent incident store returned invalid IDs during ingestion.")
                    existing = set(stored["ids"])
                new_rows = [
                    index for index, record_id in enumerate(ids)
                    if record_id not in existing
                ]
                if new_rows:
                    self.collection.add(
                        ids=[ids[index] for index in new_rows],
                        embeddings=[embeddings[index] for index in new_rows],
                        documents=[docs[index] for index in new_rows],
                        metadatas=[metadatas[index] for index in new_rows],
                    )
        for item in deduplicated:
            self._ingested_records[(item["org_id"], item["incident_id"])] = item
        return {"ingested": len(deduplicated), "backend": "local-memory" if self.collection is None or self.model is None else "chromadb"}

    def search(self, query: str, org_id: str = "demo-org", machine_id: Optional[str] = None, top_k: int = 3) -> List[Dict[str, Any]]:
        if not isinstance(query, str) or not query.strip():
            return []
        if len(query) > 8192:
            raise ValueError("RAG query exceeds the 8192-character limit.")
        if isinstance(top_k, bool) or not isinstance(top_k, int):
            raise ValueError("top_k must be an integer.")
        if top_k < 0:
            raise ValueError("top_k cannot be negative.")
        if top_k == 0:
            return []
        if not str(org_id).strip():
            return []
        if machine_id is not None and not isinstance(machine_id, str):
            raise ValueError("machine_id must be a string when provided.")

        if self.collection is not None and not self._model_attempted:
            self._load_model()
        if self.collection is not None and self.model is not None:
            if hasattr(self.collection, "count") and self.collection.count() == 0:
                records_for_ingest = self.load_csv()
                if records_for_ingest:
                    self.ingest(records_for_ingest)
            try:
                where = {"org_id": str(org_id).strip()}
                if machine_id:
                    where["machine_id"] = str(machine_id).strip().upper()
                query_embedding = self.model.encode([query])[0].tolist()
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    where=where,
                    include=["documents", "metadatas", "distances"],
                )
            except Exception as exc:
                raise RuntimeError(f"Persistent incident retrieval failed: {type(exc).__name__}: {exc}") from exc
            if not isinstance(results, dict):
                raise RuntimeError("Persistent incident retrieval returned an invalid response.")
            result_arrays = []
            for field in ("ids", "documents", "metadatas", "distances"):
                value = results.get(field)
                if not isinstance(value, list) or not value or not isinstance(value[0], list):
                    raise RuntimeError(f"Persistent incident retrieval returned invalid {field}.")
                result_arrays.append(value[0])
            ids, documents, metadatas, distances = result_arrays
            if not (len(ids) == len(documents) == len(metadatas) == len(distances)):
                raise RuntimeError("Persistent incident retrieval returned inconsistent result lengths.")
            hits = []
            for incident_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
                if not isinstance(metadata, dict) or not isinstance(document, str) or isinstance(distance, bool):
                    raise RuntimeError("Persistent incident retrieval returned malformed evidence.")
                try:
                    distance = float(distance)
                except (TypeError, ValueError, OverflowError) as exc:
                    raise RuntimeError("Persistent incident retrieval returned an invalid distance.") from exc
                if not math.isfinite(distance):
                    raise RuntimeError("Persistent incident retrieval returned a non-finite distance.")
                if str(metadata.get("org_id", "")) != str(org_id).strip():
                    continue
                if machine_id and str(metadata.get("machine_id", "")).upper() != str(machine_id).strip().upper():
                    continue
                relevance = max(-1.0, min(1.0, 1.0 - float(distance)))
                if relevance < MIN_RELEVANCE:
                    continue
                hits.append({
                    "incident_id": metadata.get("incident_id", incident_id),
                    "machine_id": metadata.get("machine_id"),
                    "score": relevance,
                    "score_kind": "cosine_similarity_not_calibrated_probability",
                    "root_cause": metadata.get("root_cause"),
                    "defect": metadata.get("defect"),
                    "synthetic": bool(metadata.get("synthetic", True)),
                    "evidence": document,
                    "org_id": metadata.get("org_id"),
                })
            return hits

        records = self.load_csv()
        records_by_key = {
            (str(record.get("org_id", "demo-org")).strip(), str(record["incident_id"])): record
            for record in records
        }
        records_by_key.update(self._ingested_records)
        records = list(records_by_key.values())
        filtered = [record for record in records if str(record.get("org_id", "demo-org")).strip() == str(org_id).strip()]
        if machine_id:
            filtered = [record for record in filtered if str(record.get("machine_id")).strip() == str(machine_id).strip().upper()]
        if not filtered:
            return []

        if self.model is not None and cosine_similarity is not None:
            cache_key = (
                str(self.data_dir / "synthetic_incidents.csv"),
                tuple((record["incident_id"], record["evidence"]) for record in filtered),
            )
            vectors = self._embedding_cache.get(cache_key)
            if vectors is None:
                documents = [record.get("evidence", "") for record in filtered]
                vectors = self.model.encode(documents)
                self._embedding_cache = {cache_key: vectors}
            query_embedding = self.model.encode([query])[0]
            similarities = cosine_similarity([query_embedding], vectors)[0]
        elif TfidfVectorizer is not None and cosine_similarity is not None:
            vectorizer = TfidfVectorizer(stop_words="english")
            try:
                matrix = vectorizer.fit_transform([query] + [record.get("evidence", "") for record in filtered])
            except ValueError as exc:
                if "empty vocabulary" in str(exc).lower():
                    return []
                raise
            similarities = cosine_similarity(matrix[0:1], matrix[1:])[0]
        else:
            return []
        ranked = sorted(zip(filtered, similarities), key=lambda item: item[1], reverse=True)[:top_k]
        return [
            {
                "incident_id": rec["incident_id"],
                "machine_id": rec["machine_id"],
                "score": float(sim),
                "score_kind": "cosine_similarity_not_calibrated_probability",
                "root_cause": rec.get("root_cause"),
                "defect": rec.get("defect"),
                "synthetic": bool(rec.get("synthetic", True)),
                "evidence": rec.get("evidence"),
                "org_id": rec.get("org_id", org_id),
            }
            for rec, sim in ranked
            if float(sim) >= MIN_RELEVANCE
        ]


_DEFAULT_KB: Optional[IncidentKnowledgeBase] = None


def search_similar_incidents(query: str, org_id: str = "demo-org", machine_id: Optional[str] = None, top_k: int = 3) -> List[Dict[str, Any]]:
    global _DEFAULT_KB
    if _DEFAULT_KB is None:
        _DEFAULT_KB = IncidentKnowledgeBase()
    return _DEFAULT_KB.search(query=query, org_id=org_id, machine_id=machine_id, top_k=top_k)
