# 通用科研执行器设计

## 目标

把现有的“文献 → 问题 → 实验设计”交接，扩展成一个可验证的小闭环：Agent 选定问题后，只能从已注册、可审计的实验适配器中选择方法，冻结数据与预算，执行多种方法对比，保存逐任务结果和资源账本，再把数字结果交给论文生成阶段。

本阶段不允许模型直接执行任意 shell/Python 代码，也不声称已经解决任意学科的自主科研。先用一个与旧的 bitemporal memory 课题不同的多跳问答/检索停止策略案例验证闭环。

## 架构

- `research/experiment_protocol.py`：定义注册适配器、实验计划校验和冻结协议。
- `research/qa_dataset.py`：生成可复现的多跳问答小数据集，提供独立答案和证据 oracle。
- `research/generic_runner.py`：读取计划，调用注册适配器选择上下文，使用 `ModelGateway` 进行回答，逐任务记录结果、调用 ID、实际 token 与摘要。
- `research/generic_paper.py`：把冻结协议、逐方法统计和失败案例整理成 Markdown/LaTeX 论文草稿；所有数字来自结果文件。
- `research/discovery.py`：接受 `adaptive-qa-v1` 这个注册适配器，并把它转成交接 artifact；未知适配器仍然拒绝执行。

## 数据流

1. 文献阶段产出问题、假设、反驳条件和实验方案。
2. 校验器检查来源、数据划分、方法白名单、调用上限和停止规则。
3. 数据集以固定 seed 生成并写入 manifest；测试集不由模型调参。
4. runner 对 `single_pass`、`fixed_two_passages`、`adaptive_stop` 做配对比较。`adaptive_stop` 只按可审计的证据覆盖规则停止，不执行模型生成代码。
5. 每个回答必须绑定任务、方法、上下文 hash 和 Gateway call ID；缺 usage 或 ledger 不一致时停止。
6. 论文生成器重新从结果文件计算准确率、平均上下文长度、token 消耗和失败任务，并明确 synthetic 数据与未验证创新的限制。

## 安全与失败处理

- 不接受计划中的 shell 命令、任意路径或任意 Python 入口；只能调用注册适配器。
- 预算采用 `ModelGateway` 的保守预留，未知花费 fail-closed。
- 结果文件、数据集、代码和计划都写入 hash；修改后必须重新运行。
- 模型输出不是 JSON 或答案字段不在任务范围内时，记录为失败，不静默修复。

## 验证标准

- 单元测试覆盖：适配器白名单、数据可复现、上下文停止规则、答案评分、计划绑定和异常停止。
- 使用离线 invoke stub 完成小规模确定性测试。
- 使用 DeepSeek 配置运行一个 12 任务、3 方法的真实小实验，生成 `results.jsonl`、`summary.json` 和论文草稿；不自动上传外部评审。
