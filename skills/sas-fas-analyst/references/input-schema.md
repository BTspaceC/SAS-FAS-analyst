# Input schema

Store normalized evidence in `01_evidence.json`:

```json
{
  "critical_fields": ["price", "shares_or_supply"],
  "metrics": {},
  "evidence": [],
  "conflicts": []
}
```

For hybrid assets, nest calculator inputs under `metrics.equity` and `metrics.crypto`; express critical fields with dotted paths such as `equity.price` and `crypto.token_price`.

The calculator reads `metrics`. Use JSON numbers without commas or currency symbols. Omit unavailable fields rather than inventing zero.

## Equity metric keys

General: `net_income`, `cash_from_operations`, `total_assets_current`, `total_assets_prior`, `ebit_current`, `tax_rate`, `invested_capital_current`, `invested_capital_prior`, `nopat_prior`, `market_value_equity`, `total_liabilities`, `working_capital`, `retained_earnings`, `revenue_current`, `revenue_prior`, `cogs_current`, `cogs_prior`, `receivables_current`, `receivables_prior`, `current_assets_current`, `current_assets_prior`, `ppe_current`, `ppe_prior`, `depreciation_current`, `depreciation_prior`, `sga_current`, `sga_prior`, `current_liabilities_current`, `current_liabilities_prior`, `long_term_debt_current`, `long_term_debt_prior`, `ebit`, `book_value_equity`, `company_class`.

For SaaS: `revenue_growth_pct`, `profit_margin_pct`, `nrr_pct`, `gross_retention_pct`, `ltv`, `cac`, `sbc`, `revenue`.

Set `company_class` to `public_manufacturing`, `private_manufacturing`, `non_manufacturing`, `bank`, `insurer`, `reit`, or another descriptive route.

For banks use: `share_price`, `tangible_book_value_per_share`, `book_value_per_share`, `reported_ltm_eps`, `core_ltm_eps`, `cet1_ratio_pct`, `binding_cet1_requirement_pct`, `noninterest_bearing_deposits`, `total_deposits`, `allowance_credit_losses`, `loan_loss_allowance`, `total_loans`, `htm_book_value`, `htm_fair_value`, and `tangible_common_equity`. Keep all balance-sheet amounts in the same currency scale. Supply fields ending in `_pct` as percentage points such as `14.1`; compatibility aliases `cet1_ratio` and `binding_cet1_requirement` accept either decimals such as `0.141` or percentage points.

## Crypto metric keys

Use `circulating_supply`, `max_supply`, `annual_new_issuance`, `monthly_newly_liquid_tokens`, `token_price`, `spot_volume_30d`, `expected_daily_sellable_tokens`, `credible_daily_spot_volume`, `period_external_revenue`, `period_token_incentives`, `period_burn_value`, `top10_holder_pct`, and `treasury_token_pct` when available.

Every calculator output includes missing-input and applicability notes. Metrics do not become facts until their inputs trace to evidence IDs.
