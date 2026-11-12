from __future__ import annotations

import argparse
from pathlib import Path

from m2.rag import IncidentKnowledgeBase


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic incident records for the M2 knowledge base.")
    parser.add_argument("--output", default="data/synthetic_incidents.csv")
    parser.add_argument("--count", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    kb = IncidentKnowledgeBase()
    records = kb.build_incident_documents(count=args.count, output_path=str(path), seed=args.seed)
    print(f"Created {len(records)} synthetic incident records at {path}")


if __name__ == "__main__":
    main()
