#!/usr/bin/env python3
import argparse
from datetime import datetime
import json
import math
import re
import sys
from pathlib import Path


EVIDENCE_READY_STATUSES = {
    "evidence_ready",
    "quantified",
    "adversarial_analysis",
    "reconciling",
    "complete",
    "blocked",
}
FINAL_SECTIONS = (
    ("verdict", ("## 一句话裁决", "## One-line verdict")),
    ("ratings", ("## 四维评级", "## Four-dimensional rating")),
    ("facts", ("## 已确认的底层事实", "## Verified underlying facts")),
    ("unknowns", ("## 核心推断与未知", "## Inferences and unknowns")),
    ("bull", ("## Bull",)),
    ("bear", ("## Bear",)),
    ("valuation", ("## 估值与概率", "## Valuation and probabilities")),
    ("market", ("## 基准率与市场结构", "## Base rates and market structure")),
    ("premortem", ("## 事前验尸", "## Pre-mortem")),
    ("action", ("## 行动与仓位", "## Action and position")),
    ("change", ("## 什么会改变结论", "## What would change the conclusion")),
    ("blind_spots", ("## 数据盲区与冲突", "## Data gaps and conflicts")),
    ("sources", ("## 来源", "## Sources")),
)


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, f"{path.name}: {exc}"


def read_text(path):
    try:
        return path.read_text(encoding="utf-8"), None
    except Exception as exc:
        return "", f"{path.name}: {exc}"


def has_path(value, dotted_path):
    current = value
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current or current[part] is None:
            return False
        current = current[part]
    return True


def get_path(value, dotted_path):
    current = value
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def valid_iso(value):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def valid_source(value):
    return isinstance(value, str) and value.startswith(("https://", "http://", "user-artifact:", "derived:"))


def collect_null_paths(value, prefix=""):
    paths = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            paths.extend(collect_null_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(collect_null_paths(child, f"{prefix}[{index}]"))
    elif value is None:
        paths.append(prefix)
    return paths


def collect_nonfinite_paths(value, prefix=""):
    paths = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            paths.extend(collect_nonfinite_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(collect_nonfinite_paths(child, f"{prefix}[{index}]"))
    elif isinstance(value, float) and not math.isfinite(value):
        paths.append(prefix)
    return paths


def collect_note_paths(value, prefix=""):
    paths = set()
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(child, str) and child.strip():
                paths.add(path)
            else:
                paths.update(collect_note_paths(child, path))
    return paths


def evidence_references(text):
    return set(re.findall(r"\bEV-[A-Za-z0-9._-]+\b", text))


def validate_markdown(path, ids, errors, *, final=False):
    text, err = read_text(path)
    if err:
        errors.append(err)
        return
    if len(text.strip()) < 80:
        errors.append(f"{path.name} is too short to be a substantive report")
        return
    refs = evidence_references(text)
    allow_no_thesis = "no defensible thesis" in text.lower() or "无可辩护" in text
    if not refs and not allow_no_thesis:
        errors.append(f"{path.name} must cite at least one evidence ID")
    unknown_refs = sorted(refs - ids)
    if unknown_refs:
        errors.append(f"{path.name} cites unknown evidence IDs: " + ", ".join(unknown_refs))
    if final:
        for label, alternatives in FINAL_SECTIONS:
            if not any(section in text for section in alternatives):
                errors.append(f"{path.name} missing {label} section")
        if not re.search(r"\[F\]\[EV-[A-Za-z0-9._-]+\]", text):
            errors.append(f"{path.name} must include at least one [F][EV-ID] fact")
        for marker in ("[I]", "[H]", "[U]"):
            if marker not in text:
                errors.append(f"{path.name} missing {marker} reasoning marker")


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
    if manifest.get("schema_version") != "5.0":
        errors.append("manifest schema_version must be 5.0")
    if manifest.get("asset_type") not in ("equity", "crypto", "hybrid"):
        errors.append("manifest asset_type must be equity, crypto, or hybrid")
    if not valid_iso(manifest.get("created_at")):
        errors.append("manifest created_at must be an ISO-8601 date or timestamp")
    completeness = manifest.get("data_completeness_score")
    if not finite_number(completeness) or not 0 <= completeness <= 100:
        errors.append("data_completeness_score must be a finite number between 0 and 100")

    status = manifest.get("status")
    blocked = status == "blocked"
    if status not in EVIDENCE_READY_STATUSES:
        errors.append("manifest status is not evidence-ready")
    if not blocked and not valid_iso(manifest.get("as_of")):
        errors.append("non-blocked run requires a valid ISO-8601 manifest as_of")
    if not blocked and finite_number(completeness) and completeness <= 0:
        errors.append("non-blocked evidence-ready run requires data_completeness_score above zero")

    critical_fields = evidence.get("critical_fields")
    if not isinstance(critical_fields, list) or not critical_fields:
        errors.append("critical_fields must be a non-empty list")
        critical_fields = []
    elif any(not isinstance(field, str) or not field.strip() for field in critical_fields):
        errors.append("critical_fields must contain only non-empty strings")
        critical_fields = [field for field in critical_fields if isinstance(field, str) and field.strip()]
    if len(set(critical_fields)) != len(critical_fields):
        errors.append("critical_fields must not contain duplicates")

    metrics = evidence.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("metrics must be an object")
        metrics = {}
    items = evidence.get("evidence")
    if not isinstance(items, list):
        errors.append("evidence must contain a list named evidence")
        items = []
    if not blocked and not items:
        errors.append("non-blocked evidence gate requires at least one evidence item")

    ids = set()
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"evidence[{i}] is not an object")
            continue
        for key in ("id", "claim", "as_of", "source_url", "source_tier", "confidence"):
            if item.get(key) in (None, ""):
                errors.append(f"evidence[{i}] missing {key}")
        if not valid_iso(item.get("as_of")):
            errors.append(f"evidence[{i}] as_of must be ISO-8601")
        if not valid_source(item.get("source_url")):
            errors.append(f"evidence[{i}] source_url must be a direct URL, user-artifact:, or derived: identifier")
        if item.get("source_tier") not in (1, 2, 3, 4, 5):
            errors.append(f"evidence[{i}] source_tier must be 1-5")
        if item.get("confidence") not in ("high", "medium", "low"):
            errors.append(f"evidence[{i}] confidence must be high, medium, or low")
        item_id = item.get("id")
        if item_id in ids:
            errors.append(f"duplicate evidence id {item_id}")
        if not isinstance(item_id, str) or not re.fullmatch(r"EV-[A-Za-z0-9._-]+", item_id):
            errors.append(f"evidence[{i}] id must match EV-<identifier>")
        if isinstance(item_id, str) and item_id:
            ids.add(item_id)

    missing_critical = sorted(field for field in set(critical_fields) if not has_path(metrics, field))
    if missing_critical and not blocked:
        errors.append("missing critical fields without blocked status: " + ", ".join(missing_critical))
    for field in critical_fields:
        if has_path(metrics, field) and not finite_number(get_path(metrics, field)):
            errors.append(f"critical metric {field} must be a finite JSON number")

    metric_evidence = evidence.get("metric_evidence")
    if not blocked:
        if not isinstance(metric_evidence, dict):
            errors.append("non-blocked evidence gate requires metric_evidence mapping")
            metric_evidence = {}
        for field in critical_fields:
            refs = metric_evidence.get(field) if isinstance(metric_evidence, dict) else None
            if not isinstance(refs, list) or not refs:
                errors.append(f"critical metric {field} requires at least one evidence ID mapping")
                continue
            if any(not isinstance(ref, str) for ref in refs):
                errors.append(f"critical metric {field} evidence mappings must be strings")
                continue
            unknown = sorted(set(refs) - ids)
            if unknown:
                errors.append(f"critical metric {field} maps to unknown evidence IDs: " + ", ".join(unknown))

    if blocked:
        blocker = root / "BLOCKER.md"
        if not blocker.exists() or blocker.stat().st_size < 80:
            errors.append("blocked run requires a substantive BLOCKER.md")

    if args.stage == "final":
        if status != "complete":
            errors.append("final run status must be complete")
        if not valid_iso(manifest.get("as_of")):
            errors.append("final manifest requires a valid ISO-8601 as_of")

        quant, quant_error = load_json(root / "02_quant.json")
        if quant_error:
            errors.append(quant_error)
            quant = {}
        if quant.get("schema_version") != "5.0":
            errors.append("02_quant.json schema_version must be 5.0")
        if quant.get("asset_type") != manifest.get("asset_type"):
            errors.append("02_quant.json asset_type must match manifest")
        calculated = quant.get("calculated")
        notes = quant.get("notes")
        if not isinstance(calculated, dict) or not calculated:
            errors.append("02_quant.json calculated must be a non-empty object")
            calculated = {}
        if not isinstance(notes, dict):
            errors.append("02_quant.json notes must be an object")
            notes = {}
        asset_type = manifest.get("asset_type")
        if asset_type == "equity" and not set(calculated).intersection(
            {"bank_route", "qoe_cfo_to_net_income", "sloan_total_accruals", "roic", "beneish_components"}
        ):
            errors.append("02_quant.json lacks recognized equity-route metrics")
        elif asset_type == "crypto" and not set(calculated).intersection(
            {"unlock_pressure_30d", "daily_sell_pressure", "gross_annual_inflation", "float_to_max_supply"}
        ):
            errors.append("02_quant.json lacks recognized crypto-route metrics")
        elif asset_type == "hybrid" and not (
            isinstance(calculated.get("equity"), dict)
            and calculated.get("equity")
            and isinstance(calculated.get("crypto"), dict)
            and calculated.get("crypto")
        ):
            errors.append("02_quant.json hybrid route requires non-empty equity and crypto objects")
        nonfinite = collect_nonfinite_paths(calculated)
        if nonfinite:
            errors.append("02_quant.json contains non-finite values: " + ", ".join(nonfinite))
        uncovered_nulls = sorted(set(collect_null_paths(calculated)) - collect_note_paths(notes))
        if uncovered_nulls:
            errors.append("02_quant.json null metrics lack explicit notes: " + ", ".join(uncovered_nulls))

        judge, judge_error = load_json(root / "06_judge.json")
        if judge_error:
            errors.append(judge_error)
            judge = {}
        if judge.get("schema_version") != "5.0":
            errors.append("06_judge.json schema_version must be 5.0")
        if judge.get("asset_type") != manifest.get("asset_type"):
            errors.append("06_judge.json asset_type must match manifest")
        if judge.get("evidence_grade") not in ("A", "B", "C", "D", "F"):
            errors.append("06_judge.json evidence_grade must be A, B, C, D, or F")
        if judge.get("fundamental_state") not in ("strengthening", "stable", "weakening", "broken"):
            errors.append("06_judge.json fundamental_state is invalid")
        if judge.get("odds_state") not in ("exceptional", "favorable", "neutral", "unfavorable", "extremely unfavorable", "undetermined"):
            errors.append("06_judge.json odds_state is invalid")
        if not isinstance(judge.get("verdict_possible"), bool):
            errors.append("06_judge.json verdict_possible must be boolean")
        action_mode = judge.get("action_mode")
        if action_mode not in ("research_only", "illustrative", "personalized"):
            errors.append("06_judge.json action_mode is invalid")
        decision = manifest.get("decision", {})
        if action_mode == "personalized" and not (
            isinstance(decision, dict)
            and decision.get("personalized_advice_requested") is True
            and decision.get("investor_profile_complete") is True
        ):
            errors.append("personalized action requires requested advice and a complete investor profile")

        probabilities = judge.get("scenario_probabilities_pct")
        if judge.get("verdict_possible") is True:
            if not isinstance(probabilities, dict) or set(probabilities) != {"bear", "base", "bull"}:
                errors.append("decidable verdict requires bear/base/bull scenario probabilities")
            elif not all(finite_number(value) and 0 <= value <= 100 for value in probabilities.values()):
                errors.append("scenario probabilities must be finite numbers between 0 and 100")
            elif not math.isclose(sum(probabilities.values()), 100, abs_tol=0.01):
                errors.append("scenario probabilities must sum to 100")
        elif not isinstance(judge.get("unresolved_evidence"), list) or not judge.get("unresolved_evidence"):
            errors.append("indeterminate verdict requires non-empty unresolved_evidence")

        judge_ids = judge.get("evidence_ids")
        if not isinstance(judge_ids, list) or not judge_ids:
            errors.append("06_judge.json requires non-empty evidence_ids")
        elif any(not isinstance(ref, str) for ref in judge_ids):
            errors.append("06_judge.json evidence_ids must contain only strings")
        else:
            unknown = sorted(set(judge_ids) - ids)
            if unknown:
                errors.append("06_judge.json cites unknown evidence IDs: " + ", ".join(unknown))

        for name in ("03_bull.md", "04_bear.md", "05_market_structure.md", "06_judge.md"):
            validate_markdown(root / name, ids, errors)
        validate_markdown(root / "07_FINAL_REPORT.md", ids, errors, final=True)

    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)
    print("VALID")


if __name__ == "__main__":
    main()
