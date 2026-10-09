# Agent记忆与上下文优化：首轮论文筛选

日期：2026-10-08。围绕初稿评审指出的精确编号检索偏置、弱基线、预算比较和公开评测不足筛选。当前是摘要、元数据及作者仓库筛选，尚不是全文系统综述。

| 论文 | 时间 | 可借鉴或比较的内容 |
|---|---|---|
| [LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory](https://arxiv.org/abs/2410.10813) | 2024 preprint / ICLR 2025 | 优先接入：知识更新、时间推理、跨会话及拒答；参考分解会话和查询扩展。 |
| [Evaluating Very Long-Term Conversational Memory of LLM Agents](https://aclanthology.org/2024.acl-long.747/) | ACL 2024 | 第二个公开数据集，用来检查方法是否仅适配一种数据。 |
| [A-MEM: Agentic Memory for LLM Agents](https://arxiv.org/abs/2502.12110) | 2025 | 学习结构化记忆条目、动态关联和记忆演化；作为记忆组织对照。 |
| [Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory](https://arxiv.org/abs/2504.19413) | 2025 | 学习事实提取和合并；资源统计包含建库、更新、检索、回答全部调用。 |
| [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956) | 2025 | 学习时间信息和事实变化；重点检查过期事实的处理。 |
| [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560) | 2023 | 补齐分层记忆背景；不能把复用既有机制当作新贡献。 |
| [EvalMem: An Operation-Level Diagnostic Framework for Long-Term Memory Systems](https://arxiv.org/abs/2609.22231) | 2026; arXiv reports accepted EMNLP Findings | 把失败分成未存入、未找回、读到后仍答错；用于诊断和消融。 |
| [LongMemEval-V2: Evaluating Long-Term Agent Memory Toward Experienced Colleagues](https://arxiv.org/abs/2605.12493) | 2026 work-in-progress preprint | 更贴近Agent工作轨迹；历史很大，优先评估接入成本。 |

## 阅读顺序

LongMemEval → Mem0 → A-MEM → Zep → EvalMem。LoCoMo与LongMemEval-V2重点阅读数据格式和评测协议。MemGPT已有引用，补读机制即可。

## 下一阶段的判断

优先研究历史事实的更新、冲突与有效时间，以及有限上下文下如何保留作答所需证据。是否有新贡献，要在全文阅读和强基线实验后判断。该方向不是首次提出时间记忆或混合检索。

建议以LongMemEval cleaned版本为首个公开评测，冻结开发集与留出评测集。先记录BM25、语义检索、混合检索、近期窗口，以及可运行的既有记忆方法；所有方法比较相同的回答证据预算，完整历史另列参考。报告答案质量、证据召回、过期事实错误和完整资源消耗。模型写作前先完成实验，不能仅加引用来改善评审分数。

## 评审建议的使用边界

AI评审列出的DOS RAG、Adaptive-k、AdaGReS等名称尚未在本次查找中逐一核实，不直接当作已确认文献或必须复现的方法。本清单仅包含已找到的原始来源。

## 来源与复现入口

- LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory: https://arxiv.org/abs/2410.10813
  作者入口：https://github.com/xiaowu0162/LongMemEval
- Evaluating Very Long-Term Conversational Memory of LLM Agents: https://aclanthology.org/2024.acl-long.747/
  作者入口：https://github.com/snap-research/locomo
- A-MEM: Agentic Memory for LLM Agents: https://arxiv.org/abs/2502.12110
  作者入口：https://github.com/agiresearch/A-mem
- Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory: https://arxiv.org/abs/2504.19413
- Zep: A Temporal Knowledge Graph Architecture for Agent Memory: https://arxiv.org/abs/2501.13956
- MemGPT: Towards LLMs as Operating Systems: https://arxiv.org/abs/2310.08560
- EvalMem: An Operation-Level Diagnostic Framework for Long-Term Memory Systems: https://arxiv.org/abs/2609.22231
- LongMemEval-V2: Evaluating Long-Term Agent Memory Toward Experienced Colleagues: https://arxiv.org/abs/2605.12493
  作者入口：https://xiaowu0162.github.io/longmemeval-v2/
