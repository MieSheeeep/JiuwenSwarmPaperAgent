# 自动科研系统代码拆解与复用决策

日期：2026-10-11。完成范围：两个作者仓库的核心源码静态阅读、依赖与模型入口检查。未安装其依赖，未执行其科研工作流，未调用付费模型；下述异常为代码观察，不是运行测试结论。

## 固定版本与本地状态

| 项目 | 固定 commit | 本地状态 | 许可核查 |
|---|---|---|---|
| [Agent Laboratory](https://github.com/SamuelSchmidgall/AgentLaboratory/tree/d9017d90e329112d2a80b7712f37ee9094d2cd27) | d9017d90e329112d2a80b7712f37ee9094d2cd27 | 完整浅克隆，sources/reference_repos/AgentLaboratory | 根 LICENSE 为 MIT；复制代码时保留版权和许可。papersolver.py 注明部分写作提示源于 AI Scientist，复制该部分前另外追溯许可 |
| [AI-Researcher](https://github.com/HKUDS/AI-Researcher/tree/f9a6f8480860c193afff600eeffe3defcee8a978) | f9a6f8480860c193afff600eeffe3defcee8a978 | Git 对象已下载，完整签出因模板名含冒号而失败；已从 HEAD 恢复核心 Python、研究脚本和配置 | setup.cfg 声明 MIT，但该版本 Git 文件树未找到 LICENSE/COPYING；先借鉴设计，直接复制源码前补齐许可核查 |

引用快照已在根 .gitignore 排除，不应进入我们的代码提交或比赛提交包。未读取、使用仓库自带凭据，也未将其复制进我们的配置。

## Agent Laboratory：可拆开的阶段状态机

| 代码位置 | 实际机制 | 我们的处理 |
|---|---|---|
| ai_lab_repo.py:60–82 | 文献→计划→数据准备→实验→解释→写作→修订；阶段状态、耗时与步骤数 | 借鉴阶段与失败回退；状态改成可校验 JSON，加入明确的输入版本和产物引用 |
| ai_lab_repo.py:106–126 | pickle 保存整个工作流；向多个角色同步属性 | 借鉴存档需求；我们的模块通过显式文件契约交接，避免共享可变属性与整对象存档 |
| ai_lab_repo.py:207、251 | 评审可回到规划；PaperSolver 接收 plan、exp_code、exp_results、insights、lit_review | 借鉴实验到写作的证据交接，但数据结果应是结构化且经过统计校验的产物 |
| papersolver.py:269、330 | 多候选逐步编辑；先 scaffold 再逐节生成；各节检索相关文献；以模型评分选稿 | 借鉴章节级修订；选稿先通过数字、引用与编译检查，模型评价只辅助表达修订 |
| mlesolver.py:141、276 | 模型对计划、代码和输出评分，然后筛选代码候选 | 不作为实验成败判据；方法选择依据固定开发集指标，最终结论依据留出评测 |
| tools.py:306 | 子进程执行生成代码，默认超时 600 秒 | 只借鉴超时与输出收集；首版运行固定实验入口，不直接接入任意代码执行 |
| inference.py:128–149 | DeepSeek 分支及请求模型写死 deepseek-chat | 不直接复用；接入我们现有 openJiuwen 模型配置，实际模型名以私有配置为准 |

移植障碍：requirements.txt 锁定约百余依赖，包含 torch、transformers、diffusers、旧 openai/pydantic 等；不整体安装到当前环境。papersolver 的 while 循环有“直到生成成功”条件，外层步数并不保证内层总调用有上限。report_writing 还引用 research_topic/compile_pdf 等全局名称，不能视为独立可插拔函数。上述判断均可从固定版本源码核对。

## AI-Researcher：研究和论文通过目录交接

| 代码位置 | 实际机制 | 我们的处理 |
|---|---|---|
| research_agent/run_infer_plan.py:102–113 | Prepare、Survey、Plan、ML、Judge、Experiment Analyzer 角色组成工作流 | 借鉴职责分离，映射为六模块；不用每个模块都再建多个聊天角色 |
| research_agent/run_infer_plan.py:113 以后 | 输入 ideas/references/benchmark；共享 context_variables；搜索参考仓库、下载论文、规划与实验 | 保存参考文献及方法来源，但去掉“至少选择五个仓库”和固定 GPU 两轮训练等领域预设 |
| research_agent/inno/agents/inno_agent/exp_analyser.py:20–42 | experiment_report 中追加 analysis_report 与 further_plan 字典 | 借鉴分析→追加实验交接；进一步记录证据缺口、实验优先级、预算和验证条件 |
| research_agent/inno/workflow/flowcache.py:10–123 | Agent/Tool 模块保存 messages、context_variables 或工具输入输出；缓存命中需要交互选择 | 借鉴断点存档；缓存键加入输入、数据、代码、模型和提示词版本，恢复执行不弹终端菜单 |
| paper_agent/writing.py:10–25 | 方法→相关工作→实验→引言→结论→摘要，随后修复引用并编译 ICLR 2025 文件 | 推荐这个写作依赖顺序；采用我们的提交模板，不硬编码 ICLR 2025 |
| paper_agent/section_composer.py:28–110 | 每节公共 Composer：大纲、结构/子节检查点、临时日志、随机写作模板 | 借鉴分节接口和检查点；模板选择固定并记录，缓存随输入变更失效 |
| paper_agent/experiments_composing.py:268–310、379 以后 | 从 project 代码和 Agent 缓存提取实验信息；固定四个 refine 缓存文件；用目录列表最后一个 cache | 改为显式 EvidenceBundle；不能默认“最后一个目录”就是当前有效实验 |
| benchmark_collection/utils/openai_utils.py:21–59 | GPTClient 使用 OpenAI 异步兼容客户端；环境变量设置 endpoint；多数 Composer 默认 GPT 模型 | 研究侧与写作侧是不同模型入口，都需要统一适配；只改 research 的环境模型名不够 |

移植障碍：默认研究入口依赖 Docker、浏览器与 Bash；setup.cfg 包含 LiteLLM、BrowserGym、Playwright、Docling、语音/视频与嵌入模型等广泛依赖。当前 Windows/Python 3.12/openJiuwen 环境不能据此声称已兼容。

值得直接修正的源码观察：experiments_composing.py 读到 structure checkpoint 后执行 exit()；GPTClient 接受 max_tokens 但实际请求对应参数被注释；只返回文本而未携带 provider usage；传入显式 api_key 时 api_url 只在另一分支赋值。研究 core.py 的 run/run_async 默认 max_turns 为无限，async 重试最多六次且等待可达 1200 秒。这些说明我们的全局预算、重试上限和恢复机制应独立实现。

## 最终复用清单

| 机制 | 决定 | 首版落地位置（拟） |
|---|---|---|
| 阶段推进和回退 | 借鉴 Agent Laboratory，自研受限状态机 | research/orchestrator.py |
| 分节写作、方法与结果先行 | 借鉴 AI-Researcher，自研 Composer | research/writer.py |
| 结果分析→追加实验 | 借鉴 AI-Researcher，自研结构化决策 | research/reviewer.py |
| 真实模型调用、usage、断点实验记录 | 保留现有 baseline/runtime.py、run.py 机制并抽取公共层 | research/model_gateway.py、runner.py |
| 表格和图由统计脚本产生 | 保留 baseline/analyze.py、paper.py 原则 | research/evidence.py |
| pickle、无限循环、模型自评分选最优实验、随机模板 | 不移植；替换成版本化数据、有限次数与固定指标 | contracts.py、预算管理和检查器 |
| 整套自主改代码/浏览器/GPU实验框架 | 暂不接入 | 后续确有实验需求再做隔离与适配 |

这次复用以设计机制为主，尚未将第三方源码移植进我们的运行系统。新架构与输入输出见 [框架设计](../docs/research_system_v2_design.md)。原有 baseline 保留作为回归参照。
