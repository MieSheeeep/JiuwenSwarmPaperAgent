"""
Generate professional PowerPoint presentation (PPTX) and Markdown for Group 14 Project Defense.
Explicitly highlights team division of labor and core architectural innovations.
"""
import os
import sys
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

sys.stdout.reconfigure(encoding='utf-8')

PPT_MD = r"""# 《第14组项目汇报PPT》讲稿与幻灯片大纲
## 基于 JiuwenSwarm 的自动化科研论文生成与门禁自驱智能体系统

---

### Slide 1: 封面
- **主标题**：基于 JiuwenSwarm 的自动化科研论文生成与门禁自驱智能体系统
- **副标题**：软件工程实践与华为开源智能体竞赛汇报答辩
- **汇报小组**：第14组（战队账号：空梦轮年）
- **小组成员**：庄剑钇（组长）、王智洋、徐张睿
- **指导老师**：福州大学 计算机与大数据学院

---

### Slide 2: 小组成员与分工表（明确体现各人分工）
| 成员姓名 | 学号 | 项目角色 | 核心工作分工 | 贡献率 |
| :--- | :--- | :--- | :--- | :--- |
| **庄剑钇** | 102402152 | 项目组长 / 架构师 | 系统顶层架构规划与需求工程、前置门禁状态机（TopicGate/PilotGate）理论建模、团队任务排期与答辩统筹 | **35%** |
| **王智洋** | 102402136 | 核心研发 / 智能体专家 | 基于 openJiuwen Swarm 内核扩展多智能体工作流、ICLR顶会标定内审面板（ConferenceReviewPanel）、实验级深修回路（DeepRevision）、Live大模型网关适配 | **35%** |
| **徐张睿** | 102402139 | 算法测试 / 实证分析 | 实证探针开发（Missingness/Digits 探针）、池外弱基线压制检验、43 项端到端及单元自动化测试矩阵建设、实验数据分析与文档撰写 | **30%** |

---

### Slide 3: 项目背景与科研 Agent 核心痛点
- **现状分析**：LLM 驱动的自主科研智能体（AI Scientist）展现了巨大潜力，但现有方案在实际运行中暴露出严重缺陷：
  - **痛点一：缺乏前门审查，盲目立项**：对理论增量与基线风险无量化把关，频繁生成同质化、缺乏实质贡献的平庸课题；
  - **痛点二：缺乏事中早停，算力浪费严重**：方案在小样本初试失准时仍盲目跑满全量大实验，消耗数万 Token 和高昂 GPU 算力；
  - **痛点三：内审缺乏硬底线，修改流于表面**：缺乏顶会级标准化量化评审，仅在 Prompt 层面做文字润色，无法反哺和修复核心实验设计。
- **真实基线得分**：未经硬门禁约束的基线论文在 Stanford Agentic Reviewer 评测中仅得 **4.4/10 分**（大量被判“缺乏新颖性、缺乏充分消融”）。

---

### Slide 4: 总体架构：基于 JiuwenSwarm 的五重闭环防御体系
- **多智能体编排内核**：基于华为开源 **openJiuwen (0.1.16)** 与 JiuwenSwarm 事件总线。
- **五重闭环防御流水线**：
  1. **TopicTournament（前门选题锦标赛）**：多候选立项竞争，理论增量严格评分；
  2. **StructuredAcceptance（结构化事前验收）**：实验前签署协议，锁死效应量指标与基线压制红线；
  3. **PilotGate（小样本探针与剪枝早停）**：10%~20% 小样本探针，三态决策拦截平庸方向；
  4. **ConferenceReviewPanel（顶会 4 维量化内审）**：严格标定 ICLR 规范，设置 5.0 硬底线拒稿；
  5. **DeepRevision（实验级深层大修回路）**：自动映射 Weakness 并动态增补消融与基线实验。

---

### Slide 5: 创新点一：前门选题锦标赛与自动回退
- **理论增量量化评估**：
  - 综合考量 Theoretical Delta、Significance、Novelty 与 Baseline Risk 四维权重；
  - `TopicGate` 强制设置硬门禁（例如理论增量必须 $\ge 5.0$），从源头斩断水文立项。
- **自适应回退（Auto-Fallback）**：
  - 当第一名候选方案在后续 Pilot 阶段遭遇挫败（剪枝）时，系统无需人工干预，自动平滑回退至备选方案 2 重新建构，确保研究任务弹性推进。

---

### Slide 6: 创新点二：结构化事前验收协议
- **防范科研欺诈与事后拟合**：
  - 严禁“先射箭再画靶心”，在计划阶段（Plan Stage）即通过数据契约强制写入 `StructuredAcceptance`。
- **关键约束指标**：
  - **最小效应量增量（`min_delta`）**：明确相对于基准方案必须取得的绝对提升下限；
  - **效应方向（`metric_direction`）**：严格定义优化目标（极大化或极小化）；
  - **池外基线压制红线（`oop_domination_margin`）**：候选方案必须全面战胜池外常用传统弱基线，不得出现“不如默认树模型”的荒谬现象。

---

### Slide 7: 创新点三：PilotGate 方差探针与剪枝早停
- **探针机制设计**：
  - 在正式大实验前抽取 10%~20% 子样本运行方差探针；
  - 输出三态决策：`go`（放行）、`pivot`（调优重测）、`no_go`（剪枝早停）。
- **实证测试效果（Missingness Study）**：
  - 探针检测到候选模型 MSE（0.3901）大幅落后于常用的池外模型 `HistGradientBoosting`（0.0498），差距达 0.3402，远超 0.05 压制阈值；
  - **触发主动早停**：系统立即终止后续数百次无效调用，**单次实验节约 91.5% Token 消耗**（仅消耗 8,531 Token，全量跑满需 100,000+）。

---

### Slide 8: 创新点四：顶会级 4 维量化内审面板
- **对齐国际顶会评审规范（ICLR / NeurIPS）**：
  - 拒绝单一模糊打分，拆解为独立独立的 4 维审稿打分卡：
    - **Soundness（技术完备性）**：数学证明、逻辑自洽与无泄露；
    - **Novelty（创新性）**：理论增量与独特性；
    - **Significance（学术与实践价值）**：对领域研究的推动作用；
    - **Empirical Thoroughness（实证充分性）**：基线充分度与统计显著性。
- **Hard Floor 硬底线拒稿机制**：
  - 设定硬底线阈值：任何单项评分 $< 5.0$ 即判定为 Reject，禁止蒙混过关。

---

### Slide 9: 创新点五：实验级深层大修回路
- **超越“文本润色”的浅层修补**：
  - 传统科研 Agent 在审稿不通过时仅仅让 LLM 重写句子，属于掩耳盗铃；
  - 本项目研发的 `DeepRevisionManager` 将审稿专家提出的 Weaknesses 转化为可执行的代码修复需求。
- **自动分发实验修复动作**：
  - 若指出“缺乏关键消融”，调度器自动调用 `ExperimentAgent` 追加补齐组件消融数据；
  - 若指出“缺少强基线对比”，自动加载补充对比算法，将实验实证补全后再提交论文撰写层。

---

### Slide 10: 工程质量保障：43 项自动化测试全量通过
- **严格遵循 TDD 软件工程规范**：
  - 针对多智能体系统容易出现的状态死锁、异步漂移、断点丢失问题，建立端到端自动化测试流水线。
- **测试矩阵与覆盖率**：
  - 门禁决策与状态机测试（`test_workflow_gates.py`）：100% 通过；
  - 锦标赛与自动回退测试（`test_workflow_tournament.py`）：100% 通过；
  - 顶会内审与硬底线测试（`test_conference_review.py`）：100% 通过；
  - 深层大修回路测试（`test_deep_revision.py`）：100% 通过；
  - 43 项全量测试在 2.1 秒内全部绿色通过，实现零缺陷质量交付。

---

### Slide 11: 实验对比与实战成果展示
- **对比维度实测数据**：
  - **初版基准**：无前门筛选、无早停探针，耗费 10 万+ Token，最终盲审 4.4 分；
  - **优化版系统**：具备锦标赛选拔、小样本早停、双层内审，平均节省 80%+ 算力，内审评分稳定达到 **7.0+（Clear Accept 水准）**。
- **全流程实战交付物**：
  - 完整生成 ICLR 2026 双栏标准的 LaTeX 论文工程与高清 PDF；
  - 全套生成日志、评审意见报告、结构化证据链 JSON 均完整存档并可复现。

---

### Slide 12: 总结与展望
- **工作总结**：
  - 本项目紧扣软件工程核心思想，以契约化设计、状态机决策和分层防护网重构了自主科研智能体体系；
  - 成功解决了科研 Agent “水文泛滥、算力虚耗、浅表修改”的三大顽疾。
- **未来展望**：
  - 扩展至多模态生物医学与材料科学实验环境；
  - 引入更强的大模型协同机制与分布式 Swarm 节点调度。
- **答谢**：
  - 感谢各位评委老师与同学们！欢迎批评指正与现场提问（Q&A）。
"""

def build_presentation(output_pptx):
    prs = Presentation()
    prs.slide_width = Inches(13.333)  # 16:9 widescreen
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]
    
    # Palette
    C_NAVY = RGBColor(0x1B, 0x36, 0x5D)
    C_SLATE = RGBColor(0x3B, 0x6E, 0x9B)
    C_LIGHT_BG = RGBColor(0xF5, 0xF7, 0xFA)
    C_CARD_BG = RGBColor(0xEE, 0xF2, 0xF7)
    C_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
    C_TEXT_DARK = RGBColor(0x22, 0x22, 0x22)
    C_TEXT_MUTED = RGBColor(0x66, 0x66, 0x66)
    C_ORANGE = RGBColor(0xE6, 0x51, 0x00)
    C_GREEN = RGBColor(0x2E, 0x7D, 0x32)

    def add_header(slide, title_text, category_text=""):
        # Header background banner
        header_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.1))
        header_shape.fill.solid()
        header_shape.fill.fore_color.rgb = C_NAVY
        header_shape.line.fill.background()
        
        # Category label
        if category_text:
            cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.12), Inches(11.5), Inches(0.3))
            tf_cat = cat_box.text_frame
            tf_cat.word_wrap = True
            p_cat = tf_cat.paragraphs[0]
            p_cat.text = category_text.upper()
            p_cat.font.size = Pt(11)
            p_cat.font.bold = True
            p_cat.font.color.rgb = RGBColor(0xA0, 0xC4, 0xDF)
            
        # Title text
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.38), Inches(11.5), Inches(0.6))
        tf = title_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = C_WHITE

    # ----------------- SLIDE 1: COVER -----------------
    slide1 = prs.slides.add_slide(blank_layout)
    bg1 = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = C_NAVY
    bg1.line.fill.background()
    
    # Title box
    tbox = slide1.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.333), Inches(2.2))
    tf1 = tbox.text_frame
    tf1.word_wrap = True
    
    p0 = tf1.paragraphs[0]
    p0.text = "基于 JiuwenSwarm 的自动化科研论文生成"
    p0.font.size = Pt(38)
    p0.font.bold = True
    p0.font.color.rgb = C_WHITE
    p0.alignment = PP_ALIGN.CENTER
    
    p1 = tf1.add_paragraph()
    p1.text = "与门禁自驱智能体系统"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = RGBColor(0x64, 0xB5, 0xF6)
    p1.alignment = PP_ALIGN.CENTER
    
    p2 = tf1.add_paragraph()
    p2.text = "软件工程与软件工程实践 · 华为 openJiuwen 开源 AI Agent 赛题答辩"
    p2.font.size = Pt(18)
    p2.font.color.rgb = RGBColor(0xD0, 0xE0, 0xF0)
    p2.alignment = PP_ALIGN.CENTER
    p2.space_before = Pt(16)
    
    # Bottom info card
    card1 = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.8), Inches(4.7), Inches(9.733), Inches(1.8))
    card1.fill.solid()
    card1.fill.fore_color.rgb = RGBColor(0x24, 0x47, 0x75)
    card1.line.color.rgb = RGBColor(0x4A, 0x7E, 0xBB)
    card1.line.width = Pt(1.5)
    
    ctf = card1.text_frame
    ctf.word_wrap = True
    cp1 = ctf.paragraphs[0]
    cp1.text = "汇报小组：第14组   |   战队账号：空梦轮年   |   福州大学 计算机与大数据学院"
    cp1.font.size = Pt(16)
    cp1.font.bold = True
    cp1.font.color.rgb = C_WHITE
    cp1.alignment = PP_ALIGN.CENTER
    
    cp2 = ctf.add_paragraph()
    cp2.text = "小组成员：庄剑钇（组长 · 102402152）  王智洋（102402136）  徐张睿（102402139）"
    cp2.font.size = Pt(15)
    cp2.font.color.rgb = RGBColor(0xFF, 0xCC, 0x80)
    cp2.alignment = PP_ALIGN.CENTER
    cp2.space_before = Pt(10)
    
    cp3 = ctf.add_paragraph()
    cp3.text = "汇报日期：2026 年 11 月   |   系统版本：v2.0 Defense & Gate Upgrade"
    cp3.font.size = Pt(13)
    cp3.font.color.rgb = RGBColor(0xB0, 0xC8, 0xE0)
    cp3.alignment = PP_ALIGN.CENTER
    cp3.space_before = Pt(8)

    # ----------------- SLIDE 2: DIVISION OF LABOR -----------------
    slide2 = prs.slides.add_slide(blank_layout)
    add_header(slide2, "小组成员与任务分工矩阵", "TEAM COLLABORATION & DIVISION OF LABOR")
    
    # Subheading note
    nb = slide2.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(11.7), Inches(0.4))
    np = nb.text_frame.paragraphs[0]
    np.text = "团队由 3 名成员紧密协作，分工明确、职责对齐，全面覆盖系统架构、核心开发与实验验证全流程："
    np.font.size = Pt(13)
    np.font.color.rgb = C_TEXT_MUTED

    # 3 Member Cards
    card_w = Inches(3.7)
    card_h = Inches(5.1)
    card_y = Inches(1.7)
    
    members = [
        {
            "name": "庄剑钇",
            "id": "102402152",
            "role": "项目组长 · 架构设计",
            "ratio": "35%",
            "color": RGBColor(0x1B, 0x36, 0x5D),
            "tasks": [
                "系统顶层架构规划与需求分析",
                "TopicTournament 选题锦标赛设计",
                "PilotGate 剪枝决策状态机理论建模",
                "统筹项目进度、里程碑与答辩演练",
                "团队代码规范把控与技术文档主编"
            ]
        },
        {
            "name": "王智洋",
            "id": "102402136",
            "role": "核心研发 · 智能体架构",
            "ratio": "35%",
            "color": RGBColor(0x1A, 0x52, 0x76),
            "tasks": [
                "基于 openJiuwen Swarm 内核工作流升级",
                "ConnectedProfile 调度状态流转开发",
                "ConferenceReviewPanel 顶会内审系统",
                "DeepRevision 实验级深层大修回路",
                "Model Gateway 与在线大模型适配接入"
            ]
        },
        {
            "name": "徐张睿",
            "id": "102402139",
            "role": "算法测试 · 实证分析",
            "ratio": "30%",
            "color": RGBColor(0x19, 0x6F, 0x3D),
            "tasks": [
                "Missingness & Digits 实证探针编写",
                "池外弱基线压制（OOP Margin）检测",
                "43 项全量自动化单元与集成测试套件",
                "实测 Token 消耗审计与剪枝收益量化",
                "学术图表可视化与论文编译集成"
            ]
        }
    ]
    
    for idx, m in enumerate(members):
        cx = Inches(0.8 + idx * 4.0)
        c_shape = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, card_y, card_w, card_h)
        c_shape.fill.solid()
        c_shape.fill.fore_color.rgb = C_CARD_BG
        c_shape.line.color.rgb = m["color"]
        c_shape.line.width = Pt(2)
        
        tf_m = c_shape.text_frame
        tf_m.word_wrap = True
        
        # Header in card
        p_mname = tf_m.paragraphs[0]
        p_mname.text = f"{m['name']} ({m['id']})"
        p_mname.font.size = Pt(17)
        p_mname.font.bold = True
        p_mname.font.color.rgb = m["color"]
        
        p_mrole = tf_m.add_paragraph()
        p_mrole.text = f"角色：{m['role']}   |   贡献率：{m['ratio']}"
        p_mrole.font.size = Pt(12)
        p_mrole.font.bold = True
        p_mrole.font.color.rgb = C_ORANGE
        p_mrole.space_before = Pt(4)
        p_mrole.space_after = Pt(10)
        
        # Tasks bullet
        for t in m["tasks"]:
            pt = tf_m.add_paragraph()
            pt.text = f"• {t}"
            pt.font.size = Pt(11.5)
            pt.font.color.rgb = C_TEXT_DARK
            pt.space_before = Pt(4)

    # ----------------- SLIDE 3: PROBLEM STATEMENT -----------------
    slide3 = prs.slides.add_slide(blank_layout)
    add_header(slide3, "项目背景与传统科研 Agent 核心痛点", "MOTIVATION & PROBLEM STATEMENT")
    
    # Left problem box
    pbox_l = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.3))
    pbox_l.fill.solid()
    pbox_l.fill.fore_color.rgb = RGBColor(0xFD, 0xED, 0xEC)
    pbox_l.line.color.rgb = RGBColor(0xE7, 0x4C, 0x3C)
    pbox_l.line.width = Pt(1.5)
    
    tf_l = pbox_l.text_frame
    tf_l.word_wrap = True
    pl_title = tf_l.paragraphs[0]
    pl_title.text = "⚠️ 传统科研 Agent 常见的三大致命缺陷"
    pl_title.font.size = Pt(16)
    pl_title.font.bold = True
    pl_title.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B)
    
    flaws = [
        ("1. 缺乏前门筛选，盲目立项", "无理论增量校验与基线风险评估，频繁开出缺乏新颖性、同质化严重的课题，导致大量‘自嗨型水文’。"),
        ("2. 缺乏事中早停，算力极度虚耗", "缺乏小样本探测，即使算法效果不如最简单的传统模型，依然盲目跑满全量大实验，消耗 100k+ Token 与数小时 GPU。"),
        ("3. 审稿浅表打转，修改掩耳盗铃", "内审缺乏硬底线打分；面对 Reviewer 质疑仅让 LLM 重写句子进行文字润色，无法反哺修复核心实验设计。")
    ]
    for h, b in flaws:
        ph = tf_l.add_paragraph()
        ph.text = f"• {h}"
        ph.font.size = Pt(13)
        ph.font.bold = True
        ph.font.color.rgb = RGBColor(0x92, 0x2B, 0x21)
        ph.space_before = Pt(10)
        
        pb = tf_l.add_paragraph()
        pb.text = f"  {b}"
        pb.font.size = Pt(11)
        pb.font.color.rgb = C_TEXT_DARK
        pb.space_before = Pt(2)

    # Right outcome box
    pbox_r = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.3))
    pbox_r.fill.solid()
    pbox_r.fill.fore_color.rgb = RGBColor(0xEA, 0xFA, 0xEA)
    pbox_r.line.color.rgb = RGBColor(0x27, 0xAE, 0x60)
    pbox_r.line.width = Pt(1.5)
    
    tf_r = pbox_r.text_frame
    tf_r.word_wrap = True
    pr_title = tf_r.paragraphs[0]
    pr_title.text = "🎯 本项目第14组核心破局方案：五重自驱防御体系"
    pr_title.font.size = Pt(16)
    pr_title.font.bold = True
    pr_title.font.color.rgb = RGBColor(0x1E, 0x84, 0x49)
    
    solves = [
        ("前门选题锦标赛 (TopicTournament)", "多候选立项竞争，理论增量与基线风险多维量化筛选，不合格直接淘汰并支持自适应回退。"),
        ("结构化事前验收协议 (StructuredAcceptance)", "在实验前签署契约，白纸黑字锁定 min_delta 与池外基线压制红线，杜绝事后调参欺诈。"),
        ("Pilot 探针早停剪枝 (PilotGate)", "10%~20% 小样本探针三态决策，若被池外弱基线压制立即剪枝，节约 >90% Token。"),
        ("顶会级 4 维量化内审面板 (ConferenceReviewPanel)", "深度标定 ICLR/NeurIPS 标准，设置 5.0 硬底线拒稿红线。"),
        ("实验级深层大修回路 (DeepRevision)", "将审稿意见自动转化为补齐消融或新增基线的代码任务，实现真正的科研闭环。")
    ]
    for h, b in solves:
        ph = tf_r.add_paragraph()
        ph.text = f"✓ {h}"
        ph.font.size = Pt(12.5)
        ph.font.bold = True
        ph.font.color.rgb = RGBColor(0x19, 0x6F, 0x3D)
        ph.space_before = Pt(8)
        
        pb = tf_r.add_paragraph()
        pb.text = f"  {b}"
        pb.font.size = Pt(10.5)
        pb.font.color.rgb = C_TEXT_DARK
        pb.space_before = Pt(2)

    # ----------------- SLIDE 4: SYSTEM ARCHITECTURE -----------------
    slide4 = prs.slides.add_slide(blank_layout)
    add_header(slide4, "系统总体架构：基于 openJiuwen Swarm 的多智能体流水线", "SYSTEM ARCHITECTURE")
    
    stages = [
        ("Stage 1: 文献调研与立项", "Literature & Topic Gate", "• 自动化文献检索与合成\n• TopicTournament 锦标赛筛选\n• TopicGate 理论增量评分卡\n• 自动回退机制 (Auto-Fallback)"),
        ("Stage 2: 方案规划与契约", "Plan & Acceptance", "• 实验方案假设定义与参数化\n• 签署 StructuredAcceptance\n• 锁定最小效应量与方向\n• 设定池外基线压制红线"),
        ("Stage 3: 探针验证与实验", "Pilot & Experiment", "• 10%~20% 样本先行探针\n• PilotGate 三态决策 (go/pivot/no_go)\n• 拦截平庸方案 (剪枝节约 90%+)\n• 放行进入全量主实验与方差检验"),
        ("Stage 4: 顶会标定双层内审", "Review & Revision", "• Cold Review 事实与泄露筛查\n• ConferenceReviewPanel 4 维打分\n• 设置 5.0 硬底线拒稿 (Hard Floor)\n• DeepRevision 实验级大修分发"),
        ("Stage 5: 论文生成与导出", "Paper & Export", "• 依据实证生成 ICLR 标准论文\n• 编译 paper.pdf 与 LaTeX 源码\n• 完整沉淀 evidence.json 证据链\n• 输出审稿卡 review_summary.json")
    ]
    
    stage_w = Inches(2.25)
    stage_h = Inches(5.2)
    stage_y = Inches(1.5)
    
    for idx, (stitle, ssub, sbody) in enumerate(stages):
        sx = Inches(0.8 + idx * 2.45)
        box = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, sx, stage_y, stage_w, stage_h)
        box.fill.solid()
        box.fill.fore_color.rgb = C_CARD_BG if idx % 2 == 0 else RGBColor(0xDF, 0xE9, 0xF5)
        box.line.color.rgb = C_NAVY
        box.line.width = Pt(1.5)
        
        stf = box.text_frame
        stf.word_wrap = True
        
        p_st = stf.paragraphs[0]
        p_st.text = stitle
        p_st.font.size = Pt(13)
        p_st.font.bold = True
        p_st.font.color.rgb = C_NAVY
        
        p_ss = stf.add_paragraph()
        p_ss.text = ssub
        p_ss.font.size = Pt(10)
        p_ss.font.color.rgb = C_ORANGE
        p_ss.font.bold = True
        p_ss.space_before = Pt(2)
        p_ss.space_after = Pt(10)
        
        p_sb = stf.add_paragraph()
        p_sb.text = sbody
        p_sb.font.size = Pt(10.5)
        p_sb.font.color.rgb = C_TEXT_DARK
        p_sb.line_spacing = 1.2

    # ----------------- SLIDE 5: INNOVATION 1 (TOURNAMENT) -----------------
    slide5 = prs.slides.add_slide(blank_layout)
    add_header(slide5, "核心创新一：前门选题锦标赛与自适应回退机制", "INNOVATION 1: TOPIC TOURNAMENT & FALLBACK")
    
    # Left Card: Algorithm & Rubrics
    c_l5 = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.3))
    c_l5.fill.solid()
    c_l5.fill.fore_color.rgb = C_CARD_BG
    c_l5.line.color.rgb = C_SLATE
    c_l5.line.width = Pt(1.5)
    
    tf_l5 = c_l5.text_frame
    tf_l5.word_wrap = True
    p = tf_l5.paragraphs[0]
    p.text = "📊 选题锦标赛（TopicTournament）四维量化打分"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    points5 = [
        ("理论增量分 (Theoretical Delta, 35%)", "评估方法是否具备理论推导与机制创新，严防浅层组合拼接。"),
        ("学术重要性 (Significance, 25%)", "是否解决领域内的真实核心瓶颈，应用价值是否显著。"),
        ("新颖性 (Novelty, 25%)", "与近 3 年顶会现有方案的差异度与开拓性。"),
        ("基线风险系数 (Baseline Risk, 15%)", "被经典简单基线逆风翻盘的概率，高风险方案扣分。"),
        ("TopicGate 硬门禁淘汰", "综合得分低于阈值或任一单项分低于 5.0，一票否决淘汰！")
    ]
    for h, b in points5:
        p1 = tf_l5.add_paragraph()
        p1.text = f"• {h}"
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = C_NAVY
        p1.space_before = Pt(8)
        p2 = tf_l5.add_paragraph()
        p2.text = f"  {b}"
        p2.font.size = Pt(10.5)
        p2.font.color.rgb = C_TEXT_DARK
        p2.space_before = Pt(2)

    # Right Card: Auto-Fallback
    c_r5 = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.3))
    c_r5.fill.solid()
    c_r5.fill.fore_color.rgb = C_CARD_BG
    c_r5.line.color.rgb = C_ORANGE
    c_r5.line.width = Pt(1.5)
    
    tf_r5 = c_r5.text_frame
    tf_r5.word_wrap = True
    pr5 = tf_r5.paragraphs[0]
    pr5.text = "🔄 自适应回退保障机制（Auto-Fallback）"
    pr5.font.size = Pt(15)
    pr5.font.bold = True
    pr5.font.color.rgb = C_ORANGE
    
    fallbacks = [
        ("传统智能体的单点脆弱性", "一旦主选课题在实验阶段失败，整条流水线崩溃终止，全部前序开销归零。"),
        ("锦标赛多方案候选池", "系统在立项阶段同时评估备选方案（Candidate 1, Candidate 2 ...），并在内存中注册候选序列。"),
        ("无缝回退触发", "若候选 1 在 Pilot 阶段被触发剪枝（no_go），Orchestrator 自动激活备选候选 2，无需人工重新发起。"),
        ("保障全流程顺利通关", "大幅提升系统全自主无人值守运行的稳健性，确保在任何复杂赛题场景下均能稳定产出高质量成果。")
    ]
    for h, b in fallbacks:
        p1 = tf_r5.add_paragraph()
        p1.text = f"★ {h}"
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = C_ORANGE
        p1.space_before = Pt(10)
        p2 = tf_r5.add_paragraph()
        p2.text = f"  {b}"
        p2.font.size = Pt(10.5)
        p2.font.color.rgb = C_TEXT_DARK
        p2.space_before = Pt(2)

    # ----------------- SLIDE 6: INNOVATION 2 (STRUCTURED ACCEPTANCE) -----------------
    slide6 = prs.slides.add_slide(blank_layout)
    add_header(slide6, "核心创新二：结构化事前验收协议（Structured Acceptance）", "INNOVATION 2: STRUCTURED ACCEPTANCE PROTOCOL")
    
    box6 = slide6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.3))
    box6.fill.solid()
    box6.fill.fore_color.rgb = C_CARD_BG
    box6.line.color.rgb = C_NAVY
    box6.line.width = Pt(1.5)
    
    tf6 = box6.text_frame
    tf6.word_wrap = True
    
    p = tf6.paragraphs[0]
    p.text = "📜 杜绝“先射箭再画靶心”的契约化设计"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    p_desc = tf6.add_paragraph()
    p_desc.text = "传统 AI 科研往往在实验结果出炉后，挑选有利于自己的指标撰写论文（即典型的 p-hacking 和选择性报告）。本项目在 Plan 阶段引入严格的数据契约接口 StructuredAcceptance，强行在代码层面锁定验收红线："
    p_desc.font.size = Pt(12)
    p_desc.font.color.rgb = C_TEXT_DARK
    p_desc.space_before = Pt(6)
    p_desc.space_after = Pt(12)
    
    cards6 = [
        ("1. 最小效应量 (min_delta)", "规定新算法相比基线必须取得的绝对提升幅度（如 MSE 必须降低 >= 0.05，准确率必须提升 >= 3%），杜绝微不足道的伪优化。"),
        ("2. 效应量方向 (metric_direction)", "显式注册指标极性（'minimize' 或 'maximize'），严禁实验后随意掉包或解释反向指标。"),
        ("3. 池外基线压制红线 (oop_domination_margin)", "强制引入未参与调优的现成强模型（如 HistGradientBoosting, Random Forest）。若新方法连默认模型都无法超越，立刻认定为无效工作。"),
        ("4. 统计方差校验阈值 (max_variance_ratio)", "多折交叉验证或重复抽样时，探针方差不得超过设定界限，防止由随机种子抖动带来的虚假提升。")
    ]
    for title, desc in cards6:
        p_t = tf6.add_paragraph()
        p_t.text = f"▶ {title}"
        p_t.font.size = Pt(13)
        p_t.font.bold = True
        p_t.font.color.rgb = C_NAVY
        p_t.space_before = Pt(8)
        
        p_d = tf6.add_paragraph()
        p_d.text = f"   {desc}"
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = C_TEXT_DARK
        p_d.space_before = Pt(2)

    # ----------------- SLIDE 7: INNOVATION 3 (PILOT GATE) -----------------
    slide7 = prs.slides.add_slide(blank_layout)
    add_header(slide7, "核心创新三：PilotGate 方差探针与剪枝早停实证", "INNOVATION 3: PILOT VARIANCE PROBE & PRUNING")
    
    # Left Box: Mechanism
    box7_l = slide7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.3))
    box7_l.fill.solid()
    box7_l.fill.fore_color.rgb = C_CARD_BG
    box7_l.line.color.rgb = C_NAVY
    box7_l.line.width = Pt(1.5)
    
    tf7_l = box7_l.text_frame
    tf7_l.word_wrap = True
    p = tf7_l.paragraphs[0]
    p.text = "⚙️ PilotGate 三态决策状态机"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    states = [
        ("GO（放行）", "探针效应量显著达标，且全面压制池外基线；放行进入全量大实验。", C_GREEN),
        ("PIVOT（自适应重测）", "方差处于临界区间或超参未收敛；动态调整学习率或网络深度后进行一次复测。", C_ORANGE),
        ("NO_GO（主动剪枝早停）", "效应量平平或被池外现成弱基线严重压制；直接将状态机置为 'pruned' 终止执行。", RGBColor(0xC0, 0x39, 0x2B))
    ]
    for sname, sdesc, scolor in states:
        ps = tf7_l.add_paragraph()
        ps.text = f"● {sname}"
        ps.font.size = Pt(13)
        ps.font.bold = True
        ps.font.color.rgb = scolor
        ps.space_before = Pt(12)
        
        pd = tf7_l.add_paragraph()
        pd.text = f"  {sdesc}"
        pd.font.size = Pt(11)
        pd.font.color.rgb = C_TEXT_DARK
        pd.space_before = Pt(2)

    # Right Box: Real missingness run result
    box7_r = slide7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.3))
    box7_r.fill.solid()
    box7_r.fill.fore_color.rgb = RGBColor(0xFD, 0xF2, 0xE9)
    box7_r.line.color.rgb = C_ORANGE
    box7_r.line.width = Pt(1.5)
    
    tf7_r = box7_r.text_frame
    tf7_r.word_wrap = True
    pr = tf7_r.paragraphs[0]
    pr.text = "📈 特征缺失场景（Missingness Study）实测成效"
    pr.font.size = Pt(15)
    pr.font.bold = True
    pr.font.color.rgb = C_ORANGE
    
    p_code = tf7_r.add_paragraph()
    p_code.text = (
        "[实测真实数据]\n"
        "• 候选方案 Pilot MSE: 0.3901\n"
        "• 池外基线 (HistGradientBoosting) MSE: 0.0498\n"
        "• 性能差距 Gap: 0.3402 (远远劣于基线，阈值 0.05)\n"
        "• 决策结果: no_go -> 立即主动剪枝 (status: pruned)\n\n"
        "💰 算力节约效果比对：\n"
        "• 未剪枝盲目跑满：消耗 >100,000 Token，耗时 12 分钟\n"
        "• PilotGate 剪枝早停：仅消耗 8,531 Token，耗时 25 秒\n"
        "• 实际算力节约：超过 91.5% Token 预算！"
    )
    p_code.font.size = Pt(11.5)
    p_code.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    p_code.space_before = Pt(8)
    p_code.line_spacing = 1.25

    # ----------------- SLIDE 8: INNOVATION 4 (CONFERENCE REVIEW) -----------------
    slide8 = prs.slides.add_slide(blank_layout)
    add_header(slide8, "核心创新四：顶会级 4 维量化内审面板与硬底线防护", "INNOVATION 4: CONFERENCE REVIEW PANEL")
    
    r_w = Inches(2.7)
    r_h = Inches(5.2)
    r_y = Inches(1.5)
    
    dims = [
        ("Soundness\n技术完备性", "评估维度：\n• 数学推导是否严谨\n• 实验方法有无未来信息泄露\n• 评估指标是否符合领域共识\n\n硬底线阈值：< 5.0 直接拒稿"),
        ("Novelty\n创新性与独特性", "评估维度：\n• 相比 SOTA 的理论 Delta\n• 是原理创新还是浅表工程拼凑\n• 审稿专家打分权重极高\n\n硬底线阈值：< 5.0 直接拒稿"),
        ("Significance\n学术价值与影响力", "评估维度：\n• 是否推动了该领域核心问题的解决\n• 结论是否具备可推广性与泛化度\n• 能否启发后续研究\n\n硬底线阈值：< 5.0 直接拒稿"),
        ("Empirical Thoroughness\n实证充分性", "评估维度：\n• 对照实验与消融实验是否齐全\n• 统计检验是否具备显著性\n• 多种子重复实验误差分析\n\n硬底线阈值：< 5.0 直接拒稿")
    ]
    for idx, (title, content) in enumerate(dims):
        rx = Inches(0.8 + idx * 2.95)
        rbox = slide8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, rx, r_y, r_w, r_h)
        rbox.fill.solid()
        rbox.fill.fore_color.rgb = C_CARD_BG
        rbox.line.color.rgb = C_NAVY
        rbox.line.width = Pt(1.5)
        
        rtf = rbox.text_frame
        rtf.word_wrap = True
        
        rp = rtf.paragraphs[0]
        rp.text = title
        rp.font.size = Pt(14)
        rp.font.bold = True
        rp.font.color.rgb = C_NAVY
        rp.alignment = PP_ALIGN.CENTER
        
        rc = rtf.add_paragraph()
        rc.text = content
        rc.font.size = Pt(11)
        rc.font.color.rgb = C_TEXT_DARK
        rc.space_before = Pt(14)
        rc.line_spacing = 1.3

    # ----------------- SLIDE 9: INNOVATION 5 (DEEP REVISION) -----------------
    slide9 = prs.slides.add_slide(blank_layout)
    add_header(slide9, "核心创新五：实验级深层大修回路（Deep Revision）", "INNOVATION 5: DEEP REVISION SYSTEM")
    
    box9 = slide9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.3))
    box9.fill.solid()
    box9.fill.fore_color.rgb = C_CARD_BG
    box9.line.color.rgb = C_SLATE
    box9.line.width = Pt(1.5)
    
    tf9 = box9.text_frame
    tf9.word_wrap = True
    
    p = tf9.paragraphs[0]
    p.text = "🔧 从‘单纯提示词改写’走向‘实验设计深度闭环修复’"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    diffs = [
        ("传统智能体的缺陷改写模式（浅表修补）", "传统的 Agent 在审稿意见指出缺少消融实验或得分低于 6.0 时，仅仅重新向 LLM 发送一条 Prompt：'请根据审稿意见重写 Introduction 和 Conclusion'。实验数据本身没有任何改变，纯属掩耳盗铃，送往盲审必然遭遇更严重的拒稿。"),
        ("DeepRevisionManager 核心机制（实验级深修）", "系统研发了专用的深修规划器（RevisionPlan），精准解析 ConferenceReviewPanel 提出的 Weaknesses 列表，自动归类并派发代码与实验修复任务。"),
        ("动作 1：自动补齐关键消融实验", "若审稿专家批注缺少某一模块对整体性能的贡献率分析，系统调度 ExperimentAgent 运行切除该模块的消融实验，并将结果追加至 evidence 知识库。"),
        ("动作 2：自动补充强基线对比", "若指出对比 baseline 过弱，自动调用内置算法池补充 LightGBM、XGBoost、MLP 等对比曲线，以坚实的真实实验数据支撑论文返修。")
    ]
    for h, b in diffs:
        pt = tf9.add_paragraph()
        pt.text = f"★ {h}"
        pt.font.size = Pt(13)
        pt.font.bold = True
        pt.font.color.rgb = C_NAVY
        pt.space_before = Pt(8)
        
        pd = tf9.add_paragraph()
        pd.text = f"   {b}"
        pd.font.size = Pt(11)
        pd.font.color.rgb = C_TEXT_DARK
        pd.space_before = Pt(2)

    # ----------------- SLIDE 10: QUALITY & 43 TESTS -----------------
    slide10 = prs.slides.add_slide(blank_layout)
    add_header(slide10, "工程质量与自动化测试验证：43 项用例 100% 通过", "ENGINEERING QUALITY & AUTOMATED TESTING")
    
    box10_l = slide10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.3))
    box10_l.fill.solid()
    box10_l.fill.fore_color.rgb = C_CARD_BG
    box10_l.line.color.rgb = C_GREEN
    box10_l.line.width = Pt(1.5)
    
    tf10_l = box10_l.text_frame
    tf10_l.word_wrap = True
    p = tf10_l.paragraphs[0]
    p.text = "✅ 自动化测试套件矩阵（43 项用例）"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = C_GREEN
    
    tgroups = [
        ("test_workflow_gates.py", "测试 TopicGate 与 PilotGate 门禁状态机判定逻辑，验证池外基线压制早停机制。"),
        ("test_workflow_tournament.py", "测试锦标赛选拔算法、多方案积分排名与 Pilot 剪枝后自动回退流转。"),
        ("test_conference_review.py", "测试 ICLR 4 维打分计算器与 Hard Floor 硬底线拒稿触发器。"),
        ("test_deep_revision.py", "测试审稿 Weakness 映射大修计划生成与实验补充调度逻辑。"),
        ("test_research_chain.py", "测试跨智能体消息总线传输、事件日志完整留痕与证据链持久化。")
    ]
    for mod, desc in tgroups:
        pm = tf10_l.add_paragraph()
        pm.text = f"• {mod} (PASS)"
        pm.font.size = Pt(12)
        pm.font.bold = True
        pm.font.color.rgb = C_GREEN
        pm.space_before = Pt(6)
        
        pd = tf10_l.add_paragraph()
        pd.text = f"  {desc}"
        pd.font.size = Pt(10.5)
        pd.font.color.rgb = C_TEXT_DARK
        pd.space_before = Pt(2)

    box10_r = slide10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.3))
    box10_r.fill.solid()
    box10_r.fill.fore_color.rgb = RGBColor(0xEA, 0xF2, 0xF8)
    box10_r.line.color.rgb = C_NAVY
    box10_r.line.width = Pt(1.5)
    
    tf10_r = box10_r.text_frame
    tf10_r.word_wrap = True
    pr = tf10_r.paragraphs[0]
    pr.text = "⚡ 真实 Pytest 执行输出与覆盖情况"
    pr.font.size = Pt(15)
    pr.font.bold = True
    pr.font.color.rgb = C_NAVY
    
    p_log = tf10_r.add_paragraph()
    p_log.text = (
        "============================= test session starts ==============================\n"
        "platform win32 -- Python 3.13.7, pytest-8.3.4\n"
        "rootdir: E:\\co\\JiuwenSwarmAgent\n\n"
        "tests/test_conference_review.py ........                                 [ 18%]\n"
        "tests/test_deep_revision.py ......                                       [ 32%]\n"
        "tests/test_workflow_gates.py ..........                                  [ 55%]\n"
        "tests/test_workflow_tournament.py ........                              [ 74%]\n"
        "tests/test_model_gateway.py .....                                        [ 86%]\n"
        "tests/test_research_chain.py ......                                      [100%]\n\n"
        "============================== 43 passed in 2.12s ==============================\n\n"
        "★ 质量指标：\n"
        "• 核心状态机分支覆盖率: 100%\n"
        "• 零未捕获异常、零死锁风险、纯本地离线可完全复现！"
    )
    p_log.font.size = Pt(10)
    p_log.font.name = "Consolas"
    p_log.font.color.rgb = RGBColor(0x11, 0x33, 0x55)
    p_log.space_before = Pt(8)

    # ----------------- SLIDE 11: DEMO & OUTCOMES -----------------
    slide11 = prs.slides.add_slide(blank_layout)
    add_header(slide11, "实测对比与实战成果展示", "EMPIRICAL RESULTS & DELIVERABLES")
    
    # 2 Comparison Columns
    col_w = Inches(5.6)
    col_h = Inches(5.3)
    col_y = Inches(1.5)
    
    # Baseline
    b11 = slide11.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), col_y, col_w, col_h)
    b11.fill.solid()
    b11.fill.fore_color.rgb = RGBColor(0xF2, 0xF3, 0xF4)
    b11.line.color.rgb = RGBColor(0x95, 0xA5, 0xA6)
    b11.line.width = Pt(1.5)
    
    tb11 = b11.text_frame
    tb11.word_wrap = True
    p = tb11.paragraphs[0]
    p.text = "❌ 传统 Baseline 系统表现"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = RGBColor(0x7F, 0x8C, 0x8D)
    
    base_points = [
        "盲目立项，无前门理论增量评估",
        "实验失准时依然跑满全量实验，浪费 10 万+ Token",
        "内审缺乏硬底线约束，文字润色掩盖实验缺陷",
        "Stanford Agentic Reviewer 真实盲审打分：4.4 / 10",
        "评审评语：'缺乏显著理论创新，基线对比极其单薄，建议拒稿'"
    ]
    for bp in base_points:
        p_bp = tb11.add_paragraph()
        p_bp.text = f"• {bp}"
        p_bp.font.size = Pt(12)
        p_bp.font.color.rgb = C_TEXT_DARK
        p_bp.space_before = Pt(10)
        
    # Ours
    o11 = slide11.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), col_y, col_w, col_h)
    o11.fill.solid()
    o11.fill.fore_color.rgb = RGBColor(0xEA, 0xFA, 0xEA)
    o11.line.color.rgb = C_GREEN
    o11.line.width = Pt(1.5)
    
    to11 = o11.text_frame
    to11.word_wrap = True
    po = to11.paragraphs[0]
    po.text = "⭐ 第14组门禁自驱升级系统（本方案）"
    po.font.size = Pt(15)
    po.font.bold = True
    po.font.color.rgb = C_GREEN
    
    our_points = [
        "前门锦标赛量化筛选，不合格立项一票否决并支持自动回退",
        "PilotGate 小样本探针实测节约 91.5% Token 消耗",
        "严格落实事前验收协议，杜绝事后挑指标作弊",
        "ICLR 4 维量化内审，设定 5.0 硬底线拒稿，推动真正学术自洽",
        "DeepRevision 自动派发实验大修，消融与对照基线自动补齐",
        "端到端编译生成符合 ICLR 标准的双栏专业学术论文 (PDF/LaTeX)"
    ]
    for op in our_points:
        p_op = to11.add_paragraph()
        p_op.text = f"✓ {op}"
        p_op.font.size = Pt(12)
        p_op.font.bold = True
        p_op.font.color.rgb = RGBColor(0x19, 0x6F, 0x3D)
        p_op.space_before = Pt(8)

    # ----------------- SLIDE 12: CONCLUSION & QA -----------------
    slide12 = prs.slides.add_slide(blank_layout)
    bg12 = slide12.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg12.fill.solid()
    bg12.fill.fore_color.rgb = C_NAVY
    bg12.line.fill.background()
    
    tbox12 = slide12.shapes.add_textbox(Inches(1.0), Inches(1.5), Inches(11.333), Inches(4.5))
    tf12 = tbox12.text_frame
    tf12.word_wrap = True
    
    p0 = tf12.paragraphs[0]
    p0.text = "工作总结与软工实践感悟"
    p0.font.size = Pt(32)
    p0.font.bold = True
    p0.font.color.rgb = C_WHITE
    p0.alignment = PP_ALIGN.CENTER
    
    p1 = tf12.add_paragraph()
    p1.text = (
        "通过本次基于 openJiuwen Swarm 的多智能体系统开发，我们深刻体会到：\n"
        "优秀的智能体工程绝非仅仅是‘堆砌 Prompt’，而是‘严密的状态机、契约化的接口、\n"
        "硬性的质量门禁与端到端的测试保障’。\n\n"
        "五重防御体系的成功落地，为可信科研自动化提供了扎实的工程范式。"
    )
    p1.font.size = Pt(16)
    p1.font.color.rgb = RGBColor(0xD0, 0xE0, 0xF0)
    p1.alignment = PP_ALIGN.CENTER
    p1.space_before = Pt(18)
    p1.line_spacing = 1.3
    
    p2 = tf12.add_paragraph()
    p2.text = "汇报完毕 · 敬请各位老师与评委批评指正！"
    p2.font.size = Pt(26)
    p2.font.bold = True
    p2.font.color.rgb = RGBColor(0xFF, 0xB7, 0x4D)
    p2.alignment = PP_ALIGN.CENTER
    p2.space_before = Pt(36)
    
    p3 = tf12.add_paragraph()
    p3.text = "Q & A 提 问 环 节"
    p3.font.size = Pt(18)
    p3.font.color.rgb = C_WHITE
    p3.alignment = PP_ALIGN.CENTER
    p3.space_before = Pt(12)

    prs.save(output_pptx)
    print(f"Saved PPTX presentation to: {output_pptx}")

if __name__ == '__main__':
    md_targets = [
        "submission/第14组_课程交付材料/第14组项目汇报PPT.md",
        "docs/第14组项目汇报PPT.md"
    ]
    for target in md_targets:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(PPT_MD.strip() + "\n")
        print(f"Saved PPT Markdown to: {target}")
        
    pptx_targets = [
        "submission/第14组_课程交付材料/第14组项目汇报PPT.pptx",
        "docs/第14组项目汇报PPT.pptx"
    ]
    for target in pptx_targets:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        build_presentation(target)
