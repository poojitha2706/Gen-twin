"""Adapter: Render backend  ->  incident retrieval + decision policy  ->  back to the backend.

Loop: find detections that have no cause yet, look up similar synthetic incidents, run the
fusion policy, and POST {cause, cause_confidence, action} to /anomaly/{id}/cause.

Run from the rag-module folder:
    python adapter.py            # keep running, check every 5 seconds
    python adapter.py --once     # process what is pending, then exit

Keep the optional requirements (chromadb, sentence-transformers) uninstalled: this adapter uses
the lightweight TF-IDF retrieval path, which needs no model download.
"""
import argparse
import os
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from m2.policy import decide
from m2.rag import IncidentKnowledgeBase

load_dotenv()

BACKEND = os.getenv("BACKEND_BASE_URL", "https://gen-twin.onrender.com").rstrip("/")
ORG_ID = os.getenv("ORG_ID", "demo-org")
KB_CSV = Path(__file__).resolve().parent / "data" / "surface_incidents.csv"

TOP_K = 3                           # incidents retrieved per detection
RISK_WINDOW = timedelta(minutes=10)  # recent detections that count towards history risk
RISK_FULL_AT = 10                    # this many detections inside the window = risk 1.0
TIMEOUT = 90                         # the free Render server can take about a minute to wake up


def parse_ts(value):
    ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def history_risk(record, history):
    """Placeholder risk: share of the 10-detection limit used in the 10 minutes up to this detection.

    This is a transparent stand-in for the AI4I risk model, which needs machine telemetry
    (temperature, torque, rpm, tool wear) that our camera pipeline does not produce.
    """
    end = parse_ts(record["timestamp"])
    recent = [r for r in history if end - RISK_WINDOW < parse_ts(r["timestamp"]) <= end]
    return min(1.0, len(recent) / RISK_FULL_AT)


def analyse(kb, record, risk):
    defect = record["defect_class"]
    hits = kb.search(defect.replace("_", " "), org_id=ORG_ID, machine_id=None, top_k=TOP_K)
    hits = [h for h in hits if str(h.get("defect", "")).lower() == defect.lower()]

    if hits:
        cause, votes = Counter(h["root_cause"] for h in hits).most_common(1)[0]
        support = votes / TOP_K   # share of retrieved incidents naming this cause; not a probability
    else:
        cause, support = "not found", 0.0

    result = decide(float(record["confidence"]), risk, support, defect)
    action = "auto_logged" if result["decision"] == "auto_act" else "escalated"
    return cause, support, action, result["score"]


def call(method, path, **kwargs):
    resp = requests.request(method, BACKEND + path, timeout=TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp.json()


def process_once(kb, skipped):
    done = 0
    for machine in call("GET", "/machines"):
        mid = machine["machine_id"]
        history = call("GET", f"/machines/{mid}/history")
        pending = [r for r in history if r.get("cause") is None and r["id"] not in skipped]
        for record in reversed(pending):           # oldest first, so risk builds up in order
            risk = history_risk(record, history)
            cause, support, action, score = analyse(kb, record, risk)
            try:
                call("POST", f"/anomaly/{record['id']}/cause",
                     json={"cause": cause, "cause_confidence": round(support, 4), "action": action})
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code < 500:
                    skipped.add(record["id"])       # bad request: do not retry forever
                raise
            done += 1
            print(f"[{mid}] {record['defect_class']} ({record['confidence']:.2f}) risk {risk:.1f} "
                  f"-> {action} (score {score:.2f}); cause: {cause}")
    return done


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="process pending detections and exit")
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between checks")
    args = parser.parse_args()

    kb = IncidentKnowledgeBase()
    info = kb.ingest(kb.load_csv(str(KB_CSV)))
    print(f"Loaded {info['ingested']} synthetic incidents ({info['backend']}). Backend: {BACKEND}")

    skipped = set()
    while True:
        try:
            done = process_once(kb, skipped)
            if args.once:
                print(f"Done: {done} detection(s) processed.")
                return
        except requests.RequestException as e:
            print(f"Backend problem ({e}); will retry.")
            if args.once:
                raise SystemExit(1)
        except KeyboardInterrupt:
            print("Stopped.")
            return
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("Stopped.")
            return


if __name__ == "__main__":
    main()
