# 知研 · Research Workbench

中文本地科研工作台，读取真实实验、资源账本、英文论文和外部评审；新增英文正文修订、绘图 Skill 与本地 LaTeX 编译，不启动模型调用、不修改已送评论文。适配现有 `output/memory_live_*` 运行目录以及同后缀的 `memory_paper_*` 论文目录。

## 启动

项目根目录运行：

```powershell
.\scripts\start_workbench.ps1
```

首次启动需要 Node.js 20.19+ / 22.12+ 和 npm 以安装、构建前端；构建完成后仅需已有 Python 环境。打开 <http://127.0.0.1:8765>。按 Ctrl+C 关闭服务。如需在修改前端后重建：

```powershell
.\scripts\start_workbench.ps1 -Build
```

也可手动构建与启动：

```powershell
cd frontend
npm ci
npm run build
cd ..
.venv\Scripts\python.exe -m workbench.server
```

基础 HTTP 服务使用 Python 标准库，绘图复用项目已有 Matplotlib，PDF 编译使用本机 pdflatex；可用 `--port 8766` 切换端口。服务仅监听本机 127.0.0.1，不是面向公网的多用户服务。

## 页面

项目总览展示冻结协议、主条件结果和产物流程。实验中心支持筛选、排序和逐条证据检查。错误分析按场景分解已保存错误，并展示未执行的补实验计划。写作与绘图支持六个英文章节编辑、保存新版本、差异查看、LaTeX 源码预览、图表生成及后台编译 PDF。论文评审保留原始英文 PDF 和英文评审；资源交付展示实际用量并提供白名单文件下载。

新修订写入 output/workbench/，不会继承原外部评分。实验图由真实数据和本地 Matplotlib 生成，提供 PDF/SVG/PNG；架构图附 JSON 源文件。可选 AI 生图 Skill 当前未配置。详见 [绘图与写作说明](../docs/figure_skill_integration.md)。编译需要已有 pdflatex 及模板依赖，缺失时报告失败并保留源文件，不自动安装。

主条件 256 与敏感性条件 512 的任务范围不同；Full history 不受选择上下文预算限制。Stanford 是外部 AI 估分，不等于 ICLR 正式评审或比赛总分；缺失评分不会填零。预算准入阈值不是供应商侧硬计费上限。

服务不会公开配置、API Key、私有评审 Token 单文件或任意项目路径。提交 ZIP 是明确允许的本机下载工件，其中仍含私有评审 Token，界面会提示。下载 ZIP 不代表完成比赛官网提交；没有自动上传或上游 PR 功能。

## 开发

两个终端分别运行：

```powershell
# 终端 1：项目根目录
.venv\Scripts\python.exe -m workbench.server

# 终端 2
cd frontend
npm run dev
```

访问 <http://127.0.0.1:5173>；Vite 将 `/api` 转发至 8765。生产页面、API 和 PDF 则统一由 8765 提供。

## 验证

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_workbench.py -v
cd frontend
npm run build
npm run test:e2e
```

浏览器测试需要先启动本地 Python 服务及已有 Edge。非默认安装位置可通过 `WORKBENCH_BROWSER` 指定已有 Chromium 浏览器路径，不自动下载浏览器。测试覆盖真实指标、筛选、证据详情、资源下载、移动布局、错误状态、新修订保存、未保存导航保护、轮询重试和实际 LaTeX 编译。写作测试会在 output/workbench/ 中创建新的未评审测试修订；不改动原实验数据或送评论文。预览图生成在 output/workbench-preview/。
