from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "GenTwin_M2_QA_Source.zip"

INCLUDE_PATHS = [
    ROOT / "m2",
    ROOT / "tests" / "__init__.py",
    ROOT / "tests" / "m2_scenario_catalog.py",
    ROOT / "tests" / "test_m2_core.py",
    ROOT / "tests" / "test_m2_exhaustive.py",
    ROOT / "tests" / "test_m2_local_runner.py",
    ROOT / "scripts" / "generate_incidents.py",
    ROOT / "scripts" / "run_m2_qa.py",
    ROOT / "scripts" / "run_m2_local.py",
    ROOT / "scripts" / "package_m2.py",
    ROOT / "requirements.txt",
    ROOT / "requirements-optional.txt",
    ROOT / ".env.example",
    ROOT / "README.md",
    ROOT / "qa" / "m2_test_inventory.json",
    ROOT / "qa" / "m2_test_results.json",
    ROOT / "qa" / "m2_test_summary.md",
    ROOT / "qa" / "m2_defect_fixes.json",
    ROOT / "qa" / "m2_defect_fixes.md",
    ROOT / "qa" / "coverage.json",
]
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    files = []
    for candidate in INCLUDE_PATHS:
        if candidate.is_dir():
            files.extend(
                path for path in candidate.rglob("*")
                if path.is_file() and not (set(path.parts) & EXCLUDED_PARTS)
                and path.suffix not in {".pyc", ".pyo"}
            )
        elif candidate.is_file():
            files.append(candidate)

    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            archive.write(path, path.relative_to(ROOT))
    print(f"{OUTPUT} ({OUTPUT.stat().st_size} bytes, {len(files)} files)")


if __name__ == "__main__":
    main()
