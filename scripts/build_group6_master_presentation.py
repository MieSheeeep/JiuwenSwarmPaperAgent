"""
Generate the master 20-slide PowerPoint presentation for Group 6 (Big Data Practice & openJiuwen Swarm).
Embeds full spoken presentation scripts into speaker notes for every single slide,
inserts architecture diagram images from docs/assets/,
and styles with professional corporate/academic widescreen aesthetics.
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

def build_group6_pptx(output_path):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]
    
    # Color palette
    C_NAVY = RGBColor(0x1B, 0x36, 0x5D)
    C_COBALT = RGBColor(0x28, 0x55, 0x88)
    C_LIGHT_BG = RGBColor(0xF4, 0xF6, 0xF9)
    C_CARD_BG = RGBColor(0xEE, 0xF2, 0xF7)
    C_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
    C_DARK = RGBColor(0x22, 0x22, 0x22)
    C_MUTED = RGBColor(0x66, 0x66, 0x66)
    C_ORANGE = RGBColor(0xD3, 0x54, 0x00)
    C_GREEN = RGBColor(0x27, 0xAE, 0x60)
    C_RED = RGBColor(0xC0, 0x39, 0x2B)

    def set_slide_notes(slide, notes_text):
        notes_slide = slide.notes_slide
        tf = notes_slide.notes_text_frame
        tf.text = notes_text.strip()

    def add_header(slide, title_text, category_text=""):
        banner = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.15))
        banner.fill.solid()
        banner.fill.fore_color.rgb = C_NAVY
        banner.line.fill.background()
        
        if category_text:
            cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.12), Inches(11.7), Inches(0.3))
            p_cat = cat_box.text_frame.paragraphs[0]
            p_cat.text = category_text.upper()
            p_cat.font.size = Pt(10.5)
            p_cat.font.bold = True
            p_cat.font.color.rgb = RGBColor(0x90, 0xCA, 0xF9)
            
        t_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.40), Inches(11.7), Inches(0.65))
        p_t = t_box.text_frame.paragraphs[0]
        p_t.text = title_text
        p_t.font.size = Pt(21)
        p_t.font.bold = True
        p_t.font.color.rgb = C_WHITE

    # ==================== SLIDE 1: COVER ====================
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = C_NAVY
    bg1.line.fill.background()
    
    tbox = s1.shapes.add_textbox(Inches(1.0), Inches(1.6), Inches(11.333), Inches(2.2))
    tf1 = tbox.text_frame
    tf1.word_wrap = True
    
    p0 = tf1.paragraphs[0]
    p0.text = "基于 JiuwenSwarm 的 Agent 科研论文自动生成系统"
    p0.font.size = Pt(36)
    p0.font.bold = True
    p0.font.color.rgb = C_WHITE
    p0.alignment = PP_ALIGN.CENTER
    
    p1 = tf1.add_paragraph()
    p1.text = "大数据项目实践 · 华为 openJiuwen 开源 AI Agent 赛题结题答辩"
    p1.font.size = Pt(18)
    p1.font.color.rgb = RGBColor(0x90, 0xCA, 0xF9)
    p1.alignment = PP_ALIGN.CENTER
    p1.space_before = Pt(14)
    
    c1 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.6), Inches(4.5), Inches(10.133), Inches(2.0))
    c1.fill.solid()
    c1.fill.fore_color.rgb = RGBColor(0x22, 0x43, 0x6E)
    c1.line.color.rgb = RGBColor(0x4A, 0x7E, 0xBB)
    c1.line.width = Pt(1.5)
    
    ctf = c1.text_frame
    ctf.word_wrap = True
    cp1 = ctf.paragraphs[0]
    cp1.text = "汇报小组：第 6 组   |   战队账号：空梦轮年   |   福州大学 计算机与大数据学院"
    cp1.font.size = Pt(15.5)
    cp1.font.bold = True
    cp1.font.color.rgb = C_WHITE
    cp1.alignment = PP_ALIGN.CENTER
    
    cp2 = ctf.add_paragraph()
    cp2.text = "小组成员：金若曦 (102402127)  洪豊幀 (102402124)  黄炜杰 (102402126)  黄俊翔 (102402125)  王智洋 (102402136)"
    cp2.font.size = Pt(13.5)
    cp2.font.color.rgb = RGBColor(0xFF, 0xCC, 0x80)
    cp2.alignment = PP_ALIGN.CENTER
    cp2.space_before = Pt(10)
    
    cp3 = ctf.add_paragraph()
    cp3.text = "核心创新：ICLR 标准闭环 · 可穿透证据链 · Pilot 探针早停 · 双层学术审稿 · openJiuwen 框架贡献"
    cp3.font.size = Pt(12)
    cp3.font.color.rgb = RGBColor(0xB0, 0xC8, 0xE0)
    cp3.alignment = PP_ALIGN.CENTER
    cp3.space_before = Pt(8)

    set_slide_notes(s1, """各位评委老师、同学们，大家好！我们是第6组，战队账号是“空梦轮年”。
今天我们汇报的项目是《基于 JiuwenSwarm 的 Agent 科研论文自动生成系统》。
本项目围绕自主科研智能体（AI Scientist）在实际工程落地中的关键挑战展开，基于华为开源多智能体框架 openJiuwen 与 JiuwenSwarm，构建了一套覆盖“文献调研、研究规划、受控实验、ICLR 级英文论文生成、双层学术内审以及实验级大修”的完整闭环系统。
接下来，我们将按照赛题目标、最终系统设计、核心机制、实验验证以及框架贡献展开详细汇报。""")

    # ==================== SLIDE 2: BACKGROUND ====================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "赛题背景与自主科研 Agent 的工程挑战", "PROBLEM & MOTIVATION")
    
    # 2 Big Cards
    w = Inches(5.6)
    h = Inches(5.6)
    y = Inches(1.5)
    
    # Left Card
    cl2 = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), y, w, h)
    cl2.fill.solid()
    cl2.fill.fore_color.rgb = RGBColor(0xFD, 0xED, 0xEC)
    cl2.line.color.rgb = C_RED
    cl2.line.width = Pt(1.5)
    
    tf_l2 = cl2.text_frame
    tf_l2.word_wrap = True
    p = tf_l2.paragraphs[0]
    p.text = "⚠️ 传统自主科研 Agent 的四大工程断点"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = C_RED
    
    flaws = [
        ("断点 1：立项失控", "缺乏理论增量校验，大模型往往随机开题，极易生成缺乏学术贡献与机制创新的同质化水文。"),
        ("断点 2：算力空耗", "缺乏事前验收与小样本效能探测，方案即便落后于简单传统模型，依然跑满全量大实验，消耗数万 Token 与高昂算力。"),
        ("断点 3：数据幻觉", "实验数据与论文写作严重脱节，正文宣称显著提升，翻开底层日志却查无实据，破坏可复现性。"),
        ("断点 4：浅表修补", "面对外部审稿人批评仅在 Prompt 层面做措辞重写与文字润色，无法反向驱动实验设计与消融修补。")
    ]
    for h_txt, b_txt in flaws:
        p1 = tf_l2.add_paragraph()
        p1.text = f"• {h_txt}"
        p1.font.size = Pt(12.5)
        p1.font.bold = True
        p1.font.color.rgb = RGBColor(0x92, 0x2B, 0x21)
        p1.space_before = Pt(8)
        p2 = tf_l2.add_paragraph()
        p2.text = f"  {b_txt}"
        p2.font.size = Pt(10.5)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(2)

    # Right Card
    cr2 = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), y, w, h)
    cr2.fill.solid()
    cr2.fill.fore_color.rgb = RGBColor(0xEA, 0xFA, 0xEA)
    cr2.line.color.rgb = C_GREEN
    cr2.line.width = Pt(1.5)
    
    tf_r2 = cr2.text_frame
    tf_r2.word_wrap = True
    pr = tf_r2.paragraphs[0]
    pr.text = "🎯 第 6 组工程解法：五重闭环防御体系"
    pr.font.size = Pt(15)
    pr.font.bold = True
    pr.font.color.rgb = C_GREEN
    
    solves = [
        ("前门选题量化准入", "设立理论增量、学术价值与基线风险多维加权准入门禁，杜绝空洞立项。"),
        ("事前验收协议 (StructuredAcceptance)", "实验前代码级锁定效应量极性、最小提升下限与池外基线压制红线，严防科研选择性报告。"),
        ("Pilot 探针与剪枝早停 (PilotGate)", "10%~20% 小样本探针快速辨识弱路线，若被池外默认基准压制立即熔断早停，节约 90%+ 算力。"),
        ("可穿透追溯证据链 (Evidence Artifact)", "正文图表数据强制绑定底层无锁追加日志哈希，杜绝数字编造。"),
        ("顶会双层审稿与实验大修 (DeepRevision)", "ICLR 标尺 4 维量化内审设立 5.0 硬拒稿红线；将审稿缺陷自动转化为追加消融与对比实验代码任务。")
    ]
    for h_txt, b_txt in solves:
        p1 = tf_r2.add_paragraph()
        p1.text = f"✓ {h_txt}"
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = RGBColor(0x19, 0x6F, 0x3D)
        p1.space_before = Pt(7)
        p2 = tf_r2.add_paragraph()
        p2.text = f"  {b_txt}"
        p2.font.size = Pt(10)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(2)

    set_slide_notes(s2, """近年来，以 AI Scientist 为代表的自主科研智能体引发了学界的广泛关注。但将其实际应用于严肃科研任务时，会迅速遇到四大严峻的工程断点：
第一是立项失控：大模型倾向于生成看似宏大但缺乏理论增量（Theoretical Delta）的空洞选题；
第二是算力空耗：由于缺乏早期效能探测，方案即便显著落后于经典基线，依然会机械地跑满全量大实验，带来巨大的算力与 Token 浪费；
第三是数据幻觉：传统流水线中，写作 Agent 往往在缺乏约束的情况下凭空编造实验数据，破坏了学术研究的可复现性；
第四是浅表修补：面对同行评审意见，现有系统多停留于段落重写与修饰性润色，无法真正驱动实验设计的补强。
本项目的核心使命，就是用严格的软件工程规范与自驱质量门禁，攻克这四大断点。""")

    # ==================== SLIDE 3: SCORING ====================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "赛题评分模型与系统工程设计导向", "SCORING MODEL & DESIGN TARGETS")
    
    # 4 Score Cards
    sc_w = Inches(2.7)
    sc_h = Inches(5.3)
    sc_y = Inches(1.5)
    
    scores = [
        ("论文质量 (60分)", "Stanford 盲审 (40分)\n评测 Agent (20分)", C_NAVY, 
         "系统设计靶向：\n• 严格遵循 ICLR 2026 双栏标准排版\n• 必须包含可穿透验证的实证数据\n• 拒绝纯 Prompt 文本拼凑\n• 追求学术自省与严谨论证"),
        ("系统能力 (15分)", "多智能体架构设计\n工具链路与可复现性", C_COBALT,
         "系统设计靶向：\n• 基于 openJiuwen Swarm 事件解耦\n• 状态机严密驱动六阶段流转\n• 角色上下文独立，拒绝信息混淆\n• 提供一键式无密钥复现沙箱"),
        ("资源控制 (10分)", "Token 消耗审计\n算力成本与熔断控制", C_ORANGE,
         "系统设计靶向：\n• 部署 PilotGate 小样本探针\n• 引入池外强基线压制早停机制\n• 实测节约 91.5% Token 预算\n• 每次运行输出可审计资源账单"),
        ("开源贡献 (15分)", "openJiuwen 框架级贡献\n通用 Rail 与组件沉淀", C_GREEN,
         "系统设计靶向：\n• 研发 ContextBudgetRail 预算护栏\n• 研发 VersionedMemory 记忆组件\n• 向上游提供规范补丁与文档\n• 单元测试与基座无缝兼容")
    ]
    for idx, (stitle, ssub, scolor, sdesc) in enumerate(scores):
        sx = Inches(0.8 + idx * 2.95)
        box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, sx, sc_y, sc_w, sc_h)
        box.fill.solid()
        box.fill.fore_color.rgb = C_CARD_BG
        box.line.color.rgb = scolor
        box.line.width = Pt(1.5)
        
        stf = box.text_frame
        stf.word_wrap = True
        
        sp1 = stf.paragraphs[0]
        sp1.text = stitle
        sp1.font.size = Pt(14)
        sp1.font.bold = True
        sp1.font.color.rgb = scolor
        sp1.alignment = PP_ALIGN.CENTER
        
        sp2 = stf.add_paragraph()
        sp2.text = ssub
        sp2.font.size = Pt(11)
        sp2.font.bold = True
        sp2.font.color.rgb = C_ORANGE
        sp2.alignment = PP_ALIGN.CENTER
        sp2.space_before = Pt(4)
        sp2.space_after = Pt(12)
        
        sp3 = stf.add_paragraph()
        sp3.text = sdesc
        sp3.font.size = Pt(10.5)
        sp3.font.color.rgb = C_DARK
        sp3.line_spacing = 1.3

    set_slide_notes(s3, """本次赛题制定了极其严密的量化考核模型，满分 100 分拆解为：论文质量 60 分、系统能力 15 分、资源消耗 10 分，以及 openJiuwen 框架贡献 15 分。
其中，论文质量由 Stanford Agentic Reviewer 盲审系统与官方评测 Agent 双重裁判，这意味着任何未经真实实验支撑的“虚假繁荣”都会直接被顶会评审标准一票否决；同时，资源消耗与框架贡献合计占 25 分，要求系统必须具备优秀的工程算力经济性与扎实的开源生态回哺。
针对这一评分导向，我们确立了系统的核心原则：以真实实验支撑学术论点，以顶会内审约束写作质量，以早停机制封顶计算资源，以框架补丁沉淀核心资产。""")

    # ==================== SLIDE 4: SYSTEM ARCHITECTURE & IMAGE ====================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "最终系统全景方案：端到端闭环科研智能体流水线", "SYSTEM ARCHITECTURE")
    
    # Check if system architecture image exists
    img_arch = "docs/assets/第6组_系统整体架构.png"
    if os.path.exists(img_arch):
        s4.shapes.add_picture(img_arch, Inches(0.8), Inches(1.4), Inches(7.5), Inches(5.6))
        # Right info card
        rc4 = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.5), Inches(1.4), Inches(4.0), Inches(5.6))
        rc4.fill.solid()
        rc4.fill.fore_color.rgb = C_CARD_BG
        rc4.line.color.rgb = C_NAVY
        rc4.line.width = Pt(1.5)
        
        rtf = rc4.text_frame
        rtf.word_wrap = True
        rp = rtf.paragraphs[0]
        rp.text = "六阶段自主推进与状态流转"
        rp.font.size = Pt(14)
        rp.font.bold = True
        rp.font.color.rgb = C_NAVY
        
        items4 = [
            ("1. Literature", "前门文献挖掘与选题量化，计算理论增量 Delta。"),
            ("2. Plan", "签署 StructuredAcceptance，锁定优化极性与最小增量。"),
            ("3. Pilot Gate", "10%~20% 样本探针三态决策，拦截平庸方案。"),
            ("4. Experiment", "全量受控实验，生成可追溯证据链 evidence.json。"),
            ("5. Review & Revise", "Cold Review 事实初筛 + ICLR 4 维内审 + 实验级深修。"),
            ("6. Paper & Export", "标准双栏 LaTeX 编译排版，输出高清 PDF 与代码。")
        ]
        for it_h, it_b in items4:
            p1 = rtf.add_paragraph()
            p1.text = f"▶ {it_h}"
            p1.font.size = Pt(11)
            p1.font.bold = True
            p1.font.color.rgb = C_COBALT
            p1.space_before = Pt(6)
            p2 = rtf.add_paragraph()
            p2.text = f"   {it_b}"
            p2.font.size = Pt(9.5)
            p2.font.color.rgb = C_DARK
            p2.space_before = Pt(1)
    else:
        # Fallback text card
        pass

    set_slide_notes(s4, """屏幕上展示的是第 6 组最终交付的系统全景架构。
系统输入包含研究方向、实验配置以及 Token 预算约束。底层基于我们重构的 AutonomousResearchOrchestrator，统一驱动六大标准阶段：
在文献阶段确定具有理论增量的问题空间；在规划阶段签署结构化验收契约；在实验阶段通过 Pilot 小样本探针执行早停判定，放行后开展全量实验；在审稿阶段执行事实一致性与 ICLR 四维量化内审；在写作阶段编译输出符合顶会排版规范的 LaTeX 论文源码与 PDF。
整个流水线不依赖人工介入，实现了从初始意图到学术论文交付的完全自主闭环。""")

    # ==================== SLIDE 5: MULTI-AGENT SWARM & IMAGE ====================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "基于 openJiuwen Swarm 的多智能体协作拓扑与机制", "MULTI-AGENT SWARM TOPOLOGY")
    
    img_swarm = "docs/assets/第6组_Agent协作架构.png"
    if os.path.exists(img_swarm):
        s5.shapes.add_picture(img_swarm, Inches(0.8), Inches(1.4), Inches(7.5), Inches(5.6))
        rc5 = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.5), Inches(1.4), Inches(4.0), Inches(5.6))
        rc5.fill.solid()
        rc5.fill.fore_color.rgb = C_CARD_BG
        rc5.line.color.rgb = C_COBALT
        rc5.line.width = Pt(1.5)
        
        rtf5 = rc5.text_frame
        rtf5.word_wrap = True
        rp = rtf5.paragraphs[0]
        rp.text = "智能体核心职责与交互解耦"
        rp.font.size = Pt(14)
        rp.font.bold = True
        rp.font.color.rgb = C_NAVY
        
        roles = [
            ("OrchestratorAgent", "总控调度中枢，驱动状态转移、事件推送与断点续跑。"),
            ("LiteratureAgent", "前沿学术文献收敛与背景知识图谱构建。"),
            ("PlanningAgent", "研究假设参数化、基线设计与事前契约签署。"),
            ("ExperimentAgent", "沙箱受控代码执行、探针方差与模型压制检测。"),
            ("ReviewAgent Panel", "三位一体评审团：事实初筛、4 维内审、实验深修。"),
            ("WritingAgent", "学术论证组织、ICLR 模板渲染与正文插值防伪。")
        ]
        for it_h, it_b in roles:
            p1 = rtf5.add_paragraph()
            p1.text = f"★ {it_h}"
            p1.font.size = Pt(10.5)
            p1.font.bold = True
            p1.font.color.rgb = C_COBALT
            p1.space_before = Pt(5)
            p2 = rtf5.add_paragraph()
            p2.text = f"   {it_b}"
            p2.font.size = Pt(9.5)
            p2.font.color.rgb = C_DARK
            p2.space_before = Pt(1)

    set_slide_notes(s5, """在智能体协作层面，我们依托 openJiuwen 框架实现了细粒度的角色职能解耦与上下文隔离。
很多多智能体系统容易退化为一个单一的大 Context 对话历史，导致各角色认知混淆。我们设计了 ConnectedProfile 拓扑机制：
调度中枢负责推进状态转移并触发异步事件；文献智能体专注于收敛前沿文献空间；规划智能体负责定义形式化方法；实验智能体通过受控适配器调度真实计算工具；审稿委员会独立行使评审裁决权；写作智能体则依据已锁定的证据链编撰论文。
每个 Agent 拥有独立的 Prompt System、工具集与输入输出约束，确保系统在高并发多步推演下保持高度的逻辑确定性。""")

    # ==================== SLIDE 6: TOPIC & HYPOTHESIS ====================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "前门选题与研究规划：假设空间的形式化参数映射", "TOPIC SELECTION & PARAMETERIZATION")
    
    # 2 Cards
    c6_l = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.3))
    c6_l.fill.solid()
    c6_l.fill.fore_color.rgb = C_CARD_BG
    c6_l.line.color.rgb = C_NAVY
    c6_l.line.width = Pt(1.5)
    
    tf6_l = c6_l.text_frame
    tf6_l.word_wrap = True
    p = tf6_l.paragraphs[0]
    p.text = "📊 前门选题量化打分模型"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    p_f = tf6_l.add_paragraph()
    p_f.text = "Score = 0.35·Δ_theo + 0.25·S + 0.25·N - 0.15·R_base"
    p_f.font.size = Pt(12)
    p_f.font.bold = True
    p_f.font.color.rgb = C_ORANGE
    p_f.space_before = Pt(8)
    p_f.space_after = Pt(10)
    
    p_pts = [
        ("理论增量分 (Δ_theo, 35%)", "评估方法相对现有工作的机制突破，严防空洞微调。"),
        ("学术重要性 (S, 25%)", "考察是否触及领域核心瓶颈，有无实用价值。"),
        ("学术新颖性 (N, 25%)", "与近 3 年顶会文献的差异度与开拓性。"),
        ("基线风险系数 (R_base, 15%)", "被经典简单基线逆风翻盘的概率，高风险扣分。"),
        ("准入门禁判定", "综合得分 < 6.0 或任一单项 < 5.0，一票否决淘汰！")
    ]
    for h_txt, b_txt in p_pts:
        p1 = tf6_l.add_paragraph()
        p1.text = f"• {h_txt}"
        p1.font.size = Pt(11.5)
        p1.font.bold = True
        p1.font.color.rgb = C_NAVY
        p1.space_before = Pt(6)
        p2 = tf6_l.add_paragraph()
        p2.text = f"  {b_txt}"
        p2.font.size = Pt(10)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(1)

    c6_r = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.3))
    c6_r.fill.solid()
    c6_r.fill.fore_color.rgb = C_CARD_BG
    c6_r.line.color.rgb = C_COBALT
    c6_r.line.width = Pt(1.5)
    
    tf6_r = c6_r.text_frame
    tf6_r.word_wrap = True
    pr = tf6_r.paragraphs[0]
    pr.text = "🔬 学术假设参数化（杜绝伪科学猜想）"
    pr.font.size = Pt(15)
    pr.font.bold = True
    pr.font.color.rgb = C_COBALT
    
    hypos = [
        ("自变量显式参数化", "将自然语言假设映射为严格策略集（例如长上下文配置历史：All History vs Recent Window vs Retrieval vs Retrieval+Summary）。"),
        ("因变量与优化极性", "明确定义评估指标（Accuracy, MSE, Token Cost），锁定极性为 minimize 或 maximize。"),
        ("控制变量基线化", "统一底层推理基座、提示词格式、数据规模与随机种子集合，杜绝外部环境干扰。"),
        ("可证伪性闭环", "每项假设在启动前必须具备形式化数学对偶描述，无法在代码层面被证伪的假设直接阻断在立项阶段。")
    ]
    for h_txt, b_txt in hypos:
        p1 = tf6_r.add_paragraph()
        p1.text = f"★ {h_txt}"
        p1.font.size = Pt(11.5)
        p1.font.bold = True
        p1.font.color.rgb = C_COBALT
        p1.space_before = Pt(8)
        p2 = tf6_r.add_paragraph()
        p2.text = f"  {b_txt}"
        p2.font.size = Pt(10)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(1)

    set_slide_notes(s6, """针对传统系统“盲目开题”的顽疾，我们在规划阶段引入了形式化的前门量化模型。
系统拒绝无边界的模糊立项，而是从理论增量、学术重要性、新颖性与基线风险四个维度对候选方案进行加权评分，设立 6.0 分准入门禁。
更关键的是，系统在进入实验前必须完成“假设空间的参数化”：明确将自然语言的学术假设映射为严格的数学自变量、因变量与控制变量。例如在上下文记忆研究中，严格规定比较集合为“全量历史、滑动窗口、检索机制以及检索摘要混合”，并将度量指标锚定为绝对准确率与 Token 开销比。这一机制从源头上阻断了不可检验伪科学假设的产生。""")

    # ==================== SLIDE 7: STRUCTURED ACCEPTANCE ====================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "结构化事前验收协议 (StructuredAcceptance)", "DESIGN BY CONTRACT: PRE-REGISTRATION")
    
    b7 = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.3))
    b7.fill.solid()
    b7.fill.fore_color.rgb = C_CARD_BG
    b7.line.color.rgb = C_NAVY
    b7.line.width = Pt(1.5)
    
    tf7 = b7.text_frame
    tf7.word_wrap = True
    p = tf7.paragraphs[0]
    p.text = "📜 预注册（Pre-registration）机制：杜绝“先射箭再画靶心”"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    p_desc = tf7.add_paragraph()
    p_desc.text = "在软件工程中，测试驱动开发要求“先写测试用例，再写业务实现”；同样，严肃科研必须在实验执行前签署数据契约，强行在代码层面锁定验收红线，杜绝 p-hacking 和选择性报告："
    p_desc.font.size = Pt(11.5)
    p_desc.font.color.rgb = C_DARK
    p_desc.space_before = Pt(6)
    p_desc.space_after = Pt(12)
    
    contracts = [
        ("1. 最小效应增量 (min_delta)", "规定新算法相比基线必须取得的绝对提升幅度（如准确率 >= 0.05，MSE 降低 >= 0.05），杜绝将微弱抖动包装为算法突破。"),
        ("2. 优化极性锁定 (metric_direction)", "显式注册指标极性（'minimize' 或 'maximize'），严禁实验后随意掉包或解释反向指标。"),
        ("3. 池外基线压制红线 (oop_domination_margin)", "强制引入未参与调优的现成强模型（如 HistGradientBoosting, Random Forest）。若新方法连默认模型都无法超越，立刻认定为无效工作。"),
        ("4. 统计方差校验阈值 (max_acceptable_variance)", "约束多折交叉验证抖动范围，剔除由随机种子波动带来的虚假提升。")
    ]
    for c_title, c_desc in contracts:
        pt = tf7.add_paragraph()
        pt.text = f"▶ {c_title}"
        pt.font.size = Pt(12.5)
        pt.font.bold = True
        pt.font.color.rgb = C_COBALT
        pt.space_before = Pt(8)
        
        pd = tf7.add_paragraph()
        pd.text = f"   {c_desc}"
        pd.font.size = Pt(10.5)
        pd.font.color.rgb = C_DARK
        pd.space_before = Pt(2)

    set_slide_notes(s7, """现代软件工程推崇“测试驱动开发”，而严肃科学研究必须奉行“预注册（Pre-registration）”。为了杜绝 AI 科研中常见的“先射箭后画靶心”与选择性报告（p-hacking），我们在系统中引入了 StructuredAcceptance 结构化事前验收协议。
在实验代码启动之前，规划智能体必须与环境签署数据契约，白纸黑字锁定四个核心参数：
其一是最小效应量 min_delta，明确新算法相较于 baseline 必须达到的绝对超越下限；
其二是指标极性，锁定优化方向；
其三是最大容许方差比，防范种子漂移假象；
其四是开创性地引入了池外基线压制红线。这保证了所有实验产出都在防作弊的严密监督下进行。""")

    # ==================== SLIDE 8: EVIDENCE ARTIFACT ====================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "实验适配执行与可穿透追溯证据链 (Evidence Artifact)", "TRACEABLE EVIDENCE CHAIN")
    
    # 2 Columns
    c8_l = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.3))
    c8_l.fill.solid()
    c8_l.fill.fore_color.rgb = C_CARD_BG
    c8_l.line.color.rgb = C_NAVY
    c8_l.line.width = Pt(1.5)
    
    tf8_l = c8_l.text_frame
    tf8_l.word_wrap = True
    p = tf8_l.paragraphs[0]
    p.text = "🔗 可穿透溯源数据闭环架构"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    ev_steps = [
        ("Raw Sandboxed Execution", "实验代码运行于受控沙箱，记录进程 PID、依赖版本、硬件环境与随机种子。"),
        ("Append-only JSONL Logging", "每次模型调用与指标输出生成唯一 SHA-256 哈希，日志只允许追加，严禁覆写篡改。"),
        ("Structured evidence.json", "自动提取多轮实验宏观均值、标准差、样本级明细与 Token 账单明细。"),
        ("Latex Table Interpolation", "论文表格数据通过模板标签与 evidence.json 强绑定，直接生成排版。")
    ]
    for h_txt, b_txt in ev_steps:
        p1 = tf8_l.add_paragraph()
        p1.text = f"• {h_txt}"
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = C_COBALT
        p1.space_before = Pt(8)
        p2 = tf8_l.add_paragraph()
        p2.text = f"  {b_txt}"
        p2.font.size = Pt(10)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(2)

    c8_r = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.3))
    c8_r.fill.solid()
    c8_r.fill.fore_color.rgb = RGBColor(0xEA, 0xFA, 0xEA)
    c8_r.line.color.rgb = C_GREEN
    c8_r.line.width = Pt(1.5)
    
    tf8_r = c8_r.text_frame
    tf8_r.word_wrap = True
    pr = tf8_r.paragraphs[0]
    pr.text = "🛡️ 杜绝数据幻觉：Zero-Hallucination 机制"
    pr.font.size = Pt(15)
    pr.font.bold = True
    pr.font.color.rgb = C_GREEN
    
    zh_points = [
        ("正文剥夺数值编写自由", "写作 Agent 不允许直接在 prompt 中凭空输出浮点数指标，必须声明数据取值路径。"),
        ("断言比对校验器", "渲染后的 LaTeX 源码经由验证脚本扫描，正文内所有数字必须能在 evidence.json 中命中哈希，否则阻断编译。"),
        ("真实计算账本存档", "记录 24 个合成任务、96 次作答、120 次 API 调用的全流程原始请求与响应报文。"),
        ("100% 可审计与可复现", "外部评审专家可根据证据链中的调用链完整重放实验，确保结论坚实可信。")
    ]
    for h_txt, b_txt in zh_points:
        p1 = tf8_r.add_paragraph()
        p1.text = f"✓ {h_txt}"
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = RGBColor(0x19, 0x6F, 0x3D)
        p1.space_before = Pt(8)
        p2 = tf8_r.add_paragraph()
        p2.text = f"  {b_txt}"
        p2.font.size = Pt(10)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(2)

    set_slide_notes(s8, """传统科研 Agent 生成论文最令人诟病的就是“数据幻觉”：正文写着性能提升了 15%，翻开实验日志却查无实据。
为此，我们构建了一套可穿透溯源的 Evidence 证据体系。实验适配器在沙箱中调度真实代码运行，每一次推演与评测都会生成唯一的执行哈希，并落盘至无锁追加的日志文件中。
最终汇聚成的 evidence.json 不仅记录了宏观均值，更保留了样本级明细与 Token 消耗审计。写作智能体在组织论文时，被强制剥夺了直接编写浮点数的自由，所有正文指标必须通过模板插值从证据链中提取，并经由校验器核验。这实现了科研成果在代码层面的 100% 可复现与可审计。""")

    # ==================== SLIDE 9: ICLR WRITING ====================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "ICLR 导向的学术论文自主写作系统与 LaTeX 编译", "ICLR ACADEMIC WRITING SYSTEM")
    
    b9 = s9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.3))
    b9.fill.solid()
    b9.fill.fore_color.rgb = C_CARD_BG
    b9.line.color.rgb = C_NAVY
    b9.line.width = Pt(1.5)
    
    tf9 = b9.text_frame
    tf9.word_wrap = True
    p = tf9.paragraphs[0]
    p.text = "📑 国际顶会标准论文生成技术规格"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    specs9 = [
        ("官方双栏宏包排版", "接入 ICLR 2026 官方标准双栏会议宏包（iclr2026_conference.sty），严格对齐页边距、字号与段落间距规范。"),
        ("八大核心章节严密展开", "Abstract, Introduction, Related Work, Problem Formulation, Method, Experiments, Discussion, Conclusion 逻辑自洽递进。"),
        ("BibTeX 引用双向闭环", "内建 BibTeX 语法校验器，强制确保正文引用（\\citet, \\citep）与参考文献库完全对应，杜绝虚构文献。"),
        ("自动矢量图表布局", "由实验脚本自动输出高清矢量图（results_figure.pdf）与三线表（Booktabs 规范），动态植入 LaTeX 源工程。"),
        ("编译产物一览", "输出包含 paper.pdf 高清排版文档、paper.tex 完整 LaTeX 源码工程以及各章节结构化 JSON 资产。")
    ]
    for s_title, s_desc in specs9:
        pt = tf9.add_paragraph()
        pt.text = f"▶ {s_title}"
        pt.font.size = Pt(12.5)
        pt.font.bold = True
        pt.font.color.rgb = C_COBALT
        pt.space_before = Pt(8)
        
        pd = tf9.add_paragraph()
        pd.text = f"   {s_desc}"
        pd.font.size = Pt(10.5)
        pd.font.color.rgb = C_DARK
        pd.space_before = Pt(2)

    set_slide_notes(s9, """针对赛题对国际高水平会议论文的交付要求，我们研发了对标 ICLR 规范的自主学术写作引擎。
区别于普通的 Markdown 文本拼接，系统内建了完整的 LaTeX 编译支持体系，原生遵循 ICLR 官方双栏排版规范。
写作智能体按照学术论文的标准逻辑结构组织论证，从问题陈述、数学形式化到实验对比展开严密叙述。系统内嵌的引用合规模块负责检查 BibTeX 键值映射，杜绝虚假文献引用；同时，实验生成的矢量分布图与消融对比表会自动完成排版布局。最终输出的产物不仅是一份可以直接阅读的 PDF，更是包含完整样式表与源码的标准化论文工程包。""")

    # ==================== SLIDE 10: DUAL-TIER REVIEW ====================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "顶会级双层审稿体系：事实初筛与 4 维量化内审", "DUAL-TIER ACADEMIC REVIEW SYSTEM")
    
    # 2 Review Cards
    c10_l = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.3))
    c10_l.fill.solid()
    c10_l.fill.fore_color.rgb = C_CARD_BG
    c10_l.line.color.rgb = C_COBALT
    c10_l.line.width = Pt(1.5)
    
    tf10_l = c10_l.text_frame
    tf10_l.word_wrap = True
    p = tf10_l.paragraphs[0]
    p.text = "🔍 Tier 1: Cold Review（事实一致性初筛）"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = C_COBALT
    
    c10_items = [
        ("事实穿透扫描", "直接对照底层 evidence.json 逐行核对正文数据，拦截指标抄写错误。"),
        ("过度声称拦截 (Overclaim)", "识别正文中缺乏实验证据支撑的泛化性夸大结论，标记为事实违规。"),
        ("数据泄露筛查", "检查训练集与测试集边界、滑动窗口历史是否有未定义标签泄露。"),
        ("初筛挂起机制", "若发现重大事实硬伤，不予进入后续阶段，直接挂起触发初级返修。")
    ]
    for h_txt, b_txt in c10_items:
        p1 = tf10_l.add_paragraph()
        p1.text = f"• {h_txt}"
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = C_COBALT
        p1.space_before = Pt(8)
        p2 = tf10_l.add_paragraph()
        p2.text = f"  {b_txt}"
        p2.font.size = Pt(10)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(2)

    c10_r = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.3))
    c10_r.fill.solid()
    c10_r.fill.fore_color.rgb = C_CARD_BG
    c10_r.line.color.rgb = C_NAVY
    c10_r.line.width = Pt(1.5)
    
    tf10_r = c10_r.text_frame
    tf10_r.word_wrap = True
    pr = tf10_r.paragraphs[0]
    pr.text = "⚖️ Tier 2: Conference Review Panel（顶会内审）"
    pr.font.size = Pt(15)
    pr.font.bold = True
    pr.font.color.rgb = C_NAVY
    
    pan_items = [
        ("三位一体评审团", "模拟真实学术会议多审稿人（理论专家、创新裁判、实证质检员）联合评审。"),
        ("ICLR 4 维量化标尺", "在 Soundness、Novelty、Significance、Empirical Thoroughness 四大维度独立赋分。"),
        ("详细审稿意见集", "输出 Summary of Contributions、Strengths、Weaknesses 与 Questions。"),
        ("裁决决策输出", "综合打分生成 Clear Accept, Weak Accept, 或一票否决 Reject 判定。")
    ]
    for h_txt, b_txt in pan_items:
        p1 = tf10_r.add_paragraph()
        p1.text = f"★ {h_txt}"
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = C_NAVY
        p1.space_before = Pt(8)
        p2 = tf10_r.add_paragraph()
        p2.text = f"  {b_txt}"
        p2.font.size = Pt(10)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(2)

    set_slide_notes(s10, """为了避免“论文生成后缺乏自省”的问题，我们构建了业内首创的双层学术内审体系。
第一层是 Cold Review（事实一致性初筛）：该智能体充当严苛的事实审计员，直接对照底层证据链扫描论文全篇。一旦发现正文存在未经实验支持的推论（Overclaim）、指标抄写误差或数据泄露，直接在初筛阶段挂起返修，绝不让带病稿件进入后续环节。
第二层是 ConferenceReviewPanel（顶会量化内审面板）：模拟真实学术会议的 Peer Review 机制，由多位具有不同评审偏好的虚拟评审专家，对通过初筛的论文展开独立深度的同行评议。""")

    # ==================== SLIDE 11: 4 DIMENSIONS & HARD FLOOR ====================
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "ICLR 4 维评审指标与硬底线裁决机制 (Hard Floor)", "4-DIMENSIONAL RUBRICS & HARD FLOOR")
    
    r_w = Inches(2.7)
    r_h = Inches(5.3)
    r_y = Inches(1.5)
    
    dims11 = [
        ("Soundness\n技术完备性 (30%)", "考察要点：\n• 数学推导是否严谨自洽\n• 实验方法有无未来信息泄露\n• 评估指标是否符合领域共识\n\n硬底线阈值：\n< 5.0 一票否决拒稿"),
        ("Novelty\n创新独特性 (25%)", "考察要点：\n• 相对于现有 SOTA 的理论 Delta\n• 是机制创新还是浅表工程拼凑\n• 学术界前沿差异度\n\n硬底线阈值：\n< 5.0 一票否决拒稿"),
        ("Significance\n学术价值 (20%)", "考察要点：\n• 是否推动了核心瓶颈的解决\n• 结论是否具备可推广性与泛化度\n• 能否启发后续研究\n\n硬底线阈值：\n< 5.0 一票否决拒稿"),
        ("Empirical\n实证充分性 (25%)", "考察要点：\n• 消融实验与对照基线是否齐全\n• 统计检验是否具备显著性\n• 多随机种子误差界与方差\n\n硬底线阈值：\n< 5.0 一票否决拒稿")
    ]
    for idx, (title, content) in enumerate(dims11):
        rx = Inches(0.8 + idx * 2.95)
        rbox = s11.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, rx, r_y, r_w, r_h)
        rbox.fill.solid()
        rbox.fill.fore_color.rgb = C_CARD_BG
        rbox.line.color.rgb = C_NAVY
        rbox.line.width = Pt(1.5)
        
        rtf = rbox.text_frame
        rtf.word_wrap = True
        
        rp = rtf.paragraphs[0]
        rp.text = title
        rp.font.size = Pt(13.5)
        rp.font.bold = True
        rp.font.color.rgb = C_NAVY
        rp.alignment = PP_ALIGN.CENTER
        
        rc = rtf.add_paragraph()
        rc.text = content
        rc.font.size = Pt(10.5)
        rc.font.color.rgb = C_DARK
        rc.space_before = Pt(12)
        rc.line_spacing = 1.3

    set_slide_notes(s11, """在内审面板的标准设定上，我们严密对标了 ICLR 与 NeurIPS 的官方审稿规范，拆解为四大核心维度：
Soundness 考察技术与逻辑自洽性；Novelty 评估理论增量与独特性；Significance 衡量学术价值；Empirical Thoroughness 评估实证的充分程度。
与市面上常见的模糊打分智能体不同，我们设立了极具约束力的 Hard Floor（硬底线拒稿机制）：哪怕论文综合得分看起来尚可，但只要在 Novelty 或 Empirical 等关键维度跌破 5.0 分，系统便无条件触发一票否决。这确保了系统绝不产出“文字优美但内质空洞”的平庸成果。""")

    # ==================== SLIDE 12: DEEP REVISION ====================
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, "评审反馈驱动的深层大修回路 (DeepRevision 实验级修补)", "DEEP REVISION: CODE-LEVEL EXPERIMENTAL REPAIR")
    
    # 2 Comparison Columns
    col_w = Inches(5.6)
    col_h = Inches(5.3)
    col_y = Inches(1.5)
    
    # Old
    b12_l = s12.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), col_y, col_w, col_h)
    b12_l.fill.solid()
    b12_l.fill.fore_color.rgb = RGBColor(0xFD, 0xED, 0xEC)
    b12_l.line.color.rgb = C_RED
    b12_l.line.width = Pt(1.5)
    
    tf12_l = b12_l.text_frame
    tf12_l.word_wrap = True
    p = tf12_l.paragraphs[0]
    p.text = "❌ 传统 Agent 缺陷修改模式（浅表文字修补）"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_RED
    
    flaw_pts = [
        "审稿意见指出缺少消融或得分低，仅将意见拼入 Prompt",
        "要求大模型'重新润色 Introduction 和 Conclusion'",
        "底层实验数据没有任何变动，纯属掩耳盗铃",
        "在外部严苛盲审中被一眼识破，遭遇更严厉拒稿"
    ]
    for fp in flaw_pts:
        p1 = tf12_l.add_paragraph()
        p1.text = f"• {fp}"
        p1.font.size = Pt(11.5)
        p1.font.color.rgb = C_DARK
        p1.space_before = Pt(10)
        
    # Ours
    b12_r = s12.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), col_y, col_w, col_h)
    b12_r.fill.solid()
    b12_r.fill.fore_color.rgb = RGBColor(0xEA, 0xFA, 0xEA)
    b12_r.line.color.rgb = C_GREEN
    b12_r.line.width = Pt(1.5)
    
    tf12_r = b12_r.text_frame
    tf12_r.word_wrap = True
    pr = tf12_r.paragraphs[0]
    pr.text = "⭐ 本项目 DeepRevisionManager（实验级深修）"
    pr.font.size = Pt(14)
    pr.font.bold = True
    pr.font.color.rgb = C_GREEN
    
    rev_pts = [
        "Weaknesses 语义解析：提取结构化缺陷并归类为代码修复任务",
        "自动生成 RevisionPlan：明确指定需补齐的实验类型与模块",
        "动作一：自动补齐消融实验：调度 ExperimentAgent 运行切除特定组件的消融计算，更新证据链",
        "动作二：自动追加强基线对比：加载 LightGBM、MLP 等对比曲线，以实证夯实学术论据",
        "重构正文与图表：在真实实验充实后，驱动写作层重新渲染双栏论文"
    ]
    for rp in rev_pts:
        p1 = tf12_r.add_paragraph()
        p1.text = f"✓ {rp}"
        p1.font.size = Pt(11)
        p1.font.color.rgb = RGBColor(0x19, 0x6F, 0x3D)
        p1.space_before = Pt(8)

    set_slide_notes(s12, """面对审稿人提出的负面意见，传统的科研 Agent 往往只是简单地把批评意见作为上下文塞给大模型，让其重写引言或结论，这在学术上属于典型的掩耳盗铃。
本项目研发了 DeepRevisionManager（实验级深层大修系统）。当内审专家指出“缺乏关键模块的剥离验证”或“未与强基准对比”时，系统会将该 Weakness 自动转化为形式化的实验维修工单。
调度引擎会自动唤醒实验智能体，在沙箱环境中动态补齐对应组件的消融计算，并将新生成的对比曲线追加注入证据知识库。随后，撰写模块基于充实后的全新实验数据重新绘制图表、更新正文论述。这种以真实代码和实验为支点的深层修复，实现了真正意义上的自主科研自我进化。""")

    # ==================== SLIDE 13: PILOT GATE ====================
    s13 = prs.slides.add_slide(blank_layout)
    add_header(s13, "算力控制与 PilotGate 小样本早停剪枝机制", "RESOURCE CONTROL: PILOT GATE & PRUNING")
    
    # 2 Cards
    c13_l = s13.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.3))
    c13_l.fill.solid()
    c13_l.fill.fore_color.rgb = C_CARD_BG
    c13_l.line.color.rgb = C_NAVY
    c13_l.line.width = Pt(1.5)
    
    tf13_l = c13_l.text_frame
    tf13_l.word_wrap = True
    p = tf13_l.paragraphs[0]
    p.text = "⚙️ PilotGate 三态决策状态机"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    states13 = [
        ("GO（放行）", "探针效应量显著达标，且全面压制池外基线；放行进入全量主实验。", C_GREEN),
        ("PIVOT（自适应重测）", "方差处于收敛边缘或超参未拟合；自适应微调学习率后执行复测。", C_ORANGE),
        ("NO_GO（主动剪枝早停）", "检测到候选方法被池外弱基线压制；直接置为 'pruned' 终止执行。", C_RED)
    ]
    for s_name, s_desc, s_color in states13:
        p1 = tf13_l.add_paragraph()
        p1.text = f"● {s_name}"
        p1.font.size = Pt(12.5)
        p1.font.bold = True
        p1.font.color.rgb = s_color
        p1.space_before = Pt(10)
        p2 = tf13_l.add_paragraph()
        p2.text = f"  {s_desc}"
        p2.font.size = Pt(10.5)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(2)

    c13_r = s13.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.3))
    c13_r.fill.solid()
    c13_r.fill.fore_color.rgb = RGBColor(0xFD, 0xF2, 0xE9)
    c13_r.line.color.rgb = C_ORANGE
    c13_r.line.width = Pt(1.5)
    
    tf13_r = c13_r.text_frame
    tf13_r.word_wrap = True
    pr = tf13_r.paragraphs[0]
    pr.text = "📈 真实特征缺失研究实测数据与算力收益"
    pr.font.size = Pt(15)
    pr.font.bold = True
    pr.font.color.rgb = C_ORANGE
    
    p_log = tf13_r.add_paragraph()
    p_log.text = (
        "[实测终端日志]\n"
        "• 候选方案 Pilot MSE: 0.3901\n"
        "• 池外基线 (HistGradientBoosting) MSE: 0.0498\n"
        "• 性能差距 Gap: 0.3402 (远远劣于基准，阈值 0.05)\n"
        "• PilotGate 判定: no_go -> 立即主动剪枝 (status: pruned)\n\n"
        "💰 算力开销审计对比：\n"
        "• 未剪枝盲目执行：消耗 >100,000 Token，耗时 12 分钟\n"
        "• PilotGate 剪枝早停：仅消耗 8,531 Token，耗时 25 秒\n"
        "• 实际算力节约：高达 91.5% Token 预算！"
    )
    p_log.font.size = Pt(11)
    p_log.font.color.rgb = C_DARK
    p_log.space_before = Pt(8)
    p_log.line_spacing = 1.25

    set_slide_notes(s13, """赛题设立了 10 分的资源消耗控制考核，而在现实科研中，算力预算更是至关重要的硬约束。为此，我们在主实验之前部署了 PilotGate 方差探针与剪枝早停机制。
算法在规划完成后，首先仅抽取 10% 到 20% 的微量小样本运行探针测试，输出三态决策。
屏幕上展示了一组我们在特征缺失任务中的真实实测数据：在小样本探针阶段，系统测得候选算法的 MSE 为 0.3901，而未经调优的传统弱基线 HistGradientBoosting 仅为 0.0498。系统瞬间检测到候选算法被池外模型严重压制，落后幅度达 0.34，远超预设容忍度。
PilotGate 果断判定为 no_go，状态机立即置为 pruned 早停退出。单次任务仅消耗 8,531 Token 便完成了证伪，相比盲目执行全量大实验节约了超过 91.5% 的算力开销。这充分证明了我们的系统具备高度理性的算力自觉。""")

    # ==================== SLIDE 14: EMPIRICAL CASE ====================
    s14 = prs.slides.add_slide(blank_layout)
    add_header(s14, "核心研究案例实证：长上下文记忆与缺失特征研究", "EMPIRICAL RESEARCH CASE STUDIES")
    
    # 2 Study Cards
    c14_l = s14.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.3))
    c14_l.fill.solid()
    c14_l.fill.fore_color.rgb = C_CARD_BG
    c14_l.line.color.rgb = C_NAVY
    c14_l.line.width = Pt(1.5)
    
    tf14_l = c14_l.text_frame
    tf14_l.word_wrap = True
    p = tf14_l.paragraphs[0]
    p.text = "📘 案例一：长上下文配置历史的选择机制研究"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    cs1_pts = [
        ("研究课题", "探索智能体在长周期配置交互中维持一致性的最优历史选择策略。"),
        ("对比实验组", "All History（全量） vs Recent Window（最近窗口） vs Retrieval（检索） vs Retrieval+Summary（检索加摘要）。"),
        ("实证规模", "24 个合成任务、96 次作答、120 次真实 API 调用。"),
        ("核心实验结论", "检索与摘要混合策略以仅 25% 的上下文窗口消耗取得了 100% 正确率，而滑动窗口由于断裂早期依赖骤降至 25%！"),
        ("交付成果", "完整编译生成 ICLR 论文、高清矢量折线图与证据链。")
    ]
    for h_txt, b_txt in cs1_pts:
        p1 = tf14_l.add_paragraph()
        p1.text = f"• {h_txt}"
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = C_COBALT
        p1.space_before = Pt(6)
        p2 = tf14_l.add_paragraph()
        p2.text = f"  {b_txt}"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(1)

    c14_r = s14.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.3))
    c14_r.fill.solid()
    c14_r.fill.fore_color.rgb = C_CARD_BG
    c14_r.line.color.rgb = C_COBALT
    c14_r.line.width = Pt(1.5)
    
    tf14_r = c14_r.text_frame
    tf14_r.word_wrap = True
    pr = tf14_r.paragraphs[0]
    pr.text = "📙 案例二：缺失数据下的自适应特征重构研究"
    pr.font.size = Pt(14)
    pr.font.bold = True
    pr.font.color.rgb = C_COBALT
    
    cs2_pts = [
        ("研究课题", "针对高维工业表格数据特征随机缺失下的自适应补齐与预测建模。"),
        ("门禁实战验证", "重点用于检验 PilotGate 在极端劣势条件下的风险感知与剪枝反应。"),
        ("实战结果", "在小样本阶段敏锐捕获性能缺陷，成功触发池外模型压制门禁，完成毫秒级早停。"),
        ("避免无效产出", "有效拦截了在缺乏竞争力的算法路线上生成平庸论文的潜在风险。")
    ]
    for h_txt, b_txt in cs2_pts:
        p1 = tf14_r.add_paragraph()
        p1.text = f"★ {h_txt}"
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = C_COBALT
        p1.space_before = Pt(8)
        p2 = tf14_r.add_paragraph()
        p2.text = f"  {b_txt}"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(1)

    set_slide_notes(s14, """在实际课题的研究验证中，我们开展了多个具有真实学术价值的主题实证。
其中最具代表性的是“长上下文配置历史的选择机制研究”。该课题针对智能体在长周期交互中容易发生上下文膨胀与记忆遗忘的问题，系统自主设计了全量历史、滑动窗口、单纯检索与检索加摘要四类对照组。
真实实验执行了 24 个合成任务与 120 次真实大模型 API 交互。实验清晰表明：混合检索与摘要机制能够有效消除干扰噪声，在压缩 75% 显存上下文占用的前提下维持了 100% 的准确率，而传统滑动窗口由于丢失早期全局依赖导致准确率断崖式跌落至 25%。该研究不仅提供了扎实的统计图表，更完整走通了从文献调研到 ICLR 论文生成的全部链条。""")

    # ==================== SLIDE 15: EXTERNAL REVIEW ====================
    s15 = prs.slides.add_slide(blank_layout)
    add_header(s15, "外部学术盲审 (Stanford Agentic Reviewer) 评测与客观复盘", "EXTERNAL PEER REVIEW & REFLECTION")
    
    b15 = s15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.3))
    b15.fill.solid()
    b15.fill.fore_color.rgb = C_CARD_BG
    b15.line.color.rgb = C_NAVY
    b15.line.width = Pt(1.5)
    
    tf15 = b15.text_frame
    tf15.word_wrap = True
    p = tf15.paragraphs[0]
    p.text = "🏛️ 接入赛题官方指定第三方盲审服务：Stanford Agentic Reviewer"
    p.font.size = Pt(15.5)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    ext_items = [
        ("真实异步盲审对接", "通过官方真实 Access Token 完成送审，完全脱离人工主观干预，接收无偏见的机器评审报告。"),
        ("真实盲审评分结果", "初版论文获得 Estimated Score: 4.4 ~ 4.5 / 10，在 ICLR 官方严苛标尺下被判定处于 Reject 边缘。"),
        ("核心评审意见剖析 (Weaknesses)", "1. 实验数据多基于合成任务，未充分验证现实世界极端噪声下的泛化性；\n2. 对比基准主要采用规则与轻量策略，缺乏与当前 SOTA 深度模型的同台消融。"),
        ("工程复盘与架构自省", "外部真实低分揭示了传统科研 Agent 的通病——仅把论文格式做对是远远不够的！正是外部盲审的严苛打分，促使我们坚决研发前门选题准入、顶会 4 维量化内审与 DeepRevision 实验大修回路。")
    ]
    for e_h, e_b in ext_items:
        pt = tf15.add_paragraph()
        pt.text = f"▶ {e_h}"
        pt.font.size = Pt(12)
        pt.font.bold = True
        pt.font.color.rgb = C_COBALT
        pt.space_before = Pt(8)
        pd = tf15.add_paragraph()
        pd.text = f"   {e_b}"
        pd.font.size = Pt(10)
        pd.font.color.rgb = C_DARK
        pd.space_before = Pt(2)

    set_slide_notes(s15, """在科研成果的质量验收上，我们坚持实事求是的软件工程态度，拒绝任何自我封闭的自嗨。我们将生成的学术论文提交至赛题官方推荐的 Stanford Agentic Reviewer 进行了真实的第三方学术盲审。
审稿系统在无人工干预的情况下，给出了 4.4 到 4.5 分的严厉评价，并给出了详尽的拒稿反馈。评审专家尖锐地指出：尽管论文结构完整、格式精良，但实验环境受限于合成数据集，且对比基线偏向于规则策略，缺乏对最新深度表征算法的消融支撑。
这一宝贵的真实外部评测结果，不仅没有否定我们的系统，反而强力印证了我们研发前置硬门禁与 DeepRevision 实验级大修的先见之明。它为科研 Agent 指明了演进方向：系统不能仅仅停留在“把论文格式做对”，更必须通过严苛的内审机制逼迫智能体在实验深度上下硬功夫。""")

    # ==================== SLIDE 16: FRAMEWORK CONTRIBUTION ====================
    s16 = prs.slides.add_slide(blank_layout)
    add_header(s16, "openJiuwen 框架级扩展贡献 (ContextBudgetRail & VersionedMemory)", "OPENJIUWEN FRAMEWORK CONTRIBUTIONS")
    
    # 2 Rails Cards
    c16_l = s16.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.3))
    c16_l.fill.solid()
    c16_l.fill.fore_color.rgb = C_CARD_BG
    c16_l.line.color.rgb = C_GREEN
    c16_l.line.width = Pt(1.5)
    
    tf16_l = c16_l.text_frame
    tf16_l.word_wrap = True
    p = tf16_l.paragraphs[0]
    p.text = "🛡️ 贡献一：ContextBudgetRail（预算护栏）"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_GREEN
    
    rail_pts = [
        ("上游扩展位置", "jiuwenswarm.agents.harness.common.rails"),
        ("核心机制", "在智能体每次感知-决策循环中，动态拦截并计算当前会话的累积输入/输出 Token 消耗。"),
        ("分级控制", "支持设定 Soft Limit（软预警降级）与 Hard Limit（强制熔断），杜绝长循环失控导致的账单爆炸。"),
        ("即插即用", "以标准装饰器/中间件形式无侵入接入任意 openJiuwen Agent。")
    ]
    for h_txt, b_txt in rail_pts:
        p1 = tf16_l.add_paragraph()
        p1.text = f"• {h_txt}"
        p1.font.size = Pt(11.5)
        p1.font.bold = True
        p1.font.color.rgb = C_COBALT
        p1.space_before = Pt(8)
        p2 = tf16_l.add_paragraph()
        p2.text = f"  {b_txt}"
        p2.font.size = Pt(10)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(2)

    c16_r = s16.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.3))
    c16_r.fill.solid()
    c16_r.fill.fore_color.rgb = C_CARD_BG
    c16_r.line.color.rgb = C_NAVY
    c16_r.line.width = Pt(1.5)
    
    tf16_r = c16_r.text_frame
    tf16_r.word_wrap = True
    pr = tf16_r.paragraphs[0]
    pr.text = "🧠 贡献二：VersionedMemory（版本化记忆）"
    pr.font.size = Pt(14)
    pr.font.bold = True
    pr.font.color.rgb = C_NAVY
    
    mem_pts = [
        ("解决长程痛点", "传统 Agent 记忆缺乏版本管理，多角色长周期协作极易发生状态覆盖与污染。"),
        ("Git 式版本树管理", "为每一条长程记忆赋予 Commit ID、时间戳、父节点引用与作者签名。"),
        ("冲突裁决机制", "在发生状态分歧时，提供三方合并（Three-way merge）与主权裁决策略。"),
        ("标准补丁交付", "沉淀为 framework_contribution.patch，配齐单元测试，完全符合开源合并规范。")
    ]
    for h_txt, b_txt in mem_pts:
        p1 = tf16_r.add_paragraph()
        p1.text = f"★ {h_txt}"
        p1.font.size = Pt(11.5)
        p1.font.bold = True
        p1.font.color.rgb = C_NAVY
        p1.space_before = Pt(8)
        p2 = tf16_r.add_paragraph()
        p2.text = f"  {b_txt}"
        p2.font.size = Pt(10)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(2)

    set_slide_notes(s16, """赛题明确设定了 15 分的 openJiuwen 框架贡献要求。我们不仅在业务层开发了科研应用，更深入华为开源框架底层，为 JiuwenSwarm 贡献了两大通用基础设施：
第一个是 ContextBudgetRail（上下文预算控制护栏）：针对多智能体在复杂循环中容易产生无限调用导致账单失控的问题，我们抽象出标准的 Rail 拦截器，支持在 Agent 运行时动态计算上下文预算并执行分级熔断；
第二个是 VersionedMemory（版本化记忆系统）：传统 Agent 的记忆是线性的、扁平的，多角色交互极易发生状态覆盖。我们引入了具备 Git 理念的版本树机制，赋予智能体记忆以分支、合并与版本回溯的能力。
所有源码修改均已封装为标准的补丁文件 framework_contribution.patch，并附带完备的单元测试，能够直接向 openJiuwen 官方主干提请 PR。""")

    # ==================== SLIDE 17: QUALITY & 43 TESTS ====================
    s17 = prs.slides.add_slide(blank_layout)
    add_header(s17, "工程质量保障与自动化测试验证：43 项用例 100% 通过", "TESTING & QUALITY ASSURANCE")
    
    # Left code box
    c17_l = s17.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.3))
    c17_l.fill.solid()
    c17_l.fill.fore_color.rgb = RGBColor(0xEA, 0xF2, 0xF8)
    c17_l.line.color.rgb = C_NAVY
    c17_l.line.width = Pt(1.5)
    
    tf17_l = c17_l.text_frame
    tf17_l.word_wrap = True
    p = tf17_l.paragraphs[0]
    p.text = "⚡ 真实 Pytest 执行输出与覆盖情况"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    p_code = tf17_l.add_paragraph()
    p_code.text = (
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
    p_code.font.size = Pt(9.5)
    p_code.font.name = "Consolas"
    p_code.font.color.rgb = RGBColor(0x11, 0x33, 0x55)
    p_code.space_before = Pt(8)

    # Right Card
    c17_r = s17.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.3))
    c17_r.fill.solid()
    c17_r.fill.fore_color.rgb = C_CARD_BG
    c17_r.line.color.rgb = C_GREEN
    c17_r.line.width = Pt(1.5)
    
    tf17_r = c17_r.text_frame
    tf17_r.word_wrap = True
    pr = tf17_r.paragraphs[0]
    pr.text = "🛡️ 严苛测试套件矩阵覆盖"
    pr.font.size = Pt(14)
    pr.font.bold = True
    pr.font.color.rgb = C_GREEN
    
    t_items = [
        ("门禁状态机判定 (test_workflow_gates)", "覆盖 TopicGate 阈值、PilotGate 三态输出、以及池外弱基线压制早停机制。"),
        ("锦标赛与自动回退 (test_workflow_tournament)", "验证候选方案多维评分排序、以及主选方案被剪枝后自动无缝切换备选方案。"),
        ("顶会评审与硬底线 (test_conference_review)", "验证 ICLR 4 维量化权重计算器与 5.0 Hard Floor 硬底线拒稿判定。"),
        ("实验深修回路 (test_deep_revision)", "验证审稿 Weaknesses 解析、RevisionPlan 生成及追加实验调度逻辑。"),
        ("模型网关与端到端链路 (test_research_chain)", "测试跨 Agent 消息总线传输、事件日志完整留痕与证据链持久化。")
    ]
    for h_txt, b_txt in t_items:
        p1 = tf17_r.add_paragraph()
        p1.text = f"• {h_txt}"
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = C_GREEN
        p1.space_before = Pt(6)
        p2 = tf17_r.add_paragraph()
        p2.text = f"  {b_txt}"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(1)

    set_slide_notes(s17, """高度自治的多智能体系统往往面临调试困难、状态不确定等可靠性挑战。为了保障交付质量，我们严格遵循测试驱动开发（TDD）规范，构建了覆盖全系统的 43 项自动化回归测试矩阵。
屏幕上是我们真实的 Pytest 测试终端记录：43 项测试在 2.12 秒内全量绿色通过。
我们的测试网重点覆盖了极端异常分支：
包括 TopicGate 在边界分数的淘汰判定、PilotGate 遭遇池外模型压制时的早停熔断逻辑、多候选方案的平滑回退，以及顶会内审硬底线拒稿触发器。严格的自动化测试彻底排除了异步死锁与状态漂移，确保系统在无人值守的批量生成任务中能够极其稳健地运行。""")

    # ==================== SLIDE 18: DIVISION OF LABOR ====================
    s18 = prs.slides.add_slide(blank_layout)
    add_header(s18, "小组成员分工与核心产出矩阵", "TEAM COLLABORATION & DIVISION OF LABOR")
    
    b18 = s18.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.3))
    b18.fill.solid()
    b18.fill.fore_color.rgb = C_CARD_BG
    b18.line.color.rgb = C_NAVY
    b18.line.width = Pt(1.5)
    
    tf18 = b18.text_frame
    tf18.word_wrap = True
    p = tf18.paragraphs[0]
    p.text = "👥 团队 5 位成员紧密咬合，职责完全闭环"
    p.font.size = Pt(15.5)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    divs = [
        ("王智洋 (102402136 · 架构与集成)", "负责总体架构规划、openJiuwen Swarm 内核流水线升级、Model Gateway 适配与多智能体调度驱动。"),
        ("洪豊幀 (102402124 · 数据与实验)", "负责长上下文记忆与特征缺失任务设计、实验沙箱搭建、受控代码运行与真实调用日志采集。"),
        ("黄炜杰 (102402126 · 论文生成)", "负责证据链数据绑定、ICLR 2026 双栏 LaTeX 模板工程开发、英文论证逻辑组织与图表排版。"),
        ("黄俊翔 (102402125 · 质量保障)", "负责 43 项全量自动化测试矩阵开发、Token 开销审计、可复现性环境构建与日志留痕审计。"),
        ("金若曦 (102402127 · 文档与汇报)", "负责系统使用说明书编写、课程结题报告主笔、答辩 PPT 设计与展示演练统筹。")
    ]
    for d_h, d_b in divs:
        pt = tf18.add_paragraph()
        pt.text = f"★ {d_h}"
        pt.font.size = Pt(12)
        pt.font.bold = True
        pt.font.color.rgb = C_COBALT
        pt.space_before = Pt(8)
        pd = tf18.add_paragraph()
        pd.text = f"   {d_b}"
        pd.font.size = Pt(10.5)
        pd.font.color.rgb = C_DARK
        pd.space_before = Pt(2)

    set_slide_notes(s18, """本项目的圆满交付凝聚了第 6 组全体 5 位同学的紧密协作。我们在项目启动之初就制定了清晰的软件工程 WBS 分工矩阵：
王智洋负责总体软件架构与 openJiuwen Swarm 的深度集成；
洪豊幀专注数据流水线构建、实验沙箱调度与基线数据采集；
黄炜杰攻坚证据链防作弊机制、学术英文论述组织与 LaTeX 排版系统；
黄俊翔全面把控工程质量，编写了全套 43 项测试用例并完成资源开销审计；
金若曦统筹交付规范，主笔了万字级课程报告、详细使用说明书及整套答辩演练材料。
5 位同学职责清晰、紧密咬合，确保了架构设计、核心代码、实证测试与交付成果物的高度统一。""")

    # ==================== SLIDE 19: CONCLUSION ====================
    s19 = prs.slides.add_slide(blank_layout)
    add_header(s19, "项目成果总结与系统创新价值", "PROJECT SUMMARY & INNOVATION VALUES")
    
    # 4 Value Cards
    v_w = Inches(2.7)
    v_h = Inches(5.3)
    v_y = Inches(1.5)
    
    vals = [
        ("高可靠科研系统", "六阶段闭环执行", C_NAVY,
         "• 基于 openJiuwen Swarm 架构\n• 文献到论文全自主流转\n• 无锁追加日志与事件驱动\n• 状态机支持断点续跑与回退"),
        ("自驱五重防御", "终结水文与空耗", C_COBALT,
         "• 前门选题量化准入门禁\n• 结构化事前验收协议锁定\n• Pilot 探针节约 91.5% 算力\n• 顶会双层审稿与实验深修"),
        ("严谨学术成果", "可穿透可审计", C_ORANGE,
         "• 标准 ICLR 2026 双栏论文\n• 100% 绑定底层 evidence\n• 杜绝伪科学与数据幻觉\n• 经受第三方真实盲审检验"),
        ("开源生态回哺", "通用基座组件", C_GREEN,
         "• 提交 ContextBudgetRail\n• 提交 VersionedMemory 组件\n• 规范 Patch 补丁与测试用例\n• 赋能更多智能体开发者")
    ]
    for idx, (vtitle, vsub, vcolor, vdesc) in enumerate(vals):
        vx = Inches(0.8 + idx * 2.95)
        vbox = s19.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, vx, v_y, v_w, v_h)
        vbox.fill.solid()
        vbox.fill.fore_color.rgb = C_CARD_BG
        vbox.line.color.rgb = vcolor
        vbox.line.width = Pt(1.5)
        
        vtf = vbox.text_frame
        vtf.word_wrap = True
        
        vp1 = vtf.paragraphs[0]
        vp1.text = vtitle
        vp1.font.size = Pt(14)
        vp1.font.bold = True
        vp1.font.color.rgb = vcolor
        vp1.alignment = PP_ALIGN.CENTER
        
        vp2 = vtf.add_paragraph()
        vp2.text = vsub
        vp2.font.size = Pt(11)
        vp2.font.bold = True
        vp2.font.color.rgb = C_ORANGE
        vp2.alignment = PP_ALIGN.CENTER
        vp2.space_before = Pt(4)
        vp2.space_after = Pt(12)
        
        vp3 = vtf.add_paragraph()
        vp3.text = vdesc
        vp3.font.size = Pt(10.5)
        vp3.font.color.rgb = C_DARK
        vp3.line_spacing = 1.3

    set_slide_notes(s19, """总结第 6 组的工作，我们紧扣软件工程的核心精神，交出了一份具备高度工业实用性与学术严谨度的答卷：
首先，我们构建了一套完整可落地的科研智能体系统，端到端打通了文献到论文导出的全流程；
其次，我们通过五重防御机制，解决了科研 Agent 水文泛滥、算力空耗与浅表修改的三大顽疾，使单任务 Token 开销降低了 90% 以上；
再次，我们生成了完全可穿透溯源的标准 ICLR 学术论文，并主动接入 Stanford 真实盲审检验；
最后，我们向 openJiuwen 社区回哺了通用的预算与记忆组件。
这项实践让我们深刻领悟到：真正有价值的人工智能工程，绝非简单的 Prompt 堆叠，而是用严密的架构、契约化的状态机和扎实的测试网，将不确定的模型推演约束为确定可靠的生产力。""")

    # ==================== SLIDE 20: Q&A ====================
    s20 = prs.slides.add_slide(blank_layout)
    bg20 = s20.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg20.fill.solid()
    bg20.fill.fore_color.rgb = C_NAVY
    bg20.line.fill.background()
    
    tbox20 = s20.shapes.add_textbox(Inches(1.0), Inches(1.5), Inches(11.333), Inches(4.5))
    tf20 = tbox20.text_frame
    tf20.word_wrap = True
    
    p0 = tf20.paragraphs[0]
    p0.text = "后续演进方向与答辩致谢"
    p0.font.size = Pt(32)
    p0.font.bold = True
    p0.font.color.rgb = C_WHITE
    p0.alignment = PP_ALIGN.CENTER
    
    p1 = tf20.add_paragraph()
    p1.text = (
        "未来三大演进路线：\n"
        "1. 跨学科沙箱扩展：拓展至材料物理与生物信息学仿真环境\n"
        "2. 多学派博弈审稿：引入不同学术流派智能体开展多轮辩论\n"
        "3. 动态算力分配：依据课题理论增量自适应倾斜计算资源\n\n"
        "感谢福州大学计算机与大数据学院老师们的悉心指导！\n"
        "感谢华为 openJiuwen 开源社区的技术支持！"
    )
    p1.font.size = Pt(15.5)
    p1.font.color.rgb = RGBColor(0xD0, 0xE0, 0xF0)
    p1.alignment = PP_ALIGN.CENTER
    p1.space_before = Pt(16)
    p1.line_spacing = 1.3
    
    p2 = tf20.add_paragraph()
    p2.text = "敬请各位评委老师批评指正 · 欢迎现场提问 (Q & A)"
    p2.font.size = Pt(24)
    p2.font.bold = True
    p2.font.color.rgb = RGBColor(0xFF, 0xB7, 0x4D)
    p2.alignment = PP_ALIGN.CENTER
    p2.space_before = Pt(30)

    set_slide_notes(s20, """展望未来，我们将进一步拓展系统的学科边界，探索将多智能体协作引入生物材料与物理仿真领域；同时，我们计划引入多评审专家动态博弈辩论，让大修规划具备更丰富的方法论视角。
感谢学院老师们在整个大数据项目实践课程中的悉心指导，也感谢华为 openJiuwen 社区提供的优秀开源基座！
以上是第 6 组的全部汇报内容，敬请各位评委老师批评指正！我们非常期待各位老师的提问与交流，谢谢大家！""")

    prs.save(output_path)
    print(f"Master presentation successfully saved to: {output_path}")

if __name__ == '__main__':
    targets = [
        "docs/第6组项目汇报PPT_终版.pptx",
        "第6组项目汇报PPT_终版.pptx"
    ]
    for t in targets:
        os.makedirs(os.path.dirname(os.path.abspath(t)), exist_ok=True)
        build_group6_pptx(t)
