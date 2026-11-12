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


def detect(image_path):
    """Return [(confidence, defect_class), ...] above the threshold, best first."""
    result = model(image_path, verbose=False)[0]
    found = [
        (float(b.conf), model.names[int(b.cls)])
        for b in result.boxes
        if float(b.conf) >= CONFIDENCE_THRESHOLD
    ]
    return sorted(found, reverse=True)


def send(machine_id, defect_class, confidence):
    payload = {
        "machine_id": machine_id,
        "defect_class": defect_class,
        "confidence": round(confidence, 4),
    }
    try:
        resp = requests.post(BACKEND_URL, json=payload, timeout=90)
        resp.raise_for_status()
        print(f"[{machine_id}] sent {payload} -> id {resp.json().get('id')}")
    except requests.exceptions.RequestException as e:
        print(f"[{machine_id}] failed to send: {e}")


def process(image_path, machine_id, send_all):
    found = detect(image_path)
    name = os.path.basename(image_path)
    if not found:
        print(f"[{machine_id}] no detections above threshold in {name}")
        return
    # Default: one report per image (the most confident detection).
    # --all restores one report per detected box.
    for confidence, defect_class in (found if send_all else found[:1]):
        send(machine_id, defect_class, confidence)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="image file or folder of images")
    parser.add_argument("--machine", default=DEFAULT_MACHINE)
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between images")
    parser.add_argument("--all", action="store_true", help="send every detection, not just the best per image")
    parser.add_argument("--loop", action="store_true", help="keep cycling through the images until stopped")
    args = parser.parse_args()

    if os.path.isdir(args.path):
        images = sorted(glob.glob(os.path.join(args.path, "*.jpg")))
    else:
        images = [args.path]

    if not images:
        raise SystemExit(f"No .jpg images found in {args.path}")

    while True:
        for img in images:
            print(f"Processing {os.path.basename(img)}")
            process(img, args.machine, args.all)
            time.sleep(args.interval)
        if not args.loop:
            break