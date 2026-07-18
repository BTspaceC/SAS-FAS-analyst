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
STRICT_TRUTH_DISCIPLINE = 1
SCENARIO_WEIGHT_BASES = {"empirical", "model_based", "market_implied", "mixed", "judgmental"}
RECOMMENDED_ACTIONS = {
    "aggressive_accumulate",
    "staged_accumulate",
    "watch",
    "hold",
    "reduce",
    "exit",
    "avoid",
}
NEGATIVE_CLAIM_TYPES = {"evidence_of_impairment", "insufficient_evidence_for_positive_claim"}
TRIGGER_TYPES = {"asset_valuation", "fundamental", "portfolio_risk", "market_structure", "macro", "time_based"}
FINAL_SECTIONS = (
    ("verdict", ("## 一句话裁决", "## One-line verdict")),
    ("ratings", ("## 四维评级", "## Four-dimensional rating")),
    ("facts", ("## 已确认的底层事实", "## Verified underlying facts")),
    ("unknowns", ("## 核心推断与未知", "## Inferences and unknowns")),
    ("bull", ("## Bull",)),
    ("bear", ("## Bear",)),
    ("valuation", ("## 估值与概率", "## Valuation and probabilities", "## 估值、情景权重与稳健性", "## Valuation, scenario weights and robustness")),
    ("market", ("## 基准率与市场结构", "## Base rates and market structure")),
    ("premortem", ("## 事前验尸", "## Pre-mortem")),
    ("action", ("## 行动与仓位", "## Action and position")),
    ("change", ("## 什么会改变结论", "## What would change the conclusion")),
    ("blind_spots", ("## 数据盲区与冲突", "## Data gaps and conflicts")),
    ("sources", ("## 来源", "## Sources")),
)
STRICT_FINAL_SECTIONS = (
    ("policy_forecast_boundary", ("## 投资政策与预测边界", "## Policy and forecast boundary")),
    ("scenario_robustness", ("## 估值、情景权重与稳健性", "## Valuation, scenario weights and robustness")),
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


def valid_weights(value):
    return (
        isinstance(value, dict)
        and set(value) == {"bear", "base", "bull"}
        and all(finite_number(weight) and 0 <= weight <= 100 for weight in value.values())
        and math.isclose(sum(value.values()), 100, abs_tol=0.01)
    )


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


def validate_markdown(path, ids, errors, *, final=False, strict=False):
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
        if strict:
            for label, alternatives in STRICT_FINAL_SECTIONS:
                if not any(section in text for section in alternatives):
                    errors.append(f"{path.name} missing strict {label} section")
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
    versions = manifest.get("versions")
    strict = isinstance(versions, dict) and versions.get("truth_discipline") == STRICT_TRUTH_DISCIPLINE
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
    derived_items = []
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
        source_url = item.get("source_url")
        if strict and isinstance(source_url, str) and source_url.startswith("derived:"):
            derivation = item.get("derivation")
            if not isinstance(derivation, dict):
                errors.append(f"evidence[{i}] derived source requires a derivation object")
            else:
                formula = derivation.get("formula")
                input_ids = derivation.get("input_evidence_ids")
                if not isinstance(formula, str) or not formula.strip():
                    errors.append(f"evidence[{i}] derivation requires a non-empty formula")
                if not isinstance(input_ids, list) or not input_ids or any(not isinstance(ref, str) for ref in input_ids):
                    errors.append(f"evidence[{i}] derivation requires non-empty input_evidence_ids")
                else:
                    derived_items.append((i, item_id, input_ids))

    for i, item_id, input_ids in derived_items:
        unknown = sorted(set(input_ids) - ids)
        if unknown:
            errors.append(f"evidence[{i}] derivation maps to unknown evidence IDs: " + ", ".join(unknown))
        if item_id in input_ids:
            errors.append(f"evidence[{i}] derivation must not reference itself")

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

        if strict:
            if judge.get("policy_forecast_separated") is not True:
                errors.append("strict judge requires policy_forecast_separated true")
            recommended_action = judge.get("recommended_action")
            if recommended_action not in RECOMMENDED_ACTIONS:
                errors.append("strict judge recommended_action is invalid")

            if judge.get("verdict_possible") is True:
                weights = judge.get("scenario_weights_pct")
                if not valid_weights(weights):
                    errors.append("decidable strict verdict requires bear/base/bull scenario weights totaling 100")
                if "scenario_probabilities_pct" in judge:
                    errors.append("strict judge must use scenario_weights_pct instead of scenario_probabilities_pct")
                weight_basis = judge.get("scenario_weight_basis")
                if weight_basis not in SCENARIO_WEIGHT_BASES:
                    errors.append("strict judge scenario_weight_basis is invalid")
                if judge.get("scenario_weight_confidence") not in ("high", "medium", "low"):
                    errors.append("strict judge scenario_weight_confidence is invalid")
                weight_ids = judge.get("scenario_weight_evidence_ids")
                if not isinstance(weight_ids, list) or any(not isinstance(ref, str) for ref in weight_ids):
                    errors.append("strict judge scenario_weight_evidence_ids must be a list of strings")
                    weight_ids = []
                unknown = sorted(set(weight_ids) - ids)
                if unknown:
                    errors.append("strict judge scenario weight basis cites unknown evidence IDs: " + ", ".join(unknown))
                if weight_basis in {"empirical", "model_based", "market_implied", "mixed"} and not weight_ids:
                    errors.append("non-judgmental scenario weights require supporting evidence IDs")

                robustness = judge.get("robustness_test")
                if not isinstance(robustness, dict):
                    errors.append("strict judge requires a robustness_test object")
                else:
                    cases = robustness.get("cases")
                    actions = []
                    if not isinstance(cases, list) or len(cases) < 3:
                        errors.append("robustness_test requires at least three cases")
                    else:
                        for i, case in enumerate(cases):
                            if not isinstance(case, dict):
                                errors.append(f"robustness_test case[{i}] must be an object")
                                continue
                            if not isinstance(case.get("label"), str) or not case.get("label").strip():
                                errors.append(f"robustness_test case[{i}] requires a label")
                            if not valid_weights(case.get("weights_pct")):
                                errors.append(f"robustness_test case[{i}] weights must total 100")
                            action = case.get("recommended_action")
                            if action not in RECOMMENDED_ACTIONS:
                                errors.append(f"robustness_test case[{i}] recommended_action is invalid")
                            else:
                                actions.append(action)
                    invariant = robustness.get("action_invariant")
                    if not isinstance(invariant, bool):
                        errors.append("robustness_test action_invariant must be boolean")
                    elif actions and invariant != (len(set(actions)) == 1):
                        errors.append("robustness_test action_invariant contradicts case actions")
                    if not isinstance(robustness.get("conclusion"), str) or not robustness.get("conclusion").strip():
                        errors.append("robustness_test requires a substantive conclusion")
            elif not isinstance(judge.get("unresolved_evidence"), list) or not judge.get("unresolved_evidence"):
                errors.append("indeterminate verdict requires non-empty unresolved_evidence")

            negative_claims = judge.get("negative_claims")
            if not isinstance(negative_claims, list):
                errors.append("strict judge negative_claims must be a list")
                negative_claims = []
            for i, claim in enumerate(negative_claims):
                if not isinstance(claim, dict):
                    errors.append(f"negative_claims[{i}] must be an object")
                    continue
                if not isinstance(claim.get("claim"), str) or not claim.get("claim").strip():
                    errors.append(f"negative_claims[{i}] requires a claim")
                classification = claim.get("classification")
                if classification not in NEGATIVE_CLAIM_TYPES:
                    errors.append(f"negative_claims[{i}] classification is invalid")
                claim_ids = claim.get("evidence_ids")
                if not isinstance(claim_ids, list) or not claim_ids or any(not isinstance(ref, str) for ref in claim_ids):
                    errors.append(f"negative_claims[{i}] requires evidence_ids")
                    claim_ids = []
                unknown = sorted(set(claim_ids) - ids)
                if unknown:
                    errors.append(f"negative_claims[{i}] cites unknown evidence IDs: " + ", ".join(unknown))
                if not isinstance(claim.get("decision_effect"), str) or not claim.get("decision_effect").strip():
                    errors.append(f"negative_claims[{i}] requires decision_effect")
                if classification == "insufficient_evidence_for_positive_claim" and (
                    not isinstance(claim.get("expected_observable"), str) or not claim.get("expected_observable").strip()
                ):
                    errors.append(f"negative_claims[{i}] insufficient-support claim requires expected_observable")

            triggers = judge.get("action_triggers")
            if not isinstance(triggers, list):
                errors.append("strict judge action_triggers must be a list")
                triggers = []
            if action_mode == "personalized" and not triggers:
                errors.append("personalized strict action requires at least one action trigger")
            for i, trigger in enumerate(triggers):
                if not isinstance(trigger, dict):
                    errors.append(f"action_triggers[{i}] must be an object")
                    continue
                for key in ("id", "signal_asset", "target_asset", "zone", "tranche", "review_if_untriggered"):
                    if not isinstance(trigger.get(key), str) or not trigger.get(key).strip():
                        errors.append(f"action_triggers[{i}] requires {key}")
                max_weight = trigger.get("max_portfolio_weight_pct")
                if not finite_number(max_weight) or not 0 <= max_weight <= 100:
                    errors.append(f"action_triggers[{i}] max_portfolio_weight_pct must be between 0 and 100")
                trigger_type = trigger.get("signal_type")
                if trigger_type not in TRIGGER_TYPES:
                    errors.append(f"action_triggers[{i}] signal_type is invalid")
                signal_asset = trigger.get("signal_asset")
                target_asset = trigger.get("target_asset")
                if (
                    trigger_type == "asset_valuation"
                    and isinstance(signal_asset, str)
                    and isinstance(target_asset, str)
                    and signal_asset.casefold() != target_asset.casefold()
                ):
                    errors.append(f"action_triggers[{i}] asset valuation signal cannot target another asset")
                for key in ("confirmations", "vetoes"):
                    value = trigger.get(key)
                    if not isinstance(value, list) or not value or any(not isinstance(entry, str) or not entry.strip() for entry in value):
                        errors.append(f"action_triggers[{i}] requires non-empty {key}")
                trigger_ids = trigger.get("evidence_ids")
                if not isinstance(trigger_ids, list) or not trigger_ids or any(not isinstance(ref, str) for ref in trigger_ids):
                    errors.append(f"action_triggers[{i}] requires evidence_ids")
                    trigger_ids = []
                unknown = sorted(set(trigger_ids) - ids)
                if unknown:
                    errors.append(f"action_triggers[{i}] cites unknown evidence IDs: " + ", ".join(unknown))
        else:
            probabilities = judge.get("scenario_probabilities_pct")
            if judge.get("verdict_possible") is True:
                if not valid_weights(probabilities):
                    errors.append("decidable verdict requires bear/base/bull scenario probabilities totaling 100")
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
        final_path = root / "07_FINAL_REPORT.md"
        validate_markdown(final_path, ids, errors, final=True, strict=strict)
        final_text, final_error = read_text(final_path)
        if strict and judge.get("scenario_weight_basis") == "judgmental":
            if not final_error and not (
                "主观情景权重" in final_text or "judgmental scenario weights" in final_text.lower()
            ):
                errors.append("judgmental scenario weights must be labeled explicitly in 07_FINAL_REPORT.md")
        if strict and action_mode == "personalized" and not final_error:
            for trigger in judge.get("action_triggers", []):
                trigger_id = trigger.get("id") if isinstance(trigger, dict) else None
                if isinstance(trigger_id, str) and trigger_id and trigger_id not in final_text:
                    errors.append(f"personalized action trigger {trigger_id} must appear in 07_FINAL_REPORT.md")

    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)
    print("VALID")


if __name__ == "__main__":
    main()
