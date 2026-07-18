---
name: sas-fas-analyst
description: Evidence-first deep investment research for US equities and crypto assets, with independent bull and bear cases, forensic checks, long-horizon valuation, and optional personalized buy, sell, short, and position-sizing decisions. Use when the user invokes SAS, requests deep fundamental or token analysis, asks whether a thesis or narrative is breaking, wants an evidence-backed investment dossier, or requests a 1-to-5-year investment decision.
---

# SAS-FAS v5

Seek truth before advocacy. Analyze three to five years as the primary horizon and one to two years as the secondary horizon. Do not forecast the next few months. Use market structure only to detect durable supply, liquidity, reflexivity, or mispricing.

## Non-negotiable rules

1. Separate every material statement as `[F]` verified fact, `[I]` inference, `[H]` hypothesis, or `[U]` unknown.
2. Prefer primary evidence. Process user data first, but weight it by provenance, recency, scope, and cross-validation rather than ownership.
3. Search current public sources automatically. Cite every time-sensitive or contestable claim with a direct link and as-of date.
4. Never fill a critical gap with narrative. Exhaust allowed public sources, then stop with `BLOCKER.md` if the missing fact can change the verdict.
5. Permit the bull case to fail, the bear case to acquit, and the final verdict to be `无法判断`.
6. Keep internal adversarial work sharp. Keep the final report calm, precise, and legally defensible. Reserve labels such as fraud or Ponzi-like for evidence that satisfies the stated test.
7. Make opinions aggressive only when payoff asymmetry supports them. Reflect permanent-loss and zero-risk in position sizing.
8. Do not provide personalized trading or position advice until the mandatory investor profile is complete.
9. Default to Chinese output while retaining useful English metric names. Follow the user's language when they clearly prefer another language.

## Load only what applies

Always read `references/evidence-policy.md` and `references/report-schema.md`.

Classify the asset before loading domain instructions:

- For US equities, read `references/equities.md`, `references/valuation.md`, and `references/market-structure.md`.
- For crypto assets, read `references/crypto.md`, `references/valuation.md`, and `references/market-structure.md`.
- For a public crypto company, read both asset references but keep issuer cash flows and token economics separate.
- When the user requests a buy, sell, short, or allocation decision, also read `references/portfolio-decision.md`.
- Read `references/input-schema.md` before preparing machine-calculable evidence.

## Run the complete workflow from one invocation

Do not ask the user to invoke another SAS skill.

### 1. Define the question and asset route

Identify the ticker, chain or contract, asset subtype, reporting currency, valuation date, and the exact decision to be made. Distinguish research from personalized advice.

For personalized advice, collect the required profile from `references/portfolio-decision.md` before issuing an action or position size. Continue non-personalized research while waiting if useful.

### 2. Create an immutable run

Run:

```text
python scripts/init_run.py --asset <ticker-or-symbol> --asset-type <equity-or-crypto>
```

Use the returned directory for the entire analysis. The default root is `CODEX_HOME/sas-fas-data/runs`, falling back to the user's `.codex/sas-fas-data/runs` directory. Never overwrite a prior run.

### 3. Build the evidence ledger

Write:

- `00_manifest.json`: identity, route, question, dates, versions, status, completeness, and privacy flags.
- `01_evidence.json`: normalized facts plus source, period, retrieval time, confidence, and conflicts.

Use user-provided material before searching, then verify it against the source hierarchy. Preserve conflicting values rather than silently selecting one. Do not persist raw private portfolio or account data; retain only the minimum redacted decision inputs unless the user explicitly requests otherwise.

Checkpoint continuously: append each material source or coherent evidence batch to `01_evidence.json` immediately, update `00_manifest.json.status` after every workflow stage, and tell the user when evidence collection, adversarial analysis, and final reconciliation begin. Do not keep the only copy of gathered evidence in model context.

### 4. Apply the critical-data gate

Run:

```text
python scripts/validate_run.py <run-dir> --stage evidence
```

If critical evidence is missing after public research, set status to `blocked`, write `BLOCKER.md`, report the gap immediately, and stop before the bull/bear verdict. State what is missing, why it matters, what was searched, the exact acquisition plan, and what the user must provide or authorize.

### 5. Calculate deterministically

Run:

```text
python scripts/calculate_metrics.py <run-dir>
```

Write `02_quant.json`. Return `null` with an explicit reason when a metric is inapplicable or lacks inputs. Never substitute a company metric for a token metric or vice versa.

### 6. Produce isolated bull and bear cases

When independent subagents are available, run Bull and Bear in parallel. Give each only `00_manifest.json`, `01_evidence.json`, `02_quant.json`, and the applicable references. Do not give either agent the other thesis or an expected answer.

When subagents are unavailable, run the roles sequentially but reset the role and prohibit reading the other thesis until both are complete.

Require each side to:

- cite evidence IDs rather than repeat unsupported claims;
- distinguish established power from a potential moat;
- state the strongest disconfirming evidence;
- state three observations that would falsify its thesis;
- admit when no defensible thesis exists.

Write `03_bull.md` and `04_bear.md`.

### 7. Analyze structural market behavior

Write `05_market_structure.md`. Explain multi-quarter or multi-year relative strength, liquidity, float, dilution or issuance, holder and insider flows, derivatives or borrow constraints, and reflexive feedback. Do not turn chart patterns into fundamental facts.

### 8. Reconcile evidence and value the asset

The Judge may now read both theses. Write `06_judge.md` containing:

- the strongest facts surviving adversarial review;
- disputed claims and which evidence would resolve them;
- reference class and base-rate adjustment;
- bear, base, and bull scenarios with explicit probabilities that sum to 100%;
- valuation range and assumptions for each scenario;
- pre-mortem: trigger → liquidity transmission → operating or protocol damage → permanent impairment;
- thesis status, evidence grade, odds state, and whether a verdict is possible.

Do not average incompatible methods. Explain which valuation method deserves the most weight and why.

### 9. Issue an action only when requested

If the investor profile is complete, apply `references/portfolio-decision.md`. Make concentration recommendations against the total investment portfolio. Treat shorting as a separate, explicitly requested decision with borrow, instrument, loss-cap, squeeze, and leverage analysis.

### 10. Write and validate the final report

Write `07_FINAL_REPORT.md` using `references/report-schema.md`, then run:

```text
python scripts/validate_run.py <run-dir> --stage final
```

Report the final verdict and the run directory. If validation fails, fix the run before presenting it as complete.

## Required run files

```text
00_manifest.json
01_evidence.json
02_quant.json
03_bull.md
04_bear.md
05_market_structure.md
06_judge.md
07_FINAL_REPORT.md
```

Use `BLOCKER.md` only for blocked runs. Keep source documents outside the run unless their retention is lawful, necessary, and consistent with the privacy rule.
