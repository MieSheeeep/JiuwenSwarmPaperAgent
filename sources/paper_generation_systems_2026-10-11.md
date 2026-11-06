# 自动科研与论文生成系统：模块借鉴候选

核查日期：2026-10-11。核查范围为作者论文摘要、仓库README及目录；尚未在本机运行，也未完成逐文件代码和依赖审计。候选借鉴不等于已移植或已有原创贡献。

后续进展：已完成 Agent Laboratory 与 AI-Researcher 核心源码静态拆解，固定版本、模型入口、移植障碍和许可观察见 [代码审计](research_system_code_audit_2026-10-11.md)，模块契约与落地顺序见 [第二版设计](../docs/research_system_v2_design.md)。上述“尚未完成”描述保留为候选筛选阶段的范围说明；两套完整工作流仍未运行。

| 系统 | 论文 | 作者代码 | 可借鉴部分 | 接入判断 |
|---|---|---|---|---|
| Agent Laboratory | https://arxiv.org/abs/2501.04227 | https://github.com/SamuelSchmidgall/AgentLaboratory | 文献、计划、实验、报告、阶段存档 | 第一优先；README列出Python3.12和deepseek-chat支持，MIT许可；我们的deepseek-flash仍需适配验证 |
| The AI Scientist | https://arxiv.org/abs/2408.06292 | https://github.com/SakanaAI/AI-Scientist | 模板实验、构思、写作和内部评审 | 借鉴流程与提示词；原始模板面向Linux/CUDA，非Windows直接可运行保证 |
| The AI Scientist-v2 | https://arxiv.org/abs/2504.08066 | https://github.com/SakanaAI/AI-Scientist-v2 | 实验管理与渐进式树搜索 | 后续用于选择实验分支；先控制分支数和总调用预算，避免直接运行完整重型流程 |
| AI-Researcher | https://arxiv.org/abs/2505.18705 | https://github.com/HKUDS/AI-Researcher | 文献到算法实现、独立paper_agent、Scientist-Bench | 重点读research_agent和paper_agent边界；README提供paper_agent/writing.py入口，原运行方式含Docker/GPU，移植前检查依赖和许可 |
| CycleResearcher | https://arxiv.org/abs/2411.00816 | 论文给出minjun-zhu/Researcher，但本次直接打开未成功 | 研究与审稿的迭代反馈 | 先读论文；训练/专用模型方法不是给DeepSeek加一个提示词就能等价复现 |
| FARS | https://analemma.ai/ | 本次未确认官方完整系统源码 | 连续科研流水线和成果追踪 | 参考公开设计；搜索所得OpenFARS等自称第三方复现，不能当作官方实现或用官方成果证明复现有效 |

## 建议的模块来源映射（设计提案）

1. 文献与构思：Agent Laboratory / AI-Researcher，保存论文来源、待验证问题和可行性条件。
2. 实验规划：固定数据版本、开发/留出划分、比较方法、指标、成功判据和调用预算。
3. 实验执行：保留现有真实调用、断点记录与资源日志；后续借鉴AI Scientist-v2的实验分支管理。
4. 结果与证据管理：建立实验配置、代码版本、原始结果、图表和论文陈述的关联。所有数字由统计脚本产生。
5. 写作：重点读Agent Laboratory/papersolver.py和AI-Researcher/paper_agent/writing.py；论文只能依据已保存的实验与文献证据。
6. 检查与修订：借鉴CycleResearcher的反馈循环，但区分修复表达、补证据、追加实验；每次修改记录原因和成本。

以上是我们的架构建议，不代表这些项目都提供相同的标准接口。编排继续使用openJiuwen/JiuwenSwarm，保持赛题要求的源码贡献。记忆检索方向是系统执行的研究课题，与自动科研系统本身分别说明。

## 选择原则

先集中评估Agent Laboratory和AI-Researcher，再决定哪些实现可复用。复用前核查具体版本、许可证和模型适配；借鉴和自研部分分别登记。AI Scientist系列仓库采用自定义Source Code License并要求AI生成披露，不能假设它与MIT完全相同。

不把作者报告的论文得分当作我们的可实现得分。评审闭环的目标是修复证据和实验问题，而非反复润色迎合单个AI评审器。组合已有方法需要通过独立实验说明其价值，不能仅凭模块数量宣称创新。
