# 2026-11-06 离线错误分析与下一轮实验提案

本次只读取 `output/memory_live_20261016` 的 dataset、manifest、results，复用已有 `score.exact` 与 `score.evidence_recall`，没有调用模型、生成新答案、重新评分或修改原实验及论文。输入文件 SHA-256 保存在分析 JSON 的 provenance 中，可检查分析使用的字节版本。代码不读取模型配置、请求消息或调用账本，输出只保留白名单字段及合成任务记录。

运行方法（仓库根目录）：

```powershell
python -m research.error_analysis --run-dir output/memory_live_20261016 --output output/workbench_analysis_20261106
python -m unittest discover -s tests -p test_error_analysis.py
```

输出为英文 `error_analysis.json`、`ERROR_ANALYSIS.md`、`next_experiment_plan.json`。接口 `analyze_errors(run_dir)` 返回可序列化字典且不写文件，CLI 只写独立输出目录，拒绝写入原运行目录及其子目录。重复 task/grid/result 身份、计划外结果和 split/family 不一致会报错。缺少计划结果、失败状态、非法或缺失分数会分别计数，不会混入回答错误分母。

## 分类及实际观察

“证据不完整的错误”指成功响应、exact=false 且 evidence_recall<1；“证据完整时仍错误”指成功响应、exact=false 且 evidence_recall=1。这是共同出现的现象分类，不能据此证明错误由检索器或阅读器造成。尤其摘要策略的现有 evidence_recall 度量可能不等同于原始 selected_ids 覆盖；JSON 同时保留分数、选择 ID、gold evidence 和缺失 ID，不能混用两者。

现有 324 个计划结果均存在且成功，分数均有效。177 个 exact 正确，147 个错误，其中 113 个证据不完整、34 个证据完整。该总数混合 dev/test 与两档预算，只用于核对账目，不是主要 held-out 结论。

| test 策略 | 预算 | exact 正确/总数 | 证据不完整错误 | 证据完整错误 |
|---|---:|---:|---:|---:|
| recent | 256 | 0/24 | 24 | 0 |
| recent | 512 | 0/12 | 12 | 0 |
| full | 256（标签，实际不限上下文） | 19/24 | 0 | 5 |
| versioned | 256 | 20/24 | 0 | 4 |
| no_conflict | 256 | 20/24 | 4 | 0 |
| versioned | 512 | 10/12 | 0 | 2 |
| no_conflict | 512 | 10/12 | 2 | 0 |

full 的 5 个 test 错误包括 4 个 conflict 和 1 个 historical。recent 所有 test 错误同时缺少完整 gold evidence，支持进一步检查选择策略，但不能直接将“较近记录”认定为唯一原因。full 不限上下文，不能与其他策略解释为等预算对照。

versioned 与 no_conflict 在 24 个主预算 test 配对、12 个敏感性 test 配对上，exact 与实际响应逐一相同；主预算有 4 对、敏感性预算有 2 对选择与证据召回不同。这意味着当前结果没有显示 conflict 处理带来的 exact 增益；也不能从平局推断两方法在所有任务上等价。每个 case 的 question、原始 response、gold、query、相关源记录保存在 JSON 中，英文 Markdown 完整展示 recent/full 错误案例。

例如 `test-conflict-44950fa99959a053`、`test-conflict-5f6f055527b311db`、`test-conflict-6b58a0afd98acb55`、`test-conflict-e51db3c0d64c7fa6` 是 full 在冲突族的错误；`test-historical-a3b1ada404b4c907` 是 full 的历史查询错误。具体答案请以报告中的实际 response 与 gold 为准。

## 冻结的未来提案

独立计划 JSON 标记为 `proposed_not_run`，不会被分析脚本执行。语义/混合基线提案是在固定 source-token 预算和同一 reader 下比较 BM25、本地固定版本 dense embedding 与 RRF(k=60)；conflict-aware reader 提案重放同一上下文，对 effective/observed 时间和最大时间冲突做显式比较。packer 提案区分三种方案：逐记录排序/打包基线（如 lexical/BM25）、当前 versioned 的最大时间原子组 smaller-first packer、拟议的原子组 utility/coverage-aware packer。当前 versioned 已经联合保留同属性最大时间记录，不能将原子分组误写为尚未实现。隔离启发式差异时，后两者使用完全相同的候选原子组、reader 和预算，utility/coverage 规则只在 dev 上预注册；逐记录基线提供背景对照，不能单独归因于 packing 启发式。三种方案与两种 reader 交叉比较均为未来实验，未新增运行或性能结果。

下一轮要在调用前固定新 seed、数据与代码哈希、模型版本、温度、预算、调用/费用上限，dev 调参后封存 test。报告配对差异、平局、失败分母、证据覆盖、实际 token、延迟和费用。当前小型合成任务有家族和 seed 依赖，不能推断真实对话效果。

外部验证候选依据 [LongMemEval 官方仓库](https://github.com/xiaowu0162/LongMemEval)，核对日期 2026-11-06。原版包含 500 个问题，能力包括 knowledge updates、temporal reasoning、abstention；README 在 2026 年 5 月宣布 V2。未来应固定 cleaned 原版数据版本及文件哈希，原版 500 问与合成任务分开报告；V2 作为另一个独立协议。本次没有下载或运行两者，也没有执行可能产生费用的官方模型评估脚本。

## JSON 接口

顶层字段为 `schema_version`、`run_dir`、`provenance`、`definitions`、`overview`、`groups`、`group_summaries`、`comparisons`、`cases`、`limitations`、`next_experiment_plan`。groups 按 split/family/policy/budget，group_summaries 按 split/policy/budget；每组计数包括 expected/observed/missing/failed/invalid_score/scored 行数、exact_correct、exact_errors、retrieval_insufficient_errors、complete_evidence_errors 和 exact_accuracy_scored（无有效分数时为 null）。comparisons 记录 versioned/no_conflict 的配对及排除数、双方正确/错误、单方正确、exact 平局、召回相同、选择相同、响应相同数。

测试先记录模块缺失导致的失败，再实现并通过；另补充 null/缺失 score 测试先复现异常，再修复。覆盖描述统计、平局、真实案例字段、缺失/失败/非法分数、NaN、重复/计划外结果、元数据不一致、确定性、CLI 输出以及输入字节不变。
