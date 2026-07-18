#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, f"{path.name}: {exc}"


def has_path(value, dotted_path):
    current = value
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current or current[part] is None:
            return False
        current = current[part]
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--stage", choices=["evidence", "final"], required=True)
    args = parser.parse_args()
    root = args.run_dir.resolve()
    errors = []
    manifest, err = load_json(root / "00_manifest.json")
    if err:
        errors.append(err)
        manifest = {}
    evidence, err = load_json(root / "01_evidence.json")
    if err:
        errors.append(err)
        evidence = {}

    for key in ("schema_version", "asset", "asset_type", "status"):
        if manifest.get(key) in (None, ""):
            errors.append(f"manifest missing {key}")
    if manifest.get("asset_type") not in ("equity", "crypto", "hybrid"):
        errors.append("manifest asset_type must be equity, crypto, or hybrid")
    items = evidence.get("evidence")
    if not isinstance(items, list):
        errors.append("evidence must contain a list named evidence")
        items = []
    ids = set()
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"evidence[{i}] is not an object")
            continue
        for key in ("id", "claim", "as_of", "source_url", "source_tier", "confidence"):
            if item.get(key) in (None, ""):
                errors.append(f"evidence[{i}] missing {key}")
        if item.get("source_tier") not in (1, 2, 3, 4, 5):
            errors.append(f"evidence[{i}] source_tier must be 1-5")
        if item.get("confidence") not in ("high", "medium", "low"):
            errors.append(f"evidence[{i}] confidence must be high, medium, or low")
        if item.get("id") in ids:
            errors.append(f"duplicate evidence id {item.get('id')}")
        ids.add(item.get("id"))
    metrics = evidence.get("metrics", {})
    missing_critical = sorted(field for field in set(evidence.get("critical_fields", [])) if not has_path(metrics, field))
    if missing_critical and manifest.get("status") != "blocked":
        errors.append("missing critical fields without blocked status: " + ", ".join(missing_critical))
    if manifest.get("status") == "blocked" and not (root / "BLOCKER.md").exists():
        errors.append("blocked run requires BLOCKER.md")

    if args.stage == "final":
        required = ["02_quant.json", "03_bull.md", "04_bear.md", "05_market_structure.md", "06_judge.md", "07_FINAL_REPORT.md"]
        for name in required:
            path = root / name
            if not path.exists() or path.stat().st_size == 0:
                errors.append(f"missing or empty {name}")
        _, quant_error = load_json(root / "02_quant.json")
        if quant_error:
            errors.append(quant_error)
        if manifest.get("as_of") in (None, ""):
            errors.append("final manifest requires as_of")
        completeness = manifest.get("data_completeness_score")
        if not isinstance(completeness, (int, float)) or not 0 <= completeness <= 100:
            errors.append("data_completeness_score must be between 0 and 100")
        if manifest.get("status") != "complete":
            errors.append("final run status must be complete")

    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)
    print("VALID")


if __name__ == "__main__":
    main()
