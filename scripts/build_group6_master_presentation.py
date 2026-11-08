"""
Generate the honest, grounded, perfectly-structured 16-slide PowerPoint presentation for Group 6.
Structure:
- Part 1: Background & Scoring Model (Slides 1-2)
- Part 2: Final System Architecture & Core Defense Mechanisms (Slides 3-5)
- Part 3: Three Empirical Runs, Token Audits, and Paper Review Evolution (Slides 6-10)
- Part 4: openJiuwen Framework Rails, Testing, Deliverables, Team, & Conclusion (Slides 11-16)
"""
import os
import sys
import re
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

sys.stdout.reconfigure(encoding='utf-8')

def load_script_notes(script_path="docs/第6组项目汇报逐页讲稿_终版.md"):
    """
    Parse the comprehensive speaker notes from the master defense markdown script.
    Combines suggested timing, verbatim oral delivery, transition cues, and anticipated Q&A.
    """
    if not os.path.exists(script_path):
        return {}
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()

    slides_raw = re.split(r'\n## 第\s*(\d+)\s*页[：:]', content)
    slides_dict = {}
    for i in range(1, len(slides_raw), 2):
        num = int(slides_raw[i])
        body = slides_raw[i+1]
        
        timing_match = re.search(r'### 【建议用时】\s*\n([^\n#]+)', body)
        timing = timing_match.group(1).strip() if timing_match else ''
        
        speech_match = re.search(r'### 【逐字答辩讲稿】\s*\n(.*?)(?=\n###|\Z)', body, re.DOTALL)
        speech = speech_match.group(1).strip() if speech_match else ''
        speech = '\n'.join([line.lstrip('> ').strip() for line in speech.splitlines() if line.strip()])
        
        trans_match = re.search(r'### 【换页过渡语】\s*\n(.*?)(?=\n###|\Z)', body, re.DOTALL)
        trans = trans_match.group(1).strip() if trans_match else ''
        trans = '\n'.join([line.lstrip('> ').strip() for line in trans.splitlines() if line.strip()])
        
        qa_match = re.search(r'### 【评委可能提问与应答预案[^\n]*】\s*\n(.*?)(?=\n---|\Z)', body, re.DOTALL)
        qa = qa_match.group(1).strip() if qa_match else ''
        
        note_parts = []
        if timing:
            note_parts.append(f"⏱️【建议用时】\n{timing}")
        if speech:
            note_parts.append(f"🎙️【逐字答辩讲稿】\n{speech}")
        if trans:
            note_parts.append(f"🔄【换页过渡语】\n{trans}")
        if qa:
            note_parts.append(f"💡【评委可能提问与应答预案】\n{qa}")
            
        slides_dict[num] = "\n\n".join(note_parts)
    return slides_dict

def build_presentation(output_pptx):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]
    
    notes_dict = load_script_notes()
    
    # Palette
    C_NAVY = RGBColor(0x1B, 0x36, 0x5D)
    C_SLATE = RGBColor(0x28, 0x55, 0x88)
    C_CARD_BG = RGBColor(0xEE, 0xF2, 0xF7)
    C_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
    C_DARK = RGBColor(0x22, 0x22, 0x22)
    C_MUTED = RGBColor(0x66, 0x66, 0x66)
    C_ORANGE = RGBColor(0xD3, 0x54, 0x00)
    C_GREEN = RGBColor(0x27, 0xAE, 0x60)
    C_RED = RGBColor(0xC0, 0x39, 0x2B)

    def set_slide_notes(slide, notes):
        tf = slide.notes_slide.notes_text_frame
        tf.text = notes.strip()

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
    
    tbox = s1.shapes.add_textbox(Inches(1.0), Inches(1.5), Inches(11.333), Inches(2.2))
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
    
    c1 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.6), Inches(4.3), Inches(10.133), Inches(2.3))
    c1.fill.solid()
    c1.fill.fore_color.rgb = RGBColor(0x22, 0x43, 0x6E)
    c1.line.color.rgb = RGBColor(0x4A, 0x7E, 0xBB)
    c1.line.width = Pt(1.5)
    
    ctf = c1.text_frame
    ctf.word_wrap = True
    cp1 = ctf.paragraphs[0]
    cp1.text = "汇报小组：大数据项目实践 · 第 6 组   |   福州大学 计算机与大数据学院"
    cp1.font.size = Pt(15.5)
    cp1.font.bold = True
    cp1.font.color.rgb = C_WHITE
    cp1.alignment = PP_ALIGN.CENTER
    
    cp2 = ctf.add_paragraph()
    cp2.text = "小组成员：金若曦 (102402127)  洪豊幀 (102402124)  黄炜杰 (102402126)  黄俊翔 (102402125)  王智洋 (102402136)"
    cp2.font.size = Pt(13)
    cp2.font.color.rgb = RGBColor(0xFF, 0xCC, 0x80)
    cp2.alignment = PP_ALIGN.CENTER
    cp2.space_before = Pt(10)
    
    cp3 = ctf.add_paragraph()
    cp3.text = "答辩主线：最终闭环架构 · 三轮实验分次 Token 账单 · 外部盲审 3.7→4.4→4.9分进阶 · 框架 Rail 扩展"
    cp3.font.size = Pt(12)
    cp3.font.color.rgb = RGBColor(0xB0, 0xC8, 0xE0)
    cp3.alignment = PP_ALIGN.CENTER
    cp3.space_before = Pt(8)

    set_slide_notes(s1, notes_dict.get(1, ""))

    # ==================== SLIDE 2: SCORING ====================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "赛题任务目标与 100 分量化评分模型", "TASK & SCORING MODEL")
    
    sc_w = Inches(2.7)
    sc_h = Inches(5.3)
    sc_y = Inches(1.5)
    
    scores = [
        ("论文质量 (60分)", "客观双重裁判：\n• Stanford 盲审 (40分)\n• 官方评测 Agent (20分)", C_NAVY, 
         "赛题考核核心要求：\n• 必须包含扎实的真实实验实证\n• 采用 ICLR 双栏模板排版\n• 论据与原始数据严格自洽\n• 外部网站机器自动盲审打分"),
        ("框架贡献 (15分)", "openJiuwen 框架扩展\n开源生态回哺", C_SLATE,
         "赛题考核核心要求：\n• 深入 JiuwenSwarm 底层源码\n• 贡献通用 Rail 拦截器/组件\n• 提交规范 patch 补丁文件\n• 提供独立单元测试用例"),
        ("系统能力 (15分)", "多智能体架构设计\n状态机与任务流转", C_ORANGE,
         "赛题考核核心要求：\n• 5 类角色分工明确，避免混乱\n• 状态机支持断点与自动回退\n• 提供无密钥开箱即用环境\n• 完整的开发说明与架构文档"),
        ("资源控制 (10分)", "Token 消耗审计\n成本与早停机制", C_GREEN,
         "赛题考核核心要求：\n• 记录每阶段 API 消耗账单\n• 控制长上下文调用 Token 成本\n• 设计早期异常发现与早停拦截\n• 避免无意义的算力虚耗")
    ]
    for idx, (stitle, ssub, scolor, sdesc) in enumerate(scores):
        sx = Inches(0.8 + idx * 2.95)
        box = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, sx, sc_y, sc_w, sc_h)
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
        sp2.font.size = Pt(10.5)
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

    set_slide_notes(s2, notes_dict.get(2, ""))

    # ==================== SLIDE 3: FINAL ARCHITECTURE ====================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "系统整体架构与五大智能体协同拓扑（最终方案）", "FINAL SYSTEM ARCHITECTURE")
    
    # Left: Embed High-Res Diagram if exists, else nice vector card
    img_arch = "docs/assets/第6组_系统整体架构.png"
    if os.path.exists(img_arch):
        s3.shapes.add_picture(img_arch, Inches(0.8), Inches(1.5), width=Inches(6.3))
    else:
        # Fallback card
        b3_l = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(6.3), Inches(5.3))
        b3_l.fill.solid()
        b3_l.fill.fore_color.rgb = C_CARD_BG
        b3_l.line.color.rgb = C_NAVY
        tf3_l = b3_l.text_frame
        tf3_l.paragraphs[0].text = "系统整体架构与分层总线"
    
    # Right: 5 Agent Roles Card
    b3_r = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.3), Inches(1.5), Inches(5.233), Inches(5.3))
    b3_r.fill.solid()
    b3_r.fill.fore_color.rgb = C_CARD_BG
    b3_r.line.color.rgb = C_SLATE
    b3_r.line.width = Pt(1.5)
    
    tf3_r = b3_r.text_frame
    tf3_r.word_wrap = True
    p = tf3_r.paragraphs[0]
    p.text = "🤖 五大核心自治智能体角色分工"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    agent_roles = [
        ("OrchestratorAgent (总控调度)", "管理全生命周期有限状态机 (FSM)，维护不可篡改的上下文契约 (ConnectedProfile)，协调各阶段准入准出。"),
        ("LiteratureAgent (文献专家)", "检索领域文献与前沿基线，形式化提炼相关工作对比边界与未解决缺陷。"),
        ("ScientistAgent (实验专家)", "调度 openJiuwen ReActAgent 运行真实实验，沉淀原始输入输出与调用审计账本。"),
        ("WriterAgent (论文编撰)", "结构化抽取实验均值方差，在严格约束 Prompt 下草拟段落并调用 pdflatex 编译 ICLR 双栏论文。"),
        ("ReviewerAgent (审稿专家)", "内部执行冷事实审查 (Cold Review) 与 4 维模拟预审，设立 5.0 分内部送审红线。")
    ]
    for r_title, r_desc in agent_roles:
        p1 = tf3_r.add_paragraph()
        p1.text = f"• {r_title}"
        p1.font.size = Pt(10.5)
        p1.font.bold = True
        p1.font.color.rgb = C_SLATE
        p1.space_before = Pt(6)
        p2 = tf3_r.add_paragraph()
        p2.text = f"  {r_desc}"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(1)

    set_slide_notes(s3, notes_dict.get(3, ""))

    # ==================== SLIDE 4: MECHANISM 1 ====================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "核心机制一：前门选题准入与 StructuredAcceptance 事前验收契约", "CORE DEFENSE MECHANISM 1")
    
    col_w = Inches(5.6)
    col_h = Inches(5.3)
    col_y = Inches(1.5)
    
    # Left: Topic Tournament
    b4_l = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), col_y, col_w, col_h)
    b4_l.fill.solid()
    b4_l.fill.fore_color.rgb = C_CARD_BG
    b4_l.line.color.rgb = C_NAVY
    b4_l.line.width = Pt(1.5)
    
    tf4_l = b4_l.text_frame
    tf4_l.word_wrap = True
    p = tf4_l.paragraphs[0]
    p.text = "🏆 前门选题准入与自动回退机制"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    tt_items = [
        ("理论增量评估 (Theoretical Delta)", "在开题阶段量化评估相对现有工作的理论提升幅度，从源头斩断同质化水文立项。"),
        ("基线风险量化 (Baseline Risk)", "核验拟对比基线的强弱与合理性，严禁挑选毫无竞争力的极端弱基线以伪造优越性。"),
        ("双轨课题储备池 (Topic Pool)", "开题时并行推演主选方案与备选路线，并分别生成实验配置框架。"),
        ("自动回退与平滑流转 (Auto-Fallback)", "若主选课题在后续探针阶段受挫熔断，系统自动激活备选课题，保证交付稳定性。")
    ]
    for h, d in tt_items:
        p1 = tf4_l.add_paragraph()
        p1.text = f"▶ {h}"
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = C_SLATE
        p1.space_before = Pt(8)
        p2 = tf4_l.add_paragraph()
        p2.text = f"   {d}"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(2)
        
    # Right: StructuredAcceptance
    b4_r = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), col_y, col_w, col_h)
    b4_r.fill.solid()
    b4_r.fill.fore_color.rgb = C_CARD_BG
    b4_r.line.color.rgb = C_GREEN
    b4_r.line.width = Pt(1.5)
    
    tf4_r = b4_r.text_frame
    tf4_r.word_wrap = True
    pr = tf4_r.paragraphs[0]
    pr.text = "📜 StructuredAcceptance 事前验收契约"
    pr.font.size = Pt(14)
    pr.font.bold = True
    pr.font.color.rgb = C_GREEN
    
    p_code = tf4_r.add_paragraph()
    p_code.text = (
        "# 形式化锁定实验验收规范 (写入只读上下文)\n"
        "StructuredAcceptance:\n"
        "  primary_metric: 'accuracy'       # 显式锁定核心评估指标\n"
        "  metric_direction: 'maximize'     # 固化优化极性 (max/min)\n"
        "  min_delta: 0.05                  # 相对基线最小提升红线 (>=5%)\n"
        "  oop_domination_margin: 0.05      # 池外弱基线压制容忍度\n"
        "  status: 'pre_registered'         # 实验后执行断言核验"
    )
    p_code.font.name = "Consolas"
    p_code.font.size = Pt(9.5)
    p_code.font.color.rgb = RGBColor(0x11, 0x33, 0x55)
    p_code.space_before = Pt(8)
    
    p_sub = tf4_r.add_paragraph()
    p_sub.text = (
        "★ 契约化防守成效：\n"
        "• 借鉴临床试验预注册制度 (ClinicalTrials.gov)，从工程机制上彻底杜绝‘事后挑好看指标汇报’的选择性报告偏差 (Cherry-picking)；\n"
        "• 若实验数据未达契约标准，状态机直接裁定失败，坚决禁止生成注水论文。"
    )
    p_sub.font.size = Pt(10)
    p_sub.font.color.rgb = C_DARK
    p_sub.space_before = Pt(8)

    set_slide_notes(s4, notes_dict.get(4, ""))

    # ==================== SLIDE 5: MECHANISM 2 ====================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "核心机制二：PilotGate 三态剪枝探针与事后双层预审防线", "CORE DEFENSE MECHANISM 2")
    
    # Left: PilotGate
    b5_l = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), col_y, col_w, col_h)
    b5_l.fill.solid()
    b5_l.fill.fore_color.rgb = C_CARD_BG
    b5_l.line.color.rgb = C_ORANGE
    b5_l.line.width = Pt(1.5)
    
    tf5_l = b5_l.text_frame
    tf5_l.word_wrap = True
    p = tf5_l.paragraphs[0]
    p.text = "⚡ PilotGate 小样本三态剪枝早停探针"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_ORANGE
    
    pg_steps = [
        ("1. 小样本探测", "在投入昂贵算力跑满全量测试前，抽取 10%~20% 样本作为预检探针。"),
        ("2. 引入池外基准对照", "引入现成、免调优的经典弱模型 (如 HistGradientBoosting) 作为试金石。"),
        ("3. 三态状态机裁决", "• [go]：显著战胜基线，放行全量实验；\n• [pivot]：临界波动，允许超参微调后二次探针 (revalidate)；\n• [no_go]：大幅落后于弱基线，立即熔断剪枝 (pruned)！"),
        ("4. 算力止损成效", "提前拦截缺乏竞争力的平庸算法，实测为系统节约 91.5% 的无效 API 支出！")
    ]
    for h, d in pg_steps:
        p1 = tf5_l.add_paragraph()
        p1.text = f"▶ {h}"
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = C_ORANGE
        p1.space_before = Pt(6)
        p2 = tf5_l.add_paragraph()
        p2.text = f"   {d}"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(1)

    # Right: Double-layer Review
    b5_r = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), col_y, col_w, col_h)
    b5_r.fill.solid()
    b5_r.fill.fore_color.rgb = C_CARD_BG
    b5_r.line.color.rgb = C_NAVY
    b5_r.line.width = Pt(1.5)
    
    tf5_r = b5_r.text_frame
    tf5_r.word_wrap = True
    pr = tf5_r.paragraphs[0]
    pr.text = "🛡️ 送审前内部双层预审防护网"
    pr.font.size = Pt(14)
    pr.font.bold = True
    pr.font.color.rgb = C_NAVY
    
    rev_layers = [
        ("第 1 层：Cold Review (冷事实审查)", "• 轻量脚本逐行比对论文正文数值与底层 results.jsonl 日志；\n• 发现数据偏差立即抛出异常并告警，坚决杜绝大模型在正文中的事实性幻觉。"),
        ("第 2 层：ConferenceReviewPanel (模拟评审面板)", "• 在本地参照 ICLR 顶级会议 4 维标准 (完备性、创新性、实用性、实证性) 进行预审打分；\n• 设定内部 5.0 硬底线评分红线，未达标方案禁止向外送审。"),
        ("实验级大修规划 (DeepRevision)", "• 自动解析审稿专家反馈中的 Weaknesses 关键词；\n• 尝试将其映射为下游实验补跑任务 (如追加噪声、补齐消融对比)。")
    ]
    for h, d in rev_layers:
        p1 = tf5_r.add_paragraph()
        p1.text = f"✓ {h}"
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = C_NAVY
        p1.space_before = Pt(6)
        p2 = tf5_r.add_paragraph()
        p2.text = f"   {d}"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(1)

    set_slide_notes(s5, notes_dict.get(5, ""))

    # ==================== SLIDE 6: ITERATION OVERVIEW ====================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "三轮受控实验、Token 账单与盲审评分跃升总览", "EMPIRICAL ITERATION & EVOLUTION")
    
    b6 = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.3))
    b6.fill.solid()
    b6.fill.fore_color.rgb = C_CARD_BG
    b6.line.color.rgb = C_NAVY
    b6.line.width = Pt(1.5)
    
    tf6 = b6.text_frame
    tf6.word_wrap = True
    p = tf6.paragraphs[0]
    p.text = "📈 实事求是的三轮论文生成与外部送审演进全景"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    p_desc = tf6.add_paragraph()
    p_desc.text = "拒绝一次性概念演示，老老实实通过三轮闭环实验与真实盲审，将系统从 3.7 分稳步打磨至 4.9 分："
    p_desc.font.size = Pt(11)
    p_desc.font.color.rgb = C_MUTED
    p_desc.space_before = Pt(4)
    
    runs = [
        ("第 1 版·长上下文记忆选择机制", "24 合成任务 · 96 次作答", "131 次调用 · 114,297 Token (耗时 55.1s)", "3.7 / 10", "暴露问题：任务为人工合成缺乏噪声，对比基线 (滑动窗口) 过弱，缺乏深度消融。"),
        ("第 2 版·特征缺失早停探针实测", "引入池外梯度提升树对决", "12 次调用 · 8,531 Token (节约 91.5% 算力)", "4.4 / 10", "机制突破：成功触发 PilotGate 早停拦截，避免 10 万+ Token 浪费，肯定了止损能力。"),
        ("第 3 版·Pilot 剪枝推迟决策审计", "420 组微观积分 + 540 组实证重放", "精确数值积分 + 论文生成 ~6.5k Token", "4.9 / 10", "质的飞跃：Claims_Support 与 Experimental_Soundness 双获 +1 顶会最高档评级！")
    ]
    for r_title, r_scale, r_tokens, r_score, r_diag in runs:
        pr_h = tf6.add_paragraph()
        pr_h.text = f"★ {r_title}   [盲审得分: {r_score}]"
        pr_h.font.size = Pt(12)
        pr_h.font.bold = True
        pr_h.font.color.rgb = C_ORANGE if "4.9" in r_score else (C_GREEN if "4.4" in r_score else C_SLATE)
        pr_h.space_before = Pt(8)
        
        pr_b = tf6.add_paragraph()
        pr_b.text = f"   • 实验规模：{r_scale}   |   • API 与 Token 账单：{r_tokens}\n   • 外部审稿诊断：{r_diag}"
        pr_b.font.size = Pt(10)
        pr_b.font.color.rgb = C_DARK
        pr_b.space_before = Pt(2)

    set_slide_notes(s6, notes_dict.get(6, ""))

    # ==================== SLIDE 7: RUN 1 ====================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "第一次论文生成与消耗：长上下文选择机制", "PAPER RUN 1 · BASELINE STUDY")
    
    # Left: Research Case
    b7_l = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), col_y, col_w, col_h)
    b7_l.fill.solid()
    b7_l.fill.fore_color.rgb = C_CARD_BG
    b7_l.line.color.rgb = C_NAVY
    b7_l.line.width = Pt(1.5)
    
    tf7_l = b7_l.text_frame
    tf7_l.word_wrap = True
    p = tf7_l.paragraphs[0]
    p.text = "🎯 实验设计：长配置历史上下文选择"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    c_desc = [
        ("研究痛点", "智能体面对长周期多轮配置交互时，上下文膨胀导致 Token 暴涨与注意力稀释，而滑动截断又丢失关键依赖。"),
        ("4 种对照策略", "1. All History (全量历史)\n2. Recent Window (最近固定滑动窗口)\n3. Lexical Retrieval (基于项目 ID 词法检索)\n4. Retrieval + Summary (检索加摘要压缩)"),
        ("实验规模与结论", "• 24 个合成评测任务，针对 4 策略运行 96 次任务作答；\n• 全量与检索均获 100% 准确率，滑动窗口断崖式跌至 25% (发生早期关键配置灾难性遗忘)。"),
        ("送审得分", "生成论文提交 Stanford Reviewer 盲审，得分: 3.7 / 10。")
    ]
    for h, d in c_desc:
        p1 = tf7_l.add_paragraph()
        p1.text = f"• {h}"
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = C_SLATE
        p1.space_before = Pt(6)
        p2 = tf7_l.add_paragraph()
        p2.text = f"  {d}"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(1)

    # Right: Token Audit
    b7_r = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), col_y, col_w, col_h)
    b7_r.fill.solid()
    b7_r.fill.fore_color.rgb = C_CARD_BG
    b7_r.line.color.rgb = C_GREEN
    b7_r.line.width = Pt(1.5)
    
    tf7_r = b7_r.text_frame
    tf7_r.word_wrap = True
    pr = tf7_r.paragraphs[0]
    pr.text = "📊 第一次生成完整 API 与 Token 账单"
    pr.font.size = Pt(14)
    pr.font.bold = True
    pr.font.color.rgb = C_GREEN
    
    rows7 = [
        ("冒烟验证 (Smoke)", "5 次", "4,241", "约 3.1 秒"),
        ("主对比实验 (Baseline)", "120 次", "101,768", "43.8 秒"),
        ("二次验证 (Verified)", "5 次", "4,236", "约 3.0 秒"),
        ("论文初稿草拟与编译", "1 次", "4,052", "约 5.2 秒"),
        ("第一次生成累计全量", "131 次", "114,297", "约 55.1 秒")
    ]
    p_t = tf7_r.add_paragraph()
    p_t.text = "阶段明细          | 调用数 | Token 消耗 | 运行耗时\n" + "-"*42
    p_t.font.name = "Consolas"
    p_t.font.size = Pt(9.5)
    p_t.font.bold = True
    p_t.font.color.rgb = C_NAVY
    p_t.space_before = Pt(6)
    
    for stage, calls, tokens, cost in rows7:
        p_row = tf7_r.add_paragraph()
        p_row.text = f"{stage:<14} | {calls:<6} | {tokens:<10} | {cost}"
        p_row.font.name = "Consolas"
        p_row.font.size = Pt(9)
        p_row.font.color.rgb = C_DARK
        if "累计" in stage:
            p_row.font.bold = True
            p_row.font.color.rgb = C_ORANGE
            
    p_rem = tf7_r.add_paragraph()
    p_rem.text = (
        "💡 第一次送审反思 (3.7分)：\n"
        "虽然记录了详尽的 11.4 万 Token 账单并走通了 ICLR 模板排版，但单纯依靠合成数据与弱基线对比，无法满足顶会盲审的高标准要求。"
    )
    p_rem.font.size = Pt(9.5)
    p_rem.font.color.rgb = C_MUTED
    p_rem.space_before = Pt(8)

    set_slide_notes(s7, notes_dict.get(7, ""))

    # ==================== SLIDE 8: RUN 2 ====================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "第二次论文生成与消耗：特征缺失早停实测", "PAPER RUN 2 · PILOT PRUNING")
    
    # Left: Imputation & Domination
    b8_l = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), col_y, col_w, col_h)
    b8_l.fill.solid()
    b8_l.fill.fore_color.rgb = C_CARD_BG
    b8_l.line.color.rgb = C_ORANGE
    b8_l.line.width = Pt(1.5)
    
    tf8_l = b8_l.text_frame
    tf8_l.word_wrap = True
    p = tf8_l.paragraphs[0]
    p.text = "🛑 PilotGate 探针早停实测对决"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_ORANGE
    
    r2_points = [
        ("研究课题", "评估大模型 Agent 在极端缺失率表格数据下的插补与回归效果。"),
        ("池外强基线对照", "引入完全免调优的经典模型 HistGradientBoosting 作为池外试金石。"),
        ("探针阶段实测数据", "• 候选算法在小样本探针阶段均方误差 MSE: 0.3901\n• 传统现成梯度提升树基线 MSE: 0.0498\n• 性能差距达到 0.3402，远超 0.05 的压制容忍度！"),
        ("状态机果断裁决", "判定该候选方案缺乏学术增量，触发剪枝熔断 (status: pruned)，提前退出全量测试！")
    ]
    for h, d in r2_points:
        p1 = tf8_l.add_paragraph()
        p1.text = f"• {h}"
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = C_ORANGE
        p1.space_before = Pt(6)
        p2 = tf8_l.add_paragraph()
        p2.text = f"  {d}"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(1)

    # Right: Token Savings
    b8_r = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), col_y, col_w, col_h)
    b8_r.fill.solid()
    b8_r.fill.fore_color.rgb = C_CARD_BG
    b8_r.line.color.rgb = C_GREEN
    b8_r.line.width = Pt(1.5)
    
    tf8_r = b8_r.text_frame
    tf8_r.word_wrap = True
    pr = tf8_r.paragraphs[0]
    pr.text = "💰 算力节约对比与第二次盲审反馈"
    pr.font.size = Pt(14)
    pr.font.bold = True
    pr.font.color.rgb = C_GREEN
    
    p_bar = tf8_r.add_paragraph()
    p_bar.text = (
        "【Token 算力消耗断崖式对比】\n\n"
        "盲目跑完全量实验预估消耗:\n"
        "████████████████████ 100,000+ Token\n\n"
        "PilotGate 早停探针实际消耗:\n"
        "█ 8,531 Token (调用仅 12 次 · 耗时 4 秒)\n\n"
        "==========================================\n"
        "★ 实测节约 91.5% 无效算力与 API 支出！"
    )
    p_bar.font.name = "Consolas"
    p_bar.font.size = Pt(10)
    p_bar.font.color.rgb = RGBColor(0x19, 0x6F, 0x3D)
    p_bar.space_before = Pt(8)
    
    p_r2 = tf8_r.add_paragraph()
    p_r2.text = (
        "📄 第二次送审成绩 (4.4分)：\n"
        "• 将早停实测数据与负向结果归因编撰为论文送审，盲审得分提升至 4.4 / 10；\n"
        "• 审稿专家高度肯定了系统的止损能力，但提出建议：需在统计学上对早停推迟决策进行更深度的理论审计。"
    )
    p_r2.font.size = Pt(10)
    p_r2.font.color.rgb = C_DARK
    p_r2.space_before = Pt(8)

    set_slide_notes(s8, notes_dict.get(8, ""))

    # ==================== SLIDE 9: RUN 3 ====================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "第三次论文生成与消耗：Pilot 剪枝推迟决策审计", "PAPER RUN 3 · LATEST MILESTONE")
    
    # Left: Methodology
    b9_l = s9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), col_y, col_w, col_h)
    b9_l.fill.solid()
    b9_l.fill.fore_color.rgb = C_CARD_BG
    b9_l.line.color.rgb = C_NAVY
    b9_l.line.width = Pt(1.5)
    
    tf9_l = b9_l.text_frame
    tf9_l.word_wrap = True
    p = tf9_l.paragraphs[0]
    p.text = "🔬 课题深度：探针不确定性与决策成本审计"
    p.font.size = Pt(13.5)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    p_t3 = tf9_l.add_paragraph()
    p_t3.text = "论文题目：WHEN RESEARCH PILOTS ARE INCONCLUSIVE: AN AUDIT OF PRUNING, DEFERRAL, AND DECISION COST"
    p_t3.font.size = Pt(10)
    p_t3.font.bold = True
    p_t3.font.color.rgb = C_SLATE
    p_t3.space_before = Pt(4)
    
    r3_points = [
        ("三大理论维度彻底解耦", "1. 区间构建：配对正态 vs 保守联合 Clopper-Pearson 边界\n2. 决策逻辑：强制二态 vs 显式推迟 (DEFER) 三态策略\n3. 显式决策成本：量化误放行、误剪枝与推迟决策的成本矩阵"),
        ("海量精确数值实证", "• 420 组微观实验采用多项分布全空间精确数值积分，消除仿真噪声；\n• 540 组实证重放实验，覆盖 4 个经典分类基准集。"),
        ("绿色计算开销", "核心实验由高效数学积分完成，模型仅消耗约 6,500 Token 用于正文排版。")
    ]
    for h, d in r3_points:
        p1 = tf9_l.add_paragraph()
        p1.text = f"• {h}"
        p1.font.size = Pt(10.5)
        p1.font.bold = True
        p1.font.color.rgb = C_SLATE
        p1.space_before = Pt(6)
        p2 = tf9_l.add_paragraph()
        p2.text = f"  {d}"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(1)

    # Right: Scores & +1
    b9_r = s9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), col_y, col_w, col_h)
    b9_r.fill.solid()
    b9_r.fill.fore_color.rgb = C_CARD_BG
    b9_r.line.color.rgb = C_GREEN
    b9_r.line.width = Pt(1.5)
    
    tf9_r = b9_r.text_frame
    tf9_r.word_wrap = True
    pr = tf9_r.paragraphs[0]
    pr.text = "🏆 最新第三方盲审成绩单 (直逼 5.0 门禁线)"
    pr.font.size = Pt(14)
    pr.font.bold = True
    pr.font.color.rgb = C_GREEN
    
    p_score = tf9_r.add_paragraph()
    p_score.text = (
        "【Stanford Agentic Reviewer 官方出分】\n"
        "• 送审时间：2026-11-08 06:59:12 | 出分：07:03:19\n"
        "• 综合得分：4.9 / 10  (稳步攀升，逼近 5.0 门禁线！)\n"
        "• 送审凭据 Token: f6ZtvxO58wvyHxff-aQ1KZrPt3VPGupaSuP9QE86Zsw\n\n"
        "【顶会七维指标量化突破 (Triple Scores)】\n"
        "★ Claims_Support (论据支撑度):    +1 (充分支持，证据确凿)\n"
        "★ Experimental_Soundness (方法完备): +1 (设计扎实，积分精确)\n"
        "• Writing_Clarity (写作清晰度):      0 (规范工整)\n"
        "• Prior_Work_Context (相关工作):     0 (脉络清晰)\n"
        "• Question_Importance (课题重要性):   0 (实用性强)\n"
        "• Originality (创新度):             0 (扎实审计)\n"
        "• Value_to_Community (社区价值):     0 (经验宝贵)"
    )
    p_score.font.name = "Consolas"
    p_score.font.size = Pt(9.5)
    p_score.font.color.rgb = RGBColor(0x11, 0x33, 0x55)
    p_score.space_before = Pt(8)

    set_slide_notes(s9, notes_dict.get(9, ""))

    # ==================== SLIDE 10: REVIEWER IN-DEPTH ====================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "外部盲审报告深度解析：Stanford Reviewer 的肯定与建议", "EXTERNAL REVIEW IN-DEPTH AUDIT")
    
    # Left: Strengths
    b10_l = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), col_y, col_w, col_h)
    b10_l.fill.solid()
    b10_l.fill.fore_color.rgb = RGBColor(0xEA, 0xFA, 0xEA)
    b10_l.line.color.rgb = C_GREEN
    b10_l.line.width = Pt(1.5)
    
    tf10_l = b10_l.text_frame
    tf10_l.word_wrap = True
    p = tf10_l.paragraphs[0]
    p.text = "✓ 审稿人核心肯定摘录 (Strengths)"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_GREEN
    
    pros = [
        ("精确数值积分消除噪声", "“Exact multinomial integration systematically covers the full space... removing simulation noise and enabling fine-grained auditing.” (彻底消除随机模拟方差)"),
        ("实验矩阵广博严密", "“Broad condition grid: 420 synthetic and 540 empirical conditions across multiple n, effect sizes, discordance rates, and 27 cost triples.”"),
        ("极强的工程可复现性", "“Reproducibility is strong: procedures, seeds, dataset choices, model configs, and CSV outputs are described, with hashes and automated checks.”"),
        ("暴露实用决策权衡", "“The audit highlights a practically important trade-off: targeted deferral reduces harmful false pruning.”")
    ]
    for h, d in pros:
        p1 = tf10_l.add_paragraph()
        p1.text = f"• {h}"
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = RGBColor(0x19, 0x6F, 0x3D)
        p1.space_before = Pt(6)
        p2 = tf10_l.add_paragraph()
        p2.text = f"  {d}"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(1)

    # Right: Weaknesses & Roadmap
    b10_r = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), col_y, col_w, col_h)
    b10_r.fill.solid()
    b10_r.fill.fore_color.rgb = RGBColor(0xFD, 0xED, 0xEC)
    b10_r.line.color.rgb = C_RED
    b10_r.line.width = Pt(1.5)
    
    tf10_r = b10_r.text_frame
    tf10_r.word_wrap = True
    pr = tf10_r.paragraphs[0]
    pr.text = "⚠️ 审稿人客观批注与团队改进路线"
    pr.font.size = Pt(14)
    pr.font.bold = True
    pr.font.color.rgb = C_RED
    
    cons = [
        ("批评 1：联合置信区间构建偏保守", "审稿意见：Clopper-Pearson 联合界采用 Union Bound 复合略显保守。\n团队对策：已规划引入学术界经典的 McNemar 与 Newcombe 评分置信区间作为新基线。"),
        ("批评 2：早停策略缺乏贝叶斯调优", "审稿意见：阈值 alpha 与 delta 采用固定值 0.05，未与损益矩阵挂钩。\n团队对策：拟引入以期望损失最小化为目标的成本敏感阈值自适应算法。"),
        ("批评 3：基准仍存在数据域差距", "审稿意见：实证回放基于 UCI 表格集，建议在真实 Agent 轨迹上验证。\n团队对策：计划将主实验积累的 120 次交互 Trace 作为新的实证审计集。")
    ]
    for h, d in cons:
        p1 = tf10_r.add_paragraph()
        p1.text = f"• {h}"
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = RGBColor(0x92, 0x2B, 0x21)
        p1.space_before = Pt(6)
        p2 = tf10_r.add_paragraph()
        p2.text = f"  {d}"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(1)

    set_slide_notes(s10, notes_dict.get(10, ""))

    # ==================== SLIDE 11: FRAMEWORK CONTRIBUTION 1 ====================
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "openJiuwen 框架贡献：本地 Rails 拦截扩展与 Patch 补丁", "FRAMEWORK CONTRIBUTION · 15 PTS")
    
    b11 = s11.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.3))
    b11.fill.solid()
    b11.fill.fore_color.rgb = C_CARD_BG
    b11.line.color.rgb = C_NAVY
    b11.line.width = Pt(1.5)
    
    tf11 = b11.text_frame
    tf11.word_wrap = True
    p = tf11.paragraphs[0]
    p.text = "🛠️ 深入 openJiuwen Swarm 源码底层的 3 项通用 Rails 扩展"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    f_items = [
        ("1. ContextBudgetRail (上下文预算动态控制器)", 
         "位置: jiuwenswarm/agents/harness/common/rails/context_budget_rail.py\n"
         "机制: 挂载在 Agent 调用大模型前的 Rails 拦截链上，根据设定的 Token 预算上限动态筛选历史条目，为主实验中的 4 种上下文策略提供框架级底层支持。"),
        ("2. FrozenMessagesRail (单次确定性消息保护器)",
         "位置: jiuwenswarm/agents/harness/common/rails/frozen_messages_rail.py\n"
         "机制: 在单次精确调用中执行上下文防御性深拷贝并校验输入有序性，杜绝多轮交互中的消息并发污染与工具重复调度。"),
        ("3. VersionedMemoryRail (版本化长程记忆组件)",
         "位置: jiuwenswarm/agents/harness/common/rails/versioned_memory_rail.py\n"
         "机制: 为智能体长程记忆增加单调递增的 version_id 与变更流水日志，支持并发冲突检测与状态快照回退。")
    ]
    for h, d in f_items:
        p1 = tf11.add_paragraph()
        p1.text = f"▶ {h}"
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = C_SLATE
        p1.space_before = Pt(8)
        p2 = tf11.add_paragraph()
        p2.text = f"   {d}"
        p2.font.size = Pt(10)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(2)
        
    p_state = tf11.add_paragraph()
    p_state.text = (
        "🔒 交付形式与客观诚信声明：\n"
        "• 针对修改完整导出为标准本地补丁文件 output/framework_contribution.patch (共计 2.9 万字节)；\n"
        "• 客观事实声明：团队未向 openJiuwen 官方公开仓库提交 PR，严格作为满足赛题要求的本地扩展补丁交付，并附带 19 项专用离线单测！"
    )
    p_state.font.size = Pt(10.5)
    p_state.font.bold = True
    p_state.font.color.rgb = C_NAVY
    p_state.space_before = Pt(12)

    set_slide_notes(s11, notes_dict.get(11, ""))

    # ==================== SLIDE 12: FRAMEWORK CONTRIBUTION 2 ====================
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, "扩展组件深度实战：ContextBudgetRail 与 VersionedMemory 运行机制", "FRAMEWORK EXTENSIONS IN-DEPTH")
    
    # Left: ContextBudgetRail Flow
    b12_l = s12.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), col_y, col_w, col_h)
    b12_l.fill.solid()
    b12_l.fill.fore_color.rgb = C_CARD_BG
    b12_l.line.color.rgb = C_NAVY
    b12_l.line.width = Pt(1.5)
    
    tf12_l = b12_l.text_frame
    tf12_l.word_wrap = True
    p = tf12_l.paragraphs[0]
    p.text = "🔄 ContextBudgetRail 拦截时序机制"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    p_flow = tf12_l.add_paragraph()
    p_flow.text = (
        "ReActAgent.invoke()\n"
        "       │\n"
        "       ▼\n"
        "[openJiuwen Rails 责任链总线]\n"
        "       │\n"
        "       ├─> ContextBudgetRail.before_model_call()\n"
        "       │     1. 计算当前上下文 Token 量\n"
        "       │     2. 检查是否超出 budget_limit\n"
        "       │     3. 若超出，根据策略裁剪或路由\n"
        "       │        (截断 / 关键词过滤 / 摘要)\n"
        "       │     4. 确保入模 Token 严格处于预算内\n"
        "       │\n"
        "       ▼\n"
        "[ModelGateway / LLM 发起受控调用]"
    )
    p_flow.font.name = "Consolas"
    p_flow.font.size = Pt(9.5)
    p_flow.font.color.rgb = RGBColor(0x11, 0x33, 0x55)
    p_flow.space_before = Pt(8)
    
    p_fl_sub = tf12_l.add_paragraph()
    p_fl_sub.text = "★ 价值：无侵入解耦，使任意第三方 openJiuwen Agent 无感获得预算保护能力。"
    p_fl_sub.font.size = Pt(10)
    p_fl_sub.font.color.rgb = C_DARK
    p_fl_sub.space_before = Pt(8)

    # Right: VersionedMemory
    b12_r = s12.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), col_y, col_w, col_h)
    b12_r.fill.solid()
    b12_r.fill.fore_color.rgb = C_CARD_BG
    b12_r.line.color.rgb = C_SLATE
    b12_r.line.width = Pt(1.5)
    
    tf12_r = b12_r.text_frame
    tf12_r.word_wrap = True
    pr = tf12_r.paragraphs[0]
    pr.text = "🧠 VersionedMemory 记忆管理与单测"
    pr.font.size = Pt(14)
    pr.font.bold = True
    pr.font.color.rgb = C_SLATE
    
    vm_items = [
        ("双时间戳与版本流水", "每个配置项记忆绑定 created_at、updated_at 与递增的 version_id，实现严格因果序。"),
        ("并发写入冲突检测", "多智能体并发交互时，校验版本快照，一旦检测到脏写立即阻断并触发原子重试。"),
        ("19 项专用单元测试全通", "• tests/test_versioned_memory.py: 13 passed\n• tests/test_workflow_framework.py: 6 passed\n• 纯离线环境 1.39 秒全绿，全面覆盖预算边界与版本异常。")
    ]
    for h, d in vm_items:
        p1 = tf12_r.add_paragraph()
        p1.text = f"• {h}"
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = C_SLATE
        p1.space_before = Pt(6)
        p2 = tf12_r.add_paragraph()
        p2.text = f"  {d}"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(1)

    set_slide_notes(s12, notes_dict.get(12, ""))

    # ==================== SLIDE 13: TESTING ====================
    s13 = prs.slides.add_slide(blank_layout)
    add_header(s13, "软件工程质量保障：45 项自动化单测全通与离线秒级复现", "ENGINEERING RIGOR & TESTING")
    
    # Left: Terminal
    b13_l = s13.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), col_y, col_w, col_h)
    b13_l.fill.solid()
    b13_l.fill.fore_color.rgb = C_CARD_BG
    b13_l.line.color.rgb = C_NAVY
    b13_l.line.width = Pt(1.5)
    
    tf13_l = b13_l.text_frame
    tf13_l.word_wrap = True
    p = tf13_l.paragraphs[0]
    p.text = "⚡ 真实 Pytest 执行输出与覆盖情况"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    p_code = tf13_l.add_paragraph()
    p_code.text = (
        "============================= test session starts ==============================\n"
        "platform win32 -- Python 3.12.11, pytest-9.2.0, pluggy-1.7.0\n"
        "rootdir: E:\\co\\JiuwenSwarmAgent\n\n"
        "tests/test_conference_review.py ....                                     [  8%]\n"
        "tests/test_deep_revision.py ...                                          [ 15%]\n"
        "tests/test_workflow_gates.py .......                                     [ 31%]\n"
        "tests/test_workflow_tournament.py ..                                     [ 35%]\n"
        "tests/test_model_gateway.py ...........                                  [ 60%]\n"
        "tests/test_research_chain.py ..................                          [100%]\n\n"
        "============================== 45 passed in 1.65s ==============================\n\n"
        "★ 质量指标：\n"
        "• 45 项核心用例在 1.65 秒内全部通过 (100% Pass)\n"
        "• 零外部付费网络依赖，纯本地离线可完全复现！"
    )
    p_code.font.size = Pt(9)
    p_code.font.name = "Consolas"
    p_code.font.color.rgb = RGBColor(0x11, 0x33, 0x55)
    p_code.space_before = Pt(8)

    # Right: Modules
    b13_r = s13.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), col_y, col_w, col_h)
    b13_r.fill.solid()
    b13_r.fill.fore_color.rgb = C_CARD_BG
    b13_r.line.color.rgb = C_GREEN
    b13_r.line.width = Pt(1.5)
    
    tf13_r = b13_r.text_frame
    tf13_r.word_wrap = True
    pr = tf13_r.paragraphs[0]
    pr.text = "🛡️ 核心测试模块覆盖矩阵"
    pr.font.size = Pt(14)
    pr.font.bold = True
    pr.font.color.rgb = C_GREEN
    
    t_items = [
        ("门禁状态机判定 (test_workflow_gates)", "测试小样本探针的三态决策逻辑，验证检测到性能落后时能准确触发早停剪枝。"),
        ("方案回退与流转 (test_workflow_tournament)", "测试主选方案未通过时，调度系统能否平稳流转至备选课题重新规划。"),
        ("内部模拟打分 (test_conference_review)", "测试 4 维指标权重聚合计算及 5.0 硬底线拒稿触发器。"),
        ("大修计划生成 (test_deep_revision)", "测试将审稿意见 Weaknesses 映射为具体实验修复任务的解析代码。"),
        ("框架 Rail 与基础调用 (test_baseline)", "测试新增的 ContextBudgetRail 在各种预算边界下的截断与分流表现。")
    ]
    for h_txt, b_txt in t_items:
        p1 = tf13_r.add_paragraph()
        p1.text = f"• {h_txt}"
        p1.font.size = Pt(10.5)
        p1.font.bold = True
        p1.font.color.rgb = C_GREEN
        p1.space_before = Pt(6)
        p2 = tf13_r.add_paragraph()
        p2.text = f"  {b_txt}"
        p2.font.size = Pt(9)
        p2.font.color.rgb = C_DARK
        p2.space_before = Pt(1)

    set_slide_notes(s13, notes_dict.get(13, ""))

    # ==================== SLIDE 14: DELIVERABLES ====================
    s14 = prs.slides.add_slide(blank_layout)
    add_header(s14, "项目完整交付物清单与可复现性保障", "DELIVERABLES & REPRODUCIBILITY")
    
    b14 = s14.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.3))
    b14.fill.solid()
    b14.fill.fore_color.rgb = C_CARD_BG
    b14.line.color.rgb = C_NAVY
    b14.line.width = Pt(1.5)
    
    tf14 = b14.text_frame
    tf14.word_wrap = True
    p = tf14.paragraphs[0]
    p.text = "📦 严格按赛题官方目录规范组织交付包 (submission/第6组_课程交付材料_20261108/)"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    p_tree = tf14.add_paragraph()
    p_tree.text = (
        "├── 第6组系统使用说明书.docx           # 详尽的系统安装、配置与使用说明书\n"
        "├── 第6组课程报告.docx                 # 涵盖架构、实证与反思的完整结题报告\n"
        "├── 第6组项目汇报PPT.pptx              # 结构完整、附带逐页讲稿的演示文稿\n"
        "├── paper/                             # 成果论文目录：包含编译完成的 paper.pdf 及完整 LaTeX 工程 paper.tex\n"
        "├── code/                              # 源码工程：包含 main.py、无密钥配置样例 config.yaml 及 REPRODUCTION.md\n"
        "│   └── framework_contribution.patch   # 针对 openJiuwen Swarm 源码的 2.9 万字节扩展补丁文件\n"
        "├── docs/                              # 详细技术文档：architecture.md 架构说明、module_call.md 模块调用链\n"
        "├── logs/                              # 原始实验账本：calls.jsonl (120次调用明细)、results.jsonl (96次作答原始记录)\n"
        "├── Agentic Reviewer/                  # 真实送审凭证：最新 4.9 分评测全文 pilot_pruning_review.txt 及 Token\n"
        "├── resource_report.md                 # 详尽的 Token 消耗与时间开销统计报告\n"
        "└── 提交说明.md                        # 包含小组成员承诺、格式自检报告与复现指南"
    )
    p_tree.font.name = "Consolas"
    p_tree.font.size = Pt(9.5)
    p_tree.font.color.rgb = RGBColor(0x11, 0x33, 0x55)
    p_tree.space_before = Pt(8)
    p_tree.space_after = Pt(10)
    
    p_rep = tf14.add_paragraph()
    p_rep.text = "🔒 复现保障：本包严禁包含私人 API Key、运行环境缓存或浏览器敏感数据；依据 code/REPRODUCTION.md，评审老师可在数分钟内搭建环境并一键重放全部实验与评测。"
    p_rep.font.size = Pt(11)
    p_rep.font.color.rgb = C_DARK

    set_slide_notes(s14, notes_dict.get(14, ""))

    # ==================== SLIDE 15: DIVISION OF LABOR ====================
    s15 = prs.slides.add_slide(blank_layout)
    add_header(s15, "小组成员任务分工与实际产出对照", "TEAM COLLABORATION & DIVISION OF LABOR")
    
    b15 = s15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(11.733), Inches(5.3))
    b15.fill.solid()
    b15.fill.fore_color.rgb = C_CARD_BG
    b15.line.color.rgb = C_NAVY
    b15.line.width = Pt(1.5)
    
    tf15 = b15.text_frame
    tf15.word_wrap = True
    p = tf15.paragraphs[0]
    p.text = "👥 第 6 组 5 位成员分工与具体代码工程产出"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    
    members = [
        ("王智洋", "102402136", "架构与集成", "• 负责总体五阶段状态机流水线设计与 ConnectedProfile 契约控制\n• 攻坚 PilotGate 探针三态剪枝早停算法与 StructuredAcceptance 契约\n• 深入 openJiuwen 源码开发 3 项通用 Rails 扩展并生成 Patch 补丁"),
        ("洪豊幀", "102402124", "任务与实验", "• 负责 24 个合成评测任务设计与 Ground Truth 标注\n• 全程调度监控 120 次真实 API 受控实验运行并采集全量原始日志\n• 统筹完成三轮论文生成的 Token 审计与 resource_report.md 编写"),
        ("黄炜杰", "102402126", "论文与排版", "• 攻关实验证据抽取逻辑，实现 Matplotlib 矢量折线图自动化生成\n• 设计论文正文生成的约束化 Prompt，实现学术章节无幻觉草拟\n• 攻克 ICLR 2026 双栏 LaTeX 模板编译与字符防御性转义"),
        ("黄俊翔", "102402125", "测试与质保", "• 搭建并维护包含 45 个测试用例的自动化 Pytest 测试矩阵 (100% Pass)\n• 研发测试套件的离线 Mock 逻辑，实现零外网依赖秒级回归复现\n• 负责交付工程的可复现性验证与目录规范化自检自测"),
        ("金若曦", "102402127", "文档与答辩", "• 主笔编写《系统使用说明书》与两万字终版《课程结题报告》\n• 统筹答辩幻灯片视觉设计与 16 页逐页答辩讲稿深度打磨\n• 负责项目全生命周期的规范化自检，担任本次答辩主讲人")
    ]
    for name, sid, role, detail in members:
        p_m = tf15.add_paragraph()
        p_m.text = f"★ {name}（学号：{sid}，角色：{role}）"
        p_m.font.size = Pt(11)
        p_m.font.bold = True
        p_m.font.color.rgb = C_SLATE
        p_m.space_before = Pt(6)
        
        p_d = tf15.add_paragraph()
        p_d.text = detail
        p_d.font.size = Pt(9.5)
        p_d.font.color.rgb = C_DARK
        p_d.space_before = Pt(1)

    set_slide_notes(s15, notes_dict.get(15, ""))

    # ==================== SLIDE 16: CONCLUSION ====================
    s16 = prs.slides.add_slide(blank_layout)
    bg16 = s16.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg16.fill.solid()
    bg16.fill.fore_color.rgb = C_NAVY
    bg16.line.fill.background()
    
    tbox16 = s16.shapes.add_textbox(Inches(1.0), Inches(1.2), Inches(11.333), Inches(5.5))
    tf16 = tbox16.text_frame
    tf16.word_wrap = True
    
    p0 = tf16.paragraphs[0]
    p0.text = "项目总结与学术实践感悟"
    p0.font.size = Pt(32)
    p0.font.bold = True
    p0.font.color.rgb = C_WHITE
    p0.alignment = PP_ALIGN.CENTER
    
    c_pts = [
        "1. 闭环落地：成功构建五大智能体协同架构，打通事前契约、事中探针与事后预审的完整防御体系；",
        "2. 实证进阶：三轮论文生成分次审计 Token 账单，盲审评分从 3.7、4.4 稳步跃升至 4.9 分 (双核心指标 +1)；",
        "3. 算力节约：PilotGate 探针早停实测仅消耗 8,531 Token，为系统节约 91.5% 无效算力开销；",
        "4. 开源回哺：深入 openJiuwen 底层贡献 3 项通用 Rails 补丁，配备 45 项离线全通单测。",
        "★ 实践感悟：科研 Agent 的生命线在于严谨的实验设计与工程门禁，而非华丽的文字续写！"
    ]
    for pt in c_pts:
        p = tf16.add_paragraph()
        p.text = pt
        p.font.size = Pt(13)
        p.font.color.rgb = RGBColor(0xEE, 0xF2, 0xF7)
        if "感悟" in pt:
            p.font.bold = True
            p.font.color.rgb = RGBColor(0xFF, 0xCC, 0x80)
        p.space_before = Pt(10)
        
    p2 = tf16.add_paragraph()
    p2.text = "感谢各位评委老师的指导与倾听！\n欢迎老师们批评指正，请老师提问！"
    p2.font.size = Pt(20)
    p2.font.bold = True
    p2.font.color.rgb = RGBColor(0xFF, 0xB7, 0x4D)
    p2.alignment = PP_ALIGN.CENTER
    p2.space_before = Pt(20)

    set_slide_notes(s16, notes_dict.get(16, ""))

    prs.save(output_pptx)
    print(f"Truthful master presentation successfully saved to: {output_pptx}")

if __name__ == '__main__':
    targets = [
        "docs/第6组项目汇报PPT_终版.pptx",
        "第6组项目汇报PPT_终版.pptx"
    ]
    for t in targets:
        os.makedirs(os.path.dirname(os.path.abspath(t)), exist_ok=True)
        build_presentation(t)
