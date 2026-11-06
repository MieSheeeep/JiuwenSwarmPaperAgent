# 绘图 Skill 与版本化写作

2026-11-06 已实现中文“写作与绘图”和“错误分析”页面。工作台继续使用真实实验数据，论文正文、图表标签及导出材料保持英文。

## Skill 如何接入

`workbench/figure_skills.py` 提供明确注册的本地执行器。已读取 scientific-visualization 与 matplotlib Skill 的出版规范，将色觉友好配色、英文标签、固定印刷宽度、最小字号、显式样本数、矢量导出和数据来源记录写入执行代码。工作台不会把任意 SKILL.md 当成可执行程序，也不执行用户输入的 shell 命令。

| 能力 | 实际状态 | 产物 |
|---|---|---|
| scientific-visualization | 本地 Matplotlib 执行，无模型调用 | 真实主条件准确率及每任务 provider token，PDF/SVG/PNG |
| architecture-vector | 本地矢量架构图，描述实际源码阶段 | PDF/SVG/PNG 与可编辑 architecture.json |
| scientific-schematics | 可选外部图像模型能力，当前未配置、未调用 | 尚无 AI 生图产物 |

scientific-schematics 原 Skill 使用图像生成与图像评审模型，需要额外 provider 配置；DeepSeek 文本接口不能直接替代。当前不会自动索取密钥、安装服务或产生这类费用。实验曲线由数据程序生成，不用图像模型绘制数字结果。

每次构建保存 figure_manifest.json：Skill ID、风格、规则、目标宽度、源数据 SHA256 与文件哈希。支持 Color 与 Grayscale；仅显示已观测点估计，不生成未经实验支持的误差条或显著性标记。图中的 Full history 显式标为无上限参照。

## 写作与构建

编辑器接受六个英文纯文本章节，支持已登记引用键，例如 [temporal]、[longmemeval]。LaTeX 命令被转义，生成源文件可预览与下载，不能从网页执行任意 TeX。测量表格、冻结协议和参考文献沿用已保存模板；新增文字主张仍需审查。

每次保存创建独立修订，记录父版本、正文差异、原稿与证据哈希。构建任务在修订下另建独立目录，不覆盖原始送评论文。PDF 明确标记 UNREVIEWED WORKBENCH REVISION，原外部评分不移植。图表生成和两次 pdflatex 编译在后台执行，使用固定参数、禁用 shell escape 与自动依赖安装，编译有累计超时。日志和失败保留，新 PDF 仅在成功后可下载。

仅本机服务提供 JSON 写接口，要求本地来源、JSON 内容类型、请求大小限制和每次服务实例生成的写 token。此 token 是本地请求防护，不是模型凭证。修订保存使用最新版本检查，防止两个页面静默覆盖。磁盘错误会释放任务锁；轮询短暂失败会继续重试；未保存正文离开页面会提示。

新修订目录：output/workbench/{run_id}/revisions/{revision_id}/；构建目录位于其 jobs/ 下。服务重启后旧的未完成任务显示 interrupted，可新建任务重试，不假装成功。

## 错误分析与下一轮

新增 research/error_analysis.py，只读取原始数据、保存得分与结果，不导入模型 gateway，不执行推理。主条件 Full history 的五个错误发生于完整证据条件，其中四个为冲突、一例历史查询；Recent 主条件错误均伴随源证据不完整。这是描述性分类，不是因果证明。失败、缺失与无效评分单独报告。

后续提出语义/混合检索、冲突感知回答、当前原子组装包与替代分配规则的比较。计划与真实测量明确分开。LongMemEval 候选基准信息来自 [官方仓库](https://github.com/xiaowu0162/LongMemEval)，尚未运行其评测。完整本轮记录见 error_analysis_followup_20261106.md。
