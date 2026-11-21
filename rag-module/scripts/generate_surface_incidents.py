"""Generate SYNTHETIC steel surface-defect incidents for the GenTwin Vision knowledge base.

Every record is invented for this prototype (synthetic=True); none comes from a real factory.
The causes and resolutions are plausible hot-rolling explanations written for the six NEU-DET
defect classes, so the retrieval step has relevant material for what the CV module detects.

Usage (from the rag-module folder):
    python scripts/generate_surface_incidents.py
"""
import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

COLUMNS = [
    "incident_id", "timestamp", "machine_id", "defect", "temperature_c", "vibration_mm_s",
    "shift", "root_cause", "resolution", "org_id", "synthetic", "source", "evidence",
]

# defect class -> [(root cause, resolution), ...]
KNOWLEDGE = {
    "crazing": [
        ("thermal stress from uneven cooling", "Balance the cooling spray headers and re-inspect the next three coils."),
        ("work roll surface fatigue", "Regrind or replace the work rolls and verify roll surface hardness."),
        ("excessive reduction in a single pass", "Spread the reduction over more passes and check mill load limits."),
        ("unstable finishing temperature", "Calibrate the pyrometers and stabilise the finishing temperature profile."),
        ("residual stress after coiling", "Review coiling temperature and tension, and slow the cooling rate."),
    ],
    "inclusion": [
        ("slag carryover during casting", "Improve slag control at the ladle and tundish, then sample the next heat."),
        ("refractory erosion in the tundish", "Inspect the tundish lining and replace eroded refractory."),
        ("insufficient steel cleanliness", "Extend ladle treatment and check the deoxidation practice."),
        ("mould powder entrapment", "Adjust mould level control and powder feed rate."),
        ("oxide formed during reoxidation", "Check argon shrouding between the ladle and the tundish."),
    ],
    "patches": [
        ("uneven descaling leaving oxide patches", "Inspect descaling nozzles and verify water pressure across the strip width."),
        ("inconsistent coolant spray coverage", "Clean blocked spray nozzles and re-check the coverage pattern."),
        ("roll surface contamination", "Clean the rolls and check for oil leakage near the roll chocks."),
        ("local temperature variation across the strip", "Check furnace burner balance and strip edge heating."),
        ("scale residue from the reheating furnace", "Review furnace atmosphere and dwell time, then re-descale."),
    ],
    "pitted_surface": [
        ("scale pressed into the strip at the stand", "Increase descaling efficiency before the first stand."),
        ("corrosion pits from moisture during storage", "Dry the coils before storage and improve warehouse ventilation."),
        ("worn descaling nozzles", "Replace worn nozzles and verify the spray angle."),
        ("pickling bath acid concentration too high", "Check pickling acid concentration and immersion time."),
        ("damaged work roll surface", "Replace the damaged roll and inspect neighbouring rolls."),
    ],
    "rolled-in_scale": [
        ("ineffective descaling before rolling", "Raise descaling water pressure and check nozzle alignment."),
        ("reheating furnace temperature too high", "Lower the furnace set point and shorten the soak time."),
        ("low descaling water pressure", "Inspect the high-pressure pump and filters, and restore pressure."),
        ("long delay between descaling and rolling", "Shorten the transfer time or add an intermediate descaler."),
        ("oxidising furnace atmosphere", "Adjust the air-fuel ratio to reduce scale formation."),
    ],
    "scratches": [
        ("foreign particles on guide rollers", "Clean the guide rollers and inspect the strip path for debris."),
        ("misaligned guides scraping the strip", "Realign the side guides and check clearances."),
        ("worn roller bearings causing strip drag", "Replace the worn bearings and confirm free roller rotation."),
        ("sharp burrs on a table roller", "Dress or replace the damaged table roller."),
        ("strip contact with the entry guide edge", "Adjust the entry guide height and strip centring."),
    ],
}

# relative frequency of the 1st..5th cause listed for each defect
CAUSE_WEIGHTS = [0.40, 0.25, 0.15, 0.12, 0.08]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/surface_incidents.csv")
    parser.add_argument("--per-class", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--machines", type=int, default=4, help="number of machines, named machine_01, machine_02, ...")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    machines = [f"machine_{i:02d}" for i in range(1, args.machines + 1)]
    start = datetime(2026, 1, 5, 6, 0, 0)

    rows = []
    for defect, options in KNOWLEDGE.items():
        for _ in range(args.per_class):
            # a few root causes dominate, as in real incident logs
            cause, resolution = rng.choices(options, weights=CAUSE_WEIGHTS, k=1)[0]
            machine = rng.choice(machines)
            shift = rng.choice("ABC")
            temperature = round(rng.uniform(55, 95), 1)
            vibration = round(rng.uniform(0.2, 3.0), 2)
            rows.append({
                "machine_id": machine, "defect": defect, "temperature_c": temperature,
                "vibration_mm_s": vibration, "shift": shift, "root_cause": cause, "resolution": resolution,
                "evidence": (f"{machine} {defect.replace('_', ' ')} during shift {shift}; "
                             f"temperature {temperature}C, vibration {vibration} mm/s; "
                             f"likely root cause: {cause}."),
            })

    rng.shuffle(rows)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for i, r in enumerate(rows, start=1):
            writer.writerow({
                "incident_id": f"SURF-{i:04d}",
                "timestamp": (start + timedelta(hours=7 * i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "org_id": "demo-org", "synthetic": "True", "source": "synthetic_surface_incident_generator",
                **r,
            })
    print(f"Wrote {len(rows)} synthetic incidents to {out}")


if __name__ == "__main__":
    main()
