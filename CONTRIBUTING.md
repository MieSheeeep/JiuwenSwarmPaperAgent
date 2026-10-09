# 协作说明

在自己的分支修改代码或文档，通过Pull Request合并到main。建议按工作命名分支，例如feature/memory-update或docs/research-notes。

第一次拉取请运行scripts/prepare_upstream.py，它会初始化官方源码子模块并应用本项目补丁。官方仓库版本固定在子模块记录的提交；本地upstream出现修改是应用补丁后的正常现象。

我们对官方源码的修改保存在output/framework_contribution.patch中，不依赖未推送的子模块提交。继续改官方源码时，先确认upstream没有无关修改，只暂存希望发布的文件，再用git diff --cached导出更新后的补丁。不要在这个主仓库中执行git add .来代替子模块内部的暂存，也不要推送官方origin。

提交前执行：

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
git diff --check
git diff --cached --check
```

模型配置放在config.local/中，或使用自己的JiuwenSwarm用户配置；复制config.example.yaml为config.local/config.yaml，再通过环境变量提供API_KEY。不要提交密钥、评审Access Token、个人配置、提交压缩包或截图。

output/记录已完成的初版实验，不是下一版改进的成绩。新实验使用独立输出目录，保留数据版本、参数、实际模型调用及费用统计。设计方法时只用开发集，最后在独立评测集验证；任何改变都如实记录。
