#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path


def div(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def avg(a, b):
    if a is None or b is None:
        return None
    return (a + b) / 2


def need(m, *keys):
    return [k for k in keys if m.get(k) is None]


def alias_percentage_points(value):
    if value is None:
        return None
    return value * 100 if abs(value) <= 1 else value


def bank_percentage_points(metrics, pct_key, alias_key):
    """`*_pct` inputs are percentage points; legacy aliases may be decimals."""
    if metrics.get(pct_key) is not None:
        return metrics[pct_key]
    return alias_percentage_points(metrics.get(alias_key))


def add_null_notes(value, notes, prefix=""):
    """Ensure every emitted null has a deterministic, addressable explanation."""
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            add_null_notes(child, notes, path)
    elif value is None and prefix not in notes:
        notes[prefix] = "not calculated: one or more required inputs are missing or inapplicable for this asset route"


def equity_metrics(m):
    out, notes = {}, {}
    if m.get("company_class") == "bank":
        price = m.get("share_price", m.get("price"))
        shares = m.get("shares_outstanding", m.get("shares_or_supply"))
        bvps = m.get("book_value_per_share")
        if bvps is None:
            bvps = div(m.get("book_value_equity"), shares)
        cet1_pct = bank_percentage_points(m, "cet1_ratio_pct", "cet1_ratio")
        requirement_pct = bank_percentage_points(m, "binding_cet1_requirement_pct", "binding_cet1_requirement")
        shortfall = None
        if m.get("htm_book_value") is not None and m.get("htm_fair_value") is not None:
            shortfall = m["htm_book_value"] - m["htm_fair_value"]
        out["bank_route"] = {
            "price_to_tangible_book": div(price, m.get("tangible_book_value_per_share")),
            "price_to_book": div(price, bvps),
            "reported_ltm_pe": div(price, m.get("reported_ltm_eps")),
            "core_ltm_pe": div(price, m.get("core_ltm_eps")),
            "cet1_buffer_over_binding_requirement_bps": None if cet1_pct is None or requirement_pct is None else (cet1_pct - requirement_pct) * 100,
            "noninterest_bearing_deposits_pct": None if div(m.get("noninterest_bearing_deposits"), m.get("total_deposits")) is None else div(m.get("noninterest_bearing_deposits"), m.get("total_deposits")) * 100,
            "total_acl_to_loans_pct": None if div(m.get("allowance_credit_losses"), m.get("total_loans")) is None else div(m.get("allowance_credit_losses"), m.get("total_loans")) * 100,
            "loan_loss_allowance_to_loans_pct": None if div(m.get("loan_loss_allowance"), m.get("total_loans")) is None else div(m.get("loan_loss_allowance"), m.get("total_loans")) * 100,
            "htm_unrealized_shortfall": shortfall,
            "htm_shortfall_to_tce_pct": None if div(shortfall, m.get("tangible_common_equity")) is None else div(shortfall, m.get("tangible_common_equity")) * 100,
        }
        notes["bank_route"] = "Bank-specific metrics; ordinary industrial QoE, ROIC, Beneish and Altman are intentionally skipped."
        add_null_notes(out, notes)
        return out, notes
    ni, cfo = m.get("net_income"), m.get("cash_from_operations")
    out["qoe_cfo_to_net_income"] = div(cfo, ni)
    if ni is not None and abs(ni) < 1e-9:
        notes["qoe_cfo_to_net_income"] = "near-zero net income makes QoE unstable"

    aa = avg(m.get("total_assets_current"), m.get("total_assets_prior"))
    out["sloan_total_accruals"] = div(None if ni is None or cfo is None else ni - cfo, aa)

    nopat = m.get("nopat_current")
    if nopat is None and m.get("ebit_current") is not None and m.get("tax_rate") is not None:
        nopat = m["ebit_current"] * (1 - m["tax_rate"])
    aic = avg(m.get("invested_capital_current"), m.get("invested_capital_prior"))
    out["roic"] = div(nopat, aic)
    out["roiic"] = div(
        None if nopat is None or m.get("nopat_prior") is None else nopat - m["nopat_prior"],
        None if m.get("invested_capital_current") is None or m.get("invested_capital_prior") is None else m["invested_capital_current"] - m["invested_capital_prior"],
    )

    rt, rp = m.get("revenue_current"), m.get("revenue_prior")
    ct, cp = m.get("cogs_current"), m.get("cogs_prior")
    dsri = div(div(m.get("receivables_current"), rt), div(m.get("receivables_prior"), rp))
    gmi = div(div(None if rp is None or cp is None else rp - cp, rp), div(None if rt is None or ct is None else rt - ct, rt))
    aqi_t = None if need(m, "current_assets_current", "ppe_current", "total_assets_current") else 1 - (m["current_assets_current"] + m["ppe_current"]) / m["total_assets_current"]
    aqi_p = None if need(m, "current_assets_prior", "ppe_prior", "total_assets_prior") else 1 - (m["current_assets_prior"] + m["ppe_prior"]) / m["total_assets_prior"]
    aqi = div(aqi_t, aqi_p)
    sgi = div(rt, rp)
    depi = div(div(m.get("depreciation_prior"), None if m.get("depreciation_prior") is None or m.get("ppe_prior") is None else m["depreciation_prior"] + m["ppe_prior"]), div(m.get("depreciation_current"), None if m.get("depreciation_current") is None or m.get("ppe_current") is None else m["depreciation_current"] + m["ppe_current"]))
    sgai = div(div(m.get("sga_current"), rt), div(m.get("sga_prior"), rp))
    lev_t = div(None if m.get("current_liabilities_current") is None or m.get("long_term_debt_current") is None else m["current_liabilities_current"] + m["long_term_debt_current"], m.get("total_assets_current"))
    lev_p = div(None if m.get("current_liabilities_prior") is None or m.get("long_term_debt_prior") is None else m["current_liabilities_prior"] + m["long_term_debt_prior"], m.get("total_assets_prior"))
    lvgi = div(lev_t, lev_p)
    continuing_income = m.get("income_from_continuing_operations")
    tata = div(
        None if continuing_income is None or cfo is None else continuing_income - cfo,
        m.get("total_assets_current"),
    )
    beneish_parts = {"dsri": dsri, "gmi": gmi, "aqi": aqi, "sgi": sgi, "depi": depi, "sgai": sgai, "lvgi": lvgi, "tata": tata}
    out["beneish_components"] = beneish_parts
    if all(v is not None and math.isfinite(v) for v in beneish_parts.values()):
        out["beneish_m_score"] = -4.84 + .92*dsri + .528*gmi + .404*aqi + .892*sgi + .115*depi - .172*sgai - .327*lvgi + 4.679*tata
    else:
        out["beneish_m_score"] = None
        notes["beneish_m_score"] = "requires all eight valid components"
    if tata is None:
        notes["beneish_components.tata"] = (
            "requires income_from_continuing_operations, cash_from_operations, and total_assets_current"
        )

    cls = m.get("company_class")
    x1 = div(m.get("working_capital"), m.get("total_assets_current"))
    x2 = div(m.get("retained_earnings"), m.get("total_assets_current"))
    x3 = div(m.get("ebit"), m.get("total_assets_current"))
    x5 = div(rt, m.get("total_assets_current"))
    if cls == "public_manufacturing":
        x4 = div(m.get("market_value_equity"), m.get("total_liabilities"))
        out["altman_z"] = None if any(v is None for v in (x1,x2,x3,x4,x5)) else 1.2*x1 + 1.4*x2 + 3.3*x3 + .6*x4 + x5
    elif cls == "private_manufacturing":
        x4 = div(m.get("book_value_equity"), m.get("total_liabilities"))
        out["altman_z_prime"] = None if any(v is None for v in (x1,x2,x3,x4,x5)) else .717*x1 + .847*x2 + 3.107*x3 + .42*x4 + .998*x5
    elif cls == "non_manufacturing":
        x4 = div(m.get("book_value_equity"), m.get("total_liabilities"))
        out["altman_z_double_prime"] = None if any(v is None for v in (x1,x2,x3,x4)) else 6.56*x1 + 3.26*x2 + 6.72*x3 + 1.05*x4
    else:
        notes["altman"] = "inapplicable or company_class not specified"

    if m.get("revenue_growth_pct") is not None and m.get("profit_margin_pct") is not None:
        out["rule_of_40"] = m["revenue_growth_pct"] + m["profit_margin_pct"]
    else:
        out["rule_of_40"] = None
    out["ltv_to_cac"] = div(m.get("ltv"), m.get("cac"))
    out["sbc_to_revenue"] = div(m.get("sbc"), m.get("revenue"))
    add_null_notes(out, notes)
    return out, notes


def crypto_metrics(m):
    out, notes = {}, {}
    price = m.get("token_price")
    monthly_tokens = m.get("monthly_newly_liquid_tokens")
    daily_tokens = m.get("expected_daily_sellable_tokens")
    out["unlock_pressure_30d"] = div(None if monthly_tokens is None or price is None else monthly_tokens * price, m.get("spot_volume_30d"))
    out["daily_sell_pressure"] = div(None if daily_tokens is None or price is None else daily_tokens * price, m.get("credible_daily_spot_volume"))
    out["gross_annual_inflation"] = div(m.get("annual_new_issuance"), m.get("circulating_supply"))
    out["float_to_max_supply"] = div(m.get("circulating_supply"), m.get("max_supply"))
    revenue, incentives = m.get("period_external_revenue"), m.get("period_token_incentives")
    out["real_yield_value"] = None if revenue is None or incentives is None else revenue - incentives
    burn = m.get("period_burn_value")
    out["net_incentive_burden"] = None if revenue is None or incentives is None else incentives - revenue - (burn or 0)
    out["top10_holder_pct"] = m.get("top10_holder_pct")
    out["treasury_token_pct"] = m.get("treasury_token_pct")
    for key in ("unlock_pressure_30d", "daily_sell_pressure"):
        if out[key] is None:
            notes[key] = "requires credible spot-volume and sellable-supply inputs"
    add_null_notes(out, notes)
    return out, notes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    manifest = json.loads((run_dir / "00_manifest.json").read_text(encoding="utf-8"))
    evidence = json.loads((run_dir / "01_evidence.json").read_text(encoding="utf-8"))
    metrics = evidence.get("metrics", {})
    if manifest.get("asset_type") == "equity":
        calculated, notes = equity_metrics(metrics)
    elif manifest.get("asset_type") == "crypto":
        calculated, notes = crypto_metrics(metrics)
    elif manifest.get("asset_type") == "hybrid":
        eq, en = equity_metrics(metrics.get("equity", {}))
        cr, cn = crypto_metrics(metrics.get("crypto", {}))
        calculated, notes = {"equity": eq, "crypto": cr}, {"equity": en, "crypto": cn}
    else:
        raise ValueError("unsupported asset_type")
    output = {"schema_version": "5.0", "asset_type": manifest["asset_type"], "calculated": calculated, "notes": notes}
    (run_dir / "02_quant.json").write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(run_dir / "02_quant.json")


if __name__ == "__main__":
    main()
