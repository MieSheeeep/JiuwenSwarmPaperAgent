# 第一实现里程碑验证记录

日期：2026-10-11。开发分支：feat/research-evidence-chain。已实现历史实验→证据→确定性报告的离线链条；整体科研系统和新记忆方法尚未完成。

## 已验证的结果

- 真实输入：output/baseline 的 dataset.json、manifest.json、results.jsonl、calls.jsonl。
- 24 个历史任务、四个策略、96 条回答、120 次已记录 API 调用，独立重算总计 101,768 token。
- 新报告包含 20 条测量陈述，逐条关联策略指标、证据产物、运行产物与原始调用 ID。
- 初次执行 succeeded；相同输入第二次执行 resumed=true；全部产物摘要与原始文件摘要重新核对通过。
- 新增 18 个测试，含篡改、错配、缺失字段、缓存失效、异常检查点与失败恢复；全量 27 个测试通过。
- 独立代码审查报告的异常输入校验问题已修复，审查者复核三个回归用例通过，无剩余高/中等级发现。
- 本轮新增模型调用与 API token 均为零；原始 baseline 文件和代码未改写。

全量旧框架测试在受限环境导入时停滞；使用已有 tokenizer 缓存并在获准的本地执行环境重跑后通过，未触发模型调用。该环境调整不改变新包的离线性质。

## 评分对应

论文质量：本轮改善数字与实验证据的可追溯性，不能据此宣称科学质量或外部得分提高。系统能力：新增契约、产物谱系、失败状态和恢复。资源：提供历史实验分项和本轮零模型调用报告；完整科研总账仍待实时网关接入。openJiuwen 贡献：本轮新包属于工具层，已有 Rail patch 保留；下一阶段框架源码中的记忆 feature 需单独实现与核验。

Stanford Agentic Reviewer 和论文评测 Agent 的新评分均未产生；本地机械检查 passed 不代替它们。

## 复现与阅读

```powershell
.venv/Scripts/python -m research import-baseline --source output/baseline --output output/research_v2
.venv/Scripts/python -m unittest discover -s tests -p test_research_chain.py -v
```

[使用说明](../research/README.md)、[评分目标](competition_optimization_scorecard.md)、[本地报告](../output/research_v2/paper.md)、[资源报告](../output/research_v2/resources.json)。
