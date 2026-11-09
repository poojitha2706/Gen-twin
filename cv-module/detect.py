import argparse
import glob
import os
import time

import requests
from dotenv import load_dotenv
from ultralytics import YOLO

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL")
DEFAULT_MACHINE = os.getenv("MACHINE_ID", "machine_01")
CONFIDENCE_THRESHOLD = 0.4

model = YOLO("models/best.pt")


def run_detection(image_path, machine_id):
    results = model(image_path, verbose=False)
    sent = 0
    for r in results:
        for box in r.boxes:
            confidence = float(box.conf)
            if confidence < CONFIDENCE_THRESHOLD:
                continue
            payload = {
                "machine_id": machine_id,
                "defect_class": model.names[int(box.cls)],
                "confidence": round(confidence, 4),
            }
            try:
                resp = requests.post(BACKEND_URL, json=payload, timeout=90)
                resp.raise_for_status()
                print(f"[{machine_id}] sent {payload} -> id {resp.json().get('id')}")
                sent += 1
            except requests.exceptions.RequestException as e:
                print(f"[{machine_id}] failed to send: {e}")
    if sent == 0:
        print(f"[{machine_id}] no detections above threshold in {os.path.basename(image_path)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="image file or folder of images")
    parser.add_argument("--machine", default=DEFAULT_MACHINE)
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between images")
    args = parser.parse_args()

    if os.path.isdir(args.path):
        images = sorted(glob.glob(os.path.join(args.path, "*.jpg")))
    else:
        images = [args.path]

    for img in images:
        print(f"Processing {os.path.basename(img)}")
        run_detection(img, args.machine)
        time.sleep(args.interval)