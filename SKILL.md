---
name: sas-fas-analyst
description: >
  结构化极度对抗金融分析引擎 (SAS-FAS v2.1)。使用多智能体（看多/法务做空/基准率法官/链上情报）框架，
  深度解剖传统股票财报与加密资产链上数据，输出顶级机构研报。
  当用户要求「使用SAS-FAS分析」「生成机构研报」「分析某股票基本面」「评估某代币经济学」时触发。
---

# SAS-FAS Analyst Skill

> 本文件为 AI Agent 平台的 Skill 配置入口。完整的系统指令与工作流定义请参阅：
> **[SAS-FAS_Instruction.md](./SAS-FAS_Instruction.md)**

## 使用方式

将 `SAS-FAS_Instruction.md` 的完整内容作为 System Prompt 注入目标模型（推荐 Gemini 3.1 Pro / Claude 4.7 Opus），
随后提供财报数据或链上指标，系统将自动挂载四个智能体（Agent A/B/C/D）执行对抗式分析。
