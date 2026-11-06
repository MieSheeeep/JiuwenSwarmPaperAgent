# 优化版运行入口

执行完整有限流程：

```powershell
python -m research.orchestrator --run-dir output/new_memory_run --paper-dir output/new_memory_paper --max-total-tokens 300000
```

默认通过现有 JiuwenSwarm 私有配置接入模型；可追加 `--config-dir`。请勿向聊天、源码或提交包写入 API Key。

离线复算随包结果：

```powershell
python -c "from research.memory_analysis import analyze_memory; print(analyze_memory('output/memory_live_20261016')['evaluation_complete'])"
```

主模块：memory_run（协议/实际 Rail 调用）、model_gateway（预留/计账/恢复）、memory_dataset（独立参考答案）、memory_analysis（复算）、memory_paper（证据/写稿/源码事实校正）、orchestrator（有限流程）。历史 baseline 导入仍使用 `python -m research import-baseline`。

框架源文件在 `upstream/jiuwenswarm/agents/harness/common/`。它们是 opt-in 扩展，运行器按文件加载，不改用户安装目录。源码贡献 patch 单独提供，尚未提交上游 PR。

结果与方法边界见 docs/memory_release_20261016.md。当前新稿是受控结构化记忆实验，不是通用记忆系统或真实对话基准；外部评审状态另见 Agentic Reviewer/status.md。
