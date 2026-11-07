# JiuwenSwarmPaperAgent

统一科研框架入口为 research.workflow，包含阶段调度、工具注册、实验插件接口、审查退回、暂停与恢复。整体结构和使用说明见 [科研框架](docs/research_framework.md)。初始化与状态查看均离线；真实模型和实验只在显式安装执行器并触发后运行。

ConnectedProfile 已接入文献、问题、方案、插件检查、dev/test 执行、结果复算、写作、审查和 ICLR 导出。工作台新增“科研流程”页；具体配置见 config.workflow.example.json 与 docs/qa_dataset.example.json。启动真实运行必须显式使用 run --enable-model，本轮实现仅做离线集成验证。

已接入 Open Research Skills 的科研流程、会议论文写作和冷审查规范：阶段调用读取固定版本原文，写作接收真实数字与证据清单，评审采用五个独立上下文和一次逐条裁决，并实际执行保存答案的离线复算。安装、来源、消耗和验证边界见 [技能接入说明](docs/open_research_skills_integration.md)。

接入后已用 Flash 生成并修订一份 7 页、4008 词新稿，复用原冻结实验，最终内审待完成。本轮有操作者源码核对和事实修正；实际消耗、审查误判及干预记录见 [Flash 生成记录](docs/framework_skills_flash_run_20261107.md)。

现支持自动准备公开 QA 数据、提出并生成文档选择函数、用受限解释器检查和执行、逐页生成论文预览、按目录约定打包代码/数据/报告，以及绑定与 PDF 哈希对应的外部评审回执。视觉审阅和真实外部评审仍需实际完成，不会被编译成功或离线检查替代。

新增“文献 → 问题 → 实验方案 → 注册实验 → 论文草稿”流程：仓库 Skill 指导真实文献阅读、问题提出及方案设计；注册适配器负责冻结数据、执行可审计的小实验并把结果交给写作阶段。结果可在工作台“文献与选题”查看。运行与边界见 [流程说明](docs/literature_to_plan.md) 和 [通用科研闭环记录](docs/generic_research_run_20261106.md)。当前新增适配器是与旧记忆课题不同的 synthetic 多跳问答案例，不代表任意学科自主科研。

当前代码也包括记忆优化、公开基准适配、语义/混合检索、可追溯写作和中文工作台；下文“初版结果”仅保留历史 baseline。最新全面实验记录见 [全面升级交付](docs/research_upgrade_release_20261106.md)。原始运行账本、私有外部评审和本地生成目录默认不上传，公开代码可重新运行；框架补丁已涵盖现有全部八个扩展文件。

当前全面升级入口见 [2026-11-06 研究说明](docs/research_upgrade_20261106.md)：双模型、新种子、语义/混合检索、冲突核验、装包消融及外部基准。实际进度以 `output/review_upgrade_20261106/run_state.json` 为准；工作台的“研究升级”页独立展示本轮结果。下文早期小规模实验描述为历史记录。

本轮全部回答条件已完成，英文稿、资源与交付状态见 [全面升级交付记录](docs/research_upgrade_release_20261106.md)。

## 本地科研工作台

新增中文工作台，可查看真实实验、逐条回答与证据、错误分析、英文论文及资源；支持英文正文修订、版本差异、绘图 Skill 和本地 LaTeX 编译。启动 `.\scripts\start_workbench.ps1` 后访问 <http://127.0.0.1:8765>。这些本地操作不产生模型 API 消耗，原始送评论文保持不变；完整说明见 [frontend/README.md](frontend/README.md)。论文及学术文件保持英文。

基于openJiuwen / JiuwenSwarm的科研论文自动生成项目。当前已完成上下文选择的初版实验与论文，下一阶段研究记忆更新、检索和科研流程自动化。

当前版本是可复现的小规模试验，不代表完整自主科研系统或公开记忆评测成绩。已有论文为24个合成任务、4种策略、96次作答的结果，限制见论文及实验说明。

## 项目结构

| 位置 | 内容 |
|---|---|
| baseline/ | 数据生成、真实模型调用、实验、统计、论文生成 |
| tests/ | 上下文选择、答案评分和响应日志测试 |
| upstream/ | 固定版本的官方JiuwenSwarm源码子模块 |
| output/framework_contribution.patch | 对官方源码的三处扩展修改 |
| output/baseline/ | 初版数据、调用日志、结果及图表 |
| output/paper/ | 已审阅论文、原始模型初稿、ICLR模板和PDF |
| docs/ | 架构、模块调用、创新点及初版设计记录 |
| sources/ | 下一阶段论文清单和阅读笔记 |
| config.example.yaml | 不含密钥的模型配置样例 |

提交ZIP、评审Token、私人配置和本地环境保留在开发者机器上，不进入Git。

## 拉取与准备

需要Git与Python 3.12。首次克隆后应用官方源码扩展：

```powershell
git clone git@github.com:MieSheeeep/JiuwenSwarmPaperAgent.git
cd JiuwenSwarmPaperAgent
python scripts/prepare_upstream.py
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-baseline.txt
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

官方源码基于提交f0a69728c96b5961d993449f1a901cbd2f4dac5b。准备脚本会初始化子模块并应用补丁；已应用则保留现状，冲突则退出，不执行reset或clean。安装的jiuwenswarm依赖版本与官方源码快照不同，实验直接加载新增源码模块，并在openJiuwen ReActAgent上注册。

## 私人模型配置

```powershell
New-Item -ItemType Directory -Force config.local
Copy-Item config.example.yaml config.local/config.yaml
```

在本机环境变量中设置API_KEY；不要把真实值写进代码、Git或聊天。模型名称和服务地址可在私人config.yaml里调整。脚本也可读取自己的用户目录 ~/.jiuwenswarm/config；通过 --config-dir 或 BASELINE_CONFIG_DIR 指定私人配置目录。

## 重算已有结果（不调用API）

```powershell
.venv\Scripts\python.exe -m baseline.analyze --output output/baseline
```

## 运行新实验（产生API消耗）

```powershell
.venv\Scripts\python.exe -m baseline.run --tasks 24 --output output/my-run --concurrency 2 --config-dir config.local
.venv\Scripts\python.exe -m baseline.analyze --output output/my-run
.venv\Scripts\python.exe -m baseline.paper --results output/my-run --output output/my-paper --config-dir config.local
```

不要覆盖初版证据目录。运行器跳过已有任务/策略结果并检查参数一致性；失败记录保留，调用不自动重试。成功返回的响应在模型钩子中立即保存。中断后复跑会包含此前已保存调用的消耗，分析会检查调用与结果关联。

PDF需要本地pdflatex。将output/paper/iclr2026_conference.sty复制到新论文目录，进入该目录编译paper.tex两次。现有paper.pdf可直接阅读。若model_sections.json存在，写作脚本不会重新调用模型；reviewed_sections.json存在时使用已修订文字。

## 初版结果

| 策略 | 正确率 | 实验API总Token |
|---|---:|---:|
| 全部历史 | 24/24 | 74,665 |
| 最近窗口 | 6/24 | 15,283 |
| 项目编号检索 | 24/24 | 4,212 |
| 检索加摘要 | 24/24 | 7,608 |

问题显式包含项目编号，因此有利于精确检索；完整历史不限制长度，其余方法按cl100k_base代理Token计数限制历史预算。摘要调用纳入API消耗。一次模型、一次采样、没有真实多轮工具执行，不据此宣称新方法、泛化能力或统计等价。

合作方式见CONTRIBUTING.md；实际实验统计见output/baseline/RESULTS.md，资源汇总见resource_report.md。下一阶段阅读清单见sources/agent_memory_reading_plan.md。
