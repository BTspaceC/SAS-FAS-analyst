# Report contract

Use concise Chinese by default. Put the decision before background.

Before writing the narrative, write `06_judge.json` as the machine-checkable decision record:

```json
{
  "schema_version": "5.0",
  "asset_type": "equity",
  "evidence_grade": "B",
  "fundamental_state": "stable",
  "odds_state": "favorable",
  "verdict_possible": true,
  "action_mode": "research_only",
  "recommended_action": "watch",
  "policy_forecast_separated": true,
  "scenario_weights_pct": {"bear": 25, "base": 50, "bull": 25},
  "scenario_weight_basis": "judgmental",
  "scenario_weight_confidence": "low",
  "scenario_weight_evidence_ids": [],
  "robustness_test": {
    "cases": [
      {"label": "bearish", "weights_pct": {"bear": 40, "base": 50, "bull": 10}, "recommended_action": "watch"},
      {"label": "central", "weights_pct": {"bear": 25, "base": 50, "bull": 25}, "recommended_action": "watch"},
      {"label": "bullish", "weights_pct": {"bear": 15, "base": 50, "bull": 35}, "recommended_action": "watch"}
    ],
    "action_invariant": true,
    "conclusion": "The action remains watch across the tested judgmental weights."
  },
  "negative_claims": [],
  "action_triggers": [],
  "evidence_ids": ["EV-001", "EV-002"],
  "unresolved_evidence": []
}
```

When `verdict_possible` is false, use `odds_state: "undetermined"`, make `unresolved_evidence` non-empty, and omit scenario weights if they would imply false precision. `action_mode` is `research_only`, `illustrative`, or `personalized`; the last value requires the mandatory investor-profile gate.

`recommended_action` is `aggressive_accumulate`, `staged_accumulate`, `watch`, `hold`, `reduce`, `exit`, or `avoid`. For non-judgmental weights, `scenario_weight_evidence_ids` must identify the empirical, model, or market-implied basis. For judgmental weights, say so prominently and do not call them statistical probabilities.

`negative_claims` must classify each material negative conclusion as `evidence_of_impairment` or `insufficient_evidence_for_positive_claim`. The second classification must name the expected observable evidence. Personalized reports require non-empty `action_triggers` following `portfolio-decision.md`.

A personalized trigger uses this shape and its `id` must appear in the final report:

```json
{
  "id": "TR-001",
  "signal_asset": "BTC",
  "target_asset": "BTC",
  "signal_type": "asset_valuation",
  "zone": "broad low-valuation zone; not an exact bottom",
  "confirmations": ["realized value and long-term demand remain intact"],
  "vetoes": ["affirmative evidence of permanent thesis impairment"],
  "tranche": "release 25% of the reserved BTC capital",
  "max_portfolio_weight_pct": 15,
  "review_if_untriggered": "review every six months; retain the structural liquidity floor",
  "evidence_ids": ["EV-001"]
}
```

```markdown
# [Asset / Ticker] — SAS-FAS v5 深度研究
> 截止日期 | 资产路由 | 研究期限 | 运行状态

## 一句话裁决
[可证伪的一句话结论]

## 四维评级
| 证据等级 | 基本盘状态 | 赔率状态 | 行动建议（仅在请求且资料完整时） |

## 已确认的底层事实
- [F][EV-ID] ...

## 核心推断与未知
- [I] ...
- [H] ...
- [U] ...

## 投资政策与预测边界
[可执行政策、预测性情景，以及二者不能互相证明的边界]

## Bull：最强成立路径
[护城河/网络效应、再投资、价值捕获、证伪条件]

## Bear：永久损失路径
[会计/治理/稀释/安全/竞争、证伪条件]

## 估值、情景权重与稳健性
| 情景 | 权重及其依据 | 关键假设 | 价值区间 | 当前价格隐含 |

[至少三组权重敏感性；说明行动是否保持不变。主观权重不得称为统计概率。]

## 基准率与市场结构
[参考类别、相对表现、结构性供求、不可把价格当基本面的警告]

## 事前验尸
[触发 → 流动性传导 → 经营或协议损害 → 永久损失]

## 行动与仓位（仅在请求且资料完整时）
[分阶段仓位、释放条件、失效条件、最大风险]

## 什么会改变结论
[最少三项可观察证据]

## 数据盲区与冲突
[缺失、冲突、敏感性]

## 来源
[直接链接与截止日期]
```

Do not hide uncertainty in footnotes. If the verdict is `无法判断`, state the exact evidence needed to resolve it and the maximum defensible observation position, if the investor profile permits one.
