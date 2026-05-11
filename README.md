# SAS-FAS Analyst (v2.1)

**结构化极度对抗金融分析引擎 (Structured Adversarial Synthesis - Financial Analysis System)**

这是一个专为顶级对冲基金设计的非线性、多智能体金融分析系统 Prompt。使用多智能体（看多/法务做空/基准率法官/链上情报）框架，深度解剖传统股票财报与加密资产链上数据，输出顶级机构研报。

## 核心机制

- **Agent A (The Optimist)**: 看多引擎，基于规模经济共享、护城河穿透与隐性资本重构、管理层资本配置考核构建做多逻辑。
- **Agent B (The Short-Seller)**: 法务做空刺客，基于法务级量化排雷矩阵（Sloan、Beneish M-Score、Altman Z-Score）执行毁灭打击。
- **Agent C (The Oracle)**: 决策中枢，主导多空对抗沙盘推演，引入基准率校验 (Base Rate Check) 防脑热机制。
- **Agent D (The On-Chain Forensics Unit)**: 加密货币/代币专用模块，进行代币经济学解剖、链上基本面核查与智能合约审计。

## 文件说明

- `SKILL.md`: 适配大模型智能体平台的 Skill 配置文件。
- `SAS-FAS_Instruction.md`: 完整的 Prompt/系统指令说明书，可直接复制使用。

## 使用方法

将 `SAS-FAS_Instruction.md` 的内容作为 System Prompt 输入给 Claude 3.5 Sonnet / GPT-4o / Gemini 1.5 Pro 等主流高智商模型。随后向模型提供财报数据、SEC文件或加密资产链上数据，系统将自动挂载四个智能体执行分析。
