# Evidence policy

## Source hierarchy

Use the highest available tier and record the tier on every evidence item.

1. Regulatory filings, audited statements, court records, chain state, verified contracts, and protocol source code.
2. Issuer or foundation disclosures, official governance proposals, investor materials, and first-party operating dashboards.
3. Reputable index providers, exchanges, established data vendors, and peer-reviewed research.
4. High-quality journalism with named evidence.
5. Analyst commentary, blogs, forums, and social media. Use these to discover leads, not to establish contested facts.

## Evidence ledger

Give every item a stable ID and include:

```json
{
  "id": "EV-001",
  "claim": "normalized factual statement",
  "value": null,
  "unit": null,
  "period": "YYYY or date range",
  "as_of": "ISO-8601 timestamp",
  "source_url": "direct URL or user-artifact identifier",
  "source_tier": 1,
  "provided_by_user": false,
  "confidence": "high",
  "privacy": "public",
  "conflicts": []
}
```

Use only `high`, `medium`, or `low` for `confidence` so validation and comparisons remain deterministic.

Use one direct source per evidence item. If a claim needs multiple sources, split it into multiple evidence IDs and combine them only in an `[I]` inference. Do not attach a multi-source conclusion to one convenient URL.

For `source_url` values beginning with `derived:`, add a reproducible derivation:

```json
"derivation": {
  "formula": "source_pe * current_index_level / source_index_level",
  "input_evidence_ids": ["EV-PRICE", "EV-PE"]
}
```

For fees, yields, quotas, promotions, and similar changing terms, record `effective_from`, `effective_until` when known, and `last_verified_at`. A nominal rate and a currently effective promotional rate are separate facts.

Treat user material as priority input, not automatic ground truth. If values conflict, retain both, explain timing and definition differences, select a working value only when justified, and test verdict sensitivity to the alternative.

Keep `critical_fields` non-empty once the asset route is defined. In `metric_evidence`, map every critical numeric input to the evidence IDs that support it. Evidence-ready status requires a valid cutoff date, at least one valid evidence item, finite critical values, and complete critical-field mappings. An untouched run scaffold must fail the gate.

## Claim discipline

- `[F]` must trace to evidence IDs.
- `[I]` must name the facts and reasoning step.
- `[H]` must state a future observation that could confirm or reject it.
- `[U]` must state why the unknown matters.
- Absence of evidence is not evidence of absence unless the expected disclosure or observable footprint is specified.
- Classify a negative conclusion as `evidence_of_impairment` only when affirmative evidence shows deterioration. Use `insufficient_evidence_for_positive_claim` when the expected positive evidence is missing or too weak. The latter can block an upgrade or add recommendation, but it cannot by itself prove failure.

## Blocking rule

Block only after exhausting allowed public sources and alternatives. A missing item is critical when plausible values could change thesis status, evidence grade, scenario ordering, valuation by a material amount, or the action recommendation.

Write `BLOCKER.md` with:

1. missing item;
2. decision impact;
3. sources and substitutes attempted;
4. exact acquisition method;
5. required user action or permission;
6. workflow step that will resume.

## Privacy

Do not persist account numbers, wallet addresses, authentication data, screenshots, exact cost basis, or complete portfolio composition by default. Store redacted ranges sufficient for the decision. Retain raw private data only on explicit request.
