import pptx
import re
import sys

pptx_path = "runtime/test_out.pptx"
prs = pptx.Presentation(pptx_path)

banned_words = [
    "自研写作引擎", "自主学术写作引擎", "对标 ICLR", "对标ICLR",
    "首创", "已提交PR", "已提交 PR", "战队", "空梦轮年"
]

all_text = ""
for idx, slide in enumerate(prs.slides):
    slide_text = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            slide_text.append(shape.text_frame.text)
        elif shape.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.GROUP:
            for child in shape.shapes:
                if child.has_text_frame:
                    slide_text.append(child.text_frame.text)
    
    notes_text = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
    combined = "\n".join(slide_text) + "\n" + notes_text
    all_text += combined + "\n"
    
    print(f"--- Slide {idx+1:02d} ---")
    print(f"Slide shapes text chars: {sum(len(t) for t in slide_text)}")
    print(f"Notes text chars: {len(notes_text)}")
    
found_banned = []
for b in banned_words:
    if b in all_text:
        found_banned.append(b)

print("\n" + "="*50)
if found_banned:
    print(f"FAILED: Found banned words: {found_banned}")
    sys.exit(1)
else:
    print("PASSED: Zero banned words detected!")

# Check team members
members = ["金若曦", "洪豊幀", "黄炜杰", "黄俊翔", "王智洋"]
missing = [m for m in members if m not in all_text]
if missing:
    print(f"FAILED: Missing team members: {missing}")
    sys.exit(1)
else:
    print("PASSED: All 5 team members present!")

# Check key scores
scores = ["3.7", "4.4", "4.9"]
missing_scores = [s for s in scores if s not in all_text]
if missing_scores:
    print(f"FAILED: Missing scores: {missing_scores}")
    sys.exit(1)
else:
    print("PASSED: All three empirical scores (3.7, 4.4, 4.9) present!")

print("="*50)
