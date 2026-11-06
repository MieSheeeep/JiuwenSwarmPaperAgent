# 2026-11-06 全面升级研究

本轮独立研究目录为 `output/review_upgrade_20261106`，工作台入口为 `http://127.0.0.1:8765/#upgrade`。以该目录的 `run_state.json`、`summary.json` 和 `paper/writing_status.json` 判断实际完成状态；源码实现和本说明不代替实验完成证明。旧论文、旧 Stanford 分数与旧提交包均为历史产物。

## 模块与机制

| 模块 | 实现 | 评估边界 |
|---|---|---|
| 数据与冻结 | 新种子合成任务、装包压力任务、固定版本 LongMemEval | 72 道正常测试与 12 道压力测试分开；开发集不进入主测试 |
| 证据检索 | BM25、本地量化 MiniLM、等权 RRF、时间版本选择 | 检索过程不读取金答案；预训练模型身份和文件校验固定 |
| 装包 | 原子冲突组、小组优先、动态规划代理目标、多样性 | DP 仅优化可加代理；最终拼接文本重新计数，不声称真实 tokenizer 全局最优 |
| 回答 | 基础、冲突核验、双调用反思 | 使用实际新建 ReActAgent；冻结最终输入；反思额外调用计费 |
| 评估 | 严格 JSON 答案、词法代理、参考答案驱动的语义判断 | 外部语义判断使用 DeepSeek，属于适配评估，不能冒充官方 LongMemEval 分数 |
| 分析 | 匹配任务比较、重复一致性、任务重采样、描述性错误分组 | 重复调用不增加独立样本；生成器/对话相关性未解决，不宣称统计显著性 |
| 写作 | 英文章节、已核验参考文献、数字表格确定性生成、模型批评与有限修订 | 机械校验不保证科学正确；新稿需要新外部评审 |
| 交付 | 中文工作台、英文 LaTeX/PDF、资源报告、独立打包 | 原论文不覆盖；新包不继承旧评审 Token 或成绩 |

外部数据的 70 题固定匹配子集比较两模型和三种检索器；其余 430 题只扩展 Flash+hybrid 主方法。500 题主方法结果可以单独汇总，不能与 70 题其他方法形成未匹配比较。外部原始对话没有人工构造的事实有效区间，因此这部分不证明自由文本双时间事实抽取有效。

## 重放与新运行

安装 `requirements-baseline.txt` 与 `requirements-research-upgrade.txt`，准备兼容 JiuwenSwarm 源码和 patch，按 [外部数据协议](external_benchmark_protocol.md) 下载并核对固定数据版本，按 [检索说明](retrieval_upgrade.md) 准备固定 ONNX 模型权重。原始数据及权重不随提交包重复分发。凭证由 `baseline.runtime.read_model_config` 从个人配置读取，不应放入研究目录或提交包。

新运行必须使用新的目录；不要用改过源码的程序向本轮冻结账本追加数据。以下命令会产生实际模型 API 用量：

```powershell
.venv/Scripts/python -m research.review_upgrade --output output/new_study --max-total-tokens 3000000
```

默认使用 Flash 和 Pro 两个已配置的模型别名。供应商别名不等于不可变权重版本；模型目录与运行时依赖版本随协议记录。通过 `--prepare-only` 可以只准备协议和输入，不执行付费回答。并行执行需要单独的操作修订和分片前验证，见 [并行协议](parallel_upgrade_protocol.md)，不能直接对活跃目录启动第二个回答进程。

所有付费实验、外部判断、反思、写作和修订共同受用户批准的 3,000,000 Token 上限约束；这不是需要花完的额度。保留写稿余量，新增未知用量停止新增调用。Unicode JSONL 读取修复、协作暂停/任务分片，以及充值后的保守预留恢复修订已记录在 `protocol_amendments.jsonl`，不改变实验问题、提示、打分或预定任务。

本轮曾有三次请求在响应前抛出 FrameworkError，供应商未返回用量。原始记录仍为 `usage: null`，没有改成免费或补造实际 Token。用户继续并充值后，通过绑定原始请求/失败行哈希的 `admission_reserves.json`，每次额外冻结 10,000 Token，合计 30,000，从全局可用预算中扣除。这是超过原始请求准入预留的保守估计，不是供应商账单上界的证明，也不是已经结清的消费。任意新的未知调用仍会停止；回答矩阵完成与历史费用完全核对分开报告。原始分片保留，恢复分片写入独立目录。

外部原文中的 tokenizer 保留字符串曾触发计数器异常，发生在模型调用之前。修复改为按普通字面文本编码，不删除内容、不将其解释为模型特殊指令。先前有效文本的 token 序列与输入哈希保持一致；测试和恢复前校验覆盖这一点，操作修订已单独登记。

实验终止、账本对齐后，依次执行离线统计和有上限的写作：

```powershell
.venv/Scripts/python -m research.upgrade_analysis --run-dir output/new_study --output output/new_study
.venv/Scripts/python -m research.upgrade_errors --run-dir output/new_study
.venv/Scripts/python -m research.upgrade_manuscript --run-dir output/new_study
```

写作使用单独账本并计入总上限。LaTeX 使用禁用 shell escape 的本地编译器，结果必须查看渲染效果；编译通过不等于评审通过。论文数字表格与图从保存测量生成，模型自由正文不得自行生成实验数字。参考文献 registry 区分已集成组件和未复现的作者系统。

资源报告分别统计输入、输出和缓存 Token，并用有日期的公开价格给出美元上下界，不能当作供应商发票。本地硬件快照、CPU embedding 时间与远程 API Token 属于不同资源范围；没有测量整机能耗或训练成本。框架贡献为本地源码、测试、文档与 patch，尚无上游 PR 或合并。

## 评分证据

| 比赛项目 | 本轮交付证据 | 仍需外部确定 |
|---|---|---|
| 论文质量 60 | 新英文稿、强对照/消融、匹配统计、局限、原始调用 | Stanford 40 与论文评测 Agent 20 的新分数 |
| Agent 系统 15 | 实际 Agent 输入约束、失败停止、持久账本、批评修订和工作台 | 评委对系统能力的判断 |
| 资源 10 | 全阶段实际用量、共享上限、成本范围、本地检索记录 | 评委认可的成本指标与成绩 |
| openJiuwen 15 | 独立 Rail、SDK 契约测试、文档和可应用 patch | 上游接受与比赛贡献分 |

新稿的官方分数、官网上传状态和私有评审凭证必须绑定新 PDF 哈希，不能移植旧稿记录。
