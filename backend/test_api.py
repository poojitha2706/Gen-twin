"""Automated test. Run with:  python test_api.py   (needs: pip install httpx)"""
import os
try:
    os.remove("test_gentwin.db")  # start each run with a fresh test database
except (FileNotFoundError, PermissionError):
    pass
os.environ["DATABASE_URL"] = "sqlite:///./test_gentwin.db"

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

r = client.post("/anomaly", json={"machine_id": "m1", "defect_class": "crack", "confidence": 0.91})
assert r.status_code == 200, r.text
aid = r.json()["id"]

assert client.get("/machines").json()[0]["status"] == "anomaly_detected"
assert len(client.get("/machines/m1/history").json()) == 1

with client.websocket_connect("/ws") as ws:
    r = client.post(f"/anomaly/{aid}/cause",
                    json={"cause": "thermal stress", "cause_confidence": 0.82, "action": "escalated"})
    assert r.status_code == 200 and r.json()["action"] == "escalated"
    assert ws.receive_json()["type"] == "cause_update"

assert client.post("/anomaly/nope/cause",
                   json={"cause": "x", "cause_confidence": 0.1, "action": "escalated"}).status_code == 404
assert client.post("/machines/m1/reset").json()["status"] == "normal"
print("ALL TESTS PASSED")
try:
    os.remove("test_gentwin.db")
except PermissionError:
    pass  # Windows keeps the file locked; harmless
