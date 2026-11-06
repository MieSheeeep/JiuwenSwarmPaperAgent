# 科研 Agent 整体框架

统一入口为 research.workflow。框架负责项目调度、阶段交接、状态恢复和审查循环；具体课题通过实验插件接入。创建项目和查看状态不调用模型。

## 流程

~~~mermaid
flowchart TD
    A[用户：方向与约束] --> B[选题]
    B --> C[搜索与阅读文献]
    C --> D[提出问题与假设]
    D --> E[设计实验并冻结协议]
    E --> F[实现方法与检查接口]
    F --> G[小规模验证]
    G --> H[正式实验]
    H --> I[结果分析与证据]
    I --> J[提纲与论文写作]
    J --> K[审查]
    K -->|通过| L[编译、检查、导出]
    K -->|修改方法| E
    K -->|修改实现| F
    K -->|修改分析| I
    K -->|修改论文| J
    M[调度器：状态、预算、产物、暂停、恢复] --- C
    M --- H
    M --- K
~~~

## 分层

| 层 | 文件 | 责任 |
|---|---|---|
| 调度 | research/workflow/engine.py | 顺序、产物哈希、依赖、预算累计、暂停、审查退回 |
| 能力注册 | research/workflow/registry.py | 安装阶段执行器和具体工具 |
| Agent | research/workflow/agents.py | 各阶段角色、模型—工具循环、openJiuwen 后端 |
| 工具服务 | research/workflow/services.py | 文献搜索阅读、项目文件、实验插件接口、论文编译 |
| 项目入口 | research/workflow/__main__.py | 创建项目、查看状态、导入人工产物、失效重做 |
| 模型基础设施 | 现有 model_gateway.py、agent_invocation.py | 真实用量、调用账本、ReActAgent 和 JiuwenSwarm Rail |

所有阶段执行器都接收 Context，包含前序产物、审查反馈、剩余预算、项目目录、工具表；返回 StageResult，包含 payload 和实际 usage。具体数据集或算法不属于调度器。

## 阶段输出约定

| 阶段 | 必须交付 |
|---|---|
| topic | 方向、约束 |
| literature | 有 ID、URL、阅读范围的来源，以及方法比较和局限 |
| question | 问题、假设、真实来源 ID、反驳条件 |
| design | 数据、划分、方法、指标、预算、验收条件 |
| implementation | adapter、版本、能力 |
| pilot | 是否通过、诊断 |
| experiment | 原始结果、冻结设计哈希、资源 |
| analysis | 指标、论断、局限 |
| writing | 标题、章节、当前分析哈希、参考文献 |
| review | accept/revise/stop、具体问题、退回位置 |
| export | 文件及哈希、明确通过的检查项 |

试运行未通过时禁止正式实验。实验必须绑定设计哈希；论文必须绑定分析哈希。审查最多退回两轮。已完成步骤恢复时不重复执行。

## 模型怎样调用工具

AgentExecutor 为每个阶段加载对应角色说明。模型可返回三种 JSON 动作：tool 调用注册工具、final 提交阶段产物、blocked 说明缺少能力。工具输出返回上下文，再由模型决定下一步。每阶段最多八轮，只允许调用该阶段工具名单。

JiuwenBackend 延迟读取本地配置，实际调用沿用 openJiuwen ReActAgent、JiuwenSwarm FrozenMessagesRail 和持久 ModelGateway。框架初始化不会调用它。

standard_registry 提供文献搜索与阅读、项目文件读写、实验插件调用和论文编译。实验插件统一实现 prepare、pilot、run、analyze；领域算法、数据和环境由插件负责。缺少插件时明确停止。框架没有把“模型说已经实验”当成实际实验。

## 状态与恢复

成功阶段创建独立 JSON 文件，下游记录前序哈希。修改前序输入时 invalidate 该阶段及其下游，旧文件仍保留。产物被篡改、执行器缺失、工具报错、用量未知时停止。

执行前独占创建 active.json，防止两个 runner 同时启动同一阶段。异常保留标记；重启后必须核对底层账本，再通过 reconcile 明确记录用量与说明。pause 在阶段边界生效；已提交供应商的请求不能保证取消。工具若自行调用模型，必须通过同一预算服务并返回资源，不能隐藏开销。

## 离线使用

~~~powershell
.venv\Scripts\python.exe -m research.workflow --project output/framework_project init --topic "研究方向"
.venv\Scripts\python.exe -m research.workflow --project output/framework_project status
.venv\Scripts\python.exe -m research.workflow --project output/framework_project schema
.venv\Scripts\python.exe -m research.workflow --project output/framework_project import --stage literature --file sources.json
.venv\Scripts\python.exe -m research.workflow --project output/framework_project pause
.venv\Scripts\python.exe -m research.workflow --project output/framework_project resume
~~~

advance 命令不加载模型，只检查当前是否有可执行阶段；未安装执行器时报告 needs_input。

## 程序接入

~~~python
from research.workflow import Workflow
from research.workflow.agents import JiuwenBackend
from research.workflow.services import standard_registry

project = Workflow("output/framework_project")
# adapter 实现 ExperimentAdapter 接口；这里显式安装部署能力。
registry = standard_registry(project.directory, model=JiuwenBackend(),
                             adapters={"my_experiment": adapter})
# 真正执行需要由调用者显式触发；本次没有启动。
# await project.run(registry)
~~~

每个阶段也可使用确定性 Python handler，或人工导入结果，不强迫所有步骤都使用模型。实验插件可以替换成记忆课题、问答课题或其他研究方向。

## 已接通的执行配置

ConnectedProfile 已绑定全部十一阶段。选题由用户提供；文献阶段真实调用 arXiv 服务和阅读器；问题阶段调用模型；设计阶段按注册插件冻结数据和方法；实现阶段检查插件接口与数据；试运行和正式实验分别使用 dev/test；分析阶段从保存的回答重新评分；写作分为提纲和正文；审查可以退回；导出阶段编译 ICLR PDF，并插入代码计算的结果表。

本地 JSON 问答插件 json-qa-v1 接收独立 dev/test 任务，比较 fixed_top2、fixed_all、adaptive_top2_to4。选择器只接收问题和文档，答案标注只在评分阶段读取。数据格式见 qa_dataset.example.json，配置见仓库根目录 config.workflow.example.json。这些文件只是格式示例，不能作为科研结果。

初始化项目时指定 constraints 文件：

~~~powershell
.venv\Scripts\python.exe -m research.workflow --project output/framework_myproject init --topic "你的研究方向" --constraints config.workflow.example.json
~~~

运行命令已实现，必须显式传 --enable-model 才会调用已配置模型：

~~~powershell
.venv\Scripts\python.exe -m research.workflow --project output/framework_myproject run --enable-model --until review
~~~

本次实现没有执行该命令。工作台新增“科研流程”页面和只读 /api/workflows 接口，展示各阶段、预算、修订和中断状态；网页刷新不会启动模型。

## 交付与边界

已实现可运行调度器、各阶段接口、模型工具循环、标准工具服务、离线 CLI 和暂停恢复。离线 fixture 验证了整条控制流、审查退回、产物篡改拦截和中断核账；fixture 不计作真实科研结果。

框架已有可调用的阶段服务和一个真实问答实验插件，不再只是空执行器。对任意新学科或全新算法仍需要新的插件实现；当前不提供任意模型代码的自动部署。论文编译器会输出 visual_inspection=required，不能把编译成功当成视觉审阅完成；外部评审 token 需要与最终 PDF 对应。本次只通过注入离线模型、文献服务和编译替身检查整条真实 handler 链，未启动模型或真实实验。
