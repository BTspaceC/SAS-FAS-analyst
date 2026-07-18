#!/usr/bin/env python3
import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


def default_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    base = Path(codex_home) if codex_home else Path.home() / ".codex"
    return base / "sas-fas-data" / "runs"


def safe_asset(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-.")
    if not cleaned:
        raise ValueError("asset must contain at least one safe character")
    return cleaned.upper()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", required=True)
    parser.add_argument("--asset-type", required=True, choices=["equity", "crypto", "hybrid"])
    parser.add_argument("--runs-root", type=Path)
    parser.add_argument("--question", default="")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    root = (args.runs_root or default_root()).expanduser().resolve()
    asset = safe_asset(args.asset)
    run_dir = root / asset / now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir.mkdir(parents=True, exist_ok=False)

    manifest = {
        "schema_version": "5.0",
        "asset": asset,
        "asset_type": args.asset_type,
        "asset_subtype": None,
        "question": args.question,
        "created_at": now.isoformat(),
        "as_of": None,
        "primary_horizon": "3-5 years",
        "secondary_horizon": "1-2 years",
        "status": "collecting_evidence",
        "data_completeness_score": 0,
        "private_data_retained": False,
        "decision": {
            "personalized_advice_requested": False,
            "investor_profile_complete": False,
        },
        "versions": {"sas_fas": "5.0", "calculator": "5.0", "truth_discipline": 1},
    }
    (run_dir / "00_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (run_dir / "01_evidence.json").write_text(
        json.dumps(
            {
                "critical_fields": [],
                "metrics": {},
                "metric_evidence": {},
                "evidence": [],
                "conflicts": [],
            },
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(run_dir)


if __name__ == "__main__":
    main()
