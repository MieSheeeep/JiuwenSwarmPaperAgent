# 通用科研闭环小实验记录（2026-11-06）

这次运行验证的是新增的 `adaptive-qa-v1` 注册适配器，不是之前的 bitemporal memory 课题。它把一个简单问题固定成可复现实验：多跳问答需要两段证据时，逐条增加证据直到覆盖全部跳数，是否能达到固定取两段的效果。

## 运行结果

- 运行目录：`output/generic_qa_run_20261106_v2/`
- 12 个固定 seed 任务，3 种方法，共 36 次 DeepSeek 调用。
- 账本：36 次调用，已知 3,348 provider tokens，无 unknown spend。
- manifest SHA-256：`536a7bbcbfc20799b6879430a52cab84b7f36d2f6bac394f111ef9d0addd8061`

| 方法 | 准确率 | 证据覆盖率 | 平均段数 | provider tokens |
|---|---:|---:|---:|---:|
| single_pass | 0.00 | 0.50 | 1.00 | 900 |
| fixed_two_passages | 1.00 | 1.00 | 2.00 | 1,224 |
| adaptive_stop | 1.00 | 1.00 | 2.00 | 1,224 |

论文草稿和 PDF 在 `output/generic_qa_run_20261106_v2/paper/`。这个结果只说明注册的 synthetic 适配器在这 12 个任务上跑通；它不证明新颖性、不代表跨主题泛化，也不是 Stanford/专家评审分数。

## 如何复现

```powershell
.venv\Scripts\python.exe -m research.generic_runner `
  --output output/generic_qa_run_20261106_v2 `
  --max-total-tokens 20000 --max-calls 36
.venv\Scripts\python.exe -c "from research.generic_paper import write_paper; write_paper('output/generic_qa_run_20261106_v2','output/generic_qa_run_20261106_v2/paper')"
```

运行器只允许注册适配器，不执行计划中提供的 shell/Python 命令；模型输出、上下文 hash、调用 ID 和 token 都保存在账本中。旧的失败目录仍保留在本机作为 fail-closed 记录，未纳入提交包。
