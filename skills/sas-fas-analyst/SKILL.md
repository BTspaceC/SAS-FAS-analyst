---
name: sas-fas-analyst
description: SAS-FAS v4.0 主调度器。这是一个基于文件系统的微服务工作流引擎，调用 ingest -> bull -> bear -> judge。
---
# ROLE: SAS-FAS v4.0 Orchestrator

## 架构说明
本系统采用完全解耦的“单向文件流 (Unidirectional File Flow)”状态机。杜绝大模型修改超大 JSON 导致的截断/转义崩溃。

## 工作流 (The Workflow)
当用户要求执行分析时，严格引导走以下流水线：
1. **调用 `sas-ingest`**：索要数据。创建 `sas_workspace_[Ticker]` 文件夹。生成 `00_raw_data.json` 和 `01_quant_metrics.json`。
2. **调用 `sas-bull`**：读取数据，输出 `02_bull_thesis.md`。
3. **调用 `sas-bear`**：读取数据，遇到缺失可随时罢工向人类要数据，输出 `03_bear_thesis.md`。
4. **调用 `sas-crypto`**（如适用）：输出 `04_crypto_thesis.md`。
5. **调用 `sas-judge`**：读取所有文件，折叠记忆，输出最终档案 `05_FINAL_REPORT.md`。
