# Portfolio decision

## Mandatory investor profile

Before personalized advice, obtain:

- current position as a percentage of the total investment portfolio;
- cost basis or useful range;
- available capital and relevant correlated positions;
- three-to-five-year horizon and liquidity needs;
- maximum tolerable drawdown or permanent loss;
- leverage, derivatives, or borrowing use;
- legal, tax, or custody constraints that materially affect execution.

If incomplete, provide asset-level research and an illustrative range only. Do not present it as personalized advice.

Record only the gate outcome in `00_manifest.json.decision`: `personalized_advice_requested` and `investor_profile_complete`. Do not store raw private profile fields unless the user explicitly requests retention. Set `06_judge.json.action_mode` to `personalized` only when both flags are true.

## Four-dimensional verdict

- Evidence grade: A, B, C, D, or F.
- Fundamental state: strengthening, stable, weakening, or broken.
- Odds state: exceptional, favorable, neutral, unfavorable, or extremely unfavorable.
- Requested action: aggressive accumulate, staged accumulate, watch, hold, reduce, exit, or avoid.

## Default position bands

Express bands as a percentage of the total investment portfolio:

- observation: 0.5% to 2%;
- standard: 2% to 5%;
- high conviction: 5% to 10%;
- exceptional undervaluation: 10% to 15%;
- above 15% only when the user explicitly accepts concentration and zero-risk.

Move crypto one band lower than a comparable equity by default. Build positions in evidence-linked stages. Never average down solely because price fell.

Recommend exceptional concentration only when every extreme-undervaluation gate in `valuation.md` passes and the investor profile supports it. State what evidence releases each next tranche and what invalidates the thesis.

## Trigger discipline

Use valuation zones plus confirmation and veto conditions, not unsupported decimal thresholds. Every personalized trigger must identify:

- the signal asset and target asset;
- a valuation or market-structure zone rather than a claimed exact bottom;
- independent confirmation evidence;
- fundamental, custody, or liquidity veto conditions;
- the tranche released and the maximum resulting portfolio weight.

An asset-specific valuation signal may release capital only into the same asset. A BTC valuation metric cannot trigger an ETH purchase, and an equity multiple cannot trigger a crypto purchase, unless the receiving asset independently passes its own evidence gate. Macro or portfolio-risk triggers may affect several assets, but each target still needs a stated rationale.

If a trigger may never occur, state the time-based review or structural liquidity floor. Do not let uncalibrated precision trap capital indefinitely.

## Risk-seeking posture

Accept high failure probability only for sufficiently convex payoff. Let the thesis be aggressive while sizing for survival. Treat a small position in a credible right-tail option as different from a large position in an unverified story.

## Shorting boundary

Default sell advice means reduce, exit, or avoid. Evaluate an actual short, put, or leveraged bearish position only on explicit request and only after analyzing borrow availability and cost, instrument terms, squeeze and gap risk, maximum loss, catalyst timing, and portfolio-level exposure. Do not default to naked shorts in high-volatility equities or crypto.
