# 记忆机制优化版：实现与评测记录

本轮已完成一个有限、可复现的优化版本：JiuwenSwarm 记忆扩展、固定实验协议、真实 ReActAgent 调用、独立复算、模型写稿、源码事实修订、PDF 和资源总账。它不是无限自动发现算法的系统；论文明确披露结构化输入、单次回答及小型合成测试的限制。

## 四项评分对应交付

| 评分项 | 已交付证据 | 仍不能声称的结果 |
|---|---|---|
| 论文质量 60 | 新稿 PDF/LaTeX、预算匹配比较、时间/冲突消融、留出测试、描述性配对区间、原始模型稿与事实修订记录；外部 Stanford 新稿估分 4.5/10 | 未核验比赛 40 分项换算规则；论文评测 Agent 20 分项尚无结果，本地评审不代替它 |
| Agent 系统能力 15 | ResearchBrief→ExperimentPlan→真实执行→EvidenceBundle→ManuscriptBundle→ReviewDecision；失败/未知费用停止、响应恢复、产物关联 | 未运行完整桌面 Swarm 装配、通用自由代码生成或工具代理规划 |
| 资源 10 | 请求预留、真实 provider usage、摘要/写稿/失败校验尝试统一计账，30 万 token 准入阈值 | proxy tokenizer 不是厂商硬计费上限；无价格/发票证据时不编造人民币费用 |
| openJiuwen 贡献 15 | JiuwenSwarm 源码中的 VersionedMemoryStore、七种选择策略、VersionedMemoryRail、导出、文档、测试和 patch；在 openJiuwen 上实际调用 | 尚未向上游提 PR/合并，不把科研工具包冒充框架贡献 |

## 真实结果

6 个开发任务、24 个留出任务。主条件上下文 256 proxy token；敏感性条件 512 token，使用其中固定 12 个留出任务。8 种策略包括全历史参照、recent、lexical、BM25、versioned、去时间、去冲突以及 lexical-summary。总计 324 个条件，366 次实验模型调用；无失败、无未知用量。

| 256-token 主条件（留出集） | 精确正确 | 实验 API token |
|---|---:|---:|
| full（不受上下文预算限制的参照） | 19/24 | 40,851 |
| recent | 0/24 | 12,168 |
| lexical | 18/24 | 12,240 |
| BM25 | 6/24 | 12,180 |
| versioned | 20/24 | 9,592 |
| no_time | 8/24 | 9,350 |
| no_conflict | 20/24 | 9,440 |
| lexical_summary | 12/24 | 26,397 |

versioned 与 no_conflict 相同，不能据此宣称额外保留冲突证据提升答案准确率。versioned 的源证据召回达到完整，但模型仍有错误，表明证据充足不等于正确解释。与词法检索的差异仅涉及少量样本，描述性区间包含零；不做显著性、泛化或超过 Mem0/A-MEM 的声明。512-token 表的样本量不同，不能直接用两表百分比作预算增益结论。

实验总消耗 222,233 token。包含写稿、一次修订和内部模型审查后的本轮总账为 369 次调用、240,721 token；重复本地渲染复用了已有响应，没有新增调用。模型调用耗时相加约 378.26 秒，不等于含人工检查、浏览器等待的总墙钟时间。货币成本未估算。

## 模块及机制

框架纯模块 `upstream/jiuwenswarm/agents/harness/common/versioned_memory.py` 接受显式单属性记录，保留 valid_at 与 observed_at 两个时间点、set/delete 和源 ID。每个查询先遵守两个截止时间，再找每个属性的最大有效时间。同时间的冲突证据作为不可拆分组，预算不足时整组省略，避免选择过程抹去矛盾。no_conflict 的含义是按获知先后打破同时间冲突，并不是删除所有冲突记录。选择器不接收 gold，也不生成最终答案。

Rail 在 before_invoke 注入相同查询元数据和选出的原始记录，在 after_model_call 先保存响应与 usage，减少后处理失败造成的重复计费。研究 runtime 通过源码文件加载该扩展，避免整体安装开发分支。每次回答使用新的 ReActAgent、无工具、单模型回答调用。

数据生成与参考答案在 `research/memory_dataset.py`，不调用选择器计算 gold；任务记录按获知时间排列，记录 ID 不含任务类别标签。开发/留出按独立随机种子命名空间生成，未根据留出结果改选择器或提示词。

`model_gateway.py` 统一预留和计账。调用前写 requests，收到响应后立即写 calls。超时或缺少 usage 视为未知费用，停止后续调用；意外多响应保留额外费用并标记异常。恢复后核对数据、源码、选择、上下文、请求指纹及实际消息，然后才允许新增消耗。停止条件会写明 failed/not_run，不伪装成完整成功结果。

`memory_analysis.py` 独立复算所有样本；`orchestrator.py` 维护有限工作流；`memory_paper.py` 先捕获实验快照，再调用模型写段落，程序插入数字表格。原稿误述时间区间、冲突策略和摘要范围，已按真实源码纠正，原稿与修订记录并存。内部模型意见与官方评审分开保存。

## 复现

已有结果只需离线复算，不调用模型：

```powershell
$env:TIKTOKEN_CACHE_DIR = '本机已有的 tiktoken 缓存目录'
python -c "from research.memory_analysis import analyze_memory; print(analyze_memory('output/memory_live_20261016')['evaluation_complete'])"
```

新环境安装 `requirements-baseline.txt`，已有私有模型配置放在 JiuwenSwarm 常规配置位置，不将 API Key 写入提交包。可用 `--config-dir` 指向另一个本地配置目录。

```powershell
python -m research.orchestrator --run-dir output/new_memory_run --paper-dir output/new_memory_paper --max-total-tokens 300000
```

此命令会产生付费模型调用。已有运行的断点恢复不能混用其他模型/endpoint/源码/预算协议。未知费用需要人工核账，不能把删掉 ledger 当作恢复。LaTeX 编译需要已有 pdflatex 和模板依赖；缺失时保留源文件，不自动安装软件。

测试：`python -m unittest discover -s tests -v`。Windows 受限环境可能限制 asyncio 的本地 socket 初始化；本轮全量验证在获准的本地执行环境完成，测试使用模拟响应，不调用模型。

## 外部评审与版本

新稿已成功送至 paperreview.ai，返回 Stanford Agentic Reviewer 估分 4.5/10（ICLR 标尺），倾向拒稿。新的 Token、原始评审和回执随交付包放在 Agentic Reviewer 目录。PDF SHA256 为 `a959d2acf3544dbb5ef4df0c16ac0eeb2210e98c0ceb831183c5f4bdf9ad8903`，评审后未重编译该 PDF。旧稿 token/评审不复制到新稿目录；不将该估分直接换算为比赛分数。主要缺口及事实核对见 [评审跟进](review_followup_20261016.md)。比赛官网本版未上传，独立论文评测 Agent 尚无结果，上游 PR 未创建。

总账范围是这套运行程序记录的 DeepSeek API 调用，包含实验、摘要、写稿、修订和内部审查，不包含 Codex 编程助手、搜索/浏览器服务的用量或整机耗电。元数据与代码版本能支持复算，供应商未提供权重修订号，因此模型别名不能视为永久冻结的权重快照。
