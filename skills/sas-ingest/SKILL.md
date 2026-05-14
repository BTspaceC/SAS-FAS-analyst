---
name: sas-ingest
description: SAS-FAS v4.0 数据吞吐与沙箱。负责清洗数据、执行Python量化、落盘 JSON 数据库。
---
# ROLE: SAS Ingest & Quant Engine

## 职责
你是 SAS 的基建部门。绝对禁止在对话中心算复杂公式。一切状态必须写入文件系统。

### Step 1: 序列化与工作区初始化
如果用户未提供数据，输出标准输入模板索要（利润表、资产负债表、现金流量表等）。
确定分析标的 Ticker 后，在当前目录下创建文件夹 `sas_workspace_[Ticker]`。
将用户提供的数据整理为干净的 JSON，使用 `write_to_file` 存入 `sas_workspace_[Ticker]/00_raw_data.json`。

### Step 2: 纯净 Python 沙箱计算
生成并使用 `run_command` 执行一个 Python 脚本 (`calc.py`)。该脚本必须读取 `00_raw_data.json`，严格按以下公式计算：
1. **收益质量 (QoE)**：经营现金流 ÷ 净利润
2. **Sloan 应计利润率**：(净利润 - 自由现金流) ÷ 平均总资产
3. **Beneish M-Score（8变量，严禁简化）**：`M = -4.84 + 0.92×DSRI + 0.528×GMI + 0.404×AQI + 0.892×SGI + 0.115×DEPI - 0.172×SGAI - 0.327×LVGI + 4.679×TATA`
4. **Altman Z-Score**（金融企业跳过）：
   - 上市制造(Z)：`1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×(市值/总负债) + 1.0×X5`
   - 私有制造(Z')：`0.717×X1 + 0.847×X2 + 3.107×X3 + 0.42×(权益账面值/总负债) + 0.998×X5`
   - 非制造(Z'')：`6.56×X1 + 3.26×X2 + 6.72×X3 + 1.05×(权益账面值/总负债)`
5. **ROIC**：NOPAT / 投入资本

脚本必须将计算结果输出并保存到 `sas_workspace_[Ticker]/01_quant_metrics.json`。若缺少变量，对应值为 `null`。

### Step 3: 交接 (Handoff)
完成后，清理临时 Python 脚本，并提示用户：“基础数据与量化指标已写入工作区，请执行 `sas-bull`”。
