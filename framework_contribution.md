# JiuwenSwarm 项目适配与交付说明

更新日期：2026-11-08。本文件统一课程报告、使用说明书、讲稿和PPT中的框架相关表述。

## 工作定位

基于现有 openJiuwen `AgentRail` 接口，在本地 JiuwenSwarm 源码目录中添加适配组件，用于本项目的受控研究任务。开发借助大模型与开发工具辅助完成；团队工作包括需求设置、集成运行、实验组织、结果复核和材料整理。不将工具辅助生成的代码等同于独立提出框架级创新，也不以自我评价代替源码和运行证据。

基准源码提交为 `f0a69728c96b5961d993449f1a901cbd2f4dac5b`。补丁为 `output/framework_contribution.patch`，涉及8个文件，包括实现、包导出和文档，不是8项独立创新。2026-11-08执行补丁反向应用检查通过，说明补丁与当前工作树对应；该检查不等于在所有版本上均可应用。

## 实际功能与边界

| 组件 | 已有实现 | 未验证或不提供的能力 |
| --- | --- | --- |
| ContextBudgetRail | 在 `before_invoke` 中按给定策略和计数器选择历史证据，注入当前查询；响应后保存实际消息和用量 | 不裁剪所有持久化工具历史；证据预算不等于完整请求或总费用上限；摘要输出仍需单独检查 |
| FrozenMessagesRail | 检查准备好的消息与实际传输的一致性，限制单次模型调用，保存响应 | 不是不可篡改存储，不保证消除全部状态污染；并非任意第三方Agent均已兼容 |
| VersionedMemoryRail | 根据 `valid_at`、`observed_at`、删除和冲突规则选择结构化记录，注入查询 | 不是递增版本号、并发事务控制或快照回退，也未证明适用于任意长期记忆任务 |

运行器直接加载新增源码，再在 openJiuwen ReActAgent 上注册。已验证范围是这些模块及相关SDK契约，不是完整JiuwenSwarm桌面或Swarm装配。源码路径为 `upstream/jiuwenswarm/agents/harness/common/`。

## 当前测试口径

2026-11-08重新执行的三组离线检查：

| 文件 | 数量 | 范围 | 结果 |
| --- | ---: | --- | --- |
| tests/test_versioned_memory.py | 13 | 双时间筛选、冲突与删除记录、预算和Rail行为 | 通过 |
| tests/test_agent_invocation.py | 8 | 消息契约、异常恢复、单次调用和响应记录；实际SDK配替身传输 | 通过 |
| tests/test_baseline.py | 8 | 历史选择、预算、项目ID匹配及部分基线辅助逻辑 | 通过 |

三组共29项，不能全部称为“Rail专用测试”。其中记忆与消息/调用两组共21项，另8项属于上下文及基线。原研究轮次记录的45项核心测试是另一选择范围，不与29项相加成全量测试数。旧稿“19项专用测试”不再沿用。通过数不等于分支覆盖率、全面边界覆盖、生产可靠性或通用性证明；离线检查不等于重跑全部科研实验。耗时随环境变化，不作为固定性能承诺。

复核命令（仓库根目录，不调用付费模型）：

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -p test_versioned_memory.py
.venv/Scripts/python.exe -m unittest discover -s tests -p test_agent_invocation.py
.venv/Scripts/python.exe -m unittest discover -s tests -p test_baseline.py
```

## 交付与官方状态

交付内容是本地适配源码、说明、patch和相关测试。尚未向官方仓库提交上游PR，未获官方接受或合并。不得写作“框架底层重构”“通用框架创新”“任意Agent无感适用”或“已被社区采用”。赛题允许提交代码、Skill、说明文档和补丁等材料，但这些材料是否构成有效贡献及最终得分，由评审认定。

答辩统一表述：我们基于现有Rail接口做了服务于本项目的适配，整理了源码、文档、补丁和相关离线检查；目前没有上游PR，也没有验证通用性。
