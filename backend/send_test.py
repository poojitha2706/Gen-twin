"""Fake CV module: sends random detections to the backend so others can test."""
import random
import time
import requests

URL = "http://localhost:8000"
machines = ["machine_01", "machine_02", "machine_03"]
defects = ["crack", "scratch", "pitting", "inclusion"]

for _ in range(5):
    body = {
        "machine_id": random.choice(machines),
        "defect_class": random.choice(defects),
        "confidence": round(random.uniform(0.5, 0.99), 2),
    }
    r = requests.post(f"{URL}/anomaly", json=body)
    print(r.status_code, r.json()["id"], body)
    time.sleep(1)
