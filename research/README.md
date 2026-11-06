# 可追溯的实验—证据—论文链条

2026-10-16 已新增真实记忆研究流程，入口见 [RELEASE_README.md](RELEASE_README.md)；下文只说明 `import-baseline` 历史导入路径，该路径保持离线。新 `orchestrator` 路径会调用已配置模型并执行预算计账。

已实现第二版的第一个里程碑：历史实验导入、独立复算、产物谱系、确定性报告、机械检查、失败记录和缓存恢复。全部使用 Python 标准库及原有 baseline.dataset 评分函数，运行时不读取 API Key、不导入模型 SDK、不调用模型。

从项目根目录运行：

```powershell
.venv/Scripts/python -m research import-baseline --source output/baseline --output output/research_v2
```

首次生成后，再执行相同命令会返回 resumed=true。缓存指纹包含原始文件和本地实现版本；每个输出文件都重新核对哈希。改变输入、实现、JSON 产物或 Markdown 会导致重建。输出目录必须与输入目录分开且互不嵌套；导入不会改写原始结果。

| 文件 | 内容 |
|---|---|
| run.json | 原始文件哈希、数据集逻辑文本哈希、模型/配置、每个结果关联的调用 ID；历史代码版本未知则明确记录 |
| evidence.json | 从原始回答重新评分的各方法指标、调用用量、适用范围和局限；指向 run |
| manuscript.json | 确定性报告章节，每个测量陈述的 claim_id、指标值、范围与证据链接 |
| paper.md | 由已校验 claim 程序生成的报告和表格；这不是优化后的新论文 |
| review.json | 机械检查结果及检查边界；Stanford 和论文评测 Agent 的新评分均为空 |
| resources.json | 历史实验调用与 token、各方法分项、新链条零模型调用及本地耗时；货币成本未知 |
| scorecard.json | 用户给出的 60/15/10/15 评分项、本里程碑支撑项和剩余工作；不猜测成绩 |
| state.json | running/succeeded/failed、输入指纹和所有输出哈希 |

只有 state.json 的 status=succeeded 且本次 CLI 校验成功后，才能使用该目录的报告。失败时旧文件可能保留作诊断，不能将其当作新运行成功输出。

## 检查内容与限制

导入检查数据集摘要、任务 ID、每个 task/policy 的完整性、保存得分与重算得分、回答与真实记录响应的一致性、调用 ID 唯一性、调用顺序/归属、模型名和 provider 用量。缺失用量不是零成本。此里程碑要求完整成功的历史实验；失败/未完成实验会阻止发布报告，后续 runner 再支持失败样本与重试账单。

旧 Windows baseline 的 manifest 哈希使用写入前 LF 文本，实际文件可能为 CRLF。导入器同时核对该逻辑文本哈希、另记录未经转换的文件 SHA256，不能把两者混为一谈。

机械评审目前只认证确定性模板与登记的测量陈述。不认证自由生成的科学论证、文献真实性、原创性，也不等同 Stanford Agentic Reviewer。任意改写的正文会被标记为需另行审查。文件哈希防止无意改动，不能证明原始调用真实性，也不是数字签名。

resources.json 统计这批历史实验的回答和摘要调用，明确排除历史写稿/冒烟测试；不能直接作为完整比赛资源总账。SDK 中为零的 cost 字段不视为免费。后续 live gateway 需要把规划、写作、评审、失败重试一起计账。

新包属于科研工具层，不能冒充新的 openJiuwen/JiuwenSwarm 框架贡献。现有 context-budget Rail patch 单独保留，后续记忆机制需形成独立框架改动、测试、说明和 patch/PR。

## 测试

```powershell
.venv/Scripts/python -m unittest discover -s tests -p test_research_chain.py -v
```

测试覆盖原始数据篡改、得分伪造、调用错配、缺失用量、产物篡改、无登记正文、缓存变更和失败状态。全量回归运行 `python -m unittest discover -s tests -v`；旧 tokenizer 测试需已有 cl100k_base 缓存或能够下载该文件。新包单独运行不需要 tokenizer。
